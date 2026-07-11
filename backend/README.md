# backend — LLM API + フロントエンド

高齢者対話・見守りSNS(仮称)のバックエンド。要件は [docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md) を参照。

## セットアップ

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Azure OpenAI を使う場合は `.env.example` を `.env` にコピーしてキーを設定する。
**未設定でもモックLLMで全機能が動く**(分類はキーワードベース)。

### 投稿DB

- 既定: ローカル SQLite(`backend/posts.sqlite3`)
- チーム共有: Firestore。`.env` の `FIREBASE_CREDENTIALS_PATH` にサービスアカウント
  キーJSONの絶対パスを設定すると自動で切り替わる(キーJSONはリポジトリ外に置くこと)

## テスト

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Codespaces でみんなで試す

1. GitHub の Code ▸ Codespaces ▸ Create codespace on tano_develop
2. ターミナルで `cd backend && cp .env.example .env`(必要ならキーを設定)
3. `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000` で起動
4. ポート8000が自動転送される。PORTS タブで Visibility を **Public** にすると共有URLで誰でも試せる

## 起動

```bash
uvicorn app.main:app --reload --port 8000
```

- http://localhost:8000/ — おはなしの部屋(高齢者向けチャット画面)
- http://localhost:8000/feed.html — みんなの広場(若者向けフィード)
- http://localhost:8000/docs — API ドキュメント(Swagger UI)

## API(担当A向け)

文字起こしテキストは `POST /api/chat` に投げてください。詳細は Swagger UI か
[docs/REQUIREMENTS.md §8](../docs/REQUIREMENTS.md) を参照。

```bash
curl -X POST localhost:8000/api/chat -H 'Content-Type: application/json' -d '{
  "session_id": "test-1", "user_id": "u1", "area": "丸岡",
  "display_name": "たろう", "text": "腰が痛くて買い物がつらい"
}'
```
