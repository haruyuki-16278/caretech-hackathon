from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_returns_chat_category_for_casual_talk():
    response = client.post(
        "/api/chat",
        json={"session_id": "s1", "text": "今日はいい天気ですね"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "chat"
    assert body["consult_info"] is None
    assert body["reply"]


def test_chat_returns_consult_category_with_office_info():
    response = client.post(
        "/api/chat",
        json={"session_id": "s2", "text": "腰が痛くて買い物に行くのがつらいんだよ", "area": "丸岡"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "consult"
    assert body["consult_info"] is not None
    assert body["consult_info"]["office"] == "丸岡地域包括支援センター"
    assert body["consult_info"]["phone"] == "0776-68-1130"
    assert "丸岡地域包括支援センター" in body["reply"]


def test_chat_consult_without_area_still_returns_some_office():
    """相談カテゴリでは、居住エリア不明でも必ず窓口情報を返す(要件上の必須事項)。"""
    response = client.post(
        "/api/chat",
        json={"session_id": "s3", "text": "最近眠れなくて悩んでいます"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "consult"
    assert body["consult_info"] is not None


def test_chat_returns_story_category_with_post_proposal():
    response = client.post(
        "/api/chat",
        json={"session_id": "s4", "text": "昔、こんな面白いことがあってなぁ"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "story"
    assert body["post_proposal"]


def test_chat_requires_text_field():
    response = client.post("/api/chat", json={"session_id": "s5"})
    assert response.status_code == 422
