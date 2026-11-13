"""What KALKI did, with Undo while the app is still running. Moved out of server.py.

Each action is saved to the database so Activity survives a restart. The undo step
itself can't be saved, so Undo is only offered for actions from the current run.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import db

Result = Tuple[Dict[str, Any], int]

lock = threading.Lock()
items: List[Dict[str, Any]] = []
_unsaved = 0
KEEP_IN_MEMORY = 500
KEEP_IN_DATABASE = 2000

# server.py replaces this with its own logger.
log: Callable[[str], None] = print


def record(action: str, source: str, reversible: bool = False, undo_fn: Optional[Callable[[], Any]] = None,
           kind: str = "info") -> str:
    """Record something KALKI did. Returns its id. Recording never stops the action."""
    global _unsaved
    now = time.time()
    try:
        with db.connect() as conn:
            cursor = conn.execute("INSERT INTO activity (action, source, kind, time) VALUES (?, ?, ?, ?)",
                                  (action, source, kind, now))
            activity_id = str(cursor.lastrowid)
            conn.execute(f"DELETE FROM activity WHERE id NOT IN (SELECT id FROM activity ORDER BY id DESC LIMIT {KEEP_IN_DATABASE})")
    except Exception as exc:
        log(f"couldn't save activity: {exc}")
        with lock:
            _unsaved += 1
            activity_id = f"unsaved-{_unsaved}"
    with lock:
        items.append({
            "id": activity_id, "action": action, "source": source, "kind": kind, "time": now,
            "reversible": bool(reversible and undo_fn), "undone": False, "undo_fn": undo_fn,
        })
        del items[:-KEEP_IN_MEMORY]
    return activity_id


def public(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: item[k] for k in ("id", "action", "source", "kind", "time", "reversible", "undone")}


def list_route(body: Dict[str, Any]) -> Result:
    with lock:
        live = {a["id"]: a for a in items}
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 500").fetchall()
    shown = []
    for row in reversed(rows):
        item = live.get(str(row["id"]))
        shown.append({
            "id": str(row["id"]), "action": row["action"], "source": row["source"], "time": row["time"],
            "undone": bool(row["undone"]),
            # Undo only exists while the app that did it is still running.
            "reversible": bool(item and item["reversible"] and not row["undone"]),
        })
    return {"ok": True, "activities": shown}, 200


def undo_route(body: Dict[str, Any]) -> Result:
    wanted = body.get("id")
    with lock:
        item = next((a for a in items if a["id"] == wanted), None)
        if not item or not item["reversible"] or not item["undo_fn"] or item["undone"]:
            return {"ok": False, "error": "This can't be undone."}, 400
        # Claimed before running, so two clicks can't undo the same thing twice.
        item["undone"] = True
    try:
        item["undo_fn"]()
    except Exception as exc:
        with lock:
            item["undone"] = False
        return {"ok": False, "error": str(exc)}, 500
    try:
        with db.connect() as conn:
            conn.execute("UPDATE activity SET undone = 1 WHERE id = ?", (item["id"],))
    except Exception as exc:
        log(f"couldn't save that an activity was undone: {exc}")
    return {"ok": True}, 200


POST_ROUTES = {
    "/api/activity/list": list_route,
    "/api/activity/undo": undo_route,
}
