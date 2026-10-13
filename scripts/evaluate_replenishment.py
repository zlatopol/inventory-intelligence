"""Бэктест инвентаризационной политики: fill rate и средний запас (EX-2, Q5).

Превращает MAE в бизнес-исход: симуляция периодического обзора (review = H)
на истории Kaggle — заказы приходят через L, спрос ест виртуальный сток.

Протокол (блочный, как evaluate_horizon.py):
- якоря T: каждый H-й день последнего года датасета; знание замораживается
  (история строго < T — граница утечки = момент решения);
- в якорь: рекурсивный прогноз на окно W = L+H (ВСЕ пары сразу, LightGBM
  retrain/28d), агрегация по магазинам → F на товар; σ = std дневного
  агрегированного факта за 28 дней до T (та же Q4, что в сервисе);
- Q = policy.order_quantity — ТА ЖЕ формула, что в проде (одна реализация);
- заказ прибывает в T+L (утром, до спроса дня), спрос дня снижает сток,
  необслуженный спрос фиксируется (клиент ушёл);
- начальный сток = ceil(средний дневной спрос × W) по 28 дням ДО первого
  якоря — из замороженной истории, одинаков для всех политик.

Гипотезы (зарегистрированы ДО прогона, 2026-10-13):
- H7a: order_up_to SL=0.95 даёт fill rate ≥ 0.90;
- H7b: naive (без страхового запаса) даёт fill rate ≤ 0.70 (прогноз
  занижается в половине дней → стокауты);
- H7c: средний запас order_up_to ≤ 1.5 × naive (SS пропорционален z·σ·√W,
  не масштабирует запасы в разы).

Измеряем fill rate (доля обслуженного спроса), а не cycle service level:
симуляция естественнее его считает; z-формула нацелена на CSL — сравнение
с 0.95 честно С ОГОВОРКОЙ (это разные величины).

Запуск: .venv/bin/python scripts/evaluate_replenishment.py [max_pairs] [lead] [horizon]
  default: 50 пар, L=3, H=7. Политики: naive / order_up_to_95 / order_up_to_99.
Вывод: таблица, график docs/img/replenishment_policies.png, MLflow.
"""
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # без экрана: только файлы
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from app.ml.baseline import recursive_forecast  # noqa: E402
from app.ml.model import LightGBMModel  # noqa: E402
from app.ml.sources import load_from_kaggle_csv  # noqa: E402
from app.ml.tracking import log_evaluation  # noqa: E402
from app.recommendations.policy import (  # noqa: E402
    SIGMA_WINDOW_DAYS,
    order_quantity,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"
OUT = Path(__file__).resolve().parents[1] / "docs" / "img"


def aggregate_daily(dataset: pd.DataFrame) -> pd.Series:
    """Спрос товара по дням, суммированный по магазинам (индекс product, date)."""
    return dataset.groupby(["product_id", "date"])["demand"].sum()


def build_anchors(dataset: pd.DataFrame, horizon: int) -> list[pd.Timestamp]:
    """Якоря последнего года с шагом H; последний якорь + H ≤ конец данных."""
    dates = pd.Series(dataset["date"].unique())
    last_year = dates.dt.year.max()
    year_days = dates[dates.dt.year == last_year]
    end = year_days.max() - pd.Timedelta(days=horizon)
    return list(pd.date_range(year_days.min(), end, freq=f"{horizon}D"))


def simulate(dataset, daily, anchors, lead, horizon, policies):
    """Симуляция периодического обзора; возвращает метрики по политикам.

    Сток учитывается ПОСЛЕ событий дня (прибытие утром, спрос днём).
    """
    products = sorted(dataset["product_id"].unique())
    window = lead + horizon
    model = LightGBMModel(retrain_every=28)

    # начальный сток: замороженное среднее × окно (одинаково у всех политик)
    first_anchor = anchors[0]
    warmup = daily[
        daily.index.get_level_values("date") < first_anchor
    ].groupby("product_id").tail(SIGMA_WINDOW_DAYS)
    mean_demand = warmup.groupby("product_id").mean()

    stats = {
        name: {
            "stock": {p: math.ceil(mean_demand[p] * window) for p in products},
            "arrivals": {},  # день прибытия → {product: qty}
            "served": 0.0,
            "demanded": 0.0,
            "stock_sum": 0.0,
            "stock_days": 0,
            "stockout_days": 0,
        }
        for name, _ in policies
    }

    for i, anchor in enumerate(anchors):
        history = dataset[dataset["date"] < anchor]
        days_ahead = recursive_forecast(history, model.forecast, days=window)
        # F на товар: сумма прогноза по магазинам и дням окна
        forecast_demand = days_ahead.groupby("product_id")["prediction"].sum()
        # σ на товар: std агрегированного факта за 28 дней до якоря
        recent = daily[
            (daily.index.get_level_values("date") >= anchor
             - pd.Timedelta(days=SIGMA_WINDOW_DAYS))
            & (daily.index.get_level_values("date") < anchor)
        ].groupby("product_id").std()

        for name, service_level in policies:
            state = stats[name]
            for product in products:
                sigma = recent.get(product, 0.0)
                sigma = 0.0 if math.isnan(sigma) else float(sigma)
                qty = order_quantity(
                    float(forecast_demand.get(product, 0.0)),
                    state["stock"][product],
                    sigma,
                    window,
                    service_level,
                )
                if qty > 0:
                    arrival_day = anchor + pd.Timedelta(days=lead)
                    slot = state["arrivals"].setdefault(arrival_day, {})
                    slot[product] = slot.get(product, 0) + qty

            # дни до следующего якоря (последний якорь добирает до конца окна)
            next_anchor = (
                anchors[i + 1] if i + 1 < len(anchors)
                else anchor + pd.Timedelta(days=horizon)
            )
            for day in pd.date_range(anchor, next_anchor - pd.Timedelta(days=1)):
                arrivals_today = state["arrivals"].pop(day, {})
                for product in products:
                    state["stock"][product] += arrivals_today.get(product, 0)
                try:
                    day_demand = daily.xs(day, level="date")
                except KeyError:
                    continue
                for product, demand in day_demand.items():
                    before = state["stock"][product]
                    served = min(before, demand)
                    state["stock"][product] = before - served
                    state["served"] += served
                    state["demanded"] += demand
                    state["stock_sum"] += state["stock"][product]
                    state["stock_days"] += 1
                    if served < demand:
                        state["stockout_days"] += 1

    metrics = {}
    for name, _ in policies:
        s = stats[name]
        metrics[name] = {
            "fill_rate": s["served"] / s["demanded"],
            "avg_stock": s["stock_sum"] / s["stock_days"],
            "stockout_day_rate": s["stockout_days"] / s["stock_days"],
        }
    return metrics


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    lead = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    horizon = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    window = lead + horizon

    dataset = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    daily = aggregate_daily(dataset)
    anchors = build_anchors(dataset, horizon)
    print(
        f"Датасет: {len(dataset)} строк ({max_pairs} пар), "
        f"{dataset['date'].min().date()} → {dataset['date'].max().date()}; "
        f"якорей: {len(anchors)} (обзор каждые {horizon} дн.), L={lead}, W={window}"
    )

    policies = [
        ("naive", 0.50),          # SS=0: z(0.5)=0 — заказ ровно по прогнозу
        ("order_up_to_95", 0.95),
        ("order_up_to_99", 0.99),
    ]
    metrics = simulate(dataset, daily, anchors, lead, horizon, policies)

    print(f"\n{'policy':<16} {'fill_rate':>10} {'avg_stock':>10} {'stockout_days':>14}")
    for name, _ in policies:
        m = metrics[name]
        print(
            f"{name:<16} {m['fill_rate']:>10.4f} {m['avg_stock']:>10.1f} "
            f"{m['stockout_day_rate']:>14.4f}"
        )

    # проверка зарегистрированных гипотез
    naive, up95, up99 = metrics["naive"], metrics["order_up_to_95"], metrics["order_up_to_99"]
    print("\nГипотезы (зарегистрированы до прогона):")
    print(f"  H7a fill_rate(95) ≥ 0.90: {up95['fill_rate']:.4f} → "
          f"{'ПОДТВЕРЖДЕНА' if up95['fill_rate'] >= 0.90 else 'ОПРОВЕРГНУТА'}")
    print(f"  H7b fill_rate(naive) ≤ 0.70: {naive['fill_rate']:.4f} → "
          f"{'ПОДТВЕРЖДЕНА' if naive['fill_rate'] <= 0.70 else 'ОПРОВЕРГНУТА'}")
    print(f"  H7c avg_stock(95) ≤ 1.5×naive: {up95['avg_stock'] / naive['avg_stock']:.2f}× → "
          f"{'ПОДТВЕРЖДЕНА' if up95['avg_stock'] <= 1.5 * naive['avg_stock'] else 'ОПРОВЕРГНУТА'}")

    # --- график: цена уровня сервиса --------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    names = [name for name, _ in policies]
    fr = [metrics[n]["fill_rate"] * 100 for n in names]
    st = [metrics[n]["avg_stock"] for n in names]
    colors = ["#c0504d", "#4f81bd", "#9bbb59"]

    ax1.bar(names, fr, color=colors)
    ax1.axhline(95, color="gray", linewidth=1, linestyle=":", alpha=0.7)
    ax1.set_title("Fill rate (доля обслуженного спроса)")
    ax1.set_ylabel("%")
    ax1.set_ylim(min(fr) - 5, 100)
    ax1.tick_params(axis="x", rotation=15)
    for i, v in enumerate(fr):
        ax1.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)

    ax2.bar(names, st, color=colors)
    ax2.set_title(f"Средний запас на товар (L={lead}, H={horizon})")
    ax2.set_ylabel("шт.")
    ax2.tick_params(axis="x", rotation=15)
    for i, v in enumerate(st):
        ax2.text(i, v + max(st) * 0.01, f"{v:.0f}", ha="center", fontsize=9)

    fig.suptitle("Компромисс «уровень сервиса ↔ замороженный запас» (бэктест)")
    fig.tight_layout()
    fig.savefig(OUT / "replenishment_policies.png", dpi=150)
    plt.close(fig)
    print(f"\nСохранено: {OUT / 'replenishment_policies.png'}")

    # --- MLflow: по одной записи на политику --------------------------------
    for name, service_level in policies:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, prefix="replenishment_"
        ) as tmp:
            pd.DataFrame(
                {
                    "policy": [name],
                    "fill_rate": [metrics[name]["fill_rate"]],
                    "avg_stock": [metrics[name]["avg_stock"]],
                    "stockout_day_rate": [metrics[name]["stockout_day_rate"]],
                }
            ).to_csv(tmp.name, index=False)
            log_evaluation(
                model_name=name,
                params={
                    "source": "kaggle/store-item-demand",
                    "protocol": "replenishment_backtest",
                    "max_pairs": max_pairs,
                    "lead_time_days": lead,
                    "horizon_days": horizon,
                    "review_days": horizon,
                    "window": window,
                    "service_level": service_level,
                    "sigma_window": SIGMA_WINDOW_DAYS,
                    "anchors": len(anchors),
                },
                metrics=metrics[name],
                predictions_csv=Path(tmp.name),
            )


if __name__ == "__main__":
    main()
