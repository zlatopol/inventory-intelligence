"""API tests: /recommendations — контракт ответа и валидация (EX-2).

Модель НЕ обучается: сервис рекомендаций подменяется целиком (паттерн
test_forecast_api), внутри — реальный RecommendationService на db_session;
короткая история → baseline-ветка прогноза (без lightgbm).
"""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.events.models import StockEvent
from app.forecast.service import ForecastService
from app.main import create_app
from app.ml.sources import load_from_stock_event
from app.products.models import Product
from app.products.repository import ProductRepository
from app.recommendations.router import get_recommendation_service
from app.recommendations.service import RecommendationService
from app.stores.models import Store


@pytest.fixture
def client(db_session):
    app = create_app()

    forecast = ForecastService(
        history_loader=lambda: load_from_stock_event(db_session)
    )
    service = RecommendationService(
        forecast=forecast,
        history_loader=lambda: load_from_stock_event(db_session),
        products_loader=lambda: ProductRepository(
            db_session
        ).list_live_ordered_by_name(),
    )
    app.dependency_overrides[get_recommendation_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client


def seed_pair_history(session, product_quantity: int = 10) -> None:
    """Товар + магазин + одна отгрузка: история в один день → baseline."""
    session.add(Product(name="Сахар", warehouse_quantity=product_quantity))
    session.add(Store(name="Магазин А"))
    session.commit()
    session.add(
        StockEvent(
            event_type="shipment",
            product_id=1,
            store_id=1,
            quantity=10,
            occurred_at=datetime(2026, 10, 10, 12, tzinfo=UTC),
        )
    )
    session.commit()


class TestContract:
    def test_empty_db_returns_empty_list(self, client):
        response = client.get("/recommendations")

        assert response.status_code == 200
        body = response.json()
        assert body["recommendations"] == []
        assert body["service_level"] == 0.95
        assert body["lead_time_days"] == 3
        assert body["horizon_days"] == 7

    def test_products_without_history_are_cold_start(self, client, db_session):
        db_session.add(Product(name="Соль", warehouse_quantity=7))
        db_session.commit()

        body = client.get("/recommendations").json()

        row = body["recommendations"][0]
        assert row["status"] == "cold_start"
        assert row["warehouse_quantity"] == 7
        assert row["order_quantity"] is None

    def test_pair_history_yields_computed_row_with_baseline_warning(
        self, client, db_session
    ):
        seed_pair_history(db_session, product_quantity=0)

        body = client.get("/recommendations").json()

        row = body["recommendations"][0]
        assert row["status"] == "order"  # stock=0 → заказать точно надо
        assert row["model"] == "baseline_moving_average_7"
        assert row["order_quantity"] >= 1
        assert row["forecast_demand"] > 0
        assert body["warning"] is not None  # честность: истории < 30 дней

    def test_unknown_product_id_filter_returns_empty_list(self, client):
        response = client.get("/recommendations", params={"product_id": 999})

        assert response.status_code == 200
        assert response.json()["recommendations"] == []


class TestValidation:
    def test_cross_rule_window_over_14_rejected_by_service(self, client):
        """L+H=15: Query по отдельности валиден, перекрёстное правило — сервис."""
        response = client.get(
            "/recommendations",
            params={"lead_time_days": 8, "horizon_days": 7},
        )

        assert response.status_code == 422
        assert "14" in response.json()["detail"]

    def test_simple_bounds_rejected_by_query(self, client):
        for bad in (
            {"service_level": 1.5},
            {"service_level": 0.0},
            {"lead_time_days": 0},
            {"horizon_days": -1},
        ):
            response = client.get("/recommendations", params=bad)
            assert response.status_code == 422, bad

    def test_max_window_boundary_is_accepted(self, client):
        response = client.get(
            "/recommendations",
            params={"lead_time_days": 7, "horizon_days": 7},
        )

        assert response.status_code == 200  # пустой список, но окно валидно
