"""Reading and writing KALKI's small JSON files without ever losing data.

The dangerous pattern this replaces: read a file, treat any error as "empty", then
save, which overwrites the real data. Here the two kinds of failure stay separate:

- The file is corrupt: it's kept under a new name, and the default is returned.
- The file can't be read right now (locked, no permission): OSError is raised, so the
  caller can't go on to overwrite something it never read.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any


def read_json(path: str, default: Any) -> Any:
    """Return the file's contents, or `default` if it's missing or corrupt. Contents
    of a different type than `default` count as corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if isinstance(data, type(default)):
            return data
        reason = f"expected {type(default).__name__}"
    except ValueError as exc:
        reason = type(exc).__name__
    kept = f"{path}.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    os.replace(path, kept)
    sys.stderr.write(f"[KALKI] {os.path.basename(path)} was unreadable ({reason}), kept as {os.path.basename(kept)}\n")
    return default


def write_json(path: str, data: Any) -> None:
    """Write atomically: a crash or error leaves the old file complete."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
