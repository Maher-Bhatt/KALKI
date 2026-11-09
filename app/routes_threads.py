"""HTTP routes for conversations. Handlers take the body and return (payload, status)."""

from typing import Any, Callable, Dict, Tuple

import threads

Result = Tuple[Dict[str, Any], int]


def list_threads(body: Dict[str, Any]) -> Result:
    return {"ok": True, "threads": threads.list_all()}, 200


def save_thread(body: Dict[str, Any]) -> Result:
    try:
        threads.save(body.get("thread"))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}, 400
    return {"ok": True}, 200


def truncate_thread(body: Dict[str, Any]) -> Result:
    return {"ok": threads.truncate(str(body.get("id") or ""), str(body.get("messageId") or ""))}, 200


def delete_thread(body: Dict[str, Any]) -> Result:
    return {"ok": threads.delete(str(body.get("id") or ""))}, 200


def clear_threads(body: Dict[str, Any]) -> Result:
    threads.clear_unpinned()
    return {"ok": True}, 200


POST_ROUTES: Dict[str, Callable[[Dict[str, Any]], Result]] = {
    "/api/threads/list": list_threads,
    "/api/threads/save": save_thread,
    "/api/threads/truncate": truncate_thread,
    "/api/threads/delete": delete_thread,
    "/api/threads/clear": clear_threads,
}
