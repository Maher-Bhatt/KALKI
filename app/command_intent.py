"""Tell conversation apart from quick commands.

The quick-command matcher (handle_local in server.py) looks for phrases like "open ...",
"play ..." and "remind me ...". On its own it grabs ordinary sentences too: "remind me
what a monad is" became a task. This filter runs first and sends anything that reads as
conversation to the AI. When unsure it says "not conversation", so existing commands
keep working as they did.
"""

import re

# About the user's own things: always commands, however they're phrased.
_OWN_THINGS = re.compile(
    r"\b(?:my|this) (?:screen|clipboard|code|notes?|mail|emails?|calendar|schedule|tasks?|"
    r"reminders?|ip|wi-?fi|pc|computer|laptop|battery|memory|memories)\b"
)

# Clearly commands, whatever words follow: "add task explain the budget to sam".
_EXPLICIT_COMMAND = re.compile(
    r"^(?:add task|new task|save note:|note that|remember that|remind me (?:to|at|in|on|tomorrow|tonight))\b"
)

# Clearly questions, even about the user's own things: "how do I restart my computer".
_QUESTION_OPENER = re.compile(r"^(?:how (?:do|does|can|could|should|to)\b|why\b|should i\b)")

_COMMAND_QUESTIONS = re.compile(
    r"^(?:what(?:'s| is) (?:the )?(?:time|date|weather)(?: (?:today|now|in .+))?"
    r"|what time is it(?: now)?|what(?:'s| is) today(?:'s date)?|what day is it)\??$"
)

_CONVERSATION = re.compile(
    r"\b(?:explain(?:ed|s)?|tips?|advice|rules|formula|meaning|mean|idiom|poem|story|essay|recommend|"
    r"best practices|versus|difference between|licen[cs]es?|why|"
    r"how (?:do|does|did|to|can|could|should|would|is|are)|"
    r"should i|would you|could you explain|what (?:is|are|was|were) (?:a|an|the)\b|"
    r"what's the difference|who (?:is|was|are))\b"
)

_OPENING_PROSE = re.compile(
    r"^(?:what time is (?!it\b)"
    r"|remember (?:when|how|why|what|who)\b"
    r"|remind me (?:what|how|why|who|when|where|of)\b"
    r"|(?:open|close|play) .*\b(?:about|in my life|behind you)\b"
    r"|play .* or \w+"
    r"|play .*\b(?:this|my|that) (?:idea|plan|thought|opinion|argument)\b)"
)

_IP_OR_HOST = re.compile(
    r"^(?:localhost|\d{1,3}(?:\.\d{1,3}){3}|[0-9a-f:]*:[0-9a-f:]+|(?:[a-z0-9-]+\.)+[a-z]{2,})$",
    re.IGNORECASE,
)


def is_conversation(text: str) -> bool:
    """True if this should go to the AI rather than the quick-command matcher."""
    low = " ".join(str(text or "").lower().split())
    if not low or _EXPLICIT_COMMAND.match(low):
        return False
    if _QUESTION_OPENER.match(low):
        return True
    if _COMMAND_QUESTIONS.match(low) or _OWN_THINGS.search(low):
        return False
    if _OPENING_PROSE.match(low) or _CONVERSATION.search(low):
        return True
    return low.endswith("?")


def looks_like_host(text: str) -> bool:
    """True for a hostname or IP address, so "ping pong rules" pings nothing."""
    return bool(_IP_OR_HOST.match(str(text or "").strip()))
