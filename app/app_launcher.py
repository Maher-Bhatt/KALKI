"""Open installed apps the way the Start menu does.

"spotify.exe" only works when the app's folder is on PATH, and Microsoft Store apps
(Spotify, Apple Music, WhatsApp) never are. Windows' own list of installed apps,
Get-StartApps, has every app with the ID the Start menu launches it by, so KALKI
looks the name up there and opens it through explorer, with no shell in between.
"""

import json
import re
import subprocess
import sys
import threading
import time
from typing import Dict, Optional, Tuple

REFRESH_SECONDS = 10 * 60
_lock = threading.Lock()
_cache: Dict[str, Tuple[str, str]] = {}   # lowercase name -> (display name, AppID)
_cached_at = 0.0

# Words people add that aren't part of the app's name.
_FILLER = re.compile(r"\b(the|app|application|program|software|for me|please|now)\b")
ALIASES = {"vs code": "visual studio code", "vscode": "visual studio code", "code": "visual studio code",
           "word": "word", "excel": "excel", "powerpoint": "powerpoint", "explorer": "file explorer",
           "files": "file explorer", "terminal": "terminal", "cmd": "command prompt", "task manager": "task manager"}
_NOT_APPS = re.compile(r"\b(uninstall|readme|documentation|help|license|release notes)\b")


def _load() -> Dict[str, Tuple[str, str]]:
    if sys.platform != "win32":
        return {}
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                              "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"],
                             capture_output=True, text=True, timeout=20,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data = json.loads(res.stdout if isinstance(res.stdout, str) and res.stdout.strip() else "[]")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return {}
    if isinstance(data, dict):
        data = [data]
    return {str(d["Name"]).strip().lower(): (str(d["Name"]).strip(), str(d["AppID"])) for d in data
            if isinstance(d, dict) and d.get("Name") and d.get("AppID")}


def installed_apps(refresh: bool = False) -> Dict[str, Tuple[str, str]]:
    """{lowercase name: (display name, AppID)}. Never waits on Windows: the list is loaded
    in the background (warm() at startup) and refreshed in the background when it's old."""
    with _lock:
        stale = bool(_cache) and time.time() - _cached_at > REFRESH_SECONDS
        snapshot = dict(_cache)
    if refresh or stale:
        warm()
    return snapshot


_loading = threading.Event()


def _reload() -> None:
    global _cached_at
    try:
        fresh = _load()
        if fresh:
            with _lock:
                _cache.clear()
                _cache.update(fresh)
                _cached_at = time.time()
    finally:
        _loading.clear()


def warm(wait: bool = False) -> None:
    """Load the list of installed apps in the background (once at a time)."""
    if sys.platform != "win32":
        return
    if not _loading.is_set():
        _loading.set()
        thread = threading.Thread(target=_reload, daemon=True, name="installed-apps")
        thread.start()
        if wait:
            thread.join(30)


def find(name: str, apps: Optional[Dict[str, Tuple[str, str]]] = None) -> Optional[Tuple[str, str]]:
    """(display name, AppID) of the best installed app for a spoken name: exact, then
    starts-with, then as a whole word inside the name. Uninstallers and help entries never match."""
    apps = installed_apps() if apps is None else apps
    key = re.sub(r"\s+", " ", _FILLER.sub(" ", (name or "").lower())).strip(" .,!?")
    key = ALIASES.get(key, key)
    if not key:
        return None
    usable = {n: v for n, v in apps.items() if not _NOT_APPS.search(n)}
    if key in usable:
        return usable[key]
    for rule in (lambda n: n.startswith(key), lambda n: re.search(r"\b" + re.escape(key) + r"\b", n)):
        hits = sorted((n for n in usable if rule(n)), key=len)
        if hits:
            return usable[hits[0]]
    return None


def launch(name: str) -> Optional[str]:
    """Open the app. Returns its display name, or None if it isn't installed or wouldn't start."""
    found = find(name)
    if not found:
        return None
    display, app_id = found
    try:
        subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + app_id])
    except OSError:
        return None
    return display


def is_installed(name: str) -> bool:
    return find(name) is not None
