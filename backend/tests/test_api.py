"""API 統合テスト(モックLLM + 一時SQLiteで実行)。"""
import pytest
from fastapi.testclient import TestClient

from app import main, posts
from app.llm import MockLLM
from app.posts import SQLiteStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # LLM はモック、投稿ストアは一時DBに差し替えて隔離する
    monkeypatch.setattr(main, "llm", MockLLM())
    monkeypatch.setattr(posts, "_store", SQLiteStore(tmp_path / "posts.sqlite3"))
    main._histories.clear()
    main._pending_posts.clear()
    return TestClient(main.app)


def _chat(client, text, session_id="s1", area="三国"):
    res = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "user_id": "u1",
            "text": text,
            "area": area,
            "display_name": "テストじいちゃん",
        },
    )
    assert res.status_code == 200
    return res.json()


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_chat_returns_no_consult_info(client):
    data = _chat(client, "今日はいい天気だね")
    assert data["category"] == "chat"
    assert data["consult_info"] is None


def test_consult_always_includes_office_for_users_area(client):
    data = _chat(client, "腰が痛くて買い物がつらい", area="三国")
    assert data["category"] == "consult"
    assert data["consult_info"]["office"] == "三国地域包括支援センター"
    assert data["consult_info"]["phone"]


def test_story_then_consent_creates_post(client):
    proposal = _chat(client, "昔の祭りの思い出でなあ")
    assert proposal["category"] == "story"
    assert proposal["post_proposal"]

    consent = _chat(client, "いいよ、投稿して")
    assert consent["posted"] is True

    feed = client.get("/api/posts").json()
    assert len(feed) == 1
    assert feed[0]["display_name"] == "テストじいちゃん"


def test_story_then_refusal_does_not_post(client):
    _chat(client, "昔の祭りの思い出でなあ")
    refusal = _chat(client, "いや、やめておくよ")
    assert refusal["posted"] is False

    assert client.get("/api/posts").json() == []


def test_validation_rejects_empty_text(client):
    res = client.post(
        "/api/chat",
        json={"session_id": "s1", "user_id": "u1", "text": ""},
    )
    assert res.status_code == 422
