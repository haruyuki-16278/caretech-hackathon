"""音声入力(STT)・音声出力(TTS)のサービス層。

Azure Speech が環境変数で設定されている場合はそれを利用し、
未設定または呼び出し失敗時は None を返す(呼び出し側でフォールバック処理を行う)。
これにより、クレデンシャルが無い環境でもページ・APIそのものは動作し続ける。
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_TTS_OUTPUT_FORMAT = "audio-16khz-32kbitrate-mono-mp3"
_TTS_CONTENT_TYPE = "audio/mpeg"


class SpeechToTextService:
    """録音済み音声(バイト列)をテキストに変換する。"""

    @property
    def available(self) -> bool:
        return get_settings().azure_speech.configured

    async def transcribe(self, audio_bytes: bytes, content_type: str) -> Optional[str]:
        settings = get_settings().azure_speech
        if not settings.configured:
            return None

        url = (
            f"https://{settings.region}.stt.speech.microsoft.com/speech/recognition/"
            f"conversation/cognitiveservices/v1?language={settings.stt_language}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.key,
            "Content-Type": content_type or "audio/wav",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, content=audio_bytes)
                response.raise_for_status()
                data = response.json()
                text = data.get("DisplayText")
                return text.strip() if text else None
        except Exception:  # noqa: BLE001 - 外部API障害時はフォールバックさせるため広く捕捉
            logger.warning("音声認識(STT)に失敗しました", exc_info=True)
            return None


class TextToSpeechService:
    """応答テキストを音声(バイト列)に変換する。"""

    @property
    def available(self) -> bool:
        return get_settings().azure_speech.configured

    async def synthesize(self, text: str) -> Optional[tuple[bytes, str]]:
        settings = get_settings().azure_speech
        if not settings.configured:
            return None

        url = f"https://{settings.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": settings.key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": _TTS_OUTPUT_FORMAT,
        }
        ssml = _build_ssml(text, settings.stt_language, settings.tts_voice)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
                response.raise_for_status()
                return response.content, _TTS_CONTENT_TYPE
        except Exception:  # noqa: BLE001 - 外部API障害時はフォールバックさせるため広く捕捉
            logger.warning("音声合成(TTS)に失敗しました", exc_info=True)
            return None


def _build_ssml(text: str, language: str, voice: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<speak version="1.0" xml:lang="{language}">'
        f'<voice xml:lang="{language}" name="{voice}">{escaped}</voice>'
        "</speak>"
    )
