"""投稿ストア(F7): Firestore(共有) または SQLite(ローカル)。

FIREBASE_CREDENTIALS_PATH が設定されていれば Firestore、
FIRESTORE_PROJECT があれば ADC の Firestore、
どちらも無ければローカル SQLite にフォールバックする。
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from . import config
from .schemas import Comment, Post

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    likes INTEGER NOT NULL DEFAULT 0,
    comments TEXT NOT NULL DEFAULT '[]'
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
        # 旧スキーマからの簡易マイグレーション
        for ddl in (
            "ALTER TABLE posts ADD COLUMN likes INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE posts ADD COLUMN comments TEXT NOT NULL DEFAULT '[]'",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass  # 既に列がある
        return conn

    @staticmethod
    def _to_post(row) -> Post:
        return Post(
            id=str(row[0]),
            display_name=row[1],
            body=row[2],
            created_at=row[3],
            likes=row[4],
            comments=[Comment(**c) for c in json.loads(row[5])],
        )

    def create(self, display_name: str, body: str) -> Post:
        created_at = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO posts (display_name, body, created_at) VALUES (?, ?, ?)",
                (display_name, body, created_at),
            )
            return Post(id=str(cur.lastrowid), display_name=display_name, body=body, created_at=created_at)

    def list(self, limit: int = 50) -> List[Post]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, display_name, body, created_at, likes, comments"
                " FROM posts ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._to_post(r) for r in rows]

    def like(self, post_id: str) -> Optional[int]:
        with self._connect() as conn:
            cur = conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
            if cur.rowcount == 0:
                return None
            return conn.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()[0]

    def add_comment(self, post_id: str, name: str, body: str) -> Optional[Comment]:
        comment = Comment(name=name, body=body, created_at=_now())
        with self._connect() as conn:
            row = conn.execute("SELECT comments FROM posts WHERE id = ?", (post_id,)).fetchone()
            if row is None:
                return None
            comments = json.loads(row[0]) + [comment.model_dump()]
            conn.execute("UPDATE posts SET comments = ? WHERE id = ?", (json.dumps(comments), post_id))
        return comment


class FirestoreStore:
    """チーム共有用の投稿ストア(Firestore)。

    credentials_path 指定時はサービスアカウントキーで認証し、
    未指定時は Application Default Credentials(Cloud Run 等)を使う。
    """

    COLLECTION = "posts"

    def __init__(self, credentials_path: str = "", project: str = ""):
        from google.cloud import firestore

        self._firestore = firestore
        if credentials_path:
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(credentials_path)
            self._db = firestore.Client(credentials=creds, project=creds.project_id)
        else:
            self._db = firestore.Client(project=project or None)

    @staticmethod
    def _to_post(doc_id: str, d: dict) -> Post:
        return Post(
            id=doc_id,
            display_name=d.get("display_name") or "名無しさん",
            body=d.get("body") or "",
            created_at=d.get("created_at") or "",
            likes=d.get("likes") or 0,
            comments=[Comment(**c) for c in (d.get("comments") or [])],
        )

    def create(self, display_name: str, body: str) -> Post:
        created_at = _now()
        seq = int(datetime.now(timezone.utc).timestamp() * 1000)  # 時系列ソート用
        _, ref = self._db.collection(self.COLLECTION).add(
            {
                "display_name": display_name,
                "body": body,
                "created_at": created_at,
                "seq": seq,
                "likes": 0,
                "comments": [],
            }
        )
        return Post(id=ref.id, display_name=display_name, body=body, created_at=created_at)

    def list(self, limit: int = 50) -> List[Post]:
        docs = (
            self._db.collection(self.COLLECTION)
            .order_by("seq", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [self._to_post(doc.id, doc.to_dict()) for doc in docs]

    def like(self, post_id: str) -> Optional[int]:
        ref = self._db.collection(self.COLLECTION).document(post_id)
        snapshot = ref.get()
        if not snapshot.exists:
            return None
        ref.update({"likes": self._firestore.Increment(1)})
        return (snapshot.get("likes") or 0) + 1

    def add_comment(self, post_id: str, name: str, body: str) -> Optional[Comment]:
        ref = self._db.collection(self.COLLECTION).document(post_id)
        if not ref.get().exists:
            return None
        comment = Comment(name=name, body=body, created_at=_now())
        ref.update({"comments": self._firestore.ArrayUnion([comment.model_dump()])})
        return comment


def build_store():
    if config.FIREBASE_CREDENTIALS_PATH:
        return FirestoreStore(credentials_path=config.FIREBASE_CREDENTIALS_PATH)
    if config.FIRESTORE_PROJECT:
        return FirestoreStore(project=config.FIRESTORE_PROJECT)
    return SQLiteStore(config.POSTS_DB)


_store = build_store()


def create_post(display_name: str, body: str) -> Post:
    return _store.create(display_name, body)


def list_posts(limit: int = 50) -> List[Post]:
    return _store.list(limit)


def like_post(post_id: str) -> Optional[int]:
    return _store.like(post_id)


def add_comment(post_id: str, name: str, body: str) -> Optional[Comment]:
    return _store.add_comment(post_id, name, body)
