"""API tests for the products slice (FR-1, FR-2, FR-5, FR-6).

Run against a real PostgreSQL test database (dependency override points the app
at the test session) — validation, error mapping and happy paths end-to-end.
"""
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


# --- FR-1 -------------------------------------------------------------------


def test_create_product_returns_trimmed_name_and_zero_quantity(client):
    response = client.post("/products", json={"name": "  Молоко  "})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Молоко"  # D-1
    assert body["warehouse_quantity"] == 0  # EL-2


def test_create_product_rejects_whitespace_only_name(client):
    response = client.post("/products", json={"name": "   "})

    assert response.status_code == 400  # BR-1 via EmptyNameError
    assert "BR-1" in response.json()["detail"]


def test_create_product_rejects_duplicate_case_insensitive(client):
    client.post("/products", json={"name": "Молоко"})
    response = client.post("/products", json={"name": "молоко"})

    assert response.status_code == 409  # BR-2
    assert "BR-2" in response.json()["detail"]


# --- FR-5 -------------------------------------------------------------------


def test_receive_increases_quantity(client):
    client.post("/products", json={"name": "Сахар"})

    response = client.post("/products/Сахар/receipts", json={"quantity": 5})

    assert response.status_code == 200
    assert response.json()["warehouse_quantity"] == 5


def test_receive_rejects_zero_quantity(client):
    client.post("/products", json={"name": "Сахар"})

    response = client.post("/products/Сахар/receipts", json={"quantity": 0})

    assert response.status_code == 422  # BR-5 via InvalidReceiptQuantityError
    assert "BR-5" in response.json()["detail"]


def test_receive_rejects_fractional_quantity_at_validation(client):
    client.post("/products", json={"name": "Сахар"})

    response = client.post("/products/Сахар/receipts", json={"quantity": 2.5})

    assert response.status_code == 422  # Pydantic: not an integer at all


def test_receive_unknown_product(client):
    response = client.post("/products/Сахар/receipts", json={"quantity": 5})

    assert response.status_code == 404  # EL-7


# --- FR-2 -------------------------------------------------------------------


def test_delete_product_with_stock_blocked(client):
    client.post("/products", json={"name": "Сахар"})
    client.post("/products/Сахар/receipts", json={"quantity": 250})

    response = client.delete("/products/Сахар")

    assert response.status_code == 409  # BR-3
    names = [p["name"] for p in client.get("/products").json()]
    assert names == ["Сахар"]  # list unchanged on rejection


def test_delete_product_and_free_the_name(client):
    client.post("/products", json={"name": "Сахар"})

    assert client.delete("/products/Сахар").status_code == 204
    names = [p["name"] for p in client.get("/products").json()]
    assert names == []  # gone from the live list

    # Soft delete frees the name (ADR-0005 partial index).
    assert client.post("/products", json={"name": "сахар"}).status_code == 201


def test_delete_unknown_product(client):
    response = client.delete("/products/Сахар")

    assert response.status_code == 404


# --- FR-6 -------------------------------------------------------------------


def test_list_empty_warehouse_is_not_an_error(client):
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_list_ordering_case_insensitive(client):
    for name in ["Яблоки", "ананас", "Банан"]:
        client.post("/products", json={"name": name})

    names = [p["name"] for p in client.get("/products").json()]

    assert names == ["ананас", "Банан", "Яблоки"]  # EL-10
