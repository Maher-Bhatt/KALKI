"""Google Calendar routes, moved out of server.py."""

import os
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Tuple

import config
import gcal
import routes_settings

Result = Tuple[Dict[str, Any], int]

_config: Dict[str, Any] = {"base_dir": None, "log": print}


def configure(base_dir: str, log: Callable[[str], None]) -> None:
    _config.update(base_dir=base_dir, log=log)


def format_events(events: Any) -> List[Dict[str, Any]]:
    """Calendar events in the shape the screens use."""
    if not isinstance(events, list):
        return []
    out = []
    for event in events:
        if not isinstance(event, dict):
            continue
        start = (event.get("start") or {})
        end = (event.get("end") or {})
        start_time = start.get("dateTime") or start.get("date") or ""
        end_time = end.get("dateTime") or end.get("date") or ""
        when = start_time
        if hasattr(gcal, "_format_when"):
            try:
                when = gcal._format_when(event)
            except Exception:
                when = start_time
        title = event.get("summary") or "Untitled event"
        out.append({
            "id": event.get("id", ""), "summary": title, "title": title,
            "startTime": start_time, "endTime": end_time, "start": when, "when": when,
            "location": event.get("location") or "", "htmlLink": event.get("htmlLink") or "",
            "description": event.get("description") or "",
        })
    return out


def status(body: Dict[str, Any]) -> Result:
    connected = gcal.is_configured()
    events = []
    if connected:
        try:
            events = format_events(gcal.today_events())
        except Exception as exc:
            _config["log"](f"[Calendar] couldn't read today's events: {exc}")
            return {"ok": True, "connected": True, "events": [], "error": "Today's events couldn't be read."}, 200
    return {"ok": True, "connected": connected, "events": events}, 200


def today(body: Dict[str, Any]) -> Result:
    raw = gcal.today_events()
    return {"ok": True, "connected": gcal.is_configured(), "events": format_events(raw),
            "summary": gcal.events_summary(raw)}, 200


def upcoming(body: Dict[str, Any]) -> Result:
    try:
        count = max(1, min(50, int(body.get("n") or 5)))
    except (TypeError, ValueError):
        return {"ok": False, "error": "n must be a number"}, 400
    raw = gcal.upcoming_events(count)
    return {"ok": True, "connected": gcal.is_configured(), "events": format_events(raw),
            "summary": gcal.events_summary(raw, when_label="upcoming")}, 200


def connect(body: Dict[str, Any]) -> Result:
    """Start Google's sign-in in the browser. It finishes in the background."""
    log = _config["log"]
    client_id = getattr(config, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(config, "GOOGLE_CLIENT_SECRET", "")
    project_id = getattr(config, "GOOGLE_PROJECT_ID", "") or "kalki-desktop"
    if client_id and client_secret and gcal.CRED_PATH and not os.path.exists(gcal.CRED_PATH):
        try:
            routes_settings.write_google_credentials(gcal.CRED_PATH, client_id, client_secret, project_id)
        except OSError as exc:
            log(f"[Calendar] couldn't write Google's sign-in file: {exc}")

    def sign_in():
        try:
            log("[Calendar] Starting Google sign-in...")
            gcal._get_creds(interactive=True)
            log("[Calendar] Google sign-in finished.")
        except Exception as exc:
            log(f"[Calendar] Google sign-in didn't finish: {exc}")
            script = os.path.join(_config["base_dir"] or "", "setup_google.py")
            if os.path.exists(script):
                try:
                    subprocess.Popen([sys.executable, script])
                except OSError as start_error:
                    log(f"[Calendar] couldn't start the Google setup helper: {start_error}")

    threading.Thread(target=sign_in, daemon=True).start()
    return {"ok": True, "message": "Google sign-in opened in your browser"}, 200


GET_ROUTES = {"/api/calendar/status": status}

POST_ROUTES = {
    "/api/calendar/status": status,
    "/api/calendar/today": today,
    "/api/calendar/upcoming": upcoming,
    "/api/calendar/connect": connect,
}
