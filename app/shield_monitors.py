"""The background monitors behind the Security page's shield toggles.

Each toggle maps to code that really runs, and status() reports what is actually
happening, so the UI never has to guess:

  download_watcher  Scans new files in Downloads (Windows Defender + heuristics).
  process_monitor   Checks running processes for miners and programs run from Temp.
  clipboard_guard   Warns about pipe-to-shell commands and swapped crypto addresses.
  phishing_shield   Checks the active browser tab's address. It reads browsing
                    activity, so it's off until the user turns it on.

None of these send anything off this PC. Alerts never contain clipboard text or
full URLs, only what's needed to act on them.

Limits, stated honestly: these poll on a timer, so they warn after something
happens rather than blocking it. Windows Defender remains the real-time protection.
"""

import os
import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import antivirus
import oversight

_PARTIAL_DOWNLOAD = (".crdownload", ".part", ".partial", ".tmp", ".download", ".opdownload")
_MAX_SEEN = 5000


def _alert(kind: str, message: str, severity: str = "warning") -> None:
    oversight.record_alert(kind, message, severity)
    try:
        import notify
        notify.notify_desktop("KALKI security alert", message)
    except Exception:
        pass


class DownloadWatcher:
    def __init__(self, folder: Optional[str] = None, settle_seconds: float = 5):
        self.folder = folder or os.path.join(os.path.expanduser("~"), "Downloads")
        self.settle_seconds = settle_seconds
        self._seen: Optional[set] = None

    def available(self) -> bool:
        return os.path.isdir(self.folder)

    def _snapshot(self) -> Dict[str, float]:
        files = {}
        try:
            with os.scandir(self.folder) as entries:
                for entry in entries:
                    try:
                        if entry.is_file() and not entry.name.lower().endswith(_PARTIAL_DOWNLOAD):
                            files[entry.path] = entry.stat().st_mtime
                    except OSError:
                        continue
        except OSError:
            pass
        return files

    def poll(self) -> None:
        files = self._snapshot()
        if self._seen is None:
            # Files already here are old news. Quick Scan covers them.
            self._seen = {(path, mtime) for path, mtime in files.items()}
            return
        now = time.time()
        for path, mtime in files.items():
            key = (path, mtime)
            if key in self._seen or now - mtime < self.settle_seconds:
                continue
            self._seen.add(key)
            self._handle(path)
        if len(self._seen) > _MAX_SEEN:
            self._seen = {(path, mtime) for path, mtime in files.items()}

    def _handle(self, path: str) -> None:
        verdict = antivirus.scan_file(path)
        name = os.path.basename(path)
        if verdict.get("scan_status") == "not_scanned":
            _alert("shield_download", f"Couldn't scan the new download '{name}'. Open it with care.", "warning")
        elif not verdict.get("clean"):
            level = verdict.get("threat_level", "Medium")
            severity = "critical" if level in ("Critical", "High") else "warning"
            _alert("shield_download", f"New download '{name}' looks risky ({level}). Review it in Security.", severity)


class ProcessMonitor:
    def __init__(self):
        self._reported: set = set()

    def available(self) -> bool:
        return antivirus.psutil is not None

    def poll(self) -> None:
        result = antivirus.scan_processes()
        current = set()
        for item in result.get("suspicious", []):
            key = (item.get("pid"), item.get("reason"))
            current.add(key)
            if key not in self._reported:
                severity = "critical" if item.get("severity") in ("Critical", "High") else "warning"
                _alert("shield_process", f"{item.get('name')} (PID {item.get('pid')}): {item.get('reason')}", severity)
        self._reported = current


class ClipboardGuard:
    def __init__(self, swap_window_seconds: float = 15):
        self.swap_window = swap_window_seconds
        self._last_text: Optional[str] = None
        self._last_addresses: Dict[str, tuple] = {}

    def available(self) -> bool:
        if os.name != "nt":
            return False
        try:
            import win32clipboard  # noqa: F401
            return True
        except ImportError:
            return False

    def check(self, text: Optional[str], now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if not text or text == self._last_text:
            return None
        self._last_text = text
        now = time.time() if now is None else now
        finding = None
        result = antivirus.inspect_clipboard(text)
        if not result.get("clean"):
            finding = {"type": "command"}
            _alert("shield_clipboard",
                   "Your clipboard holds a command that downloads and runs code. Don't paste it unless you trust the source.",
                   "warning")
        for coin, addresses in (result.get("crypto_detected") or {}).items():
            address = addresses[0]
            previous = self._last_addresses.get(coin)
            if previous and previous[0] != address and now - previous[1] <= self.swap_window:
                finding = {"type": "address_swap", "coin": coin}
                _alert("shield_clipboard",
                       f"Your copied {coin} address changed within seconds, to one ending ...{address[-6:]}. "
                       "Clipboard malware does this. Check the address before sending anything.",
                       "critical")
            self._last_addresses[coin] = (address, now)
        return finding

    def poll(self) -> None:
        import clipboard_mod
        self.check(clipboard_mod.read_text())


class LinkGuard:
    def __init__(self):
        self._reported: set = set()
        self._last_url: Optional[str] = None

    def available(self) -> bool:
        if os.name != "nt":
            return False
        try:
            import comtypes  # noqa: F401
            return True
        except ImportError:
            return False

    def check(self, url: Optional[str]) -> None:
        if not url or url == self._last_url:
            return
        self._last_url = url
        verdict = antivirus.scan_url(url)
        if verdict.get("clean"):
            return
        host = urlparse(url).hostname or "this site"
        if host not in self._reported:
            self._reported.add(host)
            _alert("shield_link", f"The site '{host}' looks suspicious: {'; '.join(verdict.get('findings', []))[:160]}", "warning")

    def poll(self) -> None:
        import browser_url
        self.check(browser_url.get_active_url())


_MONITORS = {
    "download_watcher": (DownloadWatcher(), 10),
    "process_monitor": (ProcessMonitor(), 60),
    "clipboard_guard": (ClipboardGuard(), 2),
    "phishing_shield": (LinkGuard(), 5),
}
_state: Dict[str, Dict[str, Any]] = {key: {"last_check": None, "last_error": None} for key in _MONITORS}
_threads: Dict[str, threading.Thread] = {}
_start_lock = threading.Lock()


def _loop(key: str, monitor: Any, interval: float) -> None:
    com_ready = False
    while True:
        try:
            if antivirus.get_shield_settings().get(key) and monitor.available():
                if key == "phishing_shield" and not com_ready:
                    import comtypes
                    comtypes.CoInitialize()
                    com_ready = True
                monitor.poll()
                _state[key]["last_check"] = time.time()
                _state[key]["last_error"] = None
        except Exception as exc:
            _state[key]["last_error"] = str(exc)[:200]
        time.sleep(interval)


def start() -> None:
    """Start every monitor thread once. Each one checks its toggle on every cycle."""
    with _start_lock:
        for key, (monitor, interval) in _MONITORS.items():
            if key not in _threads or not _threads[key].is_alive():
                thread = threading.Thread(target=_loop, args=(key, monitor, interval), daemon=True, name=f"shield-{key}")
                thread.start()
                _threads[key] = thread


def status() -> Dict[str, Dict[str, Any]]:
    """What each monitor is really doing right now."""
    settings = antivirus.get_shield_settings()
    report = {}
    for key, (monitor, interval) in _MONITORS.items():
        enabled = bool(settings.get(key))
        available = monitor.available()
        thread = _threads.get(key)
        report[key] = {
            "enabled": enabled,
            "available": available,
            "running": bool(enabled and available and thread is not None and thread.is_alive()),
            "interval_seconds": interval,
            "last_check": _state[key]["last_check"],
            "last_error": _state[key]["last_error"],
        }
    return report
