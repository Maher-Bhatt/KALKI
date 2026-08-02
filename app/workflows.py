"""
KALKI workflow modes — single-phrase action chains.
"""

import os
import re
import json
import subprocess
import webbrowser

ACTIVE_STATE = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_ROUTINES_PATH = os.path.join(BASE_DIR, "data", "custom_routines.json")

# Action chain definitions. Each step is a (action, *args) tuple.
# Actions are interpreted by `run_mode` below.
MODES = {
    "study mode": [
        ("open_app", "code"),
        ("open_url", "https://open.spotify.com/playlist/37i9dQZF1DWWQRwui0ExPn"),
        ("set_volume", 40),
        ("speak", "Study mode engaged, Sir. Lo-fi playing, Code is open. Focus."),
    ],
    "gaming mode": [
        ("set_state", "gaming"),
        ("open_app", "steam"),
        ("open_app", "discord"),
        ("set_volume", 70),
        ("kill_app", "chrome"),
        ("kill_app", "code"),
        ("run_cmd", "powershell -Command \"Start-Process ms-settings:quietmoments\""),
        ("speak", "Gaming rig ready, Sir. Background apps cleared and settings open for Do Not Disturb."),
    ],
    "shutdown routine": [
        ("kill_app", "chrome"),
        ("kill_app", "code"),
        ("kill_app", "spotify"),
        ("kill_app", "discord"),
        ("lock_pc",),
        ("speak", "Closing things down, Sir. Locking the PC."),
    ],
    "focus mode": [
        ("set_volume", 25),
        ("kill_app", "discord"),
        ("speak", "Focus mode. Distractions silenced."),
    ],
    "morning routine": [
        ("open_url", "https://mail.google.com"),
        ("open_url", "https://calendar.google.com"),
        ("speak", "Good morning, Sir. Calendar and Gmail open."),
    ],
    "ctf mode": [
        ("set_state", "ctf"),
        ("open_app", "code"),
        ("open_app", "terminal"),
        ("speak", "CTF mode active, Sir. Neural net unconstrained. I am ready to solve challenges."),
    ],
    "developer mode": [
        ("set_state", "dev"),
        ("open_app", "code"),
        ("open_app", "terminal"),
        ("speak", "Developer mode active, Sir. IDE and terminal standing by."),
    ],
}


APP_MAP = {
    "chrome": "chrome.exe",
    "code": "code.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "steam": "steam.exe",
    "terminal": "wt.exe",
    "edge": "msedge.exe",
}


def list_modes():
    return list(MODES.keys())


# Common Google STT mishearings + casual aliases per mode.
# Lowercase. Checked as substring.
MODE_ALIASES = {
    "study mode":       ["study", "studying", "study session", "study time",
                         "focus session", "let's study"],
    "gaming mode":      ["gaming", "game mode", "let's game", "play games",
                         "gaming time"],
    "shutdown routine": ["wind down", "shutdown mode"],
    "focus mode":       ["focus", "focused mode", "concentrate", "deep work"],
    "morning routine":  ["morning", "morning mode", "wake up"],
    "ctf mode":         ["ctf", "city of mode", "see tee eff", "city of",
                         "capture the flag", "cyber mode", "hacking mode",
                         "set up mode", "ceftc mode", "ceeteeef",
                         "ctf time", "ctf session"],
    "developer mode":   ["developer mode", "dev mode", "coding mode"],
}

def load_custom_routines():
    if os.path.exists(CUSTOM_ROUTINES_PATH):
        try:
            with open(CUSTOM_ROUTINES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for mode, details in data.items():
                    # details contains "actions" and "aliases"
                    MODES[mode] = [tuple(action) for action in details.get("actions", [])]
                    MODE_ALIASES[mode] = details.get("aliases", [])
        except Exception as e:
            print(f"Error loading custom routines: {e}")

load_custom_routines()

def add_custom_routine(name, actions, aliases=None):
    """Save a custom routine dynamically."""
    name = name.lower().strip()
    if not aliases:
        aliases = []
    
    data = {}
    if os.path.exists(CUSTOM_ROUTINES_PATH):
        try:
            with open(CUSTOM_ROUTINES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    data[name] = {
        "actions": actions,
        "aliases": aliases
    }
    
    os.makedirs(os.path.dirname(CUSTOM_ROUTINES_PATH), exist_ok=True)
    with open(CUSTOM_ROUTINES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    MODES[name] = [tuple(action) for action in actions]
    MODE_ALIASES[name] = aliases

def find_mode(text):
    """Match a mode from natural-language text. Handles mishearings."""
    if not text:
        return None
    t = text.lower().strip()
    # 1) Exact mode name appears in text
    for mode in MODES.keys():
        if mode in t:
            return mode
    # 2) All words from the mode name appear (order-free)
    for mode in MODES.keys():
        words = mode.split()
        if all(w in t for w in words):
            return mode
    activation = re.search(
        r"\b(start|activate|enable|engage|begin|launch|enter|switch to|turn on)\b",
        t,
    )
    # 3) Aliases only match as a complete command or with an activation verb.
    for mode, aliases in MODE_ALIASES.items():
        for a in aliases:
            if t == a or (activation and re.search(
                    r"\b" + re.escape(a) + r"\b", t)):
                return mode
    return None


def requires_confirmation(mode_name):
    return any(
        step[0] in {"kill_app", "lock_pc"}
        for step in MODES.get(mode_name, ())
    )


def run_mode(mode_name, *, speak_fn=None, set_volume_fn=None,
             open_url_fn=None, lock_fn=None):
    """Execute a workflow. Pass in callable hooks from the server."""
    mode_name = mode_name.lower().strip()
    if mode_name not in MODES:
        return {"ok": False, "error": f"Unknown mode: {mode_name}",
                "available": list(MODES.keys())}

    actions = MODES[mode_name]
    log = []
    for step in actions:
        action = step[0]
        args = step[1:]
        try:
            if action == "open_app":
                exe = APP_MAP.get(args[0], args[0])
                subprocess.Popen([exe])
                log.append(f"opened {args[0]}")

            elif action == "kill_app":
                exe = APP_MAP.get(args[0], args[0])
                try:
                    import psutil
                    for p in psutil.process_iter(["name"]):
                        try:
                            if p.info["name"] and p.info["name"].lower() == exe.lower():
                                p.kill()
                        except Exception:
                            pass
                    log.append(f"killed {args[0]}")
                except Exception as e:
                    log.append(f"couldn't kill {args[0]}: {e}")

            elif action == "open_url":
                if open_url_fn:
                    open_url_fn(args[0])
                else:
                    webbrowser.open(args[0])
                log.append(f"opened url {args[0][:40]}")

            elif action == "set_volume":
                if set_volume_fn:
                    set_volume_fn(args[0])
                    log.append(f"volume {args[0]}")

            elif action == "lock_pc":
                if lock_fn:
                    lock_fn()
                else:
                    subprocess.Popen(
                        ["rundll32.exe", "user32.dll,LockWorkStation"]
                    )
                log.append("locked PC")

            elif action == "speak":
                if speak_fn:
                    speak_fn(args[0])
                log.append(f"said: {args[0][:30]}")
                
            elif action == "set_state":
                global ACTIVE_STATE
                ACTIVE_STATE = args[0]
                log.append(f"state set to {args[0]}")
                
            elif action == "run_cmd":
                subprocess.Popen(args[0], shell=True)
                log.append(f"ran command {args[0][:20]}")

            else:
                log.append(f"unknown action {action}")
        except Exception as e:
            log.append(f"error in {action}: {e}")

    return {"ok": True, "mode": mode_name, "log": log}
