"""API tests: FR-7 — товары по магазинам, полный жизненный цикл через эндпоинты."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.shared.db import get_session


@pytest.fixture
def client(db_session):
    app = create_app()

    def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as test_client:
        yield test_client


def seed_and_ship(client, product_qty: int = 10, request_qty: int = 5) -> None:
    client.post("/products", json={"name": "Сахар"})
    client.post("/products/Сахар/receipts", json={"quantity": product_qty})
    client.post("/stores", json={"name": "Магнит"})
    client.post("/stores", json={"name": "Пустой"})
    number = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": request_qty},
    ).json()["number"]
    client.post(f"/requests/{number}/process")


def test_fr7_nested_shape_after_shipment(client):
    seed_and_ship(client)

    stock = client.get("/stores/stock").json()

    assert stock == [
        {"name": "Магнит", "products": [{"name": "Сахар", "quantity": 5}]},
        {"name": "Пустой", "products": []},  # EL-21: показан с пустым списком
    ]


def test_fr7_empty_store_list_is_not_an_error(client):
    assert client.get("/stores/stock").json() == []


def test_fr7_reflects_processing(client):
    seed_and_ship(client)

    before = client.get("/stores/stock").json()
    number = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": 3},
    ).json()["number"]
    client.post(f"/requests/{number}/process")

    after = client.get("/stores/stock").json()

    magnit_before = before[0]["products"][0]["quantity"]
    magnit_after = after[0]["products"][0]["quantity"]
    assert (magnit_before, magnit_after) == (5, 8)  # накапливается отгрузками
