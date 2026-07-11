"""ルーター分類(F3)と同意判定(F6)のテスト(モックLLM)。"""
from app.llm import MockLLM, detect_consent


class TestDetectConsent:
    def test_yes_words_are_consent(self):
        assert detect_consent("いいよ、投稿して") == "yes"
        assert detect_consent("うん、のせてくれ") == "yes"

    def test_deny_words_are_refusal(self):
        assert detect_consent("いや、やめておくよ") == "no"
        assert detect_consent("それは載せないでほしい") == "no"

    def test_deny_takes_precedence_over_consent(self):
        # 「いいよ」を含んでも拒否語があれば no(安全側)
        assert detect_consent("いいよと言いたいが、やめておく") == "no"

    def test_unrelated_text_is_other(self):
        assert detect_consent("ところで今日は暑いね") == "other"


class TestMockLLMRouting:
    def setup_method(self):
        self.llm = MockLLM()

    def test_pain_is_classified_as_consult(self):
        result = self.llm.generate([], "腰が痛くて買い物がつらい")
        assert result["category"] == "consult"

    def test_loneliness_is_classified_as_consult(self):
        result = self.llm.generate([], "一人だとさみしいんだよ")
        assert result["category"] == "consult"

    def test_memory_is_classified_as_story_with_proposal(self):
        result = self.llm.generate([], "昔の祭りの思い出でなあ")
        assert result["category"] == "story"
        assert result["post_proposal"]

    def test_smalltalk_is_classified_as_chat(self):
        result = self.llm.generate([], "今日はいい天気だね")
        assert result["category"] == "chat"
        assert result["post_proposal"] is None
