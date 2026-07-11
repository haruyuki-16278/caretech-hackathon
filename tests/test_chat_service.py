"""対話LLM(app.services.chat)のテスト。

Azure OpenAI への実際のネットワーク呼び出しは行わず、
``httpx.MockTransport`` を使ってHTTP呼び出しパスを検証する。
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import httpx
import pytest

from app.services import chat as chat_service


def _configure_azure_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example-openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "dummy-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")


def _mock_client_factory(handler):
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=10.0)

    return factory


def _run(coro):
    return asyncio.run(coro)


def test_call_azure_openai_sends_expected_request_and_parses_reply(monkeypatch):
    _configure_azure_openai(monkeypatch)

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  こんにちは、元気そうでなによりです。 "}}]},
        )

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    reply = _run(chat_service.generate_reply("chat", "こんにちは", consult_info=None))

    assert reply == "こんにちは、元気そうでなによりです。"
    assert captured["url"].startswith("https://example-openai.azure.com/openai/deployments/dummy-deployment/")
    assert captured["headers"]["api-key"] == "dummy-key"
    assert captured["payload"]["messages"][-1] == {"role": "user", "content": "こんにちは"}


@pytest.mark.parametrize(
    "category,expected_keyword",
    [
        ("chat", "雑談"),
        ("consult", "相談"),
        ("story", "投稿"),
    ],
)
def test_system_prompt_is_category_specific(monkeypatch, category, expected_keyword):
    _configure_azure_openai(monkeypatch)

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "応答です"}}]})

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    _run(chat_service.generate_reply(category, "テスト発話", consult_info=None))

    system_message = captured["payload"]["messages"][0]
    assert system_message["role"] == "system"
    assert expected_keyword in system_message["content"]


def test_story_system_prompt_requires_confirmation_question(monkeypatch):
    _configure_azure_openai(monkeypatch)

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "いい話ですね"}}]})

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    _run(chat_service.generate_reply("story", "昔はよく山に登ったものだよ", consult_info=None))

    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "投稿" in system_prompt
    assert "尋ね" in system_prompt or "確認" in system_prompt


def test_history_turns_are_included_in_messages(monkeypatch):
    _configure_azure_openai(monkeypatch)

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "続きを聞かせてください"}}]})

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    history = [("user", "昔、川で魚を釣ったんだよ"), ("assistant", "それは楽しそうですね")]
    _run(
        chat_service.generate_reply(
            "story", "その魚は大きかったんだ", consult_info=None, history=history
        )
    )

    messages = captured["payload"]["messages"]
    # system, history(2), latest user の順で並ぶこと
    assert messages[1] == {"role": "user", "content": "昔、川で魚を釣ったんだよ"}
    assert messages[2] == {"role": "assistant", "content": "それは楽しそうですね"}
    assert messages[3] == {"role": "user", "content": "その魚は大きかったんだ"}


def test_falls_back_to_rule_based_reply_when_azure_call_fails(monkeypatch):
    _configure_azure_openai(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    reply = _run(chat_service.generate_reply("chat", "こんにちは", consult_info=None))

    assert "お話を聞かせてくださって" in reply


def test_falls_back_when_azure_openai_not_configured(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)

    reply = _run(chat_service.generate_reply("chat", "こんにちは", consult_info=None))

    assert "お話を聞かせてくださって" in reply


def test_consult_reply_appends_office_info_and_note(monkeypatch):
    from app.schemas import ConsultInfo

    _configure_azure_openai(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "お辛いですね"}}]})

    monkeypatch.setattr(chat_service, "_build_async_client", _mock_client_factory(handler))

    consult_info = ConsultInfo(
        municipality="坂井市",
        area="広域",
        office="坂井地区広域連合(保険者)",
        field="介護保険",
        note="坂井市には複数の相談窓口があります(三国・丸岡・春江・坂井)。",
    )

    reply: Optional[str] = _run(
        chat_service.generate_reply("consult", "困っています", consult_info=consult_info)
    )

    assert "坂井地区広域連合(保険者)" in reply
    assert "複数の相談窓口があります" in reply
