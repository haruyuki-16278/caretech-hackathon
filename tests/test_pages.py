from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_page_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "話しかける" in response.text


def test_index_page_includes_consult_note_element():
    """相談窓口が複数該当し地区を特定できない場合の補足メッセージ表示欄が存在すること。"""
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="consult-note"' in response.text


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_assets_served():
    js_response = client.get("/static/js/app.js")
    assert js_response.status_code == 200

    css_response = client.get("/static/css/style.css")
    assert css_response.status_code == 200
