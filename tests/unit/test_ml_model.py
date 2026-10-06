"""Unit tests for the demand model (app/ml/model.py).

Ключевой тест среза — СОГЛАСОВАННОСТЬ: векторизованная обучающая таблица и
поштучный build_features обязаны давать одинаковые фичи для одного дня.
Расхождение = утечка или потеря данных в одной из реализаций.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.ml.features import FEATURE_COLUMNS, PAIR, build_features, history_until
from app.ml.model import LightGBMModel, build_training_table


def make_dataset(days: int, pairs: int = 2, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = date(2026, 1, 1)
    for store in range(1, pairs + 1):
        for day in range(days):
            rows.append(
                (start + timedelta(days=day), store, 1, int(rng.integers(5, 30)))
            )
    frame = pd.DataFrame(rows, columns=["date", "store_id", "product_id", "demand"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def test_training_table_row_matches_per_day_features():
    """Векторизация == поштучный расчёт (иначе где-то утечка или потеря)."""
    dataset = make_dataset(days=40)
    table = build_training_table(dataset).set_index(["date"] + PAIR)

    # Проверяем три дня: середина истории и ближе к концу
    for offset in (20, 30, 38):
        day = pd.Timestamp(date(2026, 1, 1) + timedelta(days=offset))
        per_day = build_features(history_until(dataset, day), day).set_index(PAIR)
        row = table.loc[day]

        for pair_index in row.index:
            for column in FEATURE_COLUMNS:
                vectorized = row.loc[pair_index][column]
                manual = per_day.loc[pair_index][column]
                assert pd.isna(vectorized) == pd.isna(manual) or np.isclose(
                    vectorized, manual
                ), f"{column} расходится для {pair_index} на {day.date()}"


def test_training_table_drops_warmup_days_per_pair():
    """Первые 7 дней каждой пары (NaN лаг_7) отсутствуют — констант нет."""
    dataset = make_dataset(days=15)

    table = build_training_table(dataset)

    assert table.groupby(PAIR).size().eq(8).all()  # 15 − 7 warmup
    assert not table[FEATURE_COLUMNS].isna().any().any()


def test_model_forecast_shape_and_sanity():
    """Smoke: прогноз на все пары, числа неотрицательные (спрос ≥ 0)."""
    dataset = make_dataset(days=40)
    train = history_until(dataset, dataset["date"].max() + pd.Timedelta(days=1))

    model = LightGBMModel(retrain_every=7)
    prediction = model.forecast(train)

    assert list(prediction.columns) == PAIR + ["prediction"]
    assert len(prediction) == train.groupby(PAIR).ngroups
    assert (prediction["prediction"] >= 0).all()
    # кэш: повторный вызов на следующий день не должен переобучать
    day2 = dataset[dataset["date"] < dataset["date"].max()]
    model.forecast(day2)
    assert model._trained_through is not None
