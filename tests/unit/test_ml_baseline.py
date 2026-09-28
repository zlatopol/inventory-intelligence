"""Unit tests for baselines & walk-forward (app/ml/baseline.py) — synthetic frames.

Проверяются контракты моделей (на маленьких числах, где ответ виден руками)
и сама валидация walk_forward (граница утечки — Q3).
"""
import pandas as pd

from app.ml.baseline import moving_average_forecast, naive_forecast, seasonal_naive_forecast, walk_forward_evaluate
from app.ml.metrics import mae, wape


def make_dataset(rows: list[tuple]) -> pd.DataFrame:
    """Мини-датасет: [(дата-строка, store_id, product_id, demand), ...]."""
    frame = pd.DataFrame(rows, columns=["date", "store_id", "product_id", "demand"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


# --- ОБРАЗЕЦ (остальные — по аналогии) ---------------------------------------


def test_naive_takes_last_observation_per_pair():
    # ARRANGE: у пары (1,1) последнее значение — 15 (не 12!); сортировка решает
    dataset = make_dataset(
        [
            ("2026-01-01", 1, 1, 12),
            ("2026-01-02", 1, 1, 15),
            ("2026-01-02", 2, 1, 7),
        ]
    )

    # ACT
    prediction = naive_forecast(dataset)

    # ASSERT: по одной строке на пару, значения — «вчерашние»
    assert len(prediction) == 2
    by_pair = prediction.set_index(["store_id", "product_id"])["prediction"]
    assert by_pair[(1, 1)] == 15
    assert by_pair[(2, 1)] == 7


# --- ТВОИ ТЕСТЫ ---------------------------------------------------------------
# TODO 2: seasonal_naive — train заканчивается 8-м; прогноз 9-го == значение 2-го
#         (лаг 7). Импортируй seasonal_naive_forecast.
def test_seasonal_naive_uses_value_exactly_lag_days_back():
    """Прогноз на день после train = значение пары ровно lag=7 дней назад."""
    # ARRANGE: пара с историей 1–8 января; цель — 9-е, lookback — 2-е (= 15)
    dataset = make_dataset(
        [
            ("2026-01-01", 1, 1, 12),
            ("2026-01-02", 1, 1, 15),
            ("2026-01-03", 1, 1, 7),
            ("2026-01-04", 1, 1, 5),
            ("2026-01-05", 1, 1, 8),
            ("2026-01-06", 1, 1, 9),
            ("2026-01-07", 1, 1, 6),
            ("2026-01-08", 1, 1, 16),
        ]
    )

    # ACT
    prediction = seasonal_naive_forecast(dataset)

    # ASSERT: 9-е − 7 = 2-е; значение 2-го января = 15
    assert len(prediction) == 1
    by_pair = prediction.set_index(["store_id", "product_id"])["prediction"]
    assert by_pair[(1, 1)] == 15


def test_moving_average_window_and_history_shorter_than_window():
    """Окно 3: [3,4,5] → 4.0; история из одного значения — среднее по нему."""
    # ARRANGE
    dataset_1 = make_dataset(
        [
            ("2026-01-01", 1, 1, 3),
            ("2026-01-02", 1, 1, 4),
            ("2026-01-03", 1, 1, 5),
        ]
    )
    dataset_2 = make_dataset([("2026-01-01", 1, 1, 12)])

    # ACT
    prediction_1 = moving_average_forecast(dataset_1)
    prediction_2 = moving_average_forecast(dataset_2)

    # ASSERT
    by_pair = prediction_1.set_index(["store_id", "product_id"])["prediction"]
    assert by_pair[(1, 1)] == 4.0  # (3+4+5)/3
    by_pair = prediction_2.set_index(["store_id", "product_id"])["prediction"]
    assert by_pair[(1, 1)] == 12.0  # tail(окно) вернул единственное значение


def test_walk_forward_never_shows_the_predicted_day_to_the_model():
    """Шпион-утечка: валидатор обязан давать train строго ДО оценочного дня."""
    # ARRANGE: 10 ПОСЛЕДОВАТЕЛЬНЫХ дней (ловушка: дата в кортеже — не константа!)
    from datetime import date, timedelta

    dataset = make_dataset(
        [
            (str(date(2026, 1, 1) + timedelta(days=offset)), 1, 1, offset + 1)
            for offset in range(10)
        ]
    )
    seen_maxes: list = []

    def spy(train: pd.DataFrame) -> pd.DataFrame:
        seen_maxes.append(train["date"].max())
        return naive_forecast(train)

    # ACT
    result = walk_forward_evaluate(dataset, spy)

    # ASSERT: для каждого оценочного дня D максимум его train < D
    evaluated_days = sorted(result["date"].unique())
    assert len(seen_maxes) == len(evaluated_days)  # по одному вызову на день
    for seen_max, day in zip(seen_maxes, evaluated_days):
        assert seen_max < day  # граница утечки (Q3): факт дня D недоступен


def test_metrics_by_hand():
    """Метрики на числах, проверяемых руками."""
    # MAE: |3−2| + |4−6| = 1 + 2, среднее = 1.5
    assert mae(pd.Series([3, 4]), pd.Series([2, 6])) == 1.5
    # WAPE: (2+2) / (10+10) × 100 = 20%
    assert wape(pd.Series([10, 10]), pd.Series([8, 12])) == 20.0
    # факта нет совсем → inf (деление на ноль защищено)
    assert wape(pd.Series([0, 0]), pd.Series([5, 7])) == float("inf")