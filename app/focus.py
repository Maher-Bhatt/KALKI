"""Focus sessions: a timer that survives restarts, with history.

Sessions live in SQLite, so closing KALKI mid-session doesn't lose it: on the next
start the timer carries on, or the session counts as finished if its time ran out
meanwhile. A session ends one of two ways: it runs its full time (completed), or you
stop it early (stopped). Either way it stays in the history with the minutes you did.

While a session runs, KALKI holds back non-urgent spoken notifications. It doesn't
block apps or websites, and it doesn't switch on Windows Do Not Disturb.
"""

import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import db

DEFAULT_MINUTES = 25
MIN_MINUTES, MAX_MINUTES = 1, 240
# A session that finished more than this long ago (say, while KALKI was closed) is
# recorded quietly instead of announced as if it had just ended.
ANNOUNCE_WITHIN_SECONDS = 10 * 60

_lock = threading.RLock()
Result = Tuple[Dict[str, Any], int]


# ── Store ────────────────────────────────────────────────────────────────

def _row(r: Any) -> Dict[str, Any]:
    started = float(r["started"])
    planned = int(r["planned_minutes"])
    ended = r["ended"]
    done_sec = (float(ended) - started) if ended is not None else None
    return {
        "id": r["id"], "label": r["label"] or "", "minutes": planned,
        "startedAt": started, "endsAt": started + planned * 60,
        "endedAt": float(ended) if ended is not None else None,
        "completed": bool(r["completed"]),
        "focusedMinutes": round(max(0.0, done_sec) / 60, 1) if done_sec is not None else None,
    }


def clamp_minutes(value: Any) -> int:
    try:
        minutes = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError("The length must be a number of minutes.") from exc
    if not MIN_MINUTES <= minutes <= MAX_MINUTES:
        raise ValueError(f"A focus session can be {MIN_MINUTES} to {MAX_MINUTES} minutes.")
    return minutes


def finish_expired(now: Optional[float] = None) -> None:
    """Mark sessions whose time is up as completed, ending exactly when their time ran out."""
    now = time.time() if now is None else now
    with _lock, db.connect() as conn:
        conn.execute(
            "UPDATE focus_sessions SET ended = started + planned_minutes * 60, completed = 1 "
            "WHERE ended IS NULL AND started + planned_minutes * 60 <= ?", (now,))


def active(now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    finish_expired(now)
    with db.connect() as conn:
        r = conn.execute("SELECT * FROM focus_sessions WHERE ended IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    return _row(r) if r else None


def is_active(now: Optional[float] = None) -> bool:
    try:
        return active(now) is not None
    except db.StoreError:
        return False


def start(minutes: Any = DEFAULT_MINUTES, label: str = "", now: Optional[float] = None) -> Dict[str, Any]:
    """Start a session. One that's already running is stopped first and kept in the history."""
    minutes = clamp_minutes(minutes)
    label = (label or "").strip()[:120]
    now = time.time() if now is None else now
    with _lock:
        stop(now)
        with db.connect() as conn:
            cur = conn.execute("INSERT INTO focus_sessions (started, planned_minutes, label) VALUES (?, ?, ?)",
                               (now, minutes, label))
            r = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
    session = _row(r)
    _changed(True)
    return session


def stop(now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Stop the running session early. Returns it, or None if nothing was running."""
    now = time.time() if now is None else now
    with _lock:
        current = active(now)
        if not current:
            return None
        with db.connect() as conn:
            conn.execute("UPDATE focus_sessions SET ended = ?, completed = 0, announced = 1 WHERE id = ?",
                         (now, current["id"]))
            r = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (current["id"],)).fetchone()
    _changed(False)
    return _row(r)


def pop_finished(now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Completed sessions not yet announced. Ones that ended long ago come back with
    "late": True, so the caller can mention them without pretending they just ended."""
    now = time.time() if now is None else now
    with _lock:
        finish_expired(now)
        with db.connect() as conn:
            rows = conn.execute("SELECT * FROM focus_sessions WHERE completed = 1 AND announced = 0 ORDER BY id").fetchall()
            if rows:
                conn.execute(f"UPDATE focus_sessions SET announced = 1 WHERE id IN ({','.join('?' * len(rows))})",
                             [r["id"] for r in rows])
    out = []
    for r in rows:
        s = _row(r)
        s["late"] = now - s["endedAt"] > ANNOUNCE_WITHIN_SECONDS
        out.append(s)
    if out and not is_active(now):
        _changed(False)
    return out


def history(days: int = 7, now: Optional[float] = None, limit: int = 50) -> Dict[str, Any]:
    """Finished sessions from the last `days` days, newest first, with totals."""
    now = time.time() if now is None else now
    finish_expired(now)
    today = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0)
    since = (today - timedelta(days=max(1, days) - 1)).timestamp()
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM focus_sessions WHERE ended IS NOT NULL AND started >= ? "
                            "ORDER BY started DESC", (since,)).fetchall()
    sessions = [_row(r) for r in rows]
    today_ts = today.timestamp()
    today_min = sum(s["focusedMinutes"] for s in sessions if s["startedAt"] >= today_ts)
    return {
        "sessions": sessions[:limit],
        "todayMinutes": round(today_min),
        "periodMinutes": round(sum(s["focusedMinutes"] for s in sessions)),
        "completed": sum(1 for s in sessions if s["completed"]),
        "stopped": sum(1 for s in sessions if not s["completed"]),
        "days": days,
    }


def status(now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    current = active(now)
    today = history(1, now, limit=0)
    base = {"todayMinutes": today["todayMinutes"], "todaySessions": today["completed"] + today["stopped"],
            "serverTime": now}
    if not current:
        return {"active": False, "remainingSec": 0, "minutes": DEFAULT_MINUTES, "label": "", **base}
    return {"active": True, "remainingSec": max(0, int(round(current["endsAt"] - now))),
            "minutes": current["minutes"], "label": current["label"], "id": current["id"],
            "startedAt": current["startedAt"], "endsAt": current["endsAt"], **base}


# ── What a session changes elsewhere ────────────────────────────────────

_on_change: Callable[[bool], None] = lambda running: None


def configure(on_change: Callable[[bool], None]) -> None:
    """on_change(running) is called when a session starts, stops or finishes."""
    global _on_change
    _on_change = on_change


def _changed(running: bool) -> None:
    try:
        _on_change(running)
    except Exception:  # a broken hook must never lose the session itself
        pass


# ── Spoken and typed commands ────────────────────────────────────────────

_START = re.compile(
    r"^(?:please\s+)?(?:start|begin|set)?\s*(?:a|an|my)?\s*"
    r"(?:(?P<n1>\d{1,3})[\s-]*(?P<u1>minutes?|mins?|hours?|hrs?)\s+)?"
    r"focus(?:\s+(?:session|timer|mode))?"
    r"(?:\s+on\s+(?P<label>.+?))?"
    r"(?:\s+for\s+(?P<n2>\d{1,3}|an?|half\s+an?)\s*(?P<u2>minutes?|mins?|hours?|hrs?))?\s*$")
_STOP = ("end focus session", "stop focus", "cancel focus", "finish focus", "stop focus session", "end focus",
         "stop the focus session", "end the focus session", "cancel focus session", "stop focusing", "end focus mode")
_STATUS = ("focus status", "how long is left", "how much focus time", "how much time is left",
           "how much focus time is left", "time left")
_STATS = ("focus history", "focus stats", "how much did i focus today", "how long did i focus today",
          "how much have i focused today", "focus today")


def _to_minutes(number: Optional[str], unit: Optional[str]) -> Optional[int]:
    if not number:
        return None
    number = number.strip()
    if number.startswith("half"):
        value = 0.5
    elif number in ("a", "an"):
        value = 1.0
    else:
        value = float(number)
    return int(round(value * 60)) if unit and unit.startswith(("hour", "hr")) else int(round(value))


def _clock(seconds: int) -> str:
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{seconds:02d}"


def _duration(minutes: float) -> str:
    minutes = int(round(minutes))
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    h, m = divmod(minutes, 60)
    return f"{h} hour{'s' if h != 1 else ''}" + (f" {m} minutes" if m else "")


def command(t: str) -> Optional[str]:
    """The reply for a focus command, or None if `t` isn't one. `t` is lowercased."""
    t = t.strip().rstrip(".!?")
    if t in _STOP:
        ended = stop()
        if not ended:
            return "No focus session is running."
        return f"Focus session stopped after {_duration(ended['focusedMinutes'])}."
    if t in _STATUS:
        st = status()
        if not st["active"]:
            return "No focus session is running."
        return f"{_clock(st['remainingSec'])} left in your focus session" + (f" on {st['label']}." if st["label"] else ".")
    if t in _STATS:
        h = history(1, limit=0)
        if not h["todayMinutes"] and not (h["completed"] + h["stopped"]):
            return "You haven't had a focus session today."
        return (f"You focused for {_duration(h['todayMinutes'])} today across "
                f"{h['completed'] + h['stopped']} session{'s' if h['completed'] + h['stopped'] != 1 else ''}.")
    m = _START.match(t)
    if not m or not (t.startswith(("start", "begin", "set", "focus", "please")) or m.group("n1")):
        return None
    if t in ("focus", "focus mode"):  # too vague: "focus mode" is also a workflow
        return None
    minutes = _to_minutes(m.group("n1"), m.group("u1")) or _to_minutes(m.group("n2"), m.group("u2")) or DEFAULT_MINUTES
    try:
        session = start(minutes, m.group("label") or "")
    except ValueError as exc:
        return str(exc)
    on = f" on {session['label']}" if session["label"] else ""
    ends = datetime.fromtimestamp(session["endsAt"]).strftime("%I:%M %p").lstrip("0")
    return f"Focus session{on} started: {_duration(session['minutes'])}, until {ends}."


# ── Routes ───────────────────────────────────────────────────────────────

def status_route(body: Dict[str, Any]) -> Result:
    return {"ok": True, **status()}, 200


def history_route(body: Dict[str, Any]) -> Result:
    try:
        days = max(1, min(90, int(body.get("days") or 7)))
    except (TypeError, ValueError):
        return {"ok": False, "error": "days must be a number"}, 400
    return {"ok": True, **history(days)}, 200


def start_route(body: Dict[str, Any]) -> Result:
    try:
        session = start(body.get("minutes", DEFAULT_MINUTES), str(body.get("label") or ""))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}, 400
    return {"ok": True, "session": session, **status()}, 200


def stop_route(body: Dict[str, Any]) -> Result:
    ended = stop()
    return {"ok": True, "stopped": ended, **status()}, 200


GET_ROUTES = {"/api/focus": status_route, "/api/focus/history": history_route}
POST_ROUTES = {"/api/focus/start": start_route, "/api/focus/stop": stop_route, "/api/focus/history": history_route}
