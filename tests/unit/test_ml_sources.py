"""Unit tests for data sources (app/ml/sources.py) — tiny CSVs + fake session.

Главный регресс-тест: max_pairs считает ПАРЫ, а не строки (баг, уже случившийся:
head(N) давал одну-две пары за N дней — прогоны были несравнимы).

Второй регресс-блок (ADR-0007): load_from_stock_event обязан выдавать КОНТРАКТ
дневного спроса (полночь, наивные даты, агрегация по дню, сетка с нулями) из
«грязных» меток событий — время внутри дня, дубль дня, пропуск дня, пересечение
границы дня UTC→Москва.
"""
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from app.ml.sources import (
    CONTRACT_COLUMNS,
    load_from_kaggle_csv,
    load_from_stock_event,
)

TINY_CSV = """date,store,item,sales
2013-01-01,2,5,10
2013-01-02,2,5,11
2013-01-01,1,1,7
2013-01-02,1,1,8
2013-01-01,2,1,9
2013-01-02,2,1,10
"""


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "tiny.csv"
    path.write_text(TINY_CSV)
    return path


def test_contract_columns_types_and_sorting(csv_path):
    # ARRANGE → ACT
    df = load_from_kaggle_csv(csv_path)

    # ASSERT: контракт колонок, date — datetime, отсортировано по трём ключам
    assert list(df.columns) == CONTRACT_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df.equals(
        df.sort_values(["date", "store_id", "product_id"]).reset_index(drop=True)
    )


def test_max_pairs_counts_pairs_not_rows(csv_path):
    """Регрессия head(N): 2 пары ≠ 2 строки."""
    df = load_from_kaggle_csv(csv_path, max_pairs=2)

    assert len(df) == 4  # 2 пары × 2 дня, а НЕ 2 строки
    assert df.groupby(["store_id", "product_id"]).ngroups == 2


def test_max_pairs_deterministic_first_sorted_pairs(csv_path):
    # «первые» пары — в sorted-порядке: (1,1) и (2,1), не (2,5)
    df = load_from_kaggle_csv(csv_path, max_pairs=1)

    pairs = set(map(tuple, df[["store_id", "product_id"]].drop_duplicates().values))
    assert pairs == {(1, 1)}  # минимальная пара, детерминированно


def test_date_filter_is_inclusive_bounds(csv_path):
    df = load_from_kaggle_csv(csv_path, start="2013-01-02", end="2013-01-02")

    assert len(df) == 3  # все три пары, один день
    assert (df["date"] == pd.Timestamp("2013-01-02")).all()


def test_missing_columns_raise_value_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,store,sales\n2013-01-01,1,5\n")  # нет item

    with pytest.raises(ValueError, match="item"):
        load_from_kaggle_csv(bad)


# --- load_from_stock_event: контракт дневного спроса (ADR-0007) ----------------


class FakeSession:
    """Минимальная сессия: execute(select(...)).all() → заготовленные строки."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


# «Грязные» метки (UTC): время внутри дня, дубль дня, пропуск 10-го и
# 21:10 UTC = 00:10 СЛЕДУЮЩЕГО дня по Москве — граница дня (ADR-0007).
DIRTY_EVENT_ROWS = [
    (datetime(2026, 10, 8, 12, 0, tzinfo=UTC), 1, 1, 5),  # 15:00 местн., 8-е
    (datetime(2026, 10, 8, 20, 45, tzinfo=UTC), 1, 1, 7),  # 23:45 местн., 8-е
    (datetime(2026, 10, 8, 21, 10, tzinfo=UTC), 1, 1, 9),  # 00:10 местн., уже 9-е
    (datetime(2026, 10, 11, 8, 0, tzinfo=UTC), 1, 1, 4),  # 11:00 местн., 11-е
]


def test_stock_events_to_daily_demand_contract():
    # ARRANGE → ACT
    df = load_from_stock_event(FakeSession(DIRTY_EVENT_ROWS))

    # ASSERT: полная сетка 4 дней, ноль на пропущенном 10-м, одна строка/день
    assert list(df["date"]) == list(pd.date_range("2026-10-08", periods=4))
    assert list(df["demand"]) == [12, 9, 0, 4]
    assert not df.duplicated(["date", "store_id", "product_id"]).any()

    # полночь + наивные даты — контракт датасета (Q1)
    assert df["date"].equals(df["date"].dt.normalize())
    assert df["date"].dt.tz is None


def test_stock_events_day_boundary_is_business_timezone():
    """21:10 UTC 8-го = 00:10 9-го по Москве: день считается по бизнес-зоне.

    UTC-граница положила бы все три события в 8-е (demand 21) — регрессия.
    """
    df = load_from_stock_event(FakeSession(DIRTY_EVENT_ROWS))

    assert df.loc[df["date"] == pd.Timestamp("2026-10-08"), "demand"].item() == 12
    assert df.loc[df["date"] == pd.Timestamp("2026-10-09"), "demand"].item() == 9


def test_stock_events_filter_by_local_day_inclusive():
    # ARRANGE → ACT
    df = load_from_stock_event(
        FakeSession(DIRTY_EVENT_ROWS), start=date(2026, 10, 9), end=date(2026, 10, 10)
    )

    # ASSERT: фильтр по локальным дням, границы включительно
    assert list(df["date"]) == [
        pd.Timestamp("2026-10-09"),
        pd.Timestamp("2026-10-10"),
    ]
    assert list(df["demand"]) == [9, 0]


def test_stock_events_empty_returns_empty_contract_frame():
    # Пустая БД — путь API-тестов (404 из ForecastService): без падения,
    # колонки и dtype контракта на месте
    df = load_from_stock_event(FakeSession([]))

    assert list(df.columns) == CONTRACT_COLUMNS
    assert df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
