"""
KALKI Tasks & Reminders
Tasks: persistent TODO list. Reminders: time-bound; fired by background thread.
"""

import os
import json
import re
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple

TASKS_PATH: Optional[str] = None
REMINDERS_PATH: Optional[str] = None

_lock = threading.RLock()


def _atomic_write(path: str, data: Any) -> None:
    """Safely write JSON data to disk via an atomic rename operation."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ─── Tasks ──────────────────────────────────────────────
def _load_tasks() -> List[Dict[str, Any]]:
    """Load the JSON tasks file from disk."""
    if TASKS_PATH is None:
        return []
    try:
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_tasks(data: List[Dict[str, Any]]) -> None:
    """Save the JSON tasks payload to disk."""
    if TASKS_PATH is None:
        return
    with _lock:
        _atomic_write(TASKS_PATH, data)


def add_task(text: str) -> int:
    """
    Add a new uncompleted task.
    
    Args:
        text (str): The task description.
        
    Returns:
        int: The assigned task ID.
    """
    with _lock:
        tasks = _load_tasks()
        nid = (max((t["id"] for t in tasks), default=0)) + 1
        tasks.append({
            "id": nid, "text": text.strip(),
            "added": datetime.now().isoformat(timespec="seconds"),
            "done": False,
        })
        _save_tasks(tasks)
        return nid


def list_tasks(include_done: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve current tasks.
    
    Args:
        include_done (bool): Whether to include tasks that are completed.
        
    Returns:
        List[Dict[str, Any]]: A list of task dictionaries.
    """
    return [t for t in _load_tasks() if include_done or not t["done"]]


def complete_task(id_or_text: Union[str, int]) -> Optional[Dict[str, Any]]:
    """
    Mark a task as completed by matching its ID or partial text string.
    
    Args:
        id_or_text (Union[str, int]): The task ID or text search query.
        
    Returns:
        Optional[Dict[str, Any]]: The completed task dictionary, or None if not found/already completed.
    """
    needle = str(id_or_text).strip().lower()
    if not needle:
        return None
    with _lock:
        tasks = _load_tasks()
        for task in tasks:
            if str(task["id"]) == needle or needle in task["text"].lower():
                if task["done"]:
                    return None
                task["done"] = True
                task["completed"] = datetime.now().isoformat(timespec="seconds")
                _save_tasks(tasks)
                return task
    return None


def delete_task(id_or_text: Union[str, int]) -> bool:
    """
    Permanently remove a task from the list.
    
    Args:
        id_or_text (Union[str, int]): The task ID or text search query.
        
    Returns:
        bool: True if a task was successfully deleted, False otherwise.
    """
    needle = str(id_or_text).strip().lower()
    if not needle:
        return False
    with _lock:
        tasks = _load_tasks()
        keep = [task for task in tasks if not (
            str(task["id"]) == needle or needle in task["text"].lower())]
        if len(keep) != len(tasks):
            _save_tasks(keep)
            return True
    return False


def clear_completed() -> int:
    """
    Remove all completed tasks.
    
    Returns:
        int: The number of uncompleted tasks remaining.
    """
    with _lock:
        tasks = [task for task in _load_tasks() if not task["done"]]
        _save_tasks(tasks)
        return len(tasks)


def clear_all_tasks() -> bool:
    """Remove all tasks from the persistent list."""
    _save_tasks([])
    return True


# ─── Reminders ──────────────────────────────────────────
def _load_reminders() -> List[Dict[str, Any]]:
    """Load the JSON reminders file from disk."""
    if REMINDERS_PATH is None:
        return []
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reminders(data: List[Dict[str, Any]]) -> None:
    """Save the JSON reminders payload to disk."""
    if REMINDERS_PATH is None:
        return
    with _lock:
        _atomic_write(REMINDERS_PATH, data)


def add_reminder(text: str, due: Union[datetime, str]) -> int:
    """
    Schedule a reminder.
    
    Args:
        text (str): The reminder text.
        due (Union[datetime, str]): The due date/time as a datetime object or ISO string.
        
    Returns:
        int: The assigned reminder ID.
    """
    if isinstance(due, datetime):
        due = due.isoformat(timespec="seconds")
    with _lock:
        rems = _load_reminders()
        nid = (max((r["id"] for r in rems), default=0)) + 1
        rems.append({"id": nid, "text": text, "due": due, "fired": False})
        _save_reminders(rems)
        return nid


def list_reminders(include_fired: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve scheduled reminders.
    
    Args:
        include_fired (bool): Whether to include reminders that have already passed.
        
    Returns:
        List[Dict[str, Any]]: A list of reminder dictionaries.
    """
    return [r for r in _load_reminders() if include_fired or not r["fired"]]


def pop_due_reminders() -> List[Dict[str, Any]]:
    """
    Returns a list of reminders whose due-time has passed, marking them fired.
    
    Returns:
        List[Dict[str, Any]]: The reminders that just fired.
    """
    with _lock:
        rems = _load_reminders()
        now = datetime.now()
        due_rems = []
        changed = False
        for reminder in rems:
            if reminder["fired"]:
                continue
            try:
                due_at = datetime.fromisoformat(reminder["due"])
            except (TypeError, ValueError):
                continue
            if due_at <= now:
                reminder["fired"] = True
                due_rems.append(reminder)
                changed = True
        if changed:
            _save_reminders(rems)
        return due_rems


def delete_reminder(id_or_text: Union[str, int]) -> bool:
    """
    Permanently remove a reminder.
    
    Args:
        id_or_text (Union[str, int]): The reminder ID or text search query.
        
    Returns:
        bool: True if deleted, False otherwise.
    """
    needle = str(id_or_text).strip().lower()
    if not needle:
        return False
    with _lock:
        rems = _load_reminders()
        keep = [reminder for reminder in rems if not (
            str(reminder["id"]) == needle or needle in reminder["text"].lower())]
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
