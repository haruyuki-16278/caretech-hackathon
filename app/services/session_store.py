"""セッション単位の簡易な会話コンテキスト管理。

ハッカソン規模のため、プロセス内メモリ(モジュールレベルの辞書)に保持するだけの
軽量な実装とする。サーバー再起動やマルチプロセス/マルチワーカー構成では
セッションは共有されない(将来的な拡張時はRedis等の外部ストアに置き換える)。

要件定義書 5.1「会話履歴(セッション単位)を保持し、文脈を踏まえた応答を返す」
および 5.5(F6 投稿許可フロー)の最小限の実装として、以下の2つを提供する。

1. 直近の会話履歴(history)を保持し、LLM呼び出し時に渡すことで
   簡単な文脈維持を可能にする。
2. `story` に分類された発話への投稿確認待ち状態(pending_story)を保持し、
   次のターンで「はい/いいえ」を判定できるようにする。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# user/assistant 合わせて直近何ターン分の履歴を保持するか。
# 大きくしすぎるとLLM呼び出しのトークン数が増えるため、ハッカソン規模として控えめにする。
_MAX_HISTORY_TURNS = 6


@dataclass
class SessionState:
    history: list[tuple[str, str]] = field(default_factory=list)
    pending_story: Optional[str] = None

    def add_turn(self, role: str, content: str) -> None:
        self.history.append((role, content))
        if len(self.history) > _MAX_HISTORY_TURNS:
            del self.history[: len(self.history) - _MAX_HISTORY_TURNS]


class SessionStore:
    """session_id ごとの直近会話履歴・投稿確認待ち状態を保持する。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        return self._sessions.setdefault(session_id, SessionState())

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear_all(self) -> None:
        """全セッションを破棄する(主にテスト用)。"""
        self._sessions.clear()


_store = SessionStore()


def get_session_store() -> SessionStore:
    return _store
