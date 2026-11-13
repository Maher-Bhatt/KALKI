"""Password vault and screen reading quick commands, moved out of handle_local.

Both handle private things, so they're strict: a password keeps its exact capitals, a
copied password leaves the clipboard after a minute, and the screen is only captured
when you clearly ask for it, because the picture goes to the AI service.

Each function returns (handled, reply) or None.
"""

import re
from typing import Any, Callable, Dict, Optional, Tuple

import config

Reply = Optional[Tuple[bool, str]]

_LIST = ("list passwords", "list my passwords", "show my passwords", "show passwords", "what passwords do you have")
_SAVE_LONG = re.compile(r"(?:save|store|remember|note|keep)\s+(?:my\s+)?(?:the\s+)?(.+?)\s+password\s+(?:is|as|=|:)\s+(.+)$",
                        re.IGNORECASE)
_SAVE_SHORT = re.compile(r"(?:save|store|vault)\s+password\s+(\S+)\s+for\s+(.+)$", re.IGNORECASE)
_GET = re.compile(r"^(?:what(?:'s| is)|show|get|retrieve|tell me|reveal)\s+(?:me\s+)?(?:my\s+)?(.+?)\s+password\??$",
                  re.IGNORECASE)
_DELETE = re.compile(r"^(?:delete|remove|forget)\s+(?:my\s+)?(.+?)\s+password$", re.IGNORECASE)
_GENERATE = re.compile(r"^generate\s+(?:a\s+)?(?:strong\s+)?password(?:\s+of\s+(\d+))?(?:\s+characters?)?$", re.IGNORECASE)

# Asking about the screen. These can carry a question after them.
_SCREEN_PHRASES = ("see my screen", "see the screen", "look at my screen", "look at the screen", "what's on my screen",
                   "what is on my screen", "read my screen", "analyze my screen", "analyze the screen", "ocr my screen",
                   "ocr the screen")
# Short phrases that only mean the screen when they're the whole message.
_SCREEN_EXACT = ("solve this", "what does this say", "help me with this", "what am i looking at", "solve what's on screen")


def _title() -> str:
    return str(getattr(config, "OWNER_TITLE", "") or "").strip()


def _done(sentence: str) -> str:
    title = _title()
    return f"{sentence[:-1]}, {title}." if title and sentence.endswith(".") else sentence


def _original(lowered: str, t: str, raw: str) -> str:
    """The same words as typed, capitals included."""
    start = t.find(lowered)
    return raw[start:start + len(lowered)] if start >= 0 and len(raw) == len(t) else lowered


def vault_command(t: str, raw: str, deps: Dict[str, Any]) -> Reply:
    """deps: vault, copy_briefly, queue, random_password."""
    vault = deps["vault"]

    def saved(label: str, password: str) -> Tuple[bool, str]:
        result = vault.save_entry(label, password=password)
        if isinstance(result, dict) and result.get("error"):
            return True, result["error"]
        return True, _done(f"Password for {label} saved in your vault.")

    m = _SAVE_LONG.search(t)
    if m:
        password = _original(m.group(2).strip(), t, raw).strip().strip("\"'")
        return saved(m.group(1).strip(), password)
    m = _SAVE_SHORT.search(t)
    if m:
        password = _original(m.group(1).strip(), t, raw).strip("\"'")
        return saved(m.group(2).strip(), password)

    m = _GET.match(t)
    if m:
        entry = vault.find_entry(m.group(1).strip())
        if not entry:
            return None  # Not in the vault: let the Wi-Fi password command have a go.
        deps["copy_briefly"](entry["password"])
        return True, f"Copied the {entry['label']} password. It leaves your clipboard in a minute."

    if t in _LIST:
        labels = vault.list_labels()
        if not labels:
            return True, _done("Your vault is empty.")
        return True, f"I have {len(labels)} entries: " + ", ".join(entry["label"] for entry in labels) + "."

    m = _DELETE.match(t)
    if m:
        label = m.group(1).strip()

        def delete():
            return True, (f"Deleted {label} from the vault." if vault.delete_entry(label) else f"No vault entry for {label}.")
        return deps["queue"](f"Delete the {label} vault entry", delete)

    m = _GENERATE.match(t)
    if m:
        length = int(m.group(1)) if m.group(1) else 20
        if not 8 <= length <= 128:
            return True, "Password length must be between 8 and 128."
        deps["copy_briefly"](deps["random_password"](length=length))
        return True, f"Generated a {length}-character password and copied it. It leaves your clipboard in a minute."
    return None


def is_screen_request(t: str) -> bool:
    return t in _SCREEN_EXACT or any(t == p or t.startswith(p + " ") or t.startswith(p + ",") or t.startswith(p + ":")
                                     for p in _SCREEN_PHRASES)


def screen_command(t: str, raw: str, deps: Dict[str, Any]) -> Reply:
    """deps: analyze_screen, ask. Only for clear requests about the screen."""
    if not is_screen_request(t):
        return None
    question = raw
    for phrase in sorted(_SCREEN_PHRASES + _SCREEN_EXACT, key=len, reverse=True):
        question = re.sub(re.escape(phrase), "", question, flags=re.IGNORECASE)
    question = question.strip(" .,?!:") or "What is on the screen? Answer it or solve it."
    result = deps["analyze_screen"](question)
    if result.get("mode") == "ocr":
        try:
            reply = deps["ask"]([{"role": "user", "content": (
                f"I captured the screen. Text found on it:\n---\n{result['ocr'][:4000]}\n---\n\n"
                f"My question: {result.get('question', question)}\n\nAnswer directly.")}])
        except Exception as exc:
            return True, f"I read the screen, but the AI didn't answer: {exc}"
        return True, reply
    return True, result.get("reply", "I couldn't read the screen.")
