"""Unit tests: RecommendationService (app/recommendations/service.py).

ForecastService — граница, заменяется двойником с фиксированным прогнозом;
история — синтетический DataFrame контракта; товары — SimpleNamespace
(ProductLike-протоколу достаточно атрибутов).
"""
from datetime import date, timedelta
from types import SimpleNamespace

import math

import pandas as pd
import pytest

from app.recommendations.service import RecommendationService
from app.shared.errors import InvalidReplenishmentWindowError


class FakeForecastService:
    """Двойник: demand = per_day в каждый день каждой пары."""

    def __init__(self, per_day: float = 2.0, model: str = "stub",
                 warning: str | None = None) -> None:
        self.calls: list[tuple] = []
        self._per_day = per_day
        self._model = model
        self._warning = warning

    def forecast(self, store_id: int, product_id: int, days: int) -> dict:
        self.calls.append((store_id, product_id, days))
        start = date(2026, 10, 14)
        return {
            "model": self._model,
            "warning": self._warning,
            "forecast": [
                {"date": start + timedelta(days=i), "demand": self._per_day}
                for i in range(days)
            ],
        }


def make_history(stores: list[int], demands: list[int]) -> pd.DataFrame:
    """Сетка: каждый магазин × дни; demand одинаковый по магазинам в день."""
    rows = []
    start = date(2026, 9, 1)
    for offset, demand in enumerate(demands):
        for store in stores:
            rows.append((start + timedelta(days=offset), store, 1, demand))
    frame = pd.DataFrame(
        rows, columns=["date", "store_id", "product_id", "demand"]
    )
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def product(pid: int, quantity: int) -> SimpleNamespace:
    return SimpleNamespace(id=pid, name=f"Товар {pid}", warehouse_quantity=quantity)


def make_service(history, products, per_day=2.0, warning=None):
    return RecommendationService(
        forecast=FakeForecastService(per_day=per_day, warning=warning),
        history_loader=lambda: history,
        products_loader=lambda: products,
    )


CONSTANT_40_DAYS = make_history(stores=[1, 2], demands=[10] * 40)


class TestColdStart:
    def test_product_without_history_gets_cold_start_row(self):
        service = make_service(CONSTANT_40_DAYS, products=[product(7, 15)])

        result = service.recommendations()

        row = result["recommendations"][0]
        assert row["status"] == "cold_start"
        assert row["warehouse_quantity"] == 15
        assert row["forecast_demand"] is None
        assert row["order_quantity"] is None
        assert service._forecast.calls == []  # прогноз не вызывался


class TestOrderBranch:
    def test_exact_math_constant_demand_zero_sigma(self):
        """2 пары × окно 10 × 2.0/день = F=40; σ=0 → SS=0; stock=10 → Q=30."""
        service = make_service(CONSTANT_40_DAYS, products=[product(1, 10)])

        result = service.recommendations()

        row = result["recommendations"][0]
        assert row["status"] == "order"
        assert row["forecast_demand"] == 40.0
        assert row["safety_stock"] == 0.0
        assert row["order_quantity"] == 30
        assert row["model"] == "stub"
        # по одной паре на магазин, окно L+H=10
        assert service._forecast.calls == [(1, 1, 10), (2, 1, 10)]

    def test_fractional_need_ceils_through_service(self):
        """1 пара (фильтр по истории) × 10 × 2.05 = 20.5; stock=15 → Q=6."""
        history = make_history(stores=[1], demands=[10] * 40)
        service = make_service(history, products=[product(1, 15)], per_day=2.05)

        result = service.recommendations()

        assert result["recommendations"][0]["order_quantity"] == 6

    def test_safety_stock_nonzero_for_variable_demand(self):
        """2 дня истории [10, 20] → σ=√50 ≈ 7.07 → SS = z·√50·√10 ≈ 36.7."""
        history = make_history(stores=[1], demands=[10, 20])
        service = make_service(history, products=[product(1, 0)], per_day=0.0)

        row = service.recommendations()["recommendations"][0]

        expected_ss = 1.6448536 * math.sqrt(50) * math.sqrt(10)
        assert row["safety_stock"] == pytest.approx(expected_ss, abs=0.1)
        assert row["order_quantity"] == math.ceil(expected_ss)


class TestSufficientBranch:
    def test_stock_covers_forecast_and_safety(self):
        service = make_service(CONSTANT_40_DAYS, products=[product(1, 100)])

        row = service.recommendations()["recommendations"][0]

        assert row["status"] == "sufficient"
        assert row["order_quantity"] == 0
        assert row["forecast_demand"] == 40.0  # спрос виден и в этой ветке


class TestParamsAndFilter:
    def test_window_over_14_rejected_before_any_work(self):
        service = make_service(CONSTANT_40_DAYS, products=[product(1, 0)])

        with pytest.raises(InvalidReplenishmentWindowError):
            service.recommendations(lead_time_days=8, horizon_days=7)
        assert service._forecast.calls == []

    def test_product_id_filter_leaves_only_match(self):
        history = make_history(stores=[1], demands=[10] * 40)
        service = make_service(
            history, products=[product(1, 0), product(2, 0)]
        )

        result = service.recommendations(product_id=2)

        assert [r["product_id"] for r in result["recommendations"]] == [2]
        assert result["recommendations"][0]["status"] == "cold_start"

    def test_unknown_product_id_yields_empty_list(self):
        """Фильтр, не поиск: неизвестный id — пустой список, не ошибка."""
        service = make_service(CONSTANT_40_DAYS, products=[product(1, 0)])

        result = service.recommendations(product_id=999)

        assert result["recommendations"] == []

    def test_warning_propagates_to_list_level(self):
        """Предупреждение baseline глобально (span-based) — поднимаем наверх."""
        service = make_service(
            CONSTANT_40_DAYS,
            products=[product(1, 0)],
            warning="история мала",
        )

        result = service.recommendations()

        assert result["warning"] == "история мала"
