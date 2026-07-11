# caretech-hackathon

高齢者対話・見守りSNS(仮称)— caretech-hackathon 提出プロダクト

詳細な要件は [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) を参照してください。

## 音声チャットページ

高齢者が**ボタンを押して話しかけ**、サーバーから**音声で返事を受け取れる** Web アプリです。
当初は別デバイスで行う想定だった音声入力・音声出力(要件定義書 F1)を、Webブラウザだけで完結するように実装しています。

- ブラウザで録音(`MediaRecorder` / `getUserMedia`)し、サーバー(`/api/voice-chat`)に音声を送信
- サーバー側で 音声認識(STT)→ 対話応答生成(LLM/ルーター/相談窓口検索)→ 音声合成(TTS) を行い、テキストと音声(base64)をまとめて返却
- 応答音声はページ内で自動再生
- Azure Speech の資格情報(`AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION`)が未設定の場合でも、
  - サーバーは「聞き取れませんでした」旨のフォールバック応答を返し
  - ブラウザ標準の音声合成(Web Speech API)で応答を読み上げる
  ため、ページ自体は常に利用可能です
- マイクが使えない場合のために、文字入力での代替送信フォーム(`/api/chat`)も用意しています
- アップロードされる音声ファイルには上限サイズ(既定10MB、`VOICE_MAX_UPLOAD_BYTES` で変更可)を設け、
  超過時は `413 Payload Too Large` を返します(サーバーリソース保護のため)

### 発話分類(ルーター)の現状と制約

`session_id` ごとに直近の会話履歴・投稿確認待ち状態を簡易的に保持しており(`app/services/session_store.py`)、
`story` に分類された発話の次のターンで「はい/いいえ」等の返答があれば、投稿の許可・却下を判定します
(F6: 投稿許可フロー の最小実装)。ただし以下の制約があります。

- 発話の分類(`chat` / `consult` / `story`)は、要件定義書 5.2 が想定するLLMベースの判定ではなく、
  **キーワードベースの簡易ルーター**(`app/services/router.py`)です。「複数該当時は consult を最優先」
  という安全側の要件は満たしますが、キーワードに一致しない発話は文脈的に気がかりな内容であっても
  `chat` に分類される、逆に過去を振り返っただけの発話でもキーワードが含まれれば `consult` に
  分類される、といった誤検知が起こり得ます(`tests/test_router.py` に既知の挙動として明記)。
- セッションの会話履歴・投稿確認待ち状態は**プロセス内メモリのみ**で保持しており、
  サーバー再起動やマルチプロセス/マルチワーカー構成では共有されません(デモ規模の実装)。
- 投稿確認への回答が「はい/いいえ」のどちらとも取れない場合は、確認待ち状態を維持したまま
  通常の発話として処理を続けます(会話が脱線した場合の明示的なキャンセル操作は未実装)。

### 相談窓口の検索(あいまいさへの対応)

`app/services/offices.py` の窓口検索は、「福井県あわら市」のように都道府県名が前置されていたり、
「福井県坂井市丸岡町」のように住所文字列の一部として地区名が埋め込まれていても、
できるだけ具体的な窓口を特定します。

一方で「坂井市」のように1つの市町村に複数の地区包括支援センター(三国・丸岡・春江・坂井)が
存在する場合、地区を特定できないまま1件を機械的に選ぶことはせず、広域窓口(坂井地区広域連合)を
返しつつ、レスポンスの `consult_info.note` に候補地区名を明示します。フロントエンド・LLM側は
この `note` を踏まえて、利用者に地区名を尋ねる等のフォローが可能です。

### セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 環境変数

`.env.example` を参考に、必要な値を環境変数として設定してください(**APIキーはリポジトリにコミットしないこと**)。

| 変数 | 説明 | 未設定時の挙動 |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_DEPLOYMENT` / `AZURE_OPENAI_API_VERSION` | 対話LLM(Azure OpenAI) | ルールベースの簡易応答にフォールバック |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` / `AZURE_SPEECH_STT_LANGUAGE` / `AZURE_SPEECH_TTS_VOICE` | 音声認識・音声合成(Azure Speech) | STTは「聞き取れませんでした」応答、TTSはブラウザ側読み上げにフォールバック |
| `CONSULTATION_OFFICES_PATH` | 相談窓口データJSONのパス | `data/consultation_offices.json` を自動探索 |
| `VOICE_MAX_UPLOAD_BYTES` | `/api/voice-chat` の音声アップロード上限バイト数 | 10MB(10485760) |

### サーバーの起動

```bash
uvicorn app.main:app --reload
```

起動後、ブラウザで `http://127.0.0.1:8000/` を開くと音声チャットページが表示されます。

### API

| メソッド/パス | 説明 |
|---|---|
| `POST /api/chat` | テキストで発話を送り、応答・分類結果・(該当時)相談窓口情報を受け取る |
| `POST /api/voice-chat` | 録音した音声(multipart/form-data)を送り、文字起こし・応答・応答音声(base64)を受け取る。アップロードサイズが上限を超える場合は `413` を返す |
| `GET /healthz` | ヘルスチェック |

いずれのレスポンスにも `awaiting_confirmation`(投稿可否の確認待ちかどうか)・`posted`(この応答で投稿が確定したか)が含まれます(F6: 投稿許可フローの最小実装)。

詳細なリクエスト/レスポンス例は [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) の「8. API インターフェース」を参照してください。

### テスト

```bash
python3 -m pytest
```

外部サービス(Azure OpenAI / Azure Speech)への実ネットワーク呼び出しはテストでは行わず、
- 音声チャットAPI(`/api/voice-chat`)のテストではSTT/TTSをスタブ(フェイク実装)に差し替え、
- 対話LLM(Azure OpenAI)呼び出しのテスト(`tests/test_chat_service.py`)では `httpx.MockTransport`
  でHTTP層をモック化し、

決定的に検証しています。

## ドキュメント

- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) - 要件定義書
- [`AGENTS.md`](AGENTS.md) - AI駆動開発フローの説明
