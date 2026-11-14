"""HTTP routes for tasks, reminders and notes.

The first route group moved out of server.py. Handlers take the request body and
return (payload, status), with no dependence on the web server, so they're easy to
test and can move to any framework later.
"""

from typing import Any, Callable, Dict, Tuple

import notes
import tasks

Result = Tuple[Dict[str, Any], int]


def _bad(message: str) -> Result:
    return {"ok": False, "error": message}, 400


def _target(body: Dict[str, Any]) -> Any:
    target = body.get("id")
    return target if target not in (None, "") else (body.get("text") or "")


def _text(body: Dict[str, Any]) -> str:
    return str(body.get("text") or "").strip()


def list_tasks(body: Dict[str, Any]) -> Result:
    return {"ok": True, "tasks": tasks.list_tasks(include_done=bool(body.get("all")))}, 200


def add_task(body: Dict[str, Any]) -> Result:
    text = _text(body)
    if not text:
        return _bad("text required")
    return {"ok": True, "id": tasks.add_task(text)}, 200


def complete_task(body: Dict[str, Any]) -> Result:
    target = _target(body)
    task = tasks.complete_task(target)
    if task:
        return {"ok": True, "task": task}, 200
    return {"ok": False, "task": None, "error": tasks.explain_no_match(target, include_done=False)}, 200


def delete_task(body: Dict[str, Any]) -> Result:
    target = _target(body)
    if tasks.delete_task(target):
        return {"ok": True}, 200
    return {"ok": False, "error": tasks.explain_no_match(target)}, 200


def list_reminders(body: Dict[str, Any]) -> Result:
    return {"ok": True, "reminders": tasks.list_reminders()}, 200


def add_reminder(body: Dict[str, Any]) -> Result:
    text, due = _text(body), body.get("due") or ""
    repeat = str(body.get("repeat") or "")
    if not (text and due):
        return _bad("text and due required")
    if not repeat:
        # "every day at 9am" can be in the time or in the text.
        repeat, due = tasks.parse_repeat(str(due))
        if not repeat:
            repeat, text = tasks.parse_repeat(text)
    try:
        reminder_id = tasks.add_reminder(text, due, repeat=repeat)
    except ValueError as exc:
        return _bad(str(exc))
    added = next((r for r in tasks.list_reminders() if r["id"] == reminder_id), None)
    return {"ok": True, "id": reminder_id, "reminder": added, "when": tasks.describe(added) if added else ""}, 200


def snooze_reminder(body: Dict[str, Any]) -> Result:
    try:
        minutes = int(body.get("minutes") or 10)
    except (TypeError, ValueError):
        return _bad("minutes must be a number")
    snoozed = tasks.snooze_reminder(body.get("id"), minutes)
    if not snoozed:
        return {"ok": False, "error": "There's no reminder to snooze."}, 404
    return {"ok": True, "reminder": snoozed}, 200


def delete_reminder(body: Dict[str, Any]) -> Result:
    return {"ok": tasks.delete_reminder(_target(body))}, 200


def add_note(body: Dict[str, Any]) -> Result:
    text = _text(body)
    if not text:
        return _bad("text required")
    return {"ok": True, "id": notes.add_note(text)}, 200


def list_notes(body: Dict[str, Any]) -> Result:
    try:
        count = int(body.get("n") or 10)
    except (TypeError, ValueError):
        return _bad("n must be a number")
    return {"ok": True, "notes": notes.list_recent(max(1, min(count, 1000)))}, 200


def search_notes(body: Dict[str, Any]) -> Result:
    return {"ok": True, "notes": notes.search(body.get("q") or "", body.get("tag") or "")}, 200


def delete_note(body: Dict[str, Any]) -> Result:
    deleted = notes.delete_note(_target(body))
    if not deleted:
        return {"ok": False, "error": "That note doesn't exist."}, 404
    return {"ok": True, "deleted": deleted}, 200


def update_note(body: Dict[str, Any]) -> Result:
    try:
        nid = int(body.get("id"))
    except (TypeError, ValueError):
        return _bad("id required")
    try:
        note = notes.update_note(nid, _text(body))
    except ValueError as exc:
        return _bad(str(exc))
    if not note:
        return {"ok": False, "error": "That note doesn't exist."}, 404
    return {"ok": True, "note": note}, 200


def restore_note(body: Dict[str, Any]) -> Result:
    note = body.get("note")
    if not isinstance(note, dict) or not all(k in note for k in ("id", "text", "ts", "date")):
        return _bad("note required")
    try:
        return {"ok": True, "note": notes.restore_note(note)}, 200
    except (TypeError, ValueError):
        return _bad("that isn't a note")


def note_tags(body: Dict[str, Any]) -> Result:
    return {"ok": True, "tags": notes.all_tags()}, 200


def export_notes(body: Dict[str, Any]) -> Result:
    chosen = notes.search(body.get("q") or "", body.get("tag") or "")
    return {"ok": True, "markdown": notes.export_markdown(chosen), "count": len(chosen)}, 200


POST_ROUTES: Dict[str, Callable[[Dict[str, Any]], Result]] = {
    "/api/tasks/list": list_tasks,
    "/api/tasks/add": add_task,
    "/api/tasks/complete": complete_task,
    "/api/tasks/delete": delete_task,
    "/api/reminders/list": list_reminders,
    "/api/reminders/add": add_reminder,
    "/api/reminders/delete": delete_reminder,
    "/api/reminders/snooze": snooze_reminder,
    "/api/notes/add": add_note,
    "/api/notes/list": list_notes,
    "/api/notes/search": search_notes,
    "/api/notes/delete": delete_note,
    "/api/notes/update": update_note,
    "/api/notes/restore": restore_note,
    "/api/notes/tags": note_tags,
    "/api/notes/export": export_notes,
}
