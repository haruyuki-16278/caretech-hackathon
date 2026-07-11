from __future__ import annotations

import asyncio
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_stt_service, get_tts_service
from app.main import app


class FakeSTT:
    """テスト用の音声認識スタブ。"""

    def __init__(self, transcript: Optional[str], available: bool = True):
        self._transcript = transcript
        self._available = available

    @property
    def available(self) -> bool:
        return self._available

    async def transcribe(self, audio_bytes: bytes, content_type: str) -> Optional[str]:
        return self._transcript


class FakeTTS:
    """テスト用の音声合成スタブ。"""

    def __init__(self, audio: Optional[tuple[bytes, str]], available: bool = True):
        self._audio = audio
        self._available = available

    @property
    def available(self) -> bool:
        return self._available

    async def synthesize(self, text: str):
        return self._audio


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _override(stt=None, tts=None):
    if stt is not None:
        app.dependency_overrides[get_stt_service] = lambda: stt
    if tts is not None:
        app.dependency_overrides[get_tts_service] = lambda: tts


def test_voice_chat_returns_audio_when_stt_and_tts_available(client):
    _override(
        stt=FakeSTT("最近腰が痛くて困っています"),
        tts=FakeTTS((b"FAKE_AUDIO_BYTES", "audio/mpeg")),
    )

    response = client.post(
        "/api/voice-chat",
        data={"session_id": "s1", "area": "丸岡"},
        files={"audio": ("recording.webm", b"dummy-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "最近腰が痛くて困っています"
    assert body["category"] == "consult"
    assert body["consult_info"]["office"] == "丸岡地域包括支援センター"
    assert body["audio_base64"] is not None
    assert body["audio_content_type"] == "audio/mpeg"
    assert body["tts_available"] is True
    assert body["stt_available"] is True


def test_voice_chat_falls_back_when_stt_unavailable(client):
    _override(stt=FakeSTT(None, available=False), tts=FakeTTS(None, available=False))

    response = client.post(
        "/api/voice-chat",
        data={"session_id": "s2"},
        files={"audio": ("recording.webm", b"dummy-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] is None
    assert body["category"] == "chat"
    assert "聞き取れませんでした" in body["reply"]
    assert body["audio_base64"] is None
    assert body["tts_available"] is False
    assert body["stt_available"] is False


def test_voice_chat_chat_category_has_no_consult_info(client):
    _override(stt=FakeSTT("今日はいい天気ですね"), tts=FakeTTS(None, available=False))

    response = client.post(
        "/api/voice-chat",
        data={"session_id": "s3"},
        files={"audio": ("recording.webm", b"dummy-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "chat"
    assert body["consult_info"] is None
    assert body["audio_base64"] is None
