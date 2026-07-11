"""API のリクエスト/レスポンススキーマ。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["chat", "consult", "story"]


class ConsultInfo(BaseModel):
    municipality: str
    area: str
    office: str
    field: str
    address: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str = Field(default="demo-session")
    user_id: str = Field(default="demo-user")
    text: str
    area: Optional[str] = Field(
        default=None,
        description="利用者の居住エリア(市町村・地区名など)。最寄りの相談窓口検索に使用する。",
    )


class ChatResponse(BaseModel):
    reply: str
    category: Category
    consult_info: Optional[ConsultInfo] = None
    post_proposal: Optional[str] = None
    transcript: Optional[str] = None


class VoiceChatResponse(BaseModel):
    transcript: Optional[str] = Field(
        default=None, description="音声認識結果。認識できなかった場合は null。"
    )
    reply: str
    category: Category
    consult_info: Optional[ConsultInfo] = None
    post_proposal: Optional[str] = None
    audio_base64: Optional[str] = Field(
        default=None, description="応答音声(base64エンコード)。音声合成が利用できない場合は null。"
    )
    audio_content_type: Optional[str] = None
    tts_available: bool = False
    stt_available: bool = False
