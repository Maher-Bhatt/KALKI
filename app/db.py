"""KALKI's local data store: one SQLite file with versioned migrations.

Rules that keep user data safe:
- Every schema change is a numbered migration, applied in one transaction.
- An existing store is copied before it's upgraded.
- A store from a newer KALKI is refused, never modified.
- Old JSON files are imported once and left exactly as they were, so going back
  to an older version still finds them.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

MIGRATIONS: List[Tuple[int, str]] = [
    (1, """
    CREATE TABLE tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        added TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        completed TEXT
    );
    CREATE TABLE reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        due TEXT NOT NULL,
        fired INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX reminders_pending ON reminders (fired, due);
    CREATE TABLE notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '[]',
        ts TEXT NOT NULL,
        date TEXT NOT NULL
    );
    CREATE INDEX notes_date ON notes (date);
    CREATE TABLE legacy_imports (
        name TEXT PRIMARY KEY,
        imported_at TEXT NOT NULL,
        imported INTEGER NOT NULL,
        skipped INTEGER NOT NULL
    );
    """),
    (2, """
    CREATE TABLE history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        ts TEXT NOT NULL
    );
    CREATE TABLE simple_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fact TEXT NOT NULL,
        date TEXT NOT NULL
    );
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload TEXT NOT NULL
    );
    CREATE TABLE activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        source TEXT NOT NULL,
        kind TEXT NOT NULL,
        time REAL NOT NULL,
        undone INTEGER NOT NULL DEFAULT 0
    );
    """),
    (3, """
    CREATE TABLE threads (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        pinned INTEGER NOT NULL DEFAULT 0,
        archived INTEGER NOT NULL DEFAULT 0,
        model TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX threads_recent ON threads (updated_at);
    CREATE TABLE thread_messages (
        pos INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT NOT NULL REFERENCES threads (id) ON DELETE CASCADE,
        msg_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        ts INTEGER NOT NULL,
        extra TEXT NOT NULL DEFAULT '{}',
        UNIQUE (thread_id, msg_id)
    );
    """),
]
SCHEMA_VERSION = MIGRATIONS[-1][0]

_path: Optional[str] = None
_write_lock = threading.RLock()


class StoreError(Exception):
    """The store can't be used safely. The message is written for the user."""


def configure(path: Optional[str]) -> None:
    global _path
    _path = path


def current_path() -> Optional[str]:
    return _path


def _open() -> sqlite3.Connection:
    if not _path:
        raise StoreError("KALKI's data store isn't open yet.")
    os.makedirs(os.path.dirname(os.path.abspath(_path)), exist_ok=True)
    conn = sqlite3.connect(_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """A connection that commits on success, rolls back on error, and always closes."""
    conn = _open()
    try:
        with _write_lock:
            yield conn
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _statements(script: str) -> Iterator[str]:
    """Split a script so each statement runs inside our own transaction.
    (sqlite3.executescript would commit first, which breaks rollback.)"""
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                yield buffer
            buffer = ""
    if buffer.strip():
        yield buffer


def migrate() -> int:
    """Apply pending migrations, each one all-or-nothing. Returns the new version."""
    with _write_lock:
        conn = _open()
        conn.isolation_level = None
        try:
            current = _version(conn)
            for version, script in MIGRATIONS:
                if version <= current:
                    continue
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for statement in _statements(script):
                        conn.execute(statement)
                    conn.execute(f"PRAGMA user_version = {int(version)}")
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                current = version
            return current
        finally:
            conn.close()


def _copy_database(source: sqlite3.Connection, destination_path: str) -> None:
    target = sqlite3.connect(destination_path)
    try:
        source.backup(target)
    finally:
        target.close()


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _prepare_existing_store() -> None:
    if not _path or not os.path.exists(_path) or os.path.getsize(_path) == 0:
        return
    conn = _open()
    try:
        version = _version(conn)
        if version > SCHEMA_VERSION:
            raise StoreError("This data was saved by a newer version of KALKI. Update KALKI to open it.")
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if check != "ok":
            raise StoreError(f"KALKI's data store is damaged ({check}). Restore a backup.")
        if version < SCHEMA_VERSION:
            _copy_database(conn, f"{_path}.v{version}.{_stamp()}.bak")
    except sqlite3.DatabaseError as exc:
        raise StoreError(f"KALKI's data store can't be read: {exc}") from exc
    finally:
        conn.close()


def _task_row(item: Dict[str, Any]) -> Tuple:
    return (item.get("id"), str(item["text"]), str(item.get("added") or _now()),
            1 if item.get("done") else 0, item.get("completed"))


def _reminder_row(item: Dict[str, Any]) -> Tuple:
    return (item.get("id"), str(item["text"]), str(item["due"]), 1 if item.get("fired") else 0)


def _note_row(item: Dict[str, Any]) -> Tuple:
    stamp = str(item.get("ts") or _now())
    tags = item.get("tags")
    return (item.get("id"), str(item["text"]), json.dumps(tags if isinstance(tags, list) else []),
            stamp, str(item.get("date") or stamp[:10]))


def _history_row(item: Dict[str, Any]) -> Tuple:
    return (None, str(item["role"]), str(item["content"]), _now())


def _simple_memory_row(item: Dict[str, Any]) -> Tuple:
    return (None, str(item["fact"]), str(item.get("date") or _now()[:10]))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


_LEGACY: Dict[str, Tuple[str, Callable[[Dict[str, Any]], Tuple], str]] = {
    "tasks": ("tasks.json", _task_row, "tasks (id, text, added, done, completed)"),
    "reminders": ("reminders.json", _reminder_row, "reminders (id, text, due, fired)"),
    "notes": ("notes.json", _note_row, "notes (id, text, tags, ts, date)"),
    "history": ("history.json", _history_row, "history (id, role, content, ts)"),
    "memory": ("memory.json", _simple_memory_row, "simple_memories (id, fact, date)"),
}


def _import_one(name: str, data_dir: str, report: Dict[str, Dict]) -> None:
    filename, to_row, target = _LEGACY[name]
    path = os.path.join(data_dir, filename)
    with connect() as conn:
        if conn.execute("SELECT 1 FROM legacy_imports WHERE name = ?", (name,)).fetchone():
            return
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                items = json.load(handle)
            if not isinstance(items, list):
                raise ValueError("expected a list")
        except (OSError, ValueError) as exc:
            # Keep the file and try again next start, in case it gets repaired.
            report["failed"][name] = f"{filename}: {exc}"
            return

        placeholders = ", ".join("?" * (target.count(",") + 1))
        imported = skipped = 0
        for item in items:
            try:
                row = to_row(item)
                cursor = conn.execute(f"INSERT OR IGNORE INTO {target} VALUES ({placeholders})", row)
                if cursor.rowcount == 0:
                    raise ValueError("duplicate id")
                imported += 1
            except (KeyError, TypeError, AttributeError, ValueError, sqlite3.Error):
                skipped += 1
        conn.execute("INSERT INTO legacy_imports VALUES (?, ?, ?, ?)", (name, _now(), imported, skipped))
        report["imported"][name] = imported
        report["skipped"][name] = skipped


def open_store(data_dir: str) -> Dict[str, Dict]:
    """Prepare the store for use. Returns what the JSON import did."""
    if not _path:
        configure(os.path.join(data_dir, "kalki.db"))
    _prepare_existing_store()
    migrate()
    report: Dict[str, Dict] = {"imported": {}, "skipped": {}, "failed": {}}
    for name in _LEGACY:
        _import_one(name, data_dir, report)
    return report


def reimport_legacy(names: List[str], data_dir: str) -> None:
    """Replace these tables from their JSON files, for an old-format backup or a
    cloud restore. The tables are only cleared if the file can actually be read."""
    for name in names:
        filename, _, target = _LEGACY[name]
        path = os.path.join(data_dir, filename)
        with open(path, "r", encoding="utf-8") as handle:
            if not isinstance(json.load(handle), list):
                raise StoreError(f"{filename} isn't in the expected format.")
        with connect() as conn:
            conn.execute(f"DELETE FROM {target.split(' ')[0]}")
            conn.execute("DELETE FROM legacy_imports WHERE name = ?", (name,))
        report: Dict[str, Dict] = {"imported": {}, "skipped": {}, "failed": {}}
        _import_one(name, data_dir, report)
        if report["failed"]:
            raise StoreError(report["failed"][name])


def mark_imported(name: str, imported: int, skipped: int = 0) -> None:
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO legacy_imports VALUES (?, ?, ?, ?)", (name, _now(), imported, skipped))


def was_imported(name: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM legacy_imports WHERE name = ?", (name,)).fetchone() is not None


def backup_to(destination_path: str) -> None:
    """Write a consistent copy, including changes still in the write-ahead log."""
    conn = _open()
    try:
        _copy_database(conn, destination_path)
    finally:
        conn.close()


def _validate_copy(path: str) -> None:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise StoreError(f"That backup can't be opened: {exc}") from exc
    try:
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise StoreError("That backup is damaged, so nothing was restored.")
        if conn.execute("PRAGMA user_version").fetchone()[0] > SCHEMA_VERSION:
            raise StoreError("That backup is from a newer version of KALKI. Update KALKI first.")
    except sqlite3.DatabaseError as exc:
        raise StoreError("That file isn't a KALKI data backup, so nothing was restored.") from exc
    finally:
        conn.close()


def restore_from(source_path: str) -> None:
    """Replace the live data with a backup. Validates first, keeps a safety copy."""
    _validate_copy(source_path)
    with _write_lock:
        live = _open()
        source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
        try:
            _copy_database(live, f"{_path}.before-restore.{_stamp()}.bak")
            source.backup(live)
        finally:
            source.close()
            live.close()
    migrate()

