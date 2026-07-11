"""対話LLM(F2)による応答生成。

Azure OpenAI が設定されている場合はそれを用い、未設定または呼び出し失敗時は
高齢者向けの共感的なトーンを保った簡易応答(ルールベース)にフォールバックする。

カテゴリ(chat / consult / story)ごとに、求める振る舞いが異なるため、
システムプロンプトもカテゴリごとに切り替える(F3〜F6 の要件を反映)。
特に `story` では、話を聞いたうえで **必ず** 投稿してよいか本人に確認する
一文で応答を締めくくるよう明示的に指示する(F6: 投稿許可フロー)。
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional, Sequence

import httpx

from app.config import get_settings
from app.schemas import Category, ConsultInfo

logger = logging.getLogger(__name__)

# 会話履歴の1ターン。role は "user" / "assistant"。
HistoryTurn = tuple[str, str]

_BASE_PERSONA_PROMPT = (
    "あなたは高齢者に寄り添う対話相手です。丁寧で、ゆっくりとした、共感的な口調で話してください。"
    "1回の応答は短めの日本語(2〜4文程度)にまとめてください。"
)

_CATEGORY_SYSTEM_PROMPTS: dict[Category, str] = {
    "chat": (
        _BASE_PERSONA_PROMPT
        + "これは雑談です。相手の話に関心を持って相槌を打ち、自然に会話を広げてください。"
        "医療・法律などの断定的な助言は行わないでください。"
    ),
    "consult": (
        _BASE_PERSONA_PROMPT
        + "これは相談です。相手のつらい気持ちに共感し、安心できる言葉をかけてください。"
        "医療や法律について断定的な助言はせず、専門の相談窓口へ相談することを穏やかに勧めてください。"
        "窓口の名称・電話番号などの具体的な情報は、この後システム側で別途案内するため、"
        "あなたの応答本文には作り話の窓口名や電話番号を含めないでください。"
    ),
    "story": (
        _BASE_PERSONA_PROMPT
        + "これは、相手が語ってくれた昔話や思い出話です。まずその話に興味・共感を示してください。"
        "そのうえで、必ず最後に「その話をみんなにも紹介(投稿)してよいか」を本人に尋ねる一文を"
        "加えてください(例:「そのお話、みんなにも紹介してもいいですか?」)。"
        "まだ投稿の可否を確認していない段階でのみこの質問をし、独断で投稿を決めないでください。"
    ),
}


async def generate_reply(
    category: Category,
    text: str,
    consult_info: Optional[ConsultInfo],
    history: Optional[Sequence[HistoryTurn]] = None,
) -> str:
    settings = get_settings()
    if settings.azure_openai.configured:
        reply = await _call_azure_openai(text, category, history or ())
        if reply:
            return _append_consult_info(reply, category, consult_info)

    return _fallback_reply(category, text, consult_info)


def _build_async_client() -> httpx.AsyncClient:
    """Azure OpenAI 呼び出し用の httpx クライアントを生成する。

    テストではこの関数を monkeypatch し、``httpx.MockTransport`` を使った
    クライアントに差し替えることで、実際のネットワーク呼び出しなしに
    リクエスト内容(system prompt・履歴等)を検証できる。
    """
    return httpx.AsyncClient(timeout=10.0)


def _build_messages(
    text: str, category: Category, history: Iterable[HistoryTurn]
) -> list[dict[str, str]]:
    system_prompt = _CATEGORY_SYSTEM_PROMPTS.get(category, _CATEGORY_SYSTEM_PROMPTS["chat"])
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for role, content in history:
        if role not in ("user", "assistant"):
            continue
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})
    return messages


async def _call_azure_openai(
    text: str, category: Category, history: Iterable[HistoryTurn]
) -> Optional[str]:
    settings = get_settings().azure_openai
    url = (
        f"{settings.endpoint.rstrip('/')}/openai/deployments/"
        f"{settings.deployment}/chat/completions?api-version={settings.api_version}"
    )
    headers = {"api-key": settings.api_key, "Content-Type": "application/json"}
    payload = {
        "messages": _build_messages(text, category, history),
        "max_tokens": 300,
        "temperature": 0.7,
    }
    try:
        async with _build_async_client() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:  # noqa: BLE001 - 外部API障害時はフォールバックさせるため広く捕捉
        logger.warning("Azure OpenAI 呼び出しに失敗したためフォールバック応答を使用します", exc_info=True)
        return None


def _fallback_reply(
    category: Category,
    text: str,
    consult_info: Optional[ConsultInfo],
) -> str:
    if category == "consult":
        base = (
            "それはご心配なことですね。おつらいお気持ち、よくわかりますよ。"
            "一人で抱え込まず、お近くの相談窓口にも声をかけてみてくださいね。"
        )
        return _append_consult_info(base, category, consult_info)
    if category == "story":
        return (
            "それは素敵なお話ですね。もしよろしければ、そのお話をみんなにも"
            "紹介してみませんか?よろしければ「はい」と教えてください。"
        )
    return "そうなんですね。お話を聞かせてくださってありがとうございます。もっと聞かせてくださいね。"


def _append_consult_info(reply: str, category: Category, consult_info: Optional[ConsultInfo]) -> str:
    if category != "consult" or consult_info is None:
        return reply
    office_text = (
        f"\n\nお近くの相談窓口: {consult_info.office}"
        f"({consult_info.field})"
        f" 電話: {consult_info.phone or '未登録'}"
    )
    if consult_info.note:
        office_text += f"\n{consult_info.note}"
    return reply + office_text
