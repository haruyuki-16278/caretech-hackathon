"""app.services.conversation のセッションコンテキスト(簡易マルチターン)のテスト。

投稿許可フロー(F6)の「story提案 → はい/いいえ確認」の最小限の挙動と、
LLM呼び出しに直近の会話履歴が引き継がれることを検証する。
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.conversation import process_utterance
from app.services.session_store import get_session_store


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clear_sessions():
    get_session_store().clear_all()
    yield
    get_session_store().clear_all()


def test_story_utterance_sets_awaiting_confirmation():
    result = _run(process_utterance("昔、こんな面白い話があってなぁ", session_id="session-a"))

    assert result.category == "story"
    assert result.awaiting_confirmation is True
    assert result.posted is False
    assert result.post_proposal


def test_affirmative_reply_after_story_confirms_post_in_same_session():
    session_id = "session-b"
    first = _run(process_utterance("昔、こんな面白い話があってなぁ", session_id=session_id))
    assert first.awaiting_confirmation is True

    second = _run(process_utterance("はい、お願いします", session_id=session_id))

    assert second.category == "story"
    assert second.posted is True
    assert second.awaiting_confirmation is False
    # 投稿確定時は、確認待ちだった元の発話内容が投稿文案として使われる
    assert second.post_proposal == "昔、こんな面白い話があってなぁ"


def test_negative_reply_after_story_declines_post_without_error():
    session_id = "session-c"
    first = _run(process_utterance("昔、こんな面白い話があってなぁ", session_id=session_id))
    assert first.awaiting_confirmation is True

    second = _run(process_utterance("いいえ、やめておきます", session_id=session_id))

    assert second.posted is False
    assert second.awaiting_confirmation is False
    assert second.post_proposal is None


def test_confirmation_flow_is_isolated_per_session():
    """session_id が異なれば、確認待ち状態は引き継がれないこと。"""
    _run(process_utterance("昔、こんな面白い話があってなぁ", session_id="session-d1"))

    # 別セッションでの「はい」は、確認待ちがないので通常の chat 発話として扱われる
    other = _run(process_utterance("はい", session_id="session-d2"))

    assert other.category != "story" or other.posted is False


def test_recent_history_is_preserved_across_turns():
    session_id = "session-e"
    _run(process_utterance("こんにちは", session_id=session_id))
    _run(process_utterance("今日は天気がいいですね", session_id=session_id))

    session = get_session_store().get(session_id)
    contents = [content for _role, content in session.history]

    assert "こんにちは" in contents
    assert "今日は天気がいいですね" in contents
