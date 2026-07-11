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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.config import get_settings
from app.dependencies import get_stt_service, get_tts_service
from app.schemas import VoiceChatResponse
from app.services.conversation import process_utterance
from app.services.speech import SpeechToTextService, TextToSpeechService

router = APIRouter(prefix="/api", tags=["voice"])

_STT_UNAVAILABLE_REPLY = (
    "申し訳ございません、うまく聞き取れませんでした。"
    "もう一度お話しいただくか、画面下のテキスト欄に入力してみてください。"
)

_UPLOAD_TOO_LARGE_DETAIL = "音声ファイルが大きすぎます。もう少し短く録音してから、もう一度お試しください。"


def _reject_if_content_length_too_large(request: Request, max_bytes: int) -> None:
    """Content-Length ヘッダーの時点で明らかに大きすぎる場合は、
    音声本体を読み込む前に早期リジェクトする(不要なメモリ確保・処理を避ける)。

    ヘッダーが無い・不正な場合は判定できないため、実サイズでの
    チェック(``_reject_if_audio_too_large``)に委ねる。
    """
    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    try:
        if int(content_length) > max_bytes:
            raise HTTPException(status_code=413, detail=_UPLOAD_TOO_LARGE_DETAIL)
    except ValueError:
        return


def _reject_if_audio_too_large(audio_bytes: bytes, max_bytes: int) -> None:
    if len(audio_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=_UPLOAD_TOO_LARGE_DETAIL)


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    request: Request,
    audio: UploadFile = File(...),
    session_id: str = Form(default="demo-session"),
    user_id: str = Form(default="demo-user"),
    area: str | None = Form(default=None),
    stt: SpeechToTextService = Depends(get_stt_service),
    tts: TextToSpeechService = Depends(get_tts_service),
) -> VoiceChatResponse:
    max_upload_bytes = get_settings().voice_max_upload_bytes
    _reject_if_content_length_too_large(request, max_upload_bytes)

    audio_bytes = await audio.read()
    _reject_if_audio_too_large(audio_bytes, max_upload_bytes)

    content_type = audio.content_type or "audio/wav"

    transcript = await stt.transcribe(audio_bytes, content_type)

    if transcript:
        result = await process_utterance(transcript, area, session_id)
        reply = result.reply
        category = result.category
        consult_info = result.consult_info
        post_proposal = result.post_proposal
        awaiting_confirmation = result.awaiting_confirmation
        posted = result.posted
    else:
        reply = _STT_UNAVAILABLE_REPLY
        category = "chat"
        consult_info = None
        post_proposal = None
        awaiting_confirmation = False
        posted = False

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
        awaiting_confirmation=awaiting_confirmation,
        posted=posted,
    )
