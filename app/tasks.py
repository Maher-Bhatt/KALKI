"""
KALKI Tasks & Reminders
Tasks: persistent TODO list. Reminders: time-bound; fired by background thread.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple

import db


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _select_target(rows: List[Any], id_or_text: Union[str, int]) -> List[Any]:
    """Find what a request means. A number is only ever an id, so deleting item 1
    can't also hit "Call at 1pm". Text must be an exact match or a single partial
    match: anything ambiguous matches nothing rather than changing several items."""
    needle = str(id_or_text).strip().lower()
    if not needle:
        return []
    if needle.isdigit():
        return [row for row in rows if row["id"] == int(needle)]
    exact = [row for row in rows if row["text"].lower() == needle]
    if exact:
        return exact[:1]
    partial = [row for row in rows if needle in row["text"].lower()]
    return partial if len(partial) == 1 else []


def explain_no_match(id_or_text: Union[str, int], include_done: bool = True) -> str:
    """Why a task request changed nothing, in words the user can act on."""
    needle = str(id_or_text).strip().lower()
    if needle.isdigit():
        return f"No task has the number {needle}."
    rows = list_tasks(include_done=include_done)
    matches = [task["text"] for task in rows if needle and needle in task["text"].lower()]
    if len(matches) > 1:
        shown = "; ".join(matches[:5])
        return f'{len(matches)} tasks match "{needle}": {shown}. Say which one.'
    return f'No task matches "{needle}".'


# ─── Tasks ──────────────────────────────────────────────
def _task(row: Any) -> Dict[str, Any]:
    task = {"id": row["id"], "text": row["text"], "added": row["added"], "done": bool(row["done"])}
    if row["completed"]:
        task["completed"] = row["completed"]
    return task


def add_task(text: str) -> int:
    """Add a new uncompleted task and return its id."""
    with db.connect() as conn:
        cursor = conn.execute("INSERT INTO tasks (text, added) VALUES (?, ?)", (text.strip(), _now()))
        return int(cursor.lastrowid)


def list_tasks(include_done: bool = False) -> List[Dict[str, Any]]:
    """Return tasks, oldest first."""
    query = "SELECT * FROM tasks" + ("" if include_done else " WHERE done = 0") + " ORDER BY id"
    with db.connect() as conn:
        return [_task(row) for row in conn.execute(query).fetchall()]


def complete_task(id_or_text: Union[str, int]) -> Optional[Dict[str, Any]]:
    """Mark one open task done. Returns it, or None if nothing clearly matched."""
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM tasks WHERE done = 0 ORDER BY id").fetchall()
        matches = _select_target(rows, id_or_text)
        if not matches:
            return None
        stamp = _now()
        conn.execute("UPDATE tasks SET done = 1, completed = ? WHERE id = ?", (stamp, matches[0]["id"]))
        return {**_task(matches[0]), "done": True, "completed": stamp}


def delete_task(id_or_text: Union[str, int]) -> bool:
    """Permanently remove one task. Returns False if nothing clearly matched."""
    with db.connect() as conn:
        matches = _select_target(conn.execute("SELECT * FROM tasks ORDER BY id").fetchall(), id_or_text)
        if not matches:
            return False
        conn.execute("DELETE FROM tasks WHERE id = ?", (matches[0]["id"],))
        return True


def clear_completed() -> int:
    """Remove completed tasks. Returns how many tasks remain."""
    with db.connect() as conn:
        conn.execute("DELETE FROM tasks WHERE done = 1")
        return int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])


def clear_all_tasks() -> bool:
    """Remove every task."""
    with db.connect() as conn:
        conn.execute("DELETE FROM tasks")
    return True


# ─── Reminders ──────────────────────────────────────────
def _reminder(row: Any) -> Dict[str, Any]:
    return {"id": row["id"], "text": row["text"], "due": row["due"], "fired": bool(row["fired"])}


def add_reminder(text: str, due: Union[datetime, str]) -> int:
    """Schedule a reminder. `due` is a datetime, an ISO string, or natural language."""
    if isinstance(due, datetime):
        due = due.isoformat(timespec="seconds")
    elif isinstance(due, str):
        try:
            datetime.fromisoformat(due)
        except (ValueError, TypeError):
            parsed, _ = parse_when(due)
            if not parsed:
                parsed, _ = parse_when(f"at {due}")
            if not parsed:
                parsed, _ = parse_when(f"in {due}")
            if parsed:
                due = parsed.isoformat(timespec="seconds")
            else:
                due = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect() as conn:
        cursor = conn.execute("INSERT INTO reminders (text, due) VALUES (?, ?)", (text, due))
        return int(cursor.lastrowid)


def list_reminders(include_fired: bool = False) -> List[Dict[str, Any]]:
    """Return reminders, oldest first."""
    query = "SELECT * FROM reminders" + ("" if include_fired else " WHERE fired = 0") + " ORDER BY id"
    with db.connect() as conn:
        return [_reminder(row) for row in conn.execute(query).fetchall()]


def pop_due_reminders() -> List[Dict[str, Any]]:
    """Return reminders whose time has passed, and mark them fired so they fire once."""
    now = datetime.now()
    with db.connect() as conn:
        due_now = []
        for row in conn.execute("SELECT * FROM reminders WHERE fired = 0 ORDER BY id").fetchall():
            try:
                if datetime.fromisoformat(row["due"]) <= now:
                    due_now.append(row)
            except (TypeError, ValueError):
                continue
        for row in due_now:
            conn.execute("UPDATE reminders SET fired = 1 WHERE id = ?", (row["id"],))
        return [{**_reminder(row), "fired": True} for row in due_now]


def delete_reminder(id_or_text: Union[str, int]) -> bool:
    """Permanently remove one reminder. Returns False if nothing clearly matched."""
    with db.connect() as conn:
        matches = _select_target(conn.execute("SELECT * FROM reminders ORDER BY id").fetchall(), id_or_text)
        if not matches:
            return False
        conn.execute("DELETE FROM reminders WHERE id = ?", (matches[0]["id"],))
        return True


# ─── Natural-language time parsing ──────────────────────
TIME_RE_HHMM = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
DURATION_RE = re.compile(
    r"in\s+(\d+)\s+(second|minute|hour|day)s?", re.IGNORECASE)
AT_RE = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)


def parse_when(text: str) -> Tuple[Optional[datetime], str]:
    """
    Heuristically parse natural language text to extract a due time.
    
    Args:
        text (str): The natural language string (e.g. 'in 5 minutes').
        
    Returns:
        Tuple[Optional[datetime], str]: The parsed datetime and the remaining text.
    """
    now = datetime.now()
    s = text

    m = DURATION_RE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        if n <= 0 or n > 3650:
            return None, s
        delta = {
            "second": timedelta(seconds=n),
            "minute": timedelta(minutes=n),
            "hour":   timedelta(hours=n),
            "day":    timedelta(days=n),
        }[unit]
        leftover = (s[:m.start()] + s[m.end():]).strip(" ,.")
        return now + delta, leftover

    m = AT_RE.search(s)
    if m:
        h = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = (m.group(3) or "").lower()
        # Reject invalid clock values instead of wrapping them silently.
        if minute > 59:
            return None, s
        if ampm:
            if not (1 <= h <= 12):
                return None, s
            if ampm == "pm" and h < 12: h += 12
            if ampm == "am" and h == 12: h = 0
        elif not (0 <= h <= 23):
            return None, s

        target = now.replace(hour=h, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        leftover = (s[:m.start()] + s[m.end():]).strip(" ,.")
        return target, leftover

    return None, s
