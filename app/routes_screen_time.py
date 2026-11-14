"""Screen time routes: status and the week, pause, clear, forget an app, and the raw data.

Turning tracking on or off, exclusions and the retention limit are ordinary
settings (SCREEN_TIME_*), saved through the settings routes.
"""

import re
from typing import Any, Dict, Tuple

from core import productivity

Result = Tuple[Dict[str, Any], int]
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def overview(body: Dict[str, Any]) -> Result:
    return {"ok": True, "status": productivity.tracking_status(), "week": productivity.week()}, 200


def raw(body: Dict[str, Any]) -> Result:
    """Exactly what is stored, so you can see it for yourself."""
    return {"ok": True, "data": productivity.stored(), "file": productivity.DATA_FILE}, 200


def pause(body: Dict[str, Any]) -> Result:
    try:
        minutes = int(body.get("minutes") or 60)
    except (TypeError, ValueError):
        return {"ok": False, "error": "minutes must be a number"}, 400
    until = productivity.pause(minutes)
    return {"ok": True, "pausedUntil": until, "status": productivity.tracking_status()}, 200


def resume(body: Dict[str, Any]) -> Result:
    productivity.resume()
    return {"ok": True, "status": productivity.tracking_status()}, 200


def clear(body: Dict[str, Any]) -> Result:
    day = body.get("date")
    if day is not None and not (isinstance(day, str) and _DAY.fullmatch(day)):
        return {"ok": False, "error": "date must look like 2026-11-14"}, 400
    return {"ok": True, "removedDays": productivity.clear(day)}, 200


def forget(body: Dict[str, Any]) -> Result:
    app = str(body.get("app") or "").strip()
    if not app:
        return {"ok": False, "error": "app required"}, 400
    return {"ok": True, "removedSeconds": productivity.forget_app(app)}, 200


GET_ROUTES = {"/api/screentime": overview, "/api/screentime/raw": raw}
POST_ROUTES = {
    "/api/screentime": overview, "/api/screentime/raw": raw, "/api/screentime/pause": pause,
    "/api/screentime/resume": resume, "/api/screentime/clear": clear, "/api/screentime/forget": forget,
}
