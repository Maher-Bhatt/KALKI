"""Quick commands for tasks, reminders and notes, moved out of handle_local.

Each function takes the lowercased text and the original text, and returns a reply, or
None if the text isn't its command. handle_local calls them from their old positions,
so which command wins when several could match hasn't changed.
"""

import random
import re
from typing import Optional

import notes
import tasks

_ADD_NOTE = re.compile(r"^(?:take\s+(?:a\s+)?note|note\s+(?:that|this)|add\s+note|jot\s+(?:this\s+)?down)\s*[:\-]?\s+(.+)$")
_SEARCH_NOTES = re.compile(r"^search\s+notes?\s+(?:for\s+)?(.+)$")
_ADD_TASK = re.compile(r"^(?:add\s+(?:a\s+)?task|new\s+task|task)[:\-]?\s+(.+)$")
_COMPLETE_TASK = re.compile(r"^(?:complete|done(?:\s+with)?|finish|mark)\s+task\s*(.+)$")
_DELETE_TASK = re.compile(r"^(?:delete|remove|clear)\s+task\s*(.+)$")
_REMIND = re.compile(r"^remind\s+(?:me\s+)?(?:to\s+)?(.+)$")

_LIST_NOTES = {"show my notes", "list my notes", "recent notes", "what did i note", "show notes"}
_YESTERDAY_NOTES = {"what did i note yesterday", "yesterday's notes", "notes from yesterday"}
_WEEK_NOTES = {"notes this week", "this week's notes", "summarize this week's notes", "summarize my week"}
_NOTED = ("Noted.", "Got it.", "Stored, Sir.", "Down in the book.", "Filed away.", "Logged that, Sir.")

_LIST_TASKS = {"show my tasks", "show tasks", "list tasks", "list my tasks", "what are my tasks", "what's on my list",
               "what's on my todo", "my tasks", "show todo", "todo list"}
_CLEAR_ALL_TASKS = {f"{verb} {word}" for verb in ("clear all", "delete all", "remove all", "wipe all", "clear", "delete",
                                                  "remove", "wipe", "clear my", "clear the", "clear pending")
                    for word in ("tasks", "task")}
_CLEAR_DONE_TASKS = {"clear completed tasks", "clear done tasks", "clear my completed tasks", "clear completed task",
                     "clear done task"}
_ALL_WORDS = {"all", "every", "everything", "pending", "my", "the"}

_LIST_REMINDERS = {"list reminders", "my reminders", "show reminders"}
_SNOOZE = re.compile(r"^snooze(?:\s+(?:it|that|the reminder))?(?:\s+(?:for\s+)?(\d+)\s*(?:min(?:ute)?s?)?)?$")
_DELETE_REMINDER = re.compile(r"^(?:delete|remove|cancel)\s+(?:the\s+)?reminder\s+(?:to\s+|about\s+)?(.+)$")


def _original_case(captured: str, lowered: str, raw: str) -> str:
    """The captured text with the capitals the user typed."""
    text = captured.strip()
    start = lowered.find(text.lower())
    return raw[start:start + len(text)] if start >= 0 else text


def notes_command(t: str, raw: str) -> Optional[str]:
    match = _ADD_NOTE.match(t)
    if match:
        notes.add_note(_original_case(match.group(1), t, raw))
        return random.choice(_NOTED)
    if t in _LIST_NOTES:
        return notes.summarize_for_speech(notes.list_recent(5))
    if t in _YESTERDAY_NOTES:
        return notes.summarize_for_speech(notes.notes_yesterday())
    if t in _WEEK_NOTES:
        return notes.summarize_for_speech(notes.notes_this_week())
    match = _SEARCH_NOTES.match(t)
    if match:
        return notes.summarize_for_speech(notes.search(match.group(1).strip()))
    return None


def tasks_command(t: str, raw: str) -> Optional[str]:
    match = _ADD_TASK.match(t)
    if match:
        text = _original_case(match.group(1), t, raw)
        return f"Task {tasks.add_task(text)} logged: {text}."
    if t in _LIST_TASKS:
        open_tasks = tasks.list_tasks()
        if not open_tasks:
            return "Your task list is clear, Sir."
        lines = [f"{task['id']}: {task['text']}" for task in open_tasks[:8]]
        more = "" if len(open_tasks) <= 8 else f" Plus {len(open_tasks) - 8} more."
        return f"You have {len(open_tasks)} open. " + ". ".join(lines) + "." + more
    match = _COMPLETE_TASK.match(t)
    if match:
        target = match.group(1).strip()
        done = tasks.complete_task(target)
        return f"Task done: {done['text']}." if done else tasks.explain_no_match(target, include_done=False)
    if t in _CLEAR_ALL_TASKS:
        tasks.clear_all_tasks()
        return "All tasks cleared, Sir."
    if t in _CLEAR_DONE_TASKS:
        return f"Cleared. {tasks.clear_completed()} tasks remain."
    match = _DELETE_TASK.match(t)
    if match:
        target = match.group(1).strip()
        if target in _ALL_WORDS:
            tasks.clear_all_tasks()
            return "All tasks cleared, Sir."
        return "Task removed." if tasks.delete_task(target) else tasks.explain_no_match(target)
    return None


def reminders_command(t: str, raw: str) -> Optional[str]:
    match = _REMIND.match(t)
    if match:
        text = _original_case(match.group(1), t, raw)
        repeat, text = tasks.parse_repeat(text)
        when, leftover = tasks.parse_when(text)
        if when is None:
            if repeat:
                return "When should it go off? Try 'remind me every day at 9am to stretch'."
            return f"No time given, so I added it as task {tasks.add_task(text)}: {text}."
        leftover = re.sub(r"^to\s+", "", leftover or text).strip() or text
        reminder_id = tasks.add_reminder(leftover, when, repeat=repeat)
        added = next((r for r in tasks.list_reminders() if r["id"] == reminder_id), {"due": when.isoformat(), "repeat": repeat})
        return f"Reminder set for {tasks.describe(added)}: {leftover}."
    if t in _LIST_REMINDERS:
        reminders = tasks.list_reminders()
        if not reminders:
            return "No reminders set."
        lines = [f"{r['id']}, {tasks.describe(r)}: {r['text']}" for r in reminders[:6]]
        return f"{len(reminders)} reminder{'s' if len(reminders) != 1 else ''}. " + ". ".join(lines) + "."
    match = _SNOOZE.match(t)
    if match:
        snoozed = tasks.snooze_reminder(None, int(match.group(1) or 10))
        if not snoozed:
            return "There's no reminder to snooze."
        return f"Snoozed for {int(match.group(1) or 10)} minutes: {snoozed['text']}."
    match = _DELETE_REMINDER.match(t)
    if match:
        target = match.group(1).strip()
        return "Reminder deleted." if tasks.delete_reminder(target) else f"I couldn't find one reminder matching '{target}'."
    return None
