"""投稿ストア(F7): Firestore(共有) または SQLite(ローカル)。

FIREBASE_CREDENTIALS_PATH が設定されていれば Firestore を使い、
未設定ならローカル SQLite にフォールバックする。
"""
import sqlite3
from datetime import datetime, timezone
from typing import List

from . import config
from .schemas import Post

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteStore:
    """ローカル開発用の投稿ストア。"""

    def __init__(self, db_path):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute(_SQLITE_SCHEMA)
        return conn

    def create(self, display_name: str, body: str) -> Post:
        created_at = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO posts (display_name, body, created_at) VALUES (?, ?, ?)",
                (display_name, body, created_at),
            )
            return Post(id=cur.lastrowid, display_name=display_name, body=body, created_at=created_at)

    def list(self, limit: int = 50) -> List[Post]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, display_name, body, created_at FROM posts ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [Post(id=r[0], display_name=r[1], body=r[2], created_at=r[3]) for r in rows]


class FirestoreStore:
    """チーム共有用の投稿ストア(Firestore)。"""

    COLLECTION = "posts"

    def __init__(self, credentials_path: str):
        from google.cloud import firestore
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(credentials_path)
        self._db = firestore.Client(credentials=creds, project=creds.project_id)

    def create(self, display_name: str, body: str) -> Post:
        created_at = _now()
        # 時系列ソート用に seq(エポックミリ秒)を持たせる
        seq = int(datetime.now(timezone.utc).timestamp() * 1000)
        self._db.collection(self.COLLECTION).add(
            {"display_name": display_name, "body": body, "created_at": created_at, "seq": seq}
        )
        return Post(id=seq, display_name=display_name, body=body, created_at=created_at)

    def list(self, limit: int = 50) -> List[Post]:
        docs = (
            self._db.collection(self.COLLECTION)
            .order_by("seq", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [
            Post(
                id=d.get("seq") or 0,
                display_name=d.get("display_name") or "名無しさん",
                body=d.get("body") or "",
                created_at=d.get("created_at") or "",
            )
            for d in (doc.to_dict() for doc in docs)
        ]


def build_store():
    if config.FIREBASE_CREDENTIALS_PATH:
        return FirestoreStore(config.FIREBASE_CREDENTIALS_PATH)
    return SQLiteStore(config.POSTS_DB)


_store = build_store()


def create_post(display_name: str, body: str) -> Post:
    return _store.create(display_name, body)


def list_posts(limit: int = 50) -> List[Post]:
    return _store.list(limit)
