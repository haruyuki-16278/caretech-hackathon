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

### サーバーの起動

```bash
uvicorn app.main:app --reload
```

起動後、ブラウザで `http://127.0.0.1:8000/` を開くと音声チャットページが表示されます。

### API

| メソッド/パス | 説明 |
|---|---|
| `POST /api/chat` | テキストで発話を送り、応答・分類結果・(該当時)相談窓口情報を受け取る |
| `POST /api/voice-chat` | 録音した音声(multipart/form-data)を送り、文字起こし・応答・応答音声(base64)を受け取る |
| `GET /healthz` | ヘルスチェック |

詳細なリクエスト/レスポンス例は [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) の「8. API インターフェース」を参照してください。

### テスト

```bash
python3 -m pytest
```

外部サービス(Azure OpenAI / Azure Speech)の呼び出しはテストでは行わず、
音声チャットAPIのテストではスタブ(フェイク実装)に差し替えて決定的に検証しています。

## ドキュメント

- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) - 要件定義書
- [`AGENTS.md`](AGENTS.md) - AI駆動開発フローの説明
