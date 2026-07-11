"""発話をカテゴリ(chat / consult / story)に分類するルーター(F3)。

ハッカソン規模のため、まずはキーワードベースの簡易実装とする。
要件上「複数該当時は consult を最優先(安全側に倒す)」ことが必須のため、
consult のキーワードチェックを最初に行う。
"""
from __future__ import annotations

from app.schemas import Category

_CONSULT_KEYWORDS = [
    "痛い", "つらい", "辛い", "苦しい", "困った", "困って",
    "不安", "心配", "助けて", "相談", "悩み", "悩んで",
    "一人で", "独りで", "孤独", "寂しい", "さみしい",
    "お金がない", "生活が", "病気", "具合が悪い", "倒れ",
]

_STORY_KEYWORDS = [
    "昔", "むかし", "懐かしい", "若い頃", "子供の頃", "子どもの頃",
    "戦争", "伝えたい", "面白い話", "思い出",
]


def classify_utterance(text: str) -> Category:
    if any(keyword in text for keyword in _CONSULT_KEYWORDS):
        return "consult"
    if any(keyword in text for keyword in _STORY_KEYWORDS):
        return "story"
    return "chat"
