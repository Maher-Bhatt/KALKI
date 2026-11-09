"""
KALKI Notes & Journal — quick capture, tagged, full-text search.
"""

import json
import re
from datetime import datetime, timedelta

import db
from tasks import _select_target


def _note(row):
    return {"id": row["id"], "text": row["text"], "tags": json.loads(row["tags"]),
            "ts": row["ts"], "date": row["date"]}


def _extract_tags(text):
    return [t.lower() for t in re.findall(r"#(\w+)", text)]


def _query(where="", params=()):
    with db.connect() as conn:
        rows = conn.execute(f"SELECT * FROM notes {where}", params).fetchall()
    return [_note(row) for row in rows]


def add_note(text):
    text = str(text).strip()
    if not text:
        return None
    now = datetime.now()
    with db.connect() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (text, tags, ts, date) VALUES (?, ?, ?, ?)",
            (text, json.dumps(_extract_tags(text)), now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d")),
        )
        return int(cursor.lastrowid)


def list_recent(n=5):
    return _query("ORDER BY ts DESC, id DESC LIMIT ?", (int(n),))


def notes_on(date_str):
    return _query("WHERE date = ? ORDER BY ts, id", (date_str,))


def notes_yesterday():
    return notes_on((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))


def notes_this_week():
    today = datetime.now().date()
    start = today - timedelta(days=today.weekday())
    return _query("WHERE date >= ? ORDER BY ts, id", (start.strftime("%Y-%m-%d"),))


def search(query):
    q = str(query).lower()
    return [note for note in _query("ORDER BY ts DESC, id DESC")
            if q in note["text"].lower() or q in " ".join(note["tags"])]


def delete_note(nid_or_text):
    with db.connect() as conn:
        matches = _select_target(conn.execute("SELECT * FROM notes ORDER BY id").fetchall(), nid_or_text)
        if not matches:
            return False
        conn.execute("DELETE FROM notes WHERE id = ?", (matches[0]["id"],))
        return True


def summarize_for_speech(notes_list, max_items=4):
    if not notes_list:
        return "No notes."
    items = []
    for n in notes_list[:max_items]:
        items.append(n["text"][:80])
    return (f"{len(notes_list)} note{'s' if len(notes_list)!=1 else ''}. "
            + ". ".join(items))[:600]
