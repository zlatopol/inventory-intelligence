"""Разведка праздничного профиля спроса — проверка H5 («до — рост, после — спад»).

Запуск: .venv/bin/python scripts/explore_holidays.py [max_pairs]
Вывод: таблица профилей (окно ±7 дней) вокруг четырёх крупных праздников US
+ график docs/img/holidays_profile.png.

Метод (конфаунды сняты намеренно):
- нормировка: день / среднее по ТЕМ ЖЕ дням недели за прошлые 4 недели —
  уходит недельный профиль (−4 перед четвергом = воскресенье) и медленный
  тренд (летний рамп вокруг 4 июля);
- профиль усреднён по годам 2013–2017;
- календарь — пакет `holidays` (выбор Q3): плавающие даты не считаем руками.

Вердикт (см. вывод): H5 ОТКЛОНЕНА — предпраздничного роста нет; единственный
устойчивый эффект — широкая «полоса закрытия» Рождества/Нового года
(≈0.83–0.91 на −5…+3), пересекающая границу месяца. Спад после Дня
благодарения — начало той же декабрьской ямы, не «постпраздничный спад».
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import holidays  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")  # без экрана: только файлы
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from app.ml.sources import load_from_kaggle_csv  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "train.csv"
OUT = Path(__file__).resolve().parents[1] / "docs" / "img"

WINDOW = 7          # ± дней вокруг праздника
REF_WEEKS = 4       # глубина нормировки «тот же день недели»
MIN_REFS = 2        # меньше референсов (начало датасета) — день пропускаем

# Четыре крупных праздника: ищем по подстроке имени (пакет пишет и
# «... (observed)» — переносы праздников тоже учитываем)
HOLIDAY_MATCHES = {
    "New Year's Day": "New Year",
    "Independence Day": "Independence",
    "Christmas Day": "Christmas",
    "Thanksgiving": "Thanksgiving",
}


def weekday_normalized(daily: pd.Series) -> pd.Series:
    """day / среднее по тем же дням недели за REF_WEEKS недель назад."""
    ratio = {}
    for day in daily.index:
        refs = [
            day - pd.Timedelta(weeks=k) for k in range(1, REF_WEEKS + 1)
        ]
        refs = [r for r in refs if r in daily.index]
        if len(refs) >= MIN_REFS:
            ratio[day] = daily[day] / daily[refs].mean()
    return pd.Series(ratio)


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    df = load_from_kaggle_csv(DATA_PATH, max_pairs=max_pairs)
    daily = df.groupby("date")["demand"].mean()
    ratio = weekday_normalized(daily)

    us = holidays.country_holidays("US", years=range(2013, 2018))
    profiles: dict[str, dict[int, float]] = {}
    for label, needle in HOLIDAY_MATCHES.items():
        dates = sorted(d for d, name in us.items() if needle in name)
        prof: dict[int, list[float]] = {}
        for h in dates:
            for off in range(-WINDOW, WINDOW + 1):
                day = pd.Timestamp(h) + pd.Timedelta(days=off)
                if day in ratio.index:
                    prof.setdefault(off, []).append(ratio[day])
        profiles[label] = {o: sum(v) / len(v) for o, v in sorted(prof.items())}

    # --- таблица -------------------------------------------------------------
    offsets = range(-WINDOW, WINDOW + 1)
    header = "offset    " + "".join(f"{o:+d}    " for o in offsets)
    print(header)
    for label, prof in profiles.items():
        print(f"{label:13s}" + "".join(f"{prof[o]:.2f}  " for o in offsets))

    # --- график --------------------------------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, prof in profiles.items():
        xs = list(prof)
        ax.plot(xs, [prof[o] for o in xs], marker="o", label=label)
    ax.axhline(1.0, color="gray", linewidth=1, linestyle="--", alpha=0.7)
    ax.axvline(0.0, color="gray", linewidth=1, linestyle=":", alpha=0.5)
    ax.set_title("Профиль спроса вокруг праздника (нормировка: тот же день "
                 "недели ×4 нед., среднее 2013–2017)")
    ax.set_xlabel("дней до/после праздника")
    ax.set_ylabel("спрос / собственный недельный бейзлайн")
    ax.set_xticks(list(offsets))
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "holidays_profile.png", dpi=150)
    plt.close(fig)
    print(f"\nСохранено: {OUT / 'holidays_profile.png'}")


if __name__ == "__main__":
    main()
