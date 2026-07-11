"""FastAPI の Depends 経由で注入するサービスのプロバイダ。

テストではこれらの関数を app.dependency_overrides で差し替えることで、
外部サービス(Azure Speech 等)を使わずに決定的なテストを行える。
"""
from __future__ import annotations

from app.services.speech import SpeechToTextService, TextToSpeechService

_stt_service = SpeechToTextService()
_tts_service = TextToSpeechService()


def get_stt_service() -> SpeechToTextService:
    return _stt_service


def get_tts_service() -> TextToSpeechService:
    return _tts_service
