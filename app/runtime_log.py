"""Small rotating log writer used by KALKI's long-running processes."""

import json
import os
import re
import threading
from datetime import datetime


_REDACTED = "[REDACTED]"
_SECRET_PATTERNS = [
    re.compile(r"\b(?:gsk_|sk-|ghp_|github_pat_|xox[bp]-|AIza)[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|password|passwd|secret)(\s*[=:]\s*)[^\s,;&\"']{4,}"),
]
_registered_secrets = set()
_locks = {}
_locks_guard = threading.Lock()


def register_secret(value):
    """Remove this exact value from every future log line. Short values are ignored
    because scrubbing them would mangle ordinary text."""
    if isinstance(value, str) and len(value) >= 8:
        _registered_secrets.add(value)


def scrub(text):
    """Best-effort removal of credentials from text about to be logged."""
    text = str(text)
    for value in _registered_secrets:
        text = text.replace(value, _REDACTED)
    text = _SECRET_PATTERNS[0].sub(_REDACTED, text)
    text = _SECRET_PATTERNS[1].sub(lambda m: f"{m.group(1)} {_REDACTED}", text)
    return _SECRET_PATTERNS[2].sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}", text)


def _lock_for(path):
    with _locks_guard:
        return _locks.setdefault(os.path.abspath(path), threading.Lock())


def _rotate(path, max_bytes, backups):
    try:
        if os.path.getsize(path) < max_bytes:
            return
    except OSError:
        return
    for index in range(backups, 0, -1):
        src = path if index == 1 else f"{path}.{index - 1}"
        dst = f"{path}.{index}"
        if os.path.exists(src):
            try:
                os.replace(src, dst)
            except OSError:
                pass


def append_log(path, message, max_bytes=2 * 1024 * 1024, backups=3):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _lock_for(path):
        _rotate(path, max_bytes, backups)
        try:
            with open(path, "a", encoding="utf-8") as f:
                stamp = datetime.now().isoformat(timespec="seconds")
                f.write(f"[{stamp}] {scrub(message)}\n")
        except OSError:
            pass


def log_event(log_path, level, event, /, **fields):
    """Write one searchable JSON record. Secrets are scrubbed like any other line."""
    append_log(log_path, json.dumps({"level": level, "event": event, **fields}, default=str, ensure_ascii=False))
