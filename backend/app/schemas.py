"""API リクエスト/レスポンスのスキーマ(docs/REQUIREMENTS.md §8 準拠)。"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["chat", "consult", "story"]


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    # 居住エリア(あわら / 三国 / 丸岡 / 春江 / 坂井)。未指定時は坂井を既定とする
    area: str = "坂井"
    display_name: str = "名無しさん"


class ConsultInfo(BaseModel):
    municipality: str
    area: str
    office: str
    field: str
    address: Optional[str] = None
    phone: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    category: Category
    consult_info: Optional[ConsultInfo] = None
    post_proposal: Optional[str] = None
    # 直前の投稿提案に同意して投稿が作成された場合 True
    posted: bool = False


class Post(BaseModel):
    id: int
    display_name: str
    body: str
    created_at: str
