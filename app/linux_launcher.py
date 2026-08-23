#!/usr/bin/env python3
"""KALKI Linux launcher.

This is the reliable Linux entry point. It keeps the local server and listener
in child processes, opens the dashboard in the user's default browser, and
falls back gracefully when optional desktop audio or microphone packages are
not installed.
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

from runtime_paths import prepare_runtime

RUNTIME = prepare_runtime()
APP_ROOT = Path(RUNTIME.app_root)
USER_DATA = Path(RUNTIME.user_data_dir)

import config
import runtime_security

runtime_security.TOKEN_PATH = str(USER_DATA / "data" / "api_token.txt")
DATA_DIR = USER_DATA / "data"
LOG_PATH = DATA_DIR / "linux_launcher.log"

_children: dict[str, subprocess.Popen] = {}
_stopping = False


def log(message: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {message}\n")
    except OSError:
        pass


def command_for(name: str) -> list[str]:
    return [sys.executable, str(APP_ROOT / name)]


def start_child(name: str) -> None:
    previous = _children.get(name)
    if previous and previous.poll() is None:
        return
    try:
        _children[name] = subprocess.Popen(
            command_for(name),
            cwd=str(APP_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log(f"started {name} pid={_children[name].pid}")
    except OSError as exc:
        log(f"could not start {name}: {exc}")


def stop_children(*, terminate: bool = True) -> None:
    for name, process in list(_children.items()):
        if process.poll() is not None:
            continue
        try:
            process.terminate() if terminate else process.kill()
            process.wait(timeout=4)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass
        log(f"stopped {name}")


def server_ready(timeout: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", int(config.PORT)), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def open_dashboard() -> None:
    url = f"http://127.0.0.1:{int(config.PORT)}/"
    try:
        import webbrowser
        webbrowser.open(url, new=2)
        log(f"dashboard opened at {url}")
    except Exception as exc:
        log(f"could not open browser automatically: {exc}; open {url} manually")


def listener_preflight() -> tuple[bool, str]:
    """Return whether continuous listening is safe to start on this host."""
    if str(getattr(config, "LISTEN_MODE", "always")).lower() != "always":
        return False, "Continuous microphone listening is disabled; push-to-talk remains available."
    try:
        import speech_recognition  # noqa: F401
    except Exception:
        return False, "Continuous listening unavailable: install SpeechRecognition and select push-to-talk for typed/browser workflows."
    try:
        import pyaudio
    except Exception:
        return False, "Continuous listening unavailable: install PyAudio plus PortAudio; typed/browser workflows remain available."
    audio = None
    try:
        audio = pyaudio.PyAudio()
        input_devices = 0
        for index in range(audio.get_device_count()):
            try:
                if float(audio.get_device_info_by_index(index).get("maxInputChannels", 0)) > 0:
                    input_devices += 1
            except Exception:
                continue
        if input_devices == 0:
            return False, "Continuous listening unavailable: no microphone input device is visible; typed/browser workflows remain available."
    except Exception as exc:
        return False, f"Continuous listening unavailable: microphone probe failed ({exc}); typed/browser workflows remain available."
    finally:
        if audio is not None:
            try:
                audio.terminate()
            except Exception:
                pass
    return True, ""


def handle_signal(signum, _frame) -> None:
    global _stopping
    if _stopping:
        return
    _stopping = True
    log(f"received signal {signum}; stopping")
    stop_children()
    raise SystemExit(0)


def main() -> int:
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    log("Linux launcher start")

    marker = USER_DATA / "setup_complete.marker"
    if not marker.exists():
        wizard = APP_ROOT / "kalki_setup_wizard.py"
        if wizard.exists():
            log("first run: launching setup wizard")
            subprocess.run(command_for("kalki_setup_wizard.py"), cwd=str(APP_ROOT), check=False)
        if not marker.exists():
            log("setup not completed; exiting")
            return 2

    listener_enabled, listener_notice = listener_preflight()
    if listener_notice:
        os.environ["KALKI_LISTENER_NOTICE"] = listener_notice
        log(listener_notice)
    start_child("server.py")
    if not server_ready():
        log("server did not become ready; opening dashboard anyway")
    if listener_enabled:
        start_child("listener.py")
    else:
        log("listener child not started because microphone capability preflight failed or listening is disabled")
    open_dashboard()

    try:
        while True:
            time.sleep(2)
            if _stopping:
                break
            if _children.get("server.py") and _children["server.py"].poll() is not None:
                log("server exited; restarting")
                start_child("server.py")
            if listener_enabled and _children.get("listener.py") and _children["listener.py"].poll() is not None:
                log("listener exited; restarting")
                start_child("listener.py")
    finally:
        stop_children()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
