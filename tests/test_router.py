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


def test_classify_is_keyword_based_not_llm_based():
    """要件定義書 5.2 は将来的にLLM(structured output等)での分類を想定しているが、
    現状の実装(ハッカソン規模)はキーワードベースの簡易ルーターである。

    そのため、文脈的には過去の困りごとを振り返っているだけの発話でも、
    consult キーワード(「痛い」等)が含まれていれば consult に分類される
    (安全側に倒す設計だが、誤検知が起こり得るのは既知の制約)。
    """
    text = "昔は生活が苦しくて大変だったけど、今はすっかり元気になったよ"
    assert classify_utterance(text) == "consult"


def test_classify_chat_when_no_keyword_matches_even_if_implicitly_worrying():
    """キーワードに一致しない場合、内容的には気がかりでも chat に分類される
    (キーワードベースの限界。LLM分類への置き換えは今後の課題)。
    """
    text = "最近なんだか毎日がつまらないんだよねぇ"
    assert classify_utterance(text) == "chat"
