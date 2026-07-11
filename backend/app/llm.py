"""対話LLM + ルーター(F2, F3): Azure OpenAI による応答生成と発話分類。

Azure OpenAI が未設定の環境ではモックLLMにフォールバックし、
キー無しでもプロトタイプ全体が動作する。
"""
import json
from typing import Dict, List

from . import config

SYSTEM_PROMPT = """\
あなたは高齢者に寄り添う会話相手です。以下を必ず守ってください。

- 丁寧で、ゆっくりした、共感的な口調で話す(敬語。ただし堅すぎない)
- 一度に話す量は短めに。難しい言葉やカタカナ語は避ける
- 相手の発話を次の3種類に分類する
  - chat: 雑談。楽しく会話を続ける
  - consult: 悩み・困りごと・支援が必要な可能性のある内容(体調、生活、金銭、介護など)。
    共感したうえで、お住まいの地域の相談窓口を案内する一言を添える(窓口の名称・電話番号は
    別途システムが表示するので、本文には具体的な電話番号や窓口名を書かない)
  - story: 面白い話・昔の思い出・後世に伝えたい知恵
- 複数に当てはまる場合は consult を最優先にする
- 医療・法律について断定的な助言はしない

story のときの投稿文案(post_proposal)のルール:
- 話がまだ途中のうちは post_proposal を出さない(null にする)。
  「話したい」という意思表示だけ、話の断片だけのときは、聞き役に回って
  「それでどうなったんですか?」のように続きを促す
- 話がひと区切りついたと感じたら、投稿文案を作り、
  「このお話、みんなが見られる場所に投稿してもいいですか?」と確認する一言を reply に添える
- 投稿文案は直前の発話だけでなく、この会話でこれまでに語られた思い出の内容全体をまとめる
- 投稿文案は話し手の一人称で、話し手の言葉の温かみを残しつつ、100〜200字の読みやすい文章にする

必ず次の JSON だけを出力する:
{"category": "chat" | "consult" | "story", "reply": "本人への返事", "post_proposal": "storyのときだけ投稿文案。それ以外は null"}
"""

# 同意/拒否の簡易判定に使う語彙(投稿許可フロー F6)
CONSENT_WORDS = ("はい", "いいよ", "いいですよ", "うん", "お願い", "投稿して", "のせて", "載せて")
DENY_WORDS = ("いや", "やめ", "だめ", "ダメ", "遠慮", "しないで", "のせないで", "載せないで")


def detect_consent(text: str) -> str:
    """投稿提案への返答を yes / no / other に分類する。"""
    if any(w in text for w in DENY_WORDS):
        return "no"
    if any(w in text for w in CONSENT_WORDS):
        return "yes"
    return "other"


class MockLLM:
    """Azure OpenAI 未設定時のキーワードベース分類・定型応答。"""

    CONSULT_KEYWORDS = ("痛", "つらい", "辛い", "困", "不安", "心配", "お金", "介護", "病院", "眠れ", "さみし", "寂し")
    STORY_KEYWORDS = ("昔", "面白い", "おもしろい", "思い出", "戦争", "若い頃", "教えたい", "伝えたい")

    def generate(self, history: List[Dict], text: str) -> Dict:
        if any(k in text for k in self.CONSULT_KEYWORDS):
            return {
                "category": "consult",
                "reply": "それは大変ですね。おつらい気持ち、よく分かります。"
                "お住まいの地域に相談できる窓口がありますので、下に表示しますね。"
                "一人で抱え込まないでくださいね。",
                "post_proposal": None,
            }
        if any(k in text for k in self.STORY_KEYWORDS):
            proposal = f"【おじいちゃんの話】{text}"
            return {
                "category": "story",
                "reply": "それはいいお話ですねえ。ぜひ若い人にも聞かせてあげたいです。"
                "この話、みんなが見られる場所に投稿してもいいですか?",
                "post_proposal": proposal,
            }
        return {
            "category": "chat",
            "reply": "そうなんですね。それで、どうなさったんですか?もう少し聞かせてください。",
            "post_proposal": None,
        }


class AzureLLM:
    def __init__(self):
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )

    def generate(self, history: List[Dict], text: str) -> Dict:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-20:])  # 思い出話が複数ターンに渡っても全体を要約できる範囲を渡す
        messages.append({"role": "user", "content": text})

        completion = self._client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        raw = completion.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        category = data.get("category")
        if category not in ("chat", "consult", "story"):
            category = "chat"
        return {
            "category": category,
            "reply": data.get("reply") or "すみません、もう一度お話しいただけますか?",
            "post_proposal": data.get("post_proposal") if category == "story" else None,
        }


def build_llm():
    if config.azure_configured():
        return AzureLLM()
    return MockLLM()
