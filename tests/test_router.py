from __future__ import annotations

from app.services.router import classify_utterance


def test_classify_chat_by_default():
    assert classify_utterance("今日は天気がいいですね") == "chat"


def test_classify_consult_has_priority():
    # 相談キーワードと思い出キーワードが両方含まれる場合でも consult を優先する
    text = "昔は元気だったけど、最近は腰が痛くて困っています"
    assert classify_utterance(text) == "consult"


def test_classify_story():
    assert classify_utterance("昔、こんな面白い話があってなぁ") == "story"
