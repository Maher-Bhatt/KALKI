"""
KALKI v5 — Silent Launcher
==========================

This module serves as the entry point for the Jarvis (KALKI) application.
It performs the following functions:
- Registers Windows auto-start (HKCU Run + Startup folder shortcut).
- Spawns `server.py` and `listener.py` as background processes with no console windows.
- Monitors the child processes and respawns them if they unexpectedly terminate.

Ensures that only a single instance of the launcher runs simultaneously using Windows mutexes.
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from typing import Optional, Any

# Ensure we operate in the base directory where the script resides
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

import config

LOG_PATH = os.path.join(BASE_DIR, "data", "launcher.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def log(msg: str) -> None:
    """
    Append a timestamped message to the launcher log file.
    Suppresses any IO errors to ensure the launcher does not crash due to logging failures.
    
    Args:
        msg (str): The message to log.
    """
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


def find_pythonw() -> str:
    """
    Locate the pythonw.exe executable to launch processes without a visible console window.
    Falls back to python.exe or sys.executable if pythonw.exe is not found.

    Returns:
        str: Path to the Python executable.
    """
    here = os.path.dirname(sys.executable)
    p = os.path.join(here, "pythonw.exe")
    if os.path.exists(p):
        return p
    p = os.path.join(here, "python.exe")
    if os.path.exists(p):
        return p
    return sys.executable


def spawn(script: str) -> subprocess.Popen:
    """
    Spawn a Python script as a background process using pythonw.exe.
    
    Args:
        script (str): The filename of the Python script to execute (e.g., 'server.py').

    Returns:
        subprocess.Popen: The process object of the spawned script.
    """
    pyw = find_pythonw()
    # 0x08000000 is the Windows CREATE_NO_WINDOW flag
    cflags = 0x08000000 if os.name == "nt" else 0
    return subprocess.Popen(
        [pyw, os.path.join(BASE_DIR, script)],
        cwd=BASE_DIR,
        creationflags=cflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def register_registry(enabled: bool = True) -> bool:
    """
    Add or remove the launcher from the Windows Registry for auto-start.

    Args:
        enabled (bool): If True, adds to registry. If False, removes from registry.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        import winreg
    except ImportError as e:
        log(f"winreg unavailable: {e}")
        return False
        
    pyw = find_pythonw()
    launcher = os.path.abspath(__file__)
    cmd = f'"{pyw}" "{launcher}"'
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, 
            winreg.KEY_SET_VALUE | winreg.KEY_WRITE
        )
        if enabled:
            winreg.SetValueEx(key, "KALKI_v5", 0, winreg.REG_SZ, cmd)
            log(f"registry autostart set: {cmd}")
        else:
            try: 
                winreg.DeleteValue(key, "KALKI_v5")
            except FileNotFoundError: 
                pass
            log("registry autostart removed")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log(f"registry write failed: {e}")
        return False


def register_startup_folder(enabled: bool = True) -> bool:
    """
    Drop a .bat file in the user's Startup folder as a redundant auto-start mechanism.

    Args:
        enabled (bool): If True, creates the .bat file. If False, deletes it.

    Returns:
        bool: True if successful, False otherwise.
    """
    startup = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    bat = os.path.join(startup, "KALKI_v5.bat")
    pyw = find_pythonw()
    launcher = os.path.abspath(__file__)
    
    try:
        os.makedirs(startup, exist_ok=True)
        if enabled:
            content = (
                "@echo off\r\n"
                f'start "" "{pyw}" "{launcher}"\r\n'
            )
            with open(bat, "w", encoding="utf-8") as f:
                f.write(content)
            log(f"startup .bat written: {bat}")
        else:
            if os.path.exists(bat):
                os.remove(bat)
                log("startup .bat removed")
        return True
    except Exception as e:
        log(f"startup folder write failed: {e}")
        return False


def acquire_single_instance() -> Optional[Any]:
    """
    Ensure only a single instance of this launcher is running at a time.
    Uses a Windows named mutex.

    Returns:
        Optional[Any]: Returns a handle to the mutex if successfully acquired, 
                       or None if another instance is already running.
                       Returns True if the check was skipped (e.g. pywin32 missing).
    """
    try:
        import win32event
        import win32api
        import winerror
        
        # Create a named mutex; if it already exists, win32api.GetLastError() 
        # will return ERROR_ALREADY_EXISTS.
        handle = win32event.CreateMutex(None, False, "Global\\KALKI_v5_launcher")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            return None
        return handle
    except ImportError as e:
        log(f"single-instance check skipped (pywin32 not installed: {e})")
        return True  # Don't block startup if pywin32 is unavailable
    except Exception as e:
        log(f"single-instance check skipped ({e})")
        return True


def main() -> None:
    """
    Main entry point for the launcher.
    Acquires the mutex, sets up auto-start, launches the background services,
    and then enters an infinite loop to monitor and respawn them if they die.
    """
    log("launcher start")

    _lock = acquire_single_instance()
    if _lock is None:
        log("another launcher already running — exiting to avoid duplicate stack")
        return

    if getattr(config, "AUTO_START", False):
        register_registry(True)
        register_startup_folder(True)

    server_proc = spawn("server.py")
    log(f"server.py pid={server_proc.pid}")
    time.sleep(2.5)  # Give the server time to start up and bind ports
    
    listener_proc = spawn("listener.py")
    log(f"listener.py pid={listener_proc.pid}")

    try:
        while True:
            time.sleep(5)
            # Check if server process has terminated
            if server_proc.poll() is not None:
                log(f"server died (rc={server_proc.returncode}) — respawning")
                server_proc = spawn("server.py")
                
            # Check if listener process has terminated
            if listener_proc.poll() is not None:
                log(f"listener died (rc={listener_proc.returncode}) — respawning")
                listener_proc = spawn("listener.py")
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C (if run manually in a console)
        try: 
            server_proc.terminate()
        except Exception: 
            pass
        try: 
            listener_proc.terminate()
        except Exception: 
            pass
        log("launcher stopping (KeyboardInterrupt)")


if __name__ == "__main__":
    main()
