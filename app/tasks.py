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
REPEATS = ("daily", "weekdays", "weekly")


def _reminder(row: Any) -> Dict[str, Any]:
    keys = row.keys()
    return {"id": row["id"], "text": row["text"], "due": row["due"], "fired": bool(row["fired"]),
            "repeat": row["repeat"] if "repeat" in keys else "",
            "fired_at": row["fired_at"] if "fired_at" in keys else None}


def describe(item: Dict[str, Any]) -> str:
    """'3:00 PM on Friday', plus how it repeats."""
    try:
        when = datetime.fromisoformat(item["due"]).strftime("%I:%M %p on %A").lstrip("0")
    except (TypeError, ValueError):
        when = str(item.get("due", ""))
    repeat = {"daily": ", every day", "weekdays": ", every weekday", "weekly": ", every week"}.get(item.get("repeat", ""), "")
    return when + repeat


def next_occurrence(due: datetime, repeat: str, now: Optional[datetime] = None) -> datetime:
    """The first time after `now` that a repeating reminder is due. Missed ones are skipped."""
    now = now or datetime.now()
    step = timedelta(days=7) if repeat == "weekly" else timedelta(days=1)
    nxt = due
    while nxt <= now:
        nxt += step
        if repeat == "weekdays":
            while nxt.weekday() >= 5:
                nxt += timedelta(days=1)
    return nxt


def add_reminder(text: str, due: Union[datetime, str], repeat: str = "") -> int:
    """Schedule a reminder. `due` is a datetime, an ISO string, or words like "in 20 minutes".

    Raises ValueError if the time can't be understood: guessing a time would set a
    reminder the user never asked for.
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("A reminder needs something to remind you about.")
    if repeat and repeat not in REPEATS:
        raise ValueError(f"Repeat must be one of: {', '.join(REPEATS)}.")
    if isinstance(due, str):
        try:
            due = datetime.fromisoformat(due.strip())
        except (ValueError, TypeError):
            words = due.strip()
            parsed, _ = parse_when(words)
            if not parsed:
                parsed, _ = parse_when(f"at {words}")
            if not parsed:
                parsed, _ = parse_when(f"in {words}")
            if not parsed:
                raise ValueError(f"I couldn't tell when \"{words}\" is. Try \"in 20 minutes\" or \"tomorrow at 9am\".")
            due = parsed
    if not isinstance(due, datetime):
        raise ValueError("The reminder time isn't valid.")
    with db.connect() as conn:
        cursor = conn.execute("INSERT INTO reminders (text, due, repeat) VALUES (?, ?, ?)",
                              (text, due.isoformat(timespec="seconds"), repeat))
        return int(cursor.lastrowid)


def list_reminders(include_fired: bool = False) -> List[Dict[str, Any]]:
    """Return reminders, soonest first."""
    query = "SELECT * FROM reminders" + ("" if include_fired else " WHERE fired = 0") + " ORDER BY due, id"
    with db.connect() as conn:
        return [_reminder(row) for row in conn.execute(query).fetchall()]


def pop_due_reminders(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Reminders whose time has come. One-off reminders are marked fired; repeating ones move
    to their next time. Each comes back with how many minutes late it is, so a reminder
    missed while KALKI was closed can say so instead of being lost."""
    now = now or datetime.now()
    fired = []
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM reminders WHERE fired = 0 ORDER BY due, id").fetchall():
            try:
                due = datetime.fromisoformat(row["due"])
            except (TypeError, ValueError):
                continue
            if due > now:
                continue
            item = _reminder(row)
            item["late_minutes"] = int((now - due).total_seconds() // 60)
            if item["repeat"]:
                nxt = next_occurrence(due, item["repeat"], now)
                conn.execute("UPDATE reminders SET due = ?, fired_at = ? WHERE id = ?",
                             (nxt.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"), row["id"]))
                item["next"] = nxt.isoformat(timespec="seconds")
            else:
                conn.execute("UPDATE reminders SET fired = 1, fired_at = ? WHERE id = ?",
                             (now.isoformat(timespec="seconds"), row["id"]))
                item["fired"] = True
            fired.append(item)
    return fired


def snooze_reminder(id_or_text: Union[str, int, None] = None, minutes: int = 10) -> Optional[Dict[str, Any]]:
    """Bring a reminder back in `minutes`. With no target, the one that went off most recently."""
    minutes = max(1, min(24 * 60, int(minutes)))
    when = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
    with db.connect() as conn:
        if id_or_text in (None, ""):
            row = conn.execute("SELECT * FROM reminders WHERE fired_at IS NOT NULL ORDER BY fired_at DESC, id DESC LIMIT 1").fetchone()
            rows = [row] if row else []
        else:
            rows = _select_target(conn.execute("SELECT * FROM reminders ORDER BY id").fetchall(), id_or_text)
        if not rows:
            return None
        row = rows[0]
        if row["repeat"]:
            # The repeat keeps its schedule; the snooze is a one-off copy.
            cursor = conn.execute("INSERT INTO reminders (text, due) VALUES (?, ?)", (row["text"], when))
            new_id = int(cursor.lastrowid)
        else:
            conn.execute("UPDATE reminders SET fired = 0, due = ? WHERE id = ?", (when, row["id"]))
            new_id = row["id"]
        return {"id": new_id, "text": row["text"], "due": when}


def delete_reminder(id_or_text: Union[str, int]) -> bool:
    """Permanently remove one reminder. Returns False if nothing clearly matched."""
    with db.connect() as conn:
        matches = _select_target(conn.execute("SELECT * FROM reminders ORDER BY id").fetchall(), id_or_text)
        if not matches:
            return False
        conn.execute("DELETE FROM reminders WHERE id = ?", (matches[0]["id"],))
        return True


# "daily" and "weekly" on their own only count at the end or before "at", "to" or "from",
# so "read the daily report" stays a one-off reminder.
_ALONE = r"(?=\s*(?:$|,|\bat\b|\bto\b|\bfrom\b))"
_REPEAT_WORDS = (
    (re.compile(r"\b(?:every\s+weekday|on\s+weekdays|each\s+weekday)\b", re.IGNORECASE), "weekdays"),
    (re.compile(r"\b(?:every\s+day|each\s+day)\b|\bdaily\b" + _ALONE, re.IGNORECASE), "daily"),
    (re.compile(r"\b(?:every\s+week|each\s+week)\b|\bweekly\b" + _ALONE, re.IGNORECASE), "weekly"),
)
_EVERY_DAY_NAME = re.compile(r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE)


def parse_repeat(text: str) -> Tuple[str, str]:
    """("daily" / "weekdays" / "weekly" / "", the text without the repeat words)."""
    m = _EVERY_DAY_NAME.search(text)
    if m:
        # "every monday" repeats weekly; "on monday" is left for parse_when to find the day.
        return "weekly", re.sub(r"\s{2,}", " ", text[:m.start()] + "on " + m.group(1) + text[m.end():]).strip(" ,.")
    for pattern, repeat in _REPEAT_WORDS:
        m = pattern.search(text)
        if m:
            return repeat, re.sub(r"\s{2,}", " ", text[:m.start()] + text[m.end():]).strip(" ,.")
    return "", text


# ─── Natural-language time parsing ──────────────────────
TIME_RE_HHMM = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
DURATION_RE = re.compile(
    r"in\s+(\d+)\s+(second|minute|hour|day)s?", re.IGNORECASE)
AT_RE = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)
DAY_RE = re.compile(
    r"\b(?:(day after tomorrow)|(tomorrow)|(?:on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    re.IGNORECASE)
WORD_DURATION_RE = re.compile(r"\bin\s+(?:an?\s+)?(half\s+an?\s+hour|hour|minute)\b", re.IGNORECASE)
_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


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

    m = WORD_DURATION_RE.search(s)
    if m:
        word = m.group(1).lower()
        delta = timedelta(minutes=30) if word.startswith("half") else timedelta(hours=1) if word == "hour" else timedelta(minutes=1)
        return now + delta, (s[:m.start()] + s[m.end():]).strip(" ,.")

    # "tomorrow", "day after tomorrow" or a weekday sets the day; a time can come with it.
    day = DAY_RE.search(s)
    day_offset = None
    if day:
        if day.group(1):
            day_offset = 2
        elif day.group(2):
            day_offset = 1
        else:
            day_offset = (_DAYS.index(day.group(3).lower()) - now.weekday()) % 7 or 7
        s = (s[:day.start()] + s[day.end():]).strip(" ,.")

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
        if day_offset is not None:
            target += timedelta(days=day_offset)
        elif target <= now:
            target += timedelta(days=1)
        leftover = (s[:m.start()] + s[m.end():]).strip(" ,.")
        return target, leftover

    if day_offset is not None:
        # A day with no time means 9 in the morning.
        target = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        return target, s.strip(" ,.")

    return None, text
