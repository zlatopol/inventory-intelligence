"""Unit tests for the demand dataset (app/ml/dataset.py) — synthetic frames, no DB.

Проверяются контракты дизайн-решений:
- Q1/Q2: полная дневная сетка (пара × день) с нулями на пропусках;
- инвариант суммы: sum(demand) == sum(events.quantity) — ловит «молчаливые нули»;
- Q3: хронологический разрез — train строго до границы, test с неё;
- tz-регрессия: tz-aware timestamps попадают в правильные дни (баг, уже бывший).
"""
from datetime import date

import pandas as pd

from app.ml.dataset import build_demand_dataset, chronological_split


def make_events(rows: list[tuple]) -> pd.DataFrame:
    """Мини-события: [(iso_ts, store_id, product_id, quantity), ...].

    occurred_at приводится к tz-aware UTC — как его возвращает psycopg
    (продакшен-условие; наивный столбец не поймал бы tz-баг).
    """
    frame = pd.DataFrame(
        rows, columns=["occurred_at", "store_id", "product_id", "quantity"]
    )
    frame["occurred_at"] = pd.to_datetime(frame["occurred_at"], utc=True)
    return frame


# --- ОБРАЗЕЦ (ARRANGE → ACT → ASSERT; остальные — по аналогии) ---------------


def test_full_grid_fills_missing_days_with_zero():
    # ARRANGE: 2 пары, события не в каждый день
    events = make_events(
        [
            ("2026-01-01T10:00:00+00:00", 1, 1, 5),
            ("2026-01-03T10:00:00+00:00", 2, 1, 7),  # пара (2,1) живёт только 3-го
        ]
    )

    # ACT
    dataset = build_demand_dataset(events, date(2026, 1, 1), date(2026, 1, 3))

    # ASSERT: полная сетка 3 дня × 2 пары (Q2)
    assert len(dataset) == 6
    pair_2 = dataset[
        (dataset["store_id"] == 2) & (dataset["date"] < pd.Timestamp("2026-01-03"))
    ]
    assert len(pair_2) == 2  # 1 и 2 января у пары (2,1)
    assert (pair_2["demand"] == 0).all()  # нули досыпаны, не пропущены


# --- Тесты контрактов (ARRANGE → ACT → ASSERT) --------------------------------


def test_demand_sum_invariant_matches_events_quantity():
    """Инвариант суммы: ничего не потерялось и не приписалось при агрегации.

    Ловит «молчаливые нули»: если reindex не совпал по ключам, все значения
    обнуляются и суммы расходятся.
    """
    # ARRANGE: 4 события, два из них — одна пара в один день
    events = make_events(
        [
            ("2026-01-01T10:00:00+00:00", 1, 1, 5),
            ("2026-01-03T10:00:00+00:00", 2, 1, 7),
            ("2026-01-03T10:00:00+00:00", 1, 1, 10),
            ("2026-01-04T10:00:00+00:00", 2, 1, 2),
        ]
    )

    # ACT
    dataset = build_demand_dataset(events, date(2026, 1, 1), date(2026, 1, 4))

    # ASSERT
    assert dataset["demand"].sum() == events["quantity"].sum()  # 24 == 24


def test_two_events_same_pair_same_day_aggregate_into_one_row():
    """Агрегация: два события одной пары в один день → одна строка с суммой."""
    # ARRANGE
    events = make_events(
        [
            ("2026-01-02T09:00:00+00:00", 1, 1, 3),
            ("2026-01-02T18:00:00+00:00", 1, 1, 4),  # та же пара, тот же день
        ]
    )

    # ACT
    dataset = build_demand_dataset(events, date(2026, 1, 2), date(2026, 1, 2))

    # ASSERT
    pair_rows = dataset[(dataset["store_id"] == 1) & (dataset["product_id"] == 1)]
    assert len(pair_rows) == 1  # слились, а не задублировались
    assert pair_rows["demand"].iloc[0] == 7  # 3 + 4


def test_chronological_split_boundary_train_before_test_from():
    """Q3: train строго ДО границы, test — с неё включительно; потерь нет."""
    # ARRANGE: события за 4 дня
    events = make_events(
        [
            ("2026-01-01T10:00:00+00:00", 1, 1, 1),
            ("2026-01-02T10:00:00+00:00", 1, 1, 2),
            ("2026-01-03T10:00:00+00:00", 1, 1, 3),
            ("2026-01-04T10:00:00+00:00", 1, 1, 4),
        ]
    )
    dataset = build_demand_dataset(events, date(2026, 1, 1), date(2026, 1, 4))

    # ACT: разрез по 3-му числу
    train, test = chronological_split(dataset, date(2026, 1, 3))

    # ASSERT
    assert train["date"].max() < pd.Timestamp("2026-01-03")
    assert test["date"].min() >= pd.Timestamp("2026-01-03")
    assert len(train) + len(test) == len(dataset)  # ни одна строка не потерялась


def test_tz_aware_timestamp_lands_in_correct_day():
    """tz-регрессия: событие у полуночи UTC попадает в СВОЙ день.

    Регрессия = тест на уже случившийся баг: tz-aware occurred_at из psycopg
    однажды не совпал с наивной сеткой — reindex молча насыпал нулей.
    """
    # ARRANGE: 23:30 UTC 2 января — опасно близко к смене дня
    events = make_events([("2026-01-02T23:30:00+00:00", 1, 1, 9)])

    # ACT
    dataset = build_demand_dataset(events, date(2026, 1, 2), date(2026, 1, 2))

    # ASSERT: количество оказалось именно 2-го января, а не потерялось в нулях
    assert len(dataset) == 1
    assert dataset["date"].iloc[0] == pd.Timestamp("2026-01-02")
    assert dataset["demand"].iloc[0] == 9
