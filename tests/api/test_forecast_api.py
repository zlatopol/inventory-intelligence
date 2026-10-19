"""API tests: /api/forecast — контракт ответа и ошибки (без обучения модели)."""
import pytest
from fastapi.testclient import TestClient

from app.forecast.router import get_forecast_service
from app.forecast.service import ForecastService
from app.main import create_app
from app.ml.sources import load_from_stock_event
from app.shared.db import get_session


@pytest.fixture
def client(db_session):
    app = create_app()

    # Переопределяем САМ СЕРВИС (синглтон в провайдере обходит override сессии
    # и ходил бы в dev-базу с сид-данными — поймано живым прогоном).
    app.dependency_overrides[get_forecast_service] = lambda: ForecastService(
        history_loader=lambda: load_from_stock_event(db_session)
    )
    with TestClient(app) as test_client:
        yield test_client


def test_unknown_pair_returns_404(client):
    response = client.get("/api/forecast", params={"store_id": 1, "product_id": 1})

    assert response.status_code == 404
    assert "нет пары" in response.json()["detail"]


def test_days_validation_bounds(client):
    for bad_days in (0, 15, -1):
        response = client.get(
            "/api/forecast",
            params={"store_id": 1, "product_id": 1, "days": bad_days},
        )
        assert response.status_code == 422  # Query(ge=1, le=14)

    ok = client.get(
        "/api/forecast", params={"store_id": 1, "product_id": 1, "days": 1}
    )
    assert ok.status_code == 404  # валидация прошла; упали уже в домене (нет пары)
