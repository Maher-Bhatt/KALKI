"""Actions waiting for the user's approval, moved out of server.py.

An action is held here with the exact words the user will see, until they approve or
deny it on screen, say "confirm" or "cancel", or it expires. Nothing here knows about
the web server. Routes take the request body and return (payload, status).
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

Result = Tuple[Dict[str, Any], int]

DEFAULT_TTL = 30

lock = threading.Lock()
pending: Dict[str, Dict[str, Any]] = {}
_next_id = 0

_CANCEL_WORDS = ("cancel", "never mind", "nevermind")
_CONFIRM_WORDS = ("confirm", "yes confirm", "confirm it", "do it")


def queue(description: str, action: Callable[[], Any], source: str = "chat", ttl: Optional[int] = None) -> str:
    """Hold `action` until it's approved. Returns its id."""
    global _next_id
    now = time.time()
    with lock:
        _next_id += 1
        approval_id = str(_next_id)
        pending[approval_id] = {
            "id": approval_id,
            "description": description,
            "source": source,
            "action": action,
            "created": now,
            "expires": now + (ttl or DEFAULT_TTL),
        }
    return approval_id


def _drop_expired(now: float) -> None:
    for approval_id in [a for a, p in pending.items() if p["expires"] < now]:
        del pending[approval_id]


def count() -> int:
    """How many are still waiting. Expired ones don't count."""
    now = time.time()
    with lock:
        return sum(1 for p in pending.values() if p["expires"] >= now)


def waiting() -> List[Dict[str, Any]]:
    """What the screen shows: never the action itself."""
    now = time.time()
    with lock:
        _drop_expired(now)
        return [{"id": p["id"], "description": p["description"], "expires": p["expires"]} for p in pending.values()]


def decide(approval_id: Any, decision: Any) -> Result:
    with lock:
        item = pending.pop(str(approval_id), None) if approval_id is not None else None
    if not item or item["expires"] < time.time():
        return {"ok": False, "error": "This approval has expired or was already decided."}, 400
    if decision != "approve":
        return {"ok": True, "result": "Denied"}, 200
    try:
        return {"ok": True, "result": item["action"]()}, 200
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 500


def answer_spoken(command: str) -> Optional[Tuple[bool, str]]:
    """Handle "confirm" or "cancel" said or typed in chat. None if it's neither."""
    clean = "".join(c for c in (command or "") if c not in ".,!?").strip().lower()
    if clean in _CANCEL_WORDS:
        with lock:
            had_any = bool(pending)
            pending.clear()
        return (True, "Cancelled.") if had_any else None
    if clean not in _CONFIRM_WORDS:
        return None
    with lock:
        _drop_expired(time.time())
        if not pending:
            return True, "There is no active action to confirm."
        if len(pending) > 1:
            # Saying "confirm" can't show which one it means, so never guess.
            return True, (f"{len(pending)} actions are waiting, so I won't guess which you mean. "
                          "Approve or deny each one on screen.")
        item = pending.pop(next(iter(pending)))
    return item["action"]()


def list_route(body: Dict[str, Any]) -> Result:
    return {"ok": True, "approvals": waiting()}, 200


def decide_route(body: Dict[str, Any]) -> Result:
    return decide(body.get("id"), body.get("decision"))


POST_ROUTES = {
    "/api/approvals/list": list_route,
    "/api/approvals/decide": decide_route,
}
