"""The daily briefing: the sections you choose, each built on its own.

Every section runs in its own thread with a shared deadline, so a slow mail server or a
calendar that isn't connected never holds up or breaks the others. Each section says
plainly whether it worked, had nothing to report, isn't set up, failed or ran out of time.
"""

import concurrent.futures
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# id -> title. The order here is the order of the briefing.
SECTIONS: Dict[str, str] = {
    "calendar": "Calendar",
    "reminders": "Reminders",
    "tasks": "Tasks",
    "mail": "Mail",
    "sites": "Watched sites",
    "screen_time": "Yesterday's screen time",
    "weather": "Weather",
}
DEFAULT_SECTIONS = ("calendar", "reminders", "tasks", "weather")
DEADLINE_SECONDS = 8.0


class Unavailable(Exception):
    """The section isn't set up. The message tells the user how to set it up."""


Section = Callable[[], Dict[str, Any]]


# ── Sections ──────────────────────────────────────────────────────────────

def _clock(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%I:%M %p").lstrip("0")
    except (ValueError, AttributeError):
        return ""


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def calendar_section() -> Dict[str, Any]:
    import gcal
    if not gcal.is_configured():
        raise Unavailable("Connect Google Calendar in Settings to see your events here.")
    events = gcal.today_events()
    if isinstance(events, dict):
        raise RuntimeError(events.get("error") or "Google Calendar didn't answer")
    items = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        start = ev.get("start") or {}
        when = _clock(start.get("dateTime", "")) if start.get("dateTime") else "All day"
        items.append({"title": ev.get("summary") or "(no title)", "when": when})
    if not items:
        return {"text": "Nothing on your calendar today.", "items": [], "empty": True}
    listed = "; ".join(f"{i['when']} {i['title']}" for i in items[:4])
    more = f", and {len(items) - 4} more" if len(items) > 4 else ""
    return {"text": f"{_plural(len(items), 'event')} today: {listed}{more}.", "items": items}


def reminders_section(today: Optional[date] = None) -> Dict[str, Any]:
    import tasks
    today = today or date.today()
    pending = tasks.list_reminders()
    todays = []
    for r in pending:
        try:
            due = datetime.fromisoformat(r["due"])
        except (KeyError, TypeError, ValueError):
            continue
        if due.date() <= today:
            todays.append({"title": r.get("text", ""), "when": due.strftime("%I:%M %p").lstrip("0")})
    later = len(pending) - len(todays)
    if not todays:
        text = "No reminders today." + (f" {_plural(later, 'reminder')} coming up later." if later else "")
        return {"text": text, "items": [], "empty": True}
    listed = "; ".join(f"{i['when']} {i['title']}" for i in todays[:4])
    return {"text": f"{_plural(len(todays), 'reminder')} today: {listed}.", "items": todays}


def tasks_section() -> Dict[str, Any]:
    import tasks
    open_tasks = [t for t in tasks.list_tasks() if not t.get("done")]
    items = [{"title": t.get("text", "")} for t in open_tasks]
    if not items:
        return {"text": "No open tasks.", "items": [], "empty": True}
    top = "; ".join(i["title"] for i in items[:3])
    return {"text": f"{_plural(len(items), 'open task')}. Top: {top}.", "items": items}


def mail_section() -> Dict[str, Any]:
    import mail
    inbox = mail.check_inbox(limit=10, only_unread=True)
    if "error" in inbox:
        raise RuntimeError(f"Couldn't reach your mail: {inbox['error']}")
    emails = inbox.get("emails") or []
    items = [{"title": e.get("subject") or "(no subject)",
              "from": (e.get("from") or "").split("<")[0].strip().strip('"'),
              "important": bool(e.get("important"))} for e in emails]
    if not items:
        return {"text": "No unread mail.", "items": [], "empty": True}
    important = [i for i in items if i["important"]]
    text = f"{_plural(len(items), 'unread email')}"
    text += f", {len(important)} look important: " + "; ".join(i["title"] for i in important[:3]) if important else ""
    return {"text": text + ".", "items": items}


def sites_section() -> Dict[str, Any]:
    import watchdog
    if not watchdog.list_sites():
        raise Unavailable("You aren't watching any sites. Say \"watch\" and a website to add one.")
    results = watchdog.check_all()
    down = [r["host"] for r in results if not r.get("up")]
    expiring = [f"{r['host']} in {r['cert_days']} days" for r in results
                if r.get("cert_days") is not None and r["cert_days"] <= 14]
    items = [{"title": r["host"], "up": bool(r.get("up")), "cert_days": r.get("cert_days")} for r in results]
    parts = [f"{len(down)} down: {', '.join(down)}" if down else f"All {_plural(len(results), 'site')} are up"]
    if expiring:
        parts.append("certificates expiring: " + ", ".join(expiring))
    return {"text": ". ".join(parts) + ".", "items": items}


def screen_time_section() -> Dict[str, Any]:
    from core import productivity
    summary = productivity.get_daily_summary()
    return {"text": summary or "No screen time recorded yet.", "items": [], "empty": not summary}


def weather_section(latitude: Any = None, longitude: Any = None) -> Dict[str, Any]:
    """Open-Meteo: free, no account. Only your saved coordinates are sent."""
    if latitude in (None, "") or longitude in (None, ""):
        import config
        from core import location_provider
        if location_provider.enabled():
            fix = location_provider.refresh()  # this PC's location, refreshed every 30 minutes
            if not fix.get("ok") and getattr(config, "LATITUDE", None) is None:
                raise RuntimeError(fix.get("reason") or "Windows couldn't find this PC's location.")
        latitude, longitude = getattr(config, "LATITUDE", None), getattr(config, "LONGITUDE", None)
    if latitude in (None, "") or longitude in (None, ""):
        raise Unavailable("Turn on \"Use this PC's location\" in Settings > Briefing, or enter your coordinates there.")
    query = urllib.parse.urlencode({
        "latitude": f"{float(latitude):.2f}", "longitude": f"{float(longitude):.2f}",
        "current": "temperature_2m,weather_code", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto", "forecast_days": 1,
    })
    with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=6) as resp:
        data = json.load(resp)
    now = data["current"]
    daily = data["daily"]
    rain = (daily.get("precipitation_probability_max") or [None])[0]
    text = (f"{describe_weather(now.get('weather_code'))}, {round(now['temperature_2m'])}°C now. "
            f"High {round(daily['temperature_2m_max'][0])}°, low {round(daily['temperature_2m_min'][0])}°")
    text += f", {rain}% chance of rain." if rain is not None else "."
    return {"text": text, "items": []}


_WEATHER_CODES = [(0, "Clear"), (3, "Partly cloudy"), (48, "Foggy"), (57, "Drizzle"), (67, "Rain"),
                  (77, "Snow"), (82, "Rain showers"), (86, "Snow showers"), (99, "Thunderstorms")]


def describe_weather(code: Any) -> str:
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "Weather"
    for limit, name in _WEATHER_CODES:
        if code <= limit:
            return name
    return "Weather"


BUILDERS: Dict[str, Section] = {
    "calendar": calendar_section, "reminders": reminders_section, "tasks": tasks_section,
    "mail": mail_section, "sites": sites_section, "screen_time": screen_time_section,
    "weather": weather_section,
}


# ── Building the briefing ────────────────────────────────────────────────

def chosen_sections(value: Any) -> List[str]:
    """The saved setting, cleaned: known ids only, in briefing order. Unset means the defaults."""
    if isinstance(value, str):
        value = [v.strip() for v in value.split(",")]
    if not isinstance(value, (list, tuple)):
        return list(DEFAULT_SECTIONS)
    wanted = {v for v in value if v in SECTIONS}
    return [s for s in SECTIONS if s in wanted]


def build(sections: Iterable[str], builders: Optional[Dict[str, Section]] = None,
          deadline: float = DEADLINE_SECONDS, log: Callable[[str], None] = lambda m: None) -> Dict[str, Any]:
    builders = builders or BUILDERS
    order = [s for s in sections if s in builders]
    started = time.monotonic()
    results: Dict[str, Dict[str, Any]] = {}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(order)), thread_name_prefix="briefing")
    try:
        futures = {pool.submit(builders[s]): s for s in order}
        done, _ = concurrent.futures.wait(futures, timeout=deadline)
        for future, sid in futures.items():
            title = SECTIONS.get(sid, sid)
            if future not in done:
                results[sid] = {"id": sid, "title": title, "status": "timeout", "text": f"{title} took too long to answer."}
                continue
            try:
                value = future.result()
                status = "empty" if value.get("empty") else "ok"
                results[sid] = {"id": sid, "title": title, "status": status, "text": value.get("text", ""),
                                "items": value.get("items", [])}
            except Unavailable as exc:
                results[sid] = {"id": sid, "title": title, "status": "unavailable", "text": str(exc)}
            except Exception as exc:  # one failed source must not break the rest
                log(f"briefing {sid} failed: {exc}")
                results[sid] = {"id": sid, "title": title, "status": "failed",
                                "text": f"Couldn't get {title.lower()}: {_short(exc)}"}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    ordered = [results[s] for s in order]
    return {"sections": ordered, "text": spoken(ordered), "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "seconds": round(time.monotonic() - started, 2)}


def _short(exc: Exception) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text if len(text) <= 120 else text[:117] + "..."


def greeting(now: Optional[datetime] = None, title: str = "") -> str:
    hour = (now or datetime.now()).hour
    part = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    return f"Good {part}{', ' + title.strip() if title and title.strip() else ''}."


def spoken(sections: List[Dict[str, Any]], title: str = "", now: Optional[datetime] = None) -> str:
    """What gets read aloud: everything that worked, then one line naming what didn't."""
    said = [s["text"] for s in sections if s["status"] in ("ok", "empty") and s.get("text")]
    missing = [s["title"].lower() for s in sections if s["status"] in ("failed", "timeout")]
    lines = [greeting(now, title)] + said
    if missing:
        lines.append("I couldn't get " + _join(missing) + " right now.")
    if not said and not missing:
        lines.append("There's nothing to brief you on. Choose what the briefing covers in Settings.")
    return " ".join(lines)


def _join(words: List[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " or " + words[-1]


# ── Wiring ───────────────────────────────────────────────────────────────

_settings: Callable[[], Tuple[Any, str]] = lambda: (None, "")
_log: Callable[[str], None] = lambda m: None


def configure(settings: Callable[[], Tuple[Any, str]], log: Callable[[str], None]) -> None:
    """settings() returns (BRIEFING_SECTIONS value, how to address the user)."""
    global _settings, _log
    _settings, _log = settings, log


def current() -> Dict[str, Any]:
    value, title = _settings()
    result = build(chosen_sections(value), log=_log)
    result["text"] = spoken(result["sections"], title)
    return result


def get_route(body: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    result = current()
    return {"ok": True, "briefing": result, "available": [{"id": k, "title": v} for k, v in SECTIONS.items()]}, 200


GET_ROUTES = {"/api/briefing/get": get_route}


# ── The spoken briefing when your day starts ─────────────────────────────
# The first time KALKI starts or the PC wakes each day, once you're actually at
# the PC (it waits for keyboard or mouse), KALKI reads the briefing aloud.

DAY_STARTS_HOUR = 4          # before 4 am still counts as last night
SLEEP_GAP_SECONDS = 5 * 60   # a clock jump this big means the PC was asleep
PRESENT_WITHIN_SECONDS = 90  # someone touched the keyboard or mouse this recently
WAIT_FOR_YOU_SECONDS = 3 * 60 * 60


def _state_path() -> str:
    from runtime_paths import prepare_runtime
    import os
    return os.path.join(prepare_runtime().user_data_dir, "data", "briefing_state.json")


def _day(now: datetime) -> str:
    return (now - timedelta(hours=DAY_STARTS_HOUR)).date().isoformat()


def due_today(now: Optional[datetime] = None, state: Optional[Dict[str, Any]] = None) -> bool:
    """Whether today's spoken briefing hasn't happened yet."""
    import safe_json
    now = now or datetime.now()
    if state is None:
        state = safe_json.read_json(_state_path(), {}) or {}
    return state.get("last_spoken_day") != _day(now)


def mark_spoken(now: Optional[datetime] = None) -> None:
    import safe_json
    safe_json.write_json(_state_path(), {"last_spoken_day": _day(now or datetime.now())})


def morning_text(title: str = "") -> str:
    """Refresh the location first (if it's on), so the weather is for where you are now."""
    try:
        from core import location_provider
        if location_provider.enabled():
            location_provider.refresh()
    except Exception as exc:  # the briefing still runs without weather
        _log(f"briefing location refresh failed: {exc}")
    value, saved_title = _settings()
    result = build(chosen_sections(value), log=_log, deadline=DEADLINE_SECONDS)
    return spoken(result["sections"], title or saved_title)


def run_day_start(speak: Callable[[str], Any], enabled: Callable[[], bool], idle_seconds: Callable[[], float],
                  reason: str = "start", now: Callable[[], datetime] = datetime.now,
                  sleep: Callable[[float], None] = time.sleep) -> bool:
    """Speak today's briefing if it's due, once you're at the PC. Returns whether it spoke."""
    if not enabled() or not due_today(now()):
        return False
    waited = 0.0
    while idle_seconds() > PRESENT_WITHIN_SECONDS:
        if waited >= WAIT_FOR_YOU_SECONDS:
            return False
        sleep(15)
        waited += 15
    if not due_today(now()):  # another trigger got there first
        return False
    mark_spoken(now())
    _log(f"speaking the day's briefing ({reason})")
    speak(morning_text())
    return True


_watch_started = False


def start_day_watch(speak: Callable[[str], Any], enabled: Callable[[], bool], idle_seconds: Callable[[], float]) -> None:
    """Brief on start, then again the first time the PC wakes on a new day."""
    global _watch_started
    if _watch_started:
        return
    _watch_started = True
    import threading

    def watch():
        try:
            run_day_start(speak, enabled, idle_seconds, "start")
        except Exception as exc:
            _log(f"day-start briefing failed: {exc}")
        last = time.time()
        while True:
            time.sleep(30)
            gap = time.time() - last
            last = time.time()
            if gap > SLEEP_GAP_SECONDS:
                try:
                    run_day_start(speak, enabled, idle_seconds, "wake")
                except Exception as exc:
                    _log(f"wake briefing failed: {exc}")

    threading.Thread(target=watch, daemon=True, name="day-start-briefing").start()
