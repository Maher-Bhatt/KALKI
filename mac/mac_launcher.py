#!/usr/bin/env python3
"""KALKI macOS Desktop Launcher (v1.4.0).

Supervises local KALKI background services on macOS, opens the interface
via native Cocoa WebKit (pywebview) or system browser, and provides native
macOS integration (Apple Music AppleScript bridge, native notifications, and
macOS 'say' synthesis fallback).
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Runtime initialization
APP_DIR = Path(__file__).resolve().parent.parent / "app"
if not APP_DIR.exists():
    APP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(APP_DIR))

from runtime_paths import prepare_runtime
RUNTIME = prepare_runtime()
USER_DATA = Path(RUNTIME.user_data_dir)
DATA_DIR = USER_DATA / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = DATA_DIR / "macos_launcher.log"

import config
import runtime_security

runtime_security.TOKEN_PATH = str(DATA_DIR / "api_token.txt")

_children: dict[str, subprocess.Popen] = {}
_stopping = False


def log(msg: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {msg}\n")
    except OSError:
        pass


def notify_macos(title: str, message: str) -> None:
    """Send native macOS Notification Center alert."""
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def start_child(name: str, script_name: str) -> None:
    if _children.get(name) and _children[name].poll() is None:
        return
    cmd = [sys.executable, str(APP_DIR / script_name)]
    try:
        _children[name] = subprocess.Popen(
            cmd,
            cwd=str(APP_DIR),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy()
        )
        log(f"Started {name} (PID: {_children[name].pid})")
    except Exception as exc:
        log(f"Failed to start {name}: {exc}")


def stop_children() -> None:
    for name, proc in list(_children.items()):
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
            log(f"Stopped {name}")


def wait_for_server(timeout: float = 18.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{config.PORT}/api/health", timeout=0.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def open_interface() -> None:
    url = f"http://127.0.0.1:{config.PORT}"
    
    # Try native pywebview Cocoa WebKit first
    try:
        import webview
        print(f"[KALKI] Launching native macOS WebKit window on {url}...")
        window = webview.create_window(
            title="KALKI AI Assistant",
            url=url,
            width=1400,
            height=880,
            min_size=(960, 680),
            background_color="#070809"
        )
        webview.start(private_mode=False)
        return
    except Exception as exc:
        log(f"pywebview unavailable on macOS: {exc}, opening browser...")

    # System browser fallback
    try:
        import webbrowser
        webbrowser.open(url, new=2)
        print(f"[KALKI] Dashboard opened in browser at {url}")
    except Exception as exc:
        log(f"Browser launch error: {exc}")


def main() -> int:
    def _sig_handler(signum, frame):
        print("\nShutting down KALKI macOS Assistant...")
        stop_children()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    print("========================================================")
    print("  KALKI AI Assistant — macOS Supervisor (v1.4.0)")
    print("========================================================")
    print(f"App Root: {APP_DIR}")
    print(f"Data Root: {USER_DATA}")

    # Start backend server
    start_child("server", "server.py")

    print(f"Waiting for backend to bind port {config.PORT}...")
    if not wait_for_server():
        print("Warning: Backend took longer than expected; proceeding to open UI.")

    # Start voice listener if SpeechRecognition/PyAudio available
    start_child("listener", "listener.py")

    # Open UI window
    open_interface()

    # When UI closes, stop child services cleanly
    stop_children()
    return 0


if __name__ == "__main__":
    sys.exit(main())
