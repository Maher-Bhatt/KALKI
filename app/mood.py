"""Abuse detection for KALKI's mood feature.

KALKI changes its tone when the user is abusive, and locks the PC after
sustained abuse. That makes false positives expensive, so matching is strict:
whole words only, on a short list of clear insults. Everyday words that can be
rude in some sentences ("trash", "dumb", "sucks", "useless", "crap") and short
fragments ("mc", "bc", "pos", "kys") are deliberately not on the list.
"""
import re

# Clear insults. Each entry is matched as a whole word (an optional trailing
# "s" is allowed, so "idiots" counts but "idiotic" does not).
INSULT_WORDS = (
    "idiot", "moron", "asshole", "dumbass", "jackass", "bitch", "bastard",
    "motherfucker", "fucker", "stfu",
    # Hinglish
    "chutiya", "chutiye", "chutiyo", "bhosdike", "bhosdiwale", "bhosdi", "bhenchod", "behenchod", "behnchod",
    "madarchod", "maderchod", "gandu", "gaandu", "harami", "haramkhor", "bsdk", "lodu", "lawde", "lavde",
    "kamina", "kamine", "randi", "chodu",
)

# The same insults written in Devanagari. Matched as text: word boundaries don't work
# reliably with Hindi vowel marks, and none of these are parts of everyday words.
DEVANAGARI_INSULTS = (
    "चूतिया", "चुतिया", "चूतिये", "मादरचोद", "बहनचोद", "बहनचोद", "भोसड़ीके", "भोसडीके", "भोसड़ी",
    "गांडू", "गाँडू", "हरामी", "हरामखोर", "कमीना", "कमीने", "लौड़े", "लोडू", "रंडी",
)

# Insulting phrases aimed at the assistant, matched with word boundaries at
# both ends and any whitespace between the words.
INSULT_PHRASES = (
    "fuck you", "fuck off", "screw you", "shut up bitch",
)

_WORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in INSULT_WORDS) + r")s?\b",
    re.IGNORECASE,
)
_PHRASE_RE = re.compile(
    r"\b(?:" + "|".join(r"\s+".join(re.escape(p) for p in ph.split())
                        for ph in INSULT_PHRASES) + r")\b",
    re.IGNORECASE,
)

# Abusive messages in a row (net of decay) before the PC is locked.
LOCK_THRESHOLD = 11
# Streak at which KALKI starts warning that it will lock the PC.
WARN_THRESHOLD = 6


def is_abusive(text):
    """True when the message contains a clear insult as a whole word."""
    if not text or not isinstance(text, str):
        return False
    return bool(_WORD_RE.search(text) or _PHRASE_RE.search(text) or any(w in text for w in DEVANAGARI_INSULTS))


def update(state, text):
    """Update the mood streak in ``state`` for one user message.

    An abusive message adds one to the streak. Any other message takes one
    off, and the mood clears when the streak reaches zero. Returns "lock" when
    the streak reaches LOCK_THRESHOLD (the streak then resets), "warn" from
    WARN_THRESHOLD, "roast" while the mood is aggressive, and None otherwise.
    """
    streak = int(state.get("mood_aggressive_streak", 0) or 0)
    if is_abusive(text):
        streak += 1
        state["mood_aggressive"] = True
    elif streak > 0:
        streak -= 1
        if streak <= 0:
            state["mood_aggressive"] = False
    state["mood_aggressive_streak"] = streak

    if not state.get("mood_aggressive"):
        return None
    if streak >= LOCK_THRESHOLD:
        state["mood_aggressive_streak"] = 0
        state["mood_aggressive"] = False
        return "lock"
    if streak >= WARN_THRESHOLD:
        return "warn"
    return "roast"
