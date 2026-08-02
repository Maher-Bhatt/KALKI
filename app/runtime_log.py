"""Small rotating log writer used by KALKI's long-running processes."""

import os
import threading
from datetime import datetime


_locks = {}
_locks_guard = threading.Lock()


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
                f.write(f"[{stamp}] {message}\n")
        except OSError:
            pass
