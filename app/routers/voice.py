"""POST /api/voice-chat - 音声入力・音声出力に対応したチャットAPI。

ブラウザで録音した音声ファイル(multipart/form-data)を受け取り、
1. 音声認識(STT)でテキスト化
2. 対話LLM・ルーター・窓口検索(共通サービス)で応答生成
3. 音声合成(TTS)で応答音声を生成
した結果をまとめて返す。

STT/TTS が環境変数で設定されていない場合でも、テキストの応答は返せるように
フォールバックする(ページ・APIとしては利用可能な状態を保つ)。
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.dependencies import get_stt_service, get_tts_service
from app.schemas import VoiceChatResponse
from app.services.conversation import process_utterance
from app.services.speech import SpeechToTextService, TextToSpeechService

router = APIRouter(prefix="/api", tags=["voice"])

_STT_UNAVAILABLE_REPLY = (
    "申し訳ございません、うまく聞き取れませんでした。"
    "もう一度お話しいただくか、画面下のテキスト欄に入力してみてください。"
)


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str = Form(default="demo-session"),
    user_id: str = Form(default="demo-user"),
    area: str | None = Form(default=None),
    stt: SpeechToTextService = Depends(get_stt_service),
    tts: TextToSpeechService = Depends(get_tts_service),
) -> VoiceChatResponse:
    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/wav"

    transcript = await stt.transcribe(audio_bytes, content_type)

    if transcript:
        result = await process_utterance(transcript, area)
        reply = result.reply
        category = result.category
        consult_info = result.consult_info
        post_proposal = result.post_proposal
    else:
        reply = _STT_UNAVAILABLE_REPLY
        category = "chat"
        consult_info = None
        post_proposal = None

    synthesis = await tts.synthesize(reply)
    audio_base64 = None
    audio_content_type = None
    if synthesis is not None:
        audio_bytes_out, audio_content_type = synthesis
        audio_base64 = base64.b64encode(audio_bytes_out).decode("ascii")

    return VoiceChatResponse(
        transcript=transcript,
        reply=reply,
        category=category,
        consult_info=consult_info,
        post_proposal=post_proposal,
        audio_base64=audio_base64,
        audio_content_type=audio_content_type,
        tts_available=tts.available,
        stt_available=stt.available,
    )
