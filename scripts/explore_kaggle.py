"""Разведка реальных данных: профили спроса по дню недели / месяцу / году.

Запуск: .venv/bin/python scripts/explore_kaggle.py [max_pairs]
Цель — обосновать (или опровергнуть) гипотезы H1–H4 до построения фичей.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app.ml.sources import load_from_kaggle_csv  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"

DOW = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн",
          "июл", "авг", "сен", "окт", "ноя", "дек"]


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    df = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)

    print(f"=== Разведка: {len(df)} строк, {max_pairs} пар, "
          f"{df['date'].min().date()} → {df['date'].max().date()} ===\n")

    yearly = df.groupby(df["date"].dt.year)["demand"].mean()
    print("Средний спрос по ГОДАМ (тренд?):")
    for year, value in yearly.items():
        bar = "#" * int(value / 2)
        print(f"  {year}: {value:6.2f}  {bar}")
    growth = yearly.iloc[-1] / yearly.iloc[0]
    print(f"  рост за 5 лет: ×{growth:.2f} "
          f"({(growth - 1) * 100:+.0f}%)\n")

    monthly = df.groupby(df["date"].dt.month)["demand"].mean()
    print("Средний спрос по МЕСЯЦАМ (годичная сезонность?):")
    for i, value in monthly.items():
        print(f"  {MONTHS[i - 1]}: {value:6.2f}  {'#' * int(value / 2)}")
    print(f"  размах: min {monthly.min():.1f} / max {monthly.max():.1f} "
          f"(×{monthly.max() / monthly.min():.2f})\n")

    dow = df.groupby(df["date"].dt.dayofweek)["demand"].mean()
    print("Средний спрос по ДНЯМ НЕДЕЛИ:")
    for i, value in dow.items():
        print(f"  {DOW[i]}: {value:6.2f}  {'#' * int(value / 2)}")
    print(f"  размах: ×{dow.max() / dow.min():.2f}\n")

    # Стабильность недельного профиля по годам (H1 опирается на стабильность)
    pivot = df.pivot_table(
        values="demand", index=df["date"].dt.dayofweek,
        columns=df["date"].dt.year, aggfunc="mean",
    ).round(1)
    pivot.index = DOW
    print("Недельный профиль ПО ГОДАМ (стабилен ли?):")
    print(pivot.to_string(), "\n")

    # Шум отдельного дня: вариация ВНУТРИ пары-дня относительно её профиля
    df["dow_mean"] = df.groupby(
        [df["store_id"], df["product_id"], df["date"].dt.dayofweek]
    )["demand"].transform("mean")
    noise = (df["demand"] / df["dow_mean"]).std()
    print(f"Шум дня (std отн. отклонения от среднего своего дня недели пары): "
          f"{noise:.2f}")
    print("→ высокое значение = «прошлая суббота» несёт много случайного;")


if __name__ == "__main__":
    main()
