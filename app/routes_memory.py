"""HTTP routes for long-term memory. Handlers take the body and return (payload, status)."""

from typing import Any, Callable, Dict, Optional, Tuple

import semantic_memory

Result = Tuple[Dict[str, Any], int]


def _bad(message: str) -> Result:
    return {"ok": False, "error": message}, 400


def _clean_fields(body: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """Validate the optional fields. Returns (fields, error)."""
    fields: Dict[str, Any] = {}
    if body.get("importance") is not None:
        try:
            importance = int(body["importance"])
        except (TypeError, ValueError):
            return {}, "importance must be a number from 1 to 10"
        if not 1 <= importance <= 10:
            return {}, "importance must be a number from 1 to 10"
        fields["importance"] = importance
    if body.get("tags") is not None:
        if not isinstance(body["tags"], list) or not all(isinstance(tag, str) for tag in body["tags"]):
            return {}, "tags must be a list of words"
        fields["tags"] = body["tags"]
    if body.get("type") is not None:
        if not isinstance(body["type"], str):
            return {}, "type must be text"
        fields["memory_type"] = body["type"]
    return fields, None


def list_memories(body: Dict[str, Any]) -> Result:
    return {"ok": True, "memories": semantic_memory.memory.list_all()}, 200


def add_memory(body: Dict[str, Any]) -> Result:
    text = str(body.get("text") or body.get("fact") or "").strip()
    if not text:
        return _bad("text required")
    fields, error = _clean_fields(body)
    if error:
        return _bad(error)
    fields.setdefault("importance", 5)
    fields.setdefault("memory_type", "fact")
    fields.setdefault("tags", [])
    return {"ok": True, "id": semantic_memory.memory.add_memory(text, **fields)}, 200


def update_memory(body: Dict[str, Any]) -> Result:
    doc_id = body.get("id")
    text = str(body.get("text") or "").strip()
    if doc_id in (None, "") or not text:
        return _bad("id and text required")
    fields, error = _clean_fields(body)
    if error:
        return _bad(error)
    return {"ok": semantic_memory.memory.update_memory(doc_id, text, **fields)}, 200


def delete_memory(body: Dict[str, Any]) -> Result:
    doc_id = body.get("id") if "id" in body else body.get("doc_id")
    if doc_id in (None, ""):
        return _bad("id required")
    return {"ok": semantic_memory.memory.delete_memory(doc_id)}, 200


POST_ROUTES: Dict[str, Callable[[Dict[str, Any]], Result]] = {
    "/api/memory/list": list_memories,
    "/api/memory/add": add_memory,
    "/api/memory/update": update_memory,
    "/api/memory/delete": delete_memory,
}
