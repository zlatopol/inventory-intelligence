"""Unit tests for ForecastService (app/forecast/service.py) — фейковый загрузчик.

Проверяются дизайн-решения Q1–Q3: fallback на baseline при малой истории
(с пометкой), переход на lightgbm при достаточной, рекурсивный горизонт,
ручной retrain, 404 для неизвестной пары.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.forecast.service import BASELINE_TAG, MODEL_TAG, ForecastService


def make_history(days: int, stores: int = 1, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = date(2026, 1, 1)
    for store in range(1, stores + 1):
        for offset in range(days):
            rows.append(
                (start + timedelta(days=offset), store, 1, int(rng.integers(10, 20)))
            )
    frame = pd.DataFrame(rows, columns=["date", "store_id", "product_id", "demand"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def service_for(days: int, min_history_days: int = 30) -> ForecastService:
    history = make_history(days)
    return ForecastService(
        history_loader=lambda: history, min_history_days=min_history_days
    )


def test_unknown_pair_raises_lookup_error():
    service = service_for(days=40)

    with pytest.raises(LookupError, match="нет пары"):
        service.forecast(store_id=99, product_id=99, days=3)


def test_short_history_falls_back_to_baseline_with_warning():
    """Q2: истории мало → baseline + пометка. Baseline РЕКУРСИВЕН: второй день
    считает окно, в которое уже вошёл первый прогноз."""
    service = service_for(days=10, min_history_days=30)

    result = service.forecast(store_id=1, product_id=1, days=2)

    assert result["model"] == BASELINE_TAG
    assert result["warning"] is not None
    demand = make_history(10)["demand"]
    first = demand.tail(7).mean()  # среднее 4–10 января
    # окно 2-го дня: 5–10 января + первый прогноз (рекурсия горизонта)
    second = pd.concat([demand, pd.Series([first])]).tail(7).mean()
    assert [day["demand"] for day in result["forecast"]] == [
        round(first, 1),
        round(second, 1),
    ]


def test_enough_history_uses_lightgbm_without_warning():
    """Достаточно истории → lightgbm, без предупреждения, даты подряд."""
    service = service_for(days=45, min_history_days=30)

    result = service.forecast(store_id=1, product_id=1, days=3)

    assert result["model"] == MODEL_TAG
    assert result["warning"] is None
    dates = [day["date"] for day in result["forecast"]]
    assert len(dates) == 3
    assert all(b - a == pd.Timedelta(days=1) for a, b in zip(dates, dates[1:]))
    assert all(day["demand"] >= 0 for day in result["forecast"])


def test_manual_retrain_refreshes_trained_at():
    """Q1: ручное переобучение (форс-мажор) обновляет метку обучения."""
    service = service_for(days=45)

    first = service.retrain(force=True)
    second = service.retrain(force=True)

    assert first["status"] == "retrained"
    assert second["trained_at"] >= first["trained_at"]


def test_model_reused_within_ttl():
    """Кэш: второй прогноз не переобучает (trained_at не меняется)."""
    service = service_for(days=45)
    service.forecast(store_id=1, product_id=1, days=1)
    trained_at = service._trained_at

    service.forecast(store_id=1, product_id=1, days=1)

    assert service._trained_at == trained_at  # TTL не истёк — модель та же


class TestHistory:
    def test_history_returns_tail_sorted_with_day_count(self):
        service = service_for(days=40)

        result = service.history(store_id=1, product_id=1, days=7)

        assert result["days"] == 7
        dates = [day["date"] for day in result["history"]]
        assert dates == sorted(dates)  # хвост по возрастанию дат
        assert result["history"][-1]["demand"] == int(
            make_history(40)["demand"].iloc[-1]
        )  # последний день факта — последняя строка истории

    def test_history_days_larger_than_span_returns_everything(self):
        service = service_for(days=10)

        result = service.history(store_id=1, product_id=1, days=120)

        assert result["days"] == 10  # всё, что есть — не ошибка

    def test_history_unknown_pair_raises_lookup_error(self):
        service = service_for(days=40)

        with pytest.raises(LookupError, match="нет пары"):
            service.history(store_id=99, product_id=99, days=7)
