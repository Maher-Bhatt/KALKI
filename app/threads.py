"""Conversations, stored in SQLite and shared by the app, voice and Telegram.

Saving adds or updates messages and never removes them, so a window that hasn't seen
a voice reply yet can't erase it. Removal is always its own explicit call.

Message text is stored unencrypted, as it was in the browser and in history.json.
"""

import json
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import db

# After this long with no activity, a voice message starts a new conversation.
IDLE_MS = 6 * 60 * 60 * 1000

_ID = re.compile(r"[\w.-]{1,80}")
_ROLES = {"user", "assistant"}
_MESSAGE_COLUMNS = {"id", "role", "content", "ts"}

_active_lock = threading.Lock()
_active_id: Optional[str] = None


def _now() -> int:
    return int(time.time() * 1000)


def _valid_id(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{what} isn't a valid id")
    return value


def _number(value: Any, default: int) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _message_row(thread_id: str, message: Any) -> tuple:
    if not isinstance(message, dict):
        raise ValueError("each message must be an object")
    if message.get("role") not in _ROLES:
        raise ValueError("message role must be user or assistant")
    if not isinstance(message.get("content", ""), str):
        raise ValueError("message content must be text")
    extra = {k: v for k, v in message.items() if k not in _MESSAGE_COLUMNS}
    return (thread_id, _valid_id(message.get("id"), "message"), message["role"], message.get("content", ""),
            _number(message.get("ts"), _now()), json.dumps(extra))


_UPSERT_MESSAGE = """
    INSERT INTO thread_messages (thread_id, msg_id, role, content, ts, extra) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (thread_id, msg_id) DO UPDATE SET
        role = excluded.role, content = excluded.content, ts = excluded.ts, extra = excluded.extra
"""


def save(thread: Any) -> None:
    """Add or update a thread and the messages sent with it."""
    if not isinstance(thread, dict):
        raise ValueError("thread must be an object")
    thread_id = _valid_id(thread.get("id"), "thread")
    messages = thread.get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    rows = [_message_row(thread_id, m) for m in messages]
    now = _now()
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO threads (id, title, created_at, updated_at, pinned, archived, model)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (id) DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at,
                   pinned = excluded.pinned, archived = excluded.archived, model = excluded.model""",
            (thread_id, str(thread.get("title") or "New conversation")[:200], _number(thread.get("createdAt"), now),
             _number(thread.get("updatedAt"), now), 1 if thread.get("pinned") else 0,
             1 if thread.get("archived") else 0, str(thread.get("model") or "")[:100]),
        )
        conn.executemany(_UPSERT_MESSAGE, rows)


def list_all() -> List[Dict[str, Any]]:
    """Every thread with its messages: pinned first, then newest first."""
    with db.connect() as conn:
        thread_rows = conn.execute("SELECT * FROM threads ORDER BY pinned DESC, updated_at DESC, id").fetchall()
        message_rows = conn.execute("SELECT * FROM thread_messages ORDER BY pos").fetchall()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in message_rows:
        grouped.setdefault(row["thread_id"], []).append({
            **json.loads(row["extra"]), "id": row["msg_id"], "role": row["role"],
            "content": row["content"], "ts": row["ts"],
        })
    return [{
        "id": row["id"], "title": row["title"], "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        "pinned": bool(row["pinned"]), "archived": bool(row["archived"]), "model": row["model"],
        "messages": grouped.get(row["id"], []),
    } for row in thread_rows]


def truncate(thread_id: str, message_id: str) -> bool:
    """Remove a message and everything after it, as when editing and resending."""
    with db.connect() as conn:
        found = conn.execute("SELECT pos FROM thread_messages WHERE thread_id = ? AND msg_id = ?",
                             (thread_id, message_id)).fetchone()
        if not found:
            return False
        conn.execute("DELETE FROM thread_messages WHERE thread_id = ? AND pos >= ?", (thread_id, found["pos"]))
        return True


def delete(thread_id: str) -> bool:
    with db.connect() as conn:
        return conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,)).rowcount > 0


def clear_unpinned() -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM threads WHERE pinned = 0")


def set_active(thread_id: Optional[str]) -> None:
    """Remember which thread the app has open, so voice and Telegram can join it."""
    global _active_id
    with _active_lock:
        _active_id = thread_id if thread_id is None or _ID.fullmatch(str(thread_id)) else None


def _shared_thread_id(conn: Any, now: int) -> Optional[str]:
    """The open thread if it's still in use, otherwise the latest recently used one."""
    with _active_lock:
        active = _active_id
    if active:
        row = conn.execute("SELECT id, updated_at FROM threads WHERE id = ?", (active,)).fetchone()
        if row and now - row["updated_at"] < IDLE_MS:
            return row["id"]
    row = conn.execute("SELECT id, updated_at FROM threads ORDER BY updated_at DESC LIMIT 1").fetchone()
    return row["id"] if row and now - row["updated_at"] < IDLE_MS else None


def append_exchange(user_text: str, reply: str, source: str, thread_id: Optional[str] = None,
                    now: Optional[int] = None) -> str:
    """Save a turn that didn't come from the app window. Returns its thread id."""
    now = _now() if now is None else now
    with db.connect() as conn:
        target = thread_id or _shared_thread_id(conn, now)
        if target:
            conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (now, target))
        else:
            target = f"t_{uuid.uuid4().hex[:16]}"
            conn.execute(
                "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (target, (str(user_text).strip() or "New conversation")[:60], now, now),
            )
        extra = json.dumps({"origin": source, "done": True})
        for role, content in (("user", user_text), ("assistant", reply)):
            conn.execute(_UPSERT_MESSAGE, (target, f"{source[0]}_{uuid.uuid4().hex[:16]}", role, str(content), now, extra))
    return target


def recent_context(limit: int = 8, now: Optional[int] = None) -> List[Dict[str, str]]:
    """Recent turns of the shared thread, for a request that arrives without any."""
    now = _now() if now is None else now
    with db.connect() as conn:
        target = _shared_thread_id(conn, now)
        if not target:
            return []
        rows = conn.execute("SELECT role, content, extra FROM thread_messages WHERE thread_id = ? ORDER BY pos DESC",
                            (target,)).fetchall()
    context = []
    for row in rows:
        if row["content"] and not json.loads(row["extra"]).get("failed"):
            context.append({"role": row["role"], "content": row["content"]})
            if len(context) == limit:
                break
    return context[::-1]
