"""API tests for the stores slice (FR-3, FR-4, FR-11)."""
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


# --- FR-3 -------------------------------------------------------------------


def test_create_store_returns_trimmed_name(client):
    response = client.post("/stores", json={"name": "  Магнит  "})

    assert response.status_code == 201
    assert response.json()["name"] == "Магнит"  # D-1


def test_create_store_rejects_whitespace_only_name(client):
    response = client.post("/stores", json={"name": "   "})

    assert response.status_code == 400  # BR-1
    assert "BR-1" in response.json()["detail"]


def test_create_store_rejects_duplicate_case_insensitive(client):
    client.post("/stores", json={"name": "Магнит"})
    response = client.post("/stores", json={"name": "магнит"})

    assert response.status_code == 409  # BR-4
    assert "BR-4" in response.json()["detail"]


# --- FR-4 -------------------------------------------------------------------


def test_delete_store_removes_from_list_and_frees_name(client):
    client.post("/stores", json={"name": "Магнит"})

    assert client.delete("/stores/Магнит").status_code == 204
    assert client.get("/stores").json() == []

    # Soft delete frees the name (ADR-0005 partial index).
    assert client.post("/stores", json={"name": "магнит"}).status_code == 201


def test_delete_unknown_store(client):
    response = client.delete("/stores/Магнит")

    assert response.status_code == 404  # EL-8


# --- FR-11 ------------------------------------------------------------------


def test_list_empty_is_not_an_error(client):
    response = client.get("/stores")

    assert response.status_code == 200
    assert response.json() == []


def test_list_ordering_case_insensitive(client):
    for name in ["Ярче", "ашан", "Магнит"]:
        client.post("/stores", json={"name": name})

    names = [s["name"] for s in client.get("/stores").json()]

    assert names == ["ашан", "Магнит", "Ярче"]
