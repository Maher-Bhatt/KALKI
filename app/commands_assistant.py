"""Quick commands for the calendar, the microphone and "who am I", moved out of handle_local.

Each function takes the lowercased text and returns a reply, or None if the text isn't
its command. handle_local calls them from their old positions, so command order is
unchanged.
"""

import re
from typing import Any, Callable, Dict, List, Optional

import config
import gcal

# Text that asks KALKI to add something to the calendar. These must reach the AI, which
# can create the event, instead of reading out the schedule.
_CREATE_WORDS = re.compile(r"^(?:please\s+)?(?:schedule|add|create|book|set up|put|plan|arrange|move|cancel)\b")

_PAUSE = ("pause listener", "pause mic", "release the mic", "release mic", "free the mic", "free mic",
          "stop listening for a bit")
_RESUME = ("resume listener", "resume mic", "wake up listener", "start listening", "listen again")
_WHO_AM_I = ("who am i", "what's my name", "what is my name", "tell me my details", "my details",
             "who is your owner", "what do you know about me", "say my details")


def _title() -> str:
    return str(getattr(config, "OWNER_TITLE", "") or "").strip()


def _with_title(sentence: str) -> str:
    """'Done.' becomes 'Done, boss.' when a title is set, and stays 'Done.' when it isn't."""
    title = _title()
    return f"{sentence[:-1]}, {title}." if title and sentence.endswith(".") else sentence


def _not_linked() -> str:
    return _with_title("Your calendar isn't linked yet. Link Google in Settings.")


def calendar_command(t: str) -> Optional[str]:
    if _CREATE_WORDS.match(t):
        return None
    if ((("calendar" in t or "schedule" in t or "events" in t) and "tomorrow" in t)
            or t in ("what's tomorrow", "what is tomorrow", "tomorrow's events")):
        return gcal.events_summary(gcal.tomorrow_events(), when_label="tomorrow") if gcal.is_configured() else _not_linked()
    if (("calendar" in t or "schedule" in t)
            and any(k in t for k in ("what", "tell me", "show", "read", "check", "today", "my "))):
        return gcal.today_summary() if gcal.is_configured() else _not_linked()
    if t in ("upcoming events", "what's next", "next event", "my upcoming events"):
        return gcal.events_summary(gcal.upcoming_events(5)) if gcal.is_configured() else _not_linked()
    if t in ("check gmail", "check my gmail", "any gmail", "read gmail", "gmail summary"):
        if not gcal.is_configured():
            return _with_title("Gmail isn't linked yet. Link Google in Settings.")
        return gcal.gmail_summary()
    return None


def listener_command(t: str, state: Dict[str, Any]) -> Optional[str]:
    if t in _PAUSE:
        state["listener_paused"] = True
        return _with_title("Listener paused. Your microphone is free.")
    if t in _RESUME:
        state["listener_paused"] = False
        return _with_title("Listener active again.")
    return None


def owner_command(t: str, memories: Callable[[], List[Any]]) -> Optional[str]:
    """What KALKI actually knows about you: your name, place and how many memories it has."""
    if t not in _WHO_AM_I:
        return None
    name = str(getattr(config, "OWNER_NAME", "") or "").strip()
    place = ", ".join(p for p in (str(getattr(config, k, "") or "").strip()
                                  for k in ("OWNER_CITY", "OWNER_STATE", "OWNER_COUNTRY"))
                      if p and not p.startswith("Your"))
    parts = []
    if name and name != "YourName":
        parts.append(f"You are {name}" + (f", based in {place}." if place else "."))
    else:
        parts.append("I don't know your name yet. You can set it in Settings.")
    count = len(memories() or [])
    parts.append(f"I have {count} {'memory' if count == 1 else 'memories'} on file." if count else "No memories on file yet.")
    return " ".join(parts)
