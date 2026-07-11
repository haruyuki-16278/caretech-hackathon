"""担当A(音声入力)と担当B(LLM/窓口)の境界にある共通処理。

テキスト発話を受け取り、分類・窓口検索・応答生成をまとめて行う。
/api/chat と /api/voice-chat の両方から利用される共通サービス。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.schemas import Category, ConsultInfo
from app.services.chat import generate_reply
from app.services.offices import get_office_directory
from app.services.router import classify_utterance


@dataclass
class ConversationResult:
    reply: str
    category: Category
    consult_info: Optional[ConsultInfo]
    post_proposal: Optional[str] = None


async def process_utterance(text: str, area: Optional[str] = None) -> ConversationResult:
    category = classify_utterance(text)

    consult_info: Optional[ConsultInfo] = None
    if category == "consult":
        directory = get_office_directory()
        consult_info = directory.find(area)

    reply = await generate_reply(category, text, consult_info)

    post_proposal = reply if category == "story" else None

    return ConversationResult(
        reply=reply,
        category=category,
        consult_info=consult_info,
        post_proposal=post_proposal,
    )
