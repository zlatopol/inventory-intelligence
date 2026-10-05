"""Графическая разведка реальных данных (matplotlib) → docs/img/.

Запуск: .venv/bin/python scripts/plot_kaggle.py [max_pairs]
Создаёт docs/img/*.png — иллюстрации для доклада/README (данные — те же,
что в текстовой разведке explore_kaggle.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # без экрана: только файлы
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from app.ml.sources import load_from_kaggle_csv  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"
OUT = Path(__file__).resolve().parents[1] / "docs" / "img"
DOW = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн",
          "июл", "авг", "сен", "окт", "ноя", "дек"]


def style(ax, title: str, ylabel: str = "средний спрос, шт.") -> None:
    ax.set_title(title, fontsize=13)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    df = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    OUT.mkdir(parents=True, exist_ok=True)

    # --- 1. Тренд: средний спрос по годам -------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    yearly = df.groupby(df["date"].dt.year)["demand"].mean()
    bars = ax.bar(yearry := yearly.index.astype(str), yearly.values,
                  color="#4C72B0")
    for bar, value in zip(bars, yearly.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.5,
                f"{value:.1f}", ha="center", fontsize=10)
    style(ax, "Тренд: средний спрос по годам (+35% за 5 лет)")
    fig.tight_layout()
    fig.savefig(OUT / "yearly_trend.png", dpi=150)
    plt.close(fig)

    # --- 2. Годичная сезонность: по месяцам ------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    monthly = df.groupby(df["date"].dt.month)["demand"].mean()
    ax.plot(MONTHS, monthly.values, marker="o", color="#DD8452")
    ax.fill_between(range(12), monthly.values, alpha=0.15, color="#DD8452")
    style(ax, "Годичная сезонность: спрос по месяцам (×1.89 июль/январь)")
    fig.tight_layout()
    fig.savefig(OUT / "monthly_seasonality.png", dpi=150)
    plt.close(fig)

    # --- 3. Недельный профиль по годам: стабильная форма, растущий уровень
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot = df.pivot_table(values="demand", index=df["date"].dt.dayofweek,
                           columns=df["date"].dt.year, aggfunc="mean")
    for year in pivot.columns:
        ax.plot(DOW, pivot[year], marker="o", label=str(year))
    style(ax, "Недельный профиль по годам: форма стабильна, уровень растёт")
    ax.legend(title="год")
    fig.tight_layout()
    fig.savefig(OUT / "weekly_profile_by_year.png", dpi=150)
    plt.close(fig)

    # --- 4. Сырой срез: одна пара, 8 недель — шум дня глазами ------------
    fig, ax = plt.subplots(figsize=(10, 5))
    pair = df.groupby(["store_id", "product_id"]).size().idxmax()
    mask = (df["store_id"] == pair[0]) & (df["product_id"] == pair[1])
    series = df[mask].tail(56)  # последние 8 недель
    ax.plot(series["date"], series["demand"], marker=".", color="#55A868")
    style(ax, f"Сырые данные: пара {pair}, последние 8 недель (шум ≈27%)",
          ylabel="спрос, шт.")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "raw_noise.png", dpi=150)
    plt.close(fig)

    print(f"Готово: 4 графика → {OUT}/")


if __name__ == "__main__":
    main()
