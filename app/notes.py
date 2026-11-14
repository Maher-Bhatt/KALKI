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
    """Newest first, so a spoken summary starts with what's most recent."""
    today = datetime.now().date()
    start = today - timedelta(days=today.weekday())
    return _query("WHERE date >= ? ORDER BY ts DESC, id DESC", (start.strftime("%Y-%m-%d"),))


def search(query="", tag=""):
    """Notes whose text contains `query` (any case), optionally only those with `tag`. Newest first."""
    where, params = [], []
    q = str(query or "").strip().lower()
    if q:
        where.append("(lower(text) LIKE ? ESCAPE '\\' OR lower(tags) LIKE ? ESCAPE '\\')")
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        params += [like, like]
    tag = str(tag or "").strip().lstrip("#").lower()
    rows = _query(("WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts DESC, id DESC", tuple(params))
    return [note for note in rows if not tag or tag in note["tags"]]


def get_note(nid):
    found = _query("WHERE id = ?", (int(nid),))
    return found[0] if found else None


def update_note(nid, text):
    """Change a note's text. Its tags follow the new text. Returns the note, or None if it's gone."""
    text = str(text).strip()
    if not text:
        raise ValueError("A note can't be empty.")
    with db.connect() as conn:
        cursor = conn.execute("UPDATE notes SET text = ?, tags = ? WHERE id = ?",
                              (text, json.dumps(_extract_tags(text)), int(nid)))
        if not cursor.rowcount:
            return None
    return get_note(nid)


def all_tags():
    """Every tag in use, with how many notes have it, most used first."""
    counts = {}
    for note in _query():
        for tag in note["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"tag": t, "count": c} for t, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def delete_note(nid_or_text):
    """Delete one note by id or matching text. Returns the deleted note, or None."""
    with db.connect() as conn:
        matches = _select_target(conn.execute("SELECT * FROM notes ORDER BY id").fetchall(), nid_or_text)
        if not matches:
            return None
        conn.execute("DELETE FROM notes WHERE id = ?", (matches[0]["id"],))
        return _note(matches[0])


def restore_note(note):
    """Put a deleted note back exactly as it was, for Undo."""
    with db.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO notes (id, text, tags, ts, date) VALUES (?, ?, ?, ?, ?)",
                     (int(note["id"]), str(note["text"]), json.dumps(list(note.get("tags") or [])),
                      str(note["ts"]), str(note["date"])))
    return get_note(note["id"])


def export_markdown(notes_list=None):
    """All notes (or the ones given) as Markdown, grouped by day, oldest day first."""
    notes_list = list(reversed(_query("ORDER BY ts DESC, id DESC"))) if notes_list is None else notes_list
    lines = ["# KALKI notes", ""]
    day = None
    for n in sorted(notes_list, key=lambda n: (n["ts"], n["id"])):
        if n["date"] != day:
            day = n["date"]
            lines += [f"## {day}", ""]
        lines.append(f"- {n['ts'][11:16]}  " + n["text"].replace("\n", "\n  "))
    return "\n".join(lines).rstrip() + "\n"


def summarize_for_speech(notes_list, max_items=4):
    if not notes_list:
        return "No notes."
    items = []
    for n in notes_list[:max_items]:
        items.append(n["text"][:80])
    return (f"{len(notes_list)} note{'s' if len(notes_list)!=1 else ''}. "
            + ". ".join(items))[:600]
