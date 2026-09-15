"""API tests for the requests slice (FR-8, FR-9, FR-10 + BR-8 end-to-end)."""
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


def seed_stock(client, quantity: int = 10) -> None:
    client.post("/products", json={"name": "Сахар"})
    client.post("/products/Сахар/receipts", json={"quantity": quantity})
    client.post("/stores", json={"name": "Магнит"})


def submit(client, quantity: int = 5) -> int:
    """D1: номер заявки — только из ответа (sequence не сбрасывается)."""
    response = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": quantity},
    )
    assert response.status_code == 201
    return response.json()["number"]


# --- FR-8 -------------------------------------------------------------------


def test_submit_creates_request_with_russian_status(client):
    seed_stock(client)

    response = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "подана"  # развилка A: перевод на краю API
    assert body["store_name"] == "Магнит"
    assert body["processed_at"] is None
    assert isinstance(body["number"], int)


def test_submit_response_names_are_trimmed(client):
    seed_stock(client)

    response = client.post(
        "/requests",
        json={"store_name": "  Магнит  ", "product_name": "Сахар", "quantity": 5},
    )

    assert response.json()["store_name"] == "Магнит"  # D-1: сохранённое написание


def test_submit_unknown_store_404(client):
    client.post("/products", json={"name": "Сахар"})

    response = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": 5},
    )

    assert response.status_code == 404  # EL-8


def test_submit_unknown_product_404(client):
    client.post("/stores", json={"name": "Магнит"})

    response = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": 5},
    )

    assert response.status_code == 404  # EL-7


def test_submit_zero_quantity_422(client):
    seed_stock(client)

    response = client.post(
        "/requests",
        json={"store_name": "Магнит", "product_name": "Сахар", "quantity": 0},
    )

    assert response.status_code == 422  # BR-6 via service
    assert "BR-6" in response.json()["detail"]


# --- FR-9 -------------------------------------------------------------------


def test_full_lifecycle_process_updates_stock_and_status(client):
    seed_stock(client, quantity=10)
    number = submit(client, quantity=5)

    processed = client.post(f"/requests/{number}/process")

    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "обработана"
    assert body["processed_at"] is not None
    assert body["store_name"] == "Магнит"  # имена — из join, не из payload

    stock = client.get("/products").json()[0]["warehouse_quantity"]
    assert stock == 5  # склад уменьшился — виден через FR-6


def test_reprocess_returns_409(client):
    seed_stock(client)
    number = submit(client)

    client.post(f"/requests/{number}/process")
    response = client.post(f"/requests/{number}/process")

    assert response.status_code == 409  # EL-15
    assert "обработана" in response.json()["detail"]


def test_process_insufficient_stock_409(client):
    seed_stock(client, quantity=2)
    number = submit(client, quantity=5)

    response = client.post(f"/requests/{number}/process")

    assert response.status_code == 409  # BR-7
    assert "BR-7" in response.json()["detail"]


def test_process_unknown_request_404(client):
    response = client.post("/requests/999999/process")

    assert response.status_code == 404


# --- FR-10 ------------------------------------------------------------------


def test_list_shows_all_requests_ordered_by_number(client):
    seed_stock(client)
    numbers = [submit(client) for _ in range(3)]

    listed = client.get("/requests").json()

    assert [r["number"] for r in listed] == sorted(numbers)  # порядок по номеру
    assert {r["status"] for r in listed} == {"подана"}


def test_list_empty_is_not_an_error(client):
    assert client.get("/requests").json() == []


# --- BR-8: end-to-end (slices 2+3 together) ---------------------------------


def test_store_deletion_blocked_by_pending_request_then_allowed(client):
    seed_stock(client)
    number = submit(client)

    blocked = client.delete("/stores/Магнит")

    assert blocked.status_code == 409  # BR-8
    assert "BR-8" in blocked.json()["detail"]

    client.post(f"/requests/{number}/process")  # заявка обработана — блокировка снята
    assert client.delete("/stores/Магнит").status_code == 204
