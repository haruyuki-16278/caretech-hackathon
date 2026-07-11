"""担当A(音声入力)と担当B(LLM/窓口)の境界にある共通処理。

テキスト発話を受け取り、分類・窓口検索・応答生成をまとめて行う。
/api/chat と /api/voice-chat の両方から利用される共通サービス。

session_id ごとに直近の会話履歴・投稿確認待ち状態を保持する簡易な
セッションコンテキスト(app.services.session_store)を持ち、
`story` に分類された発話の後、次のターンで「はい/いいえ」の
投稿許可フロー(F6)を最小限判定する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.schemas import Category, ConsultInfo
from app.services.chat import generate_reply
from app.services.offices import get_office_directory
from app.services.router import classify_utterance
from app.services.session_store import get_session_store

_AFFIRMATIVE_KEYWORDS = [
    "はい", "うん", "ええ", "お願いします", "お願いね", "お願い",
    "いいよ", "いいです", "投稿して", "紹介して", "ok", "OK", "オッケー",
]
_NEGATIVE_KEYWORDS = [
    "いいえ", "やめて", "やめとく", "いや", "結構です", "しないで", "不要です", "だめ",
]

_STORY_DECLINED_REPLY = "承知しました。無理にお伝えしなくて大丈夫ですよ。またいつでもお話しくださいね。"
_STORY_CONFIRMED_REPLY = "ありがとうございます!素敵なお話を、みんなにもご紹介させていただきますね。"


@dataclass
class ConversationResult:
    reply: str
    category: Category
    consult_info: Optional[ConsultInfo]
    post_proposal: Optional[str] = None
    awaiting_confirmation: bool = False
    posted: bool = False


def _is_negative(text: str) -> bool:
    return any(keyword in text for keyword in _NEGATIVE_KEYWORDS)


def _is_affirmative(text: str) -> bool:
    if _is_negative(text):
        return False
    return any(keyword in text for keyword in _AFFIRMATIVE_KEYWORDS)


async def process_utterance(
    text: str,
    area: Optional[str] = None,
    session_id: str = "demo-session",
) -> ConversationResult:
    session = get_session_store().get(session_id)

    # story提案への「はい/いいえ」の判定(F6: 投稿許可フロー)。
    # 会話履歴には記録するが、ルーターによる再分類は行わない
    # (「はい」のような短い返答はカテゴリ判定に馴染まないため)。
    if session.pending_story is not None:
        if _is_negative(text):
            session.pending_story = None
            session.add_turn("user", text)
            session.add_turn("assistant", _STORY_DECLINED_REPLY)
            return ConversationResult(
                reply=_STORY_DECLINED_REPLY,
                category="story",
                consult_info=None,
                post_proposal=None,
                awaiting_confirmation=False,
                posted=False,
            )
        if _is_affirmative(text):
            confirmed_story = session.pending_story
            session.pending_story = None
            session.add_turn("user", text)
            session.add_turn("assistant", _STORY_CONFIRMED_REPLY)
            return ConversationResult(
                reply=_STORY_CONFIRMED_REPLY,
                category="story",
                consult_info=None,
                post_proposal=confirmed_story,
                awaiting_confirmation=False,
                posted=True,
            )
        # 「はい/いいえ」のどちらとも取れない場合は、通常の発話として処理を続ける
        # (pending_story はクリアせず、後で改めて確認できるようにする)。

    category = classify_utterance(text)

    consult_info: Optional[ConsultInfo] = None
    if category == "consult":
        directory = get_office_directory()
        consult_info = directory.find(area)

    reply = await generate_reply(category, text, consult_info, history=session.history)

    post_proposal = reply if category == "story" else None
    if category == "story":
        session.pending_story = text

    session.add_turn("user", text)
    session.add_turn("assistant", reply)

    return ConversationResult(
        reply=reply,
        category=category,
        consult_info=consult_info,
        post_proposal=post_proposal,
        awaiting_confirmation=category == "story",
        posted=False,
    )
