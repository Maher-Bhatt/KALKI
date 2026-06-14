"""
KALKI Tasks & Reminders
Tasks: persistent TODO list. Reminders: time-bound; fired by background thread.
"""

import os
import json
import re
import threading
from datetime import datetime, timedelta

TASKS_PATH = None
REMINDERS_PATH = None

_lock = threading.Lock()


def _atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ─── Tasks ──────────────────────────────────────────────
def _load_tasks():
    try:
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_tasks(data):
    with _lock:
        _atomic_write(TASKS_PATH, data)


def add_task(text):
    with _lock:
        try:
            with open(TASKS_PATH, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception:
            tasks = []
        nid = (max((t["id"] for t in tasks), default=0)) + 1
        tasks.append({
            "id": nid, "text": text.strip(),
            "added": datetime.now().isoformat(timespec="seconds"),
            "done": False,
        })
        _atomic_write(TASKS_PATH, tasks)
        return nid


def list_tasks(include_done=False):
    return [t for t in _load_tasks() if include_done or not t["done"]]


def complete_task(id_or_text):
    tasks = _load_tasks()
    needle = str(id_or_text).lower()
    for t in tasks:
        if str(t["id"]) == needle or needle in t["text"].lower():
            if t["done"]:
                return None
            t["done"] = True
            t["completed"] = datetime.now().isoformat(timespec="seconds")
            _save_tasks(tasks)
            return t
    return None


def delete_task(id_or_text):
    tasks = _load_tasks()
    needle = str(id_or_text).lower()
    keep = [t for t in tasks if not (
        str(t["id"]) == needle or needle in t["text"].lower())]
    if len(keep) != len(tasks):
        _save_tasks(keep)
        return True
    return False


def clear_completed():
    tasks = [t for t in _load_tasks() if not t["done"]]
    _save_tasks(tasks)
    return len(tasks)


def clear_all_tasks():
    _save_tasks([])
    return True


# ─── Reminders ──────────────────────────────────────────
def _load_reminders():
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reminders(data):
    with _lock:
        _atomic_write(REMINDERS_PATH, data)


def add_reminder(text, due):
    """due: datetime or ISO string"""
    if isinstance(due, datetime):
        due = due.isoformat(timespec="seconds")
    with _lock:
        try:
            with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
                rems = json.load(f)
        except Exception:
            rems = []
        nid = (max((r["id"] for r in rems), default=0)) + 1
        rems.append({"id": nid, "text": text, "due": due, "fired": False})
        _atomic_write(REMINDERS_PATH, rems)
        return nid


def list_reminders(include_fired=False):
    return [r for r in _load_reminders() if include_fired or not r["fired"]]


def pop_due_reminders():
    """Returns list of reminders whose due-time has passed. Marks them fired."""
    rems = _load_reminders()
    now = datetime.now()
    due = []
    changed = False
    for r in rems:
        if r["fired"]:
            continue
        try:
            d = datetime.fromisoformat(r["due"])
        except Exception:
            continue
        if d <= now:
            r["fired"] = True
            due.append(r)
            changed = True
    if changed:
        _save_reminders(rems)
    return due


def delete_reminder(id_or_text):
    rems = _load_reminders()
    needle = str(id_or_text).lower()
    keep = [r for r in rems if not (
        str(r["id"]) == needle or needle in r["text"].lower())]
    if len(keep) != len(rems):
        _save_reminders(keep)
        return True
    return False


# ─── Natural-language time parsing ──────────────────────
TIME_RE_HHMM = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
DURATION_RE = re.compile(
    r"in\s+(\d+)\s+(second|minute|hour|day)s?", re.IGNORECASE)
AT_RE = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)


def parse_when(text):
    """Heuristic. Returns (datetime|None, leftover_text)."""
    now = datetime.now()
    s = text

    m = DURATION_RE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
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
        h = int(m.group(1)); minute = int(m.group(2) or 0)
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
        cand = now.replace(hour=h, minute=minute, second=0, microsecond=0)
        if cand < now:
            cand += timedelta(days=1)
        leftover = (s[:m.start()] + s[m.end():]).strip(" ,.")
        return cand, leftover

    return None, s
