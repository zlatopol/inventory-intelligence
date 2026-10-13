"""Блочная оценка рекурсивного горизонта: деградация качества по k = 1..14.

Симулирует обещание сервиса «прогноз на 1–14 дней»: в якорный день T знание
замораживается (история строго < T), модель уходит рекурсивно на 14 дней
(её же прогнозы кормят лаги), каждый день сверяется с фактом.

Запуск: .venv/bin/python scripts/evaluate_horizon.py [max_pairs] [step]
  max_pairs — пар (default 50); step — шаг якорей в днях (default 2).
  Якоря: весь последний год датасета, отступ 14 дней от конца
  (каждому якорю нужен фактический горизонт для сверки).

Гипотезы (зарегистрированы ДО прогона, 2026-10-12):
- H6a: MAE растёт с k медленно до 7, после 8 быстрее — lag_7 для k>7
  становится собственным прогнозом (потеря контакта с реальностью);
- H6b: рекурсивный seasonal_naive почти плоский (недельный паттерн
  заморожен, гнить нечему);
- H6c: отрыв модели от бейзлайнов сужается к хвосту, но не исчезает
  (календарь и уровень пары остаются настоящими).

Вывод: таблица MAE по k (модель / seasonal_naive / moving_average),
график docs/img/horizon_degradation.png, прогон в MLflow.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # без экрана: только файлы
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from app.ml.baseline import (  # noqa: E402
    blocked_horizon_evaluate,
    moving_average_forecast,
    seasonal_naive_forecast,
)
from app.ml.metrics import mae, wape  # noqa: E402
from app.ml.model import LightGBMModel  # noqa: E402
from app.ml.sources import load_from_kaggle_csv  # noqa: E402
from app.ml.tracking import log_evaluation  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"
OUT = Path(__file__).resolve().parents[1] / "docs" / "img"

HORIZON = 14
WARMUP = 8  # как в evaluate_model.py: lag_7 выкалывает 7 первых дней пары


def build_anchors(dataset: pd.DataFrame, step: int) -> list[pd.Timestamp]:
    """Якоря последнего года: [последний день года − HORIZON, 1 января], шаг step."""
    dates = pd.Series(dataset["date"].unique())
    last_year = dates.dt.year.max()
    year_days = dates[dates.dt.year == last_year]
    end = year_days.max() - pd.Timedelta(days=HORIZON)  # факту нужен горизонт
    anchors = pd.date_range(year_days.min(), end, freq=f"{step}D")
    return list(anchors)


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    dataset = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    anchors = build_anchors(dataset, step)
    print(
        f"Датасет: {len(dataset)} строк ({max_pairs} пар), "
        f"{dataset['date'].min().date()} → {dataset['date'].max().date()}; "
        f"якорей: {len(anchors)} (шаг {step})"
    )

    models = {
        "lightgbm": LightGBMModel(retrain_every=28).forecast,
        "seasonal_naive_7": seasonal_naive_forecast,
        "moving_average_7": moving_average_forecast,
    }

    results = {}
    for name, forecast_next in models.items():
        result = blocked_horizon_evaluate(dataset, forecast_next, anchors, HORIZON)
        # у модели первые WARMUP дней пары могут дать NaN — честно исключаем
        # одинаковые дни для всех участников сравнения
        results[name] = result.dropna(subset=["actual", "prediction"])

    # --- таблица по горизонтам -------------------------------------------
    print(f"\n{'k':>3} {'lightgbm':>10} {'snaive7':>10} {'ma7':>10}")
    table_rows = []
    for k in range(1, HORIZON + 1):
        row = {"k": k}
        for name, result in results.items():
            slice_k = result[result["k"] == k]
            row[name] = mae(slice_k["actual"], slice_k["prediction"])
        table_rows.append(row)
        print(
            f"{k:>3} {row['lightgbm']:>10.2f} "
            f"{row['seasonal_naive_7']:>10.2f} {row['moving_average_7']:>10.2f}"
        )

    # итоговые метрики по ВСЕМУ горизонту (одна строка в MLflow)
    overall = {
        name: {
            "mae": mae(r["actual"], r["prediction"]),
            "wape": wape(r["actual"], r["prediction"]),
        }
        for name, r in results.items()
    }
    for name, m in overall.items():
        print(f"{name:<18} MAE={m['mae']:.2f}  WAPE={m['wape']:.1f}%")

    # --- график ------------------------------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    metrics_table = pd.DataFrame(table_rows)
    for name in models:
        ax.plot(
            metrics_table["k"], metrics_table[name], marker="o", label=name
        )
    ax.axvline(7.5, color="gray", linewidth=1, linestyle=":", alpha=0.7)
    ax.annotate("k=8: lag_7 теряет контакт с фактом", xy=(8, metrics_table["lightgbm"].iloc[7]),
                xytext=(9, metrics_table["lightgbm"].iloc[7] * 1.15),
                fontsize=9, color="gray")
    ax.set_title(f"Деградация качества по горизонту (якорей {len(anchors)}, шаг {step})")
    ax.set_xlabel("k — дней от якоря")
    ax.set_ylabel("MAE, шт.")
    ax.set_xticks(range(1, HORIZON + 1))
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "horizon_degradation.png", dpi=150)
    plt.close(fig)
    print(f"\nСохранено: {OUT / 'horizon_degradation.png'}")

    # --- MLflow: по одной записи на модель ---------------------------------
    for name, result in results.items():
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, prefix="horizon_"
        ) as tmp:
            result.to_csv(tmp.name, index=False)
            log_evaluation(
                model_name=name,
                params={
                    "source": "kaggle/store-item-demand",
                    "protocol": "blocked_horizon",
                    "max_pairs": max_pairs,
                    "step": step,
                    "horizon": HORIZON,
                    "warmup": WARMUP,
                    "anchors": len(anchors),
                },
                metrics=overall[name],
                predictions_csv=Path(tmp.name),
            )


if __name__ == "__main__":
    main()
