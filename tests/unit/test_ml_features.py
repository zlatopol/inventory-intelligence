"""Unit tests for the feature builder (app/ml/features.py) — synthetic frames.

Главная тема — ГРАНИЦЫ ВРЕМЕНИ: фичи дня D обязаны строиться только из
прошлого. Данные подбираются так, чтобы ответ был виден руками.
"""
from datetime import date

import pandas as pd
import pytest

from app.ml.features import (
    HOLIDAY_FAR,
    FEATURE_COLUMNS,
    _holiday_distances,
    build_features,
    history_until,
)

TARGET = date(2026, 1, 10)  # суббота


def make_history(rows: list[tuple]) -> pd.DataFrame:
    """История: [(дата-строка, store, product, demand), ...] — ДО TARGET."""
    frame = pd.DataFrame(rows, columns=["date", "store_id", "product_id", "demand"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values(["date", "store_id", "product_id"]).reset_index(drop=True)


def one_pair_history(demands_by_day: dict) -> pd.DataFrame:
    """История одной пары (1,1): {'2026-01-05': 3, ...} → DataFrame."""
    return make_history([(day, 1, 1, qty) for day, qty in demands_by_day.items()])


# --- Граница времени и календарь --------------------------------------------


def test_history_until_cuts_strictly_before_the_day():
    """Граница: всё строго раньше дня — сам день исключается (Q3 как API)."""
    dataset = one_pair_history({"2026-01-09": 5, "2026-01-10": 7, "2026-01-11": 9})

    history = history_until(dataset, "2026-01-10")

    assert history["date"].max() == pd.Timestamp("2026-01-09")  # 10-е и 11-е отрезаны


def test_features_refuse_history_containing_target_day():
    """Страж утечки: история, содержащая target, → ValueError, а не тихой гонки."""
    history = one_pair_history({"2026-01-09": 5, "2026-01-10": 7})  # 10-е внутри!

    with pytest.raises(ValueError, match="граница утечки|target_day"):
        build_features(history, TARGET)


def test_calendar_features_come_from_target_date_itself():
    """dayofweek/month/year — из даты цели: 2026-01-10 = суббота, январь."""
    history = one_pair_history({"2026-01-09": 5})

    features = build_features(history, TARGET)

    row = features.iloc[0]
    assert row["dayofweek"] == 5  # суббота (пн=0)
    assert row["month"] == 1
    assert row["year"] == 2026


def test_holiday_distances_boundary_cases():
    """Дистанции: до/от ближайшего праздника; сам праздник — days_to=0;
    пустой календарь/вне покрытия → HOLIDAY_FAR (знание «далеко», не NaN)."""
    calendar = frozenset({date(2026, 1, 5), date(2026, 1, 20)})

    # между праздниками: вперёд до 20-го — 6 дней, назад до 5-го — 9
    assert _holiday_distances(pd.Timestamp("2026-01-14"), calendar) == (6, 9)
    # в сам праздник: days_to=0, days_from смотрит на прошедший
    assert _holiday_distances(pd.Timestamp("2026-01-20"), calendar) == (0, 15)
    # вне покрытия календаря (позади всех): 999/999… нет — вперёд праздников нет,
    # назад есть; пустой календарь — оба HOLIDAY_FAR
    assert _holiday_distances(pd.Timestamp("2026-02-01"), calendar) == (HOLIDAY_FAR, 12)
    assert _holiday_distances(pd.Timestamp("2026-01-14"), frozenset()) == (
        HOLIDAY_FAR,
        HOLIDAY_FAR,
    )


def test_holiday_features_reach_build_features_output():
    """Фича доезжает до выхода build_features: одна для всех пар
    (свойство даты), дефолт-вызов без календаря — HOLIDAY_FAR."""
    history = make_history(
        [("2026-01-09", 1, 1, 5), ("2026-01-09", 2, 1, 7)]
    )
    calendar = frozenset({date(2026, 1, 5), date(2026, 1, 15)})

    with_cal = build_features(history, TARGET, holiday_days=calendar)
    no_cal = build_features(history, TARGET)

    assert (with_cal["days_to_holiday"] == 5).all()   # 10-е → 15-е
    assert (with_cal["days_from_holiday"] == 5).all()  # 10-е ← 5-го
    assert (no_cal[["days_to_holiday", "days_from_holiday"]] == HOLIDAY_FAR).all().all()


# --- Тесты фич ----------------------------------------------------------------


def test_lag_features_come_from_exact_days_of_history():
    """lag_1 = спрос накануне (9-е), lag_7 = спрос ровно 7 дней назад (3-е)."""
    history = one_pair_history(
        {
            "2026-01-03": 10,
            "2026-01-04": 20,
            "2026-01-05": 30,
            "2026-01-06": 40,
            "2026-01-07": 50,
            "2026-01-08": 60,
            "2026-01-09": 70,
        }
    )

    features = build_features(history, TARGET)

    row = features.iloc[0]
    assert row["lag_1"] == 70  # спрос 9-го
    assert row["lag_7"] == 10  # спрос 3-го (target − 7)


def test_rolling_mean_is_average_of_last_seven_days():
    """Окно — 7 дней ДО границы (3–9 января); среднее считается руками."""
    history = one_pair_history(
        {
            "2026-01-03": 10,
            "2026-01-04": 20,
            "2026-01-05": 30,
            "2026-01-06": 40,
            "2026-01-07": 50,
            "2026-01-08": 60,
            "2026-01-09": 70,
        }
    )

    features = build_features(history, TARGET)

    row = features.iloc[0]
    expected_mean = sum(range(10, 80, 10)) / 7  # (10+20+30+40+50+60+70)/7
    assert row["rolling_mean_7"] == expected_mean


def test_expanding_mean_pair_averages_all_past_demands():
    """Уровень пары — среднее всей её истории: [2, 4] → 3.0."""
    history = one_pair_history(
        {
            "2026-01-03": 2,
            "2026-01-04": 4,
        }
    )

    features = build_features(history, TARGET)

    assert features.iloc[0]["expanding_mean_pair"] == 3.0


def test_features_cover_all_pairs_with_contract_columns():
    """По одной строке на встреченную пару; колонки = PAIR + FEATURE_COLUMNS."""
    history = make_history(
        [
            ("2026-01-03", 1, 1, 5),
            ("2026-01-04", 1, 2, 10),
            ("2026-01-05", 2, 1, 15),
        ]
    )

    features = build_features(history, TARGET)

    assert set(features[["store_id", "product_id"]].itertuples(index=False)) == {
        (1, 1),
        (1, 2),
        (2, 1),
    }
    assert list(features.columns) == ["store_id", "product_id"] + FEATURE_COLUMNS


def test_short_history_yields_nan_lag7_and_mean_of_available_days():
    """Правда о прошлом: недели назад нет → lag_7 NaN; окно — по имеющимся."""
    history = one_pair_history(
        {
            "2026-01-07": 10,
            "2026-01-08": 20,
            "2026-01-09": 30,
        }
    )

    features = build_features(history, TARGET)

    row = features.iloc[0]
    assert pd.isna(row["lag_7"])  # нет данных за неделю назад
    expected_mean = (10 + 20 + 30) / 3  # среднее трёх дней
    assert row["rolling_mean_7"] == expected_mean
