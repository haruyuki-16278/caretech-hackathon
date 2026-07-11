"""投稿ストア(F7): SQLite による軽量な投稿保存。"""
import sqlite3
from datetime import datetime, timezone
from typing import List

from .config import POSTS_DB
from .schemas import Post

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(POSTS_DB)
    conn.execute(_SCHEMA)
    return conn


def create_post(display_name: str, body: str) -> Post:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO posts (display_name, body, created_at) VALUES (?, ?, ?)",
            (display_name, body, created_at),
        )
        return Post(id=cur.lastrowid, display_name=display_name, body=body, created_at=created_at)


def list_posts(limit: int = 50) -> List[Post]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, display_name, body, created_at FROM posts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [Post(id=r[0], display_name=r[1], body=r[2], created_at=r[3]) for r in rows]
