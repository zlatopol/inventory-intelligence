"""Unit tests for data sources (app/ml/sources.py) — tiny CSVs in tmp_path.

Главный регресс-тест: max_pairs считает ПАРЫ, а не строки (баг, уже случившийся:
head(N) давал одну-две пары за N дней — прогоны были несравнимы).
"""
import pandas as pd
import pytest

from app.ml.sources import CONTRACT_COLUMNS, load_from_kaggle_csv

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
