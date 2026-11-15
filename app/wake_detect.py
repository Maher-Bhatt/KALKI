"""Is this "Hey KALKI"? Decided from what speech recognition wrote down.

Speech services rarely spell an unusual name right. Tested on 75 recordings (5 voices, US,
Indian and British accents), Google wrote "Hey Kalki" as "hey cookie", "high quality",
"Khaki", "Kyunki" or "ykal ki"; Groq Whisper with a hint wrote "Hey KALKI" correctly. So:

  wake   a clear spelling of the name (any engine): act on it.
  maybe  a known mishearing at the start of what was said: confirm with Whisper when
         possible, or accept the safest ones ("hey cookie ...") without it.

Everyday words are never enough on their own: "hockey", "call key" and "Kelly" don't wake
KALKI, and a mishearing only counts at the very start, right after "hey" or "okay".
"""

import re
from typing import Tuple

# Clear spellings of the name, anywhere in what was said.
_NAME = r"(?:kalki|kalky|kalkee|kalkie|kalkey|calki|calky|calkee|calkie|calkey|khalki|kalgi|kal\s?ki|cal\s?ki|ykal\s?ki)"
_WAKE = re.compile(r"\b" + _NAME + r"\b", re.I)

# What comes before the name when people call it.
_HEY = r"(?:hey|hay|hi|hai|hello|ok|okay|okey|o\.?\s?k\.?|ay|y)"

# Mishearings of the name that only count straight after "hey"/"okay" at the start.
_SAFE_MISHEARD = r"(?:cookie|cookies|khaki|kaki|kyunki|kunki|cocky|kelki|kelky|kulki|gulki)"
# Mishearings that are also everyday phrases: only with confirmation from Whisper.
_RISKY_MISHEARD = r"(?:quality|kalgary|calgary|culkin|call\s+key|cal\s+key|kalpi|kelly|call\s+he)"

_GREETING_ONLY = re.compile(r"^\W*(?:(?:" + _HEY + r"|high|please|so|oh|yo)[\s,.!-]*){0,2}$", re.I)

_START_SAFE = re.compile(r"^\W*" + _HEY + r"[\s,.!-]+" + _SAFE_MISHEARD + r"\b", re.I)
_START_RISKY = re.compile(r"^\W*(?:" + _HEY + r"|high)[\s,.!-]+" + _RISKY_MISHEARD + r"\b", re.I)
_START_BARE = re.compile(r"^\W*(?:" + _SAFE_MISHEARD + r")\b", re.I)


def _after(text: str, end: int) -> str:
    return text[end:].strip(" \t,.:;!?-")


def classify(text: str) -> Tuple[str, str, bool]:
    """(level, command, needs_confirmation) for one transcript.

    level is "wake", "maybe" or "" (not addressed to KALKI). command is what follows
    the name, possibly empty ("Hey KALKI" on its own). needs_confirmation is True when
    the match should be checked with a more accurate transcription first.
    """
    text = (text or "").strip()
    if not text:
        return "", "", False
    m = _WAKE.search(text)
    # The name has to open what was said ("Hey KALKI, ...", "KALKI, ..."): talking about
    # KALKI in the middle of a sentence isn't calling it.
    if m and _GREETING_ONLY.match(text[:m.start()]):
        return "wake", _after(text, m.end()), False
    m = _START_SAFE.match(text)
    if m:
        return "maybe", _after(text, m.end()), False
    m = _START_RISKY.match(text) or _START_BARE.match(text)
    if m:
        return "maybe", _after(text, m.end()), True
    return "", "", False


def is_addressed(text: str) -> bool:
    return classify(text)[0] == "wake"
