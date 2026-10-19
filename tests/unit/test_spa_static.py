"""Unit tests: SPAStaticFiles — поведение фолбэка (ADR-0009).

Класс тестируется изолированно на tmp-каталоге: реальный frontend/dist
в сборке CI отсутствует, а контракт (неизвестный путь → index.html,
неизвестный /api/* → JSON 404) не зависит от содержимого каталога.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import SPAStaticFiles


def make_spa_app(tmp_path) -> FastAPI:
    (tmp_path / "index.html").write_text("<html>spa</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory=str(tmp_path), html=True), name="spa")
    return app


def test_root_serves_index_html(tmp_path):
    client = TestClient(make_spa_app(tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "spa" in response.text


def test_real_asset_is_served_as_is(tmp_path):
    client = TestClient(make_spa_app(tmp_path))

    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_unknown_spa_route_falls_back_to_index_html(tmp_path):
    """Refresh на /forecast не должен давать 404 — клиентский роутер рисует."""
    client = TestClient(make_spa_app(tmp_path))

    response = client.get("/forecast")

    assert response.status_code == 200
    assert "spa" in response.text


def test_unknown_api_path_stays_json_404(tmp_path):
    """Неизвестный /api/* — ошибка API, а не HTML-страница."""
    client = TestClient(make_spa_app(tmp_path))

    response = client.get("/api/nope")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "spa" not in response.text
