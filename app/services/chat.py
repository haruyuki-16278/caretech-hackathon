"""対話LLM(F2)による応答生成。

Azure OpenAI が設定されている場合はそれを用い、未設定または呼び出し失敗時は
高齢者向けの共感的なトーンを保った簡易応答(ルールベース)にフォールバックする。
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.schemas import Category, ConsultInfo

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "あなたは高齢者に寄り添う対話相手です。丁寧で、ゆっくりとした、共感的な口調で話してください。"
    "医療や法律について断定的な助言はせず、必要に応じて専門の窓口へ相談することを穏やかに勧めてください。"
)


async def generate_reply(
    category: Category,
    text: str,
    consult_info: Optional[ConsultInfo],
) -> str:
    settings = get_settings()
    if settings.azure_openai.configured:
        reply = await _call_azure_openai(text, category)
        if reply:
            return _append_consult_info(reply, category, consult_info)

    return _fallback_reply(category, text, consult_info)


async def _call_azure_openai(text: str, category: Category) -> Optional[str]:
    settings = get_settings().azure_openai
    url = (
        f"{settings.endpoint.rstrip('/')}/openai/deployments/"
        f"{settings.deployment}/chat/completions?api-version={settings.api_version}"
    )
    headers = {"api-key": settings.api_key, "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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
    return reply + office_text
