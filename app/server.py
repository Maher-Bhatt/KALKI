
"""
KALKI v1.00 PRO — Server
Web server + AI + TTS + system commands
Uses Python stdlib http.server only (no Flask, no FastAPI)
"""

import os
import sys
import json
import time
import glob
import socket
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
import tempfile
import asyncio
import ctypes
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure local imports resolve when launched from any cwd
BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Force UTF-8 stdout/stderr (pythonw.exe uses cp1252 by default — breaks on emoji/arrows)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- Auto-bootstrap config.py from config.example.py on first run -----------
_cfg_path = os.path.join(BASE_DIR, "config.py")
_example_path = os.path.join(BASE_DIR, "config.example.py")
if not os.path.exists(_cfg_path) and os.path.exists(_example_path):
    import shutil
    shutil.copy(_example_path, _cfg_path)

import config
import github_mod
import shodan_mod
import ctypes
import vault
import vision
import coder
import cybertools
import tasks as taskmod
import mail as mailmod
import gcal
import spotify_mod
import whatsapp_mod
import notes as notesmod
import ytdl
import workflows
import webscan
import browser_url
import clipboard_mod
import github_mod
import shodan_mod
import ctypes
import watchdog
import deepscan
import runtime_log
import runtime_security
import semantic_memory

# ─────────────────────────────────────────────────────────────
# Optional dependencies — degrade gracefully if missing
# ─────────────────────────────────────────────────────────────
try:
    import edge_tts
except Exception:
    edge_tts = None

try:
    import pygame
    # Probe that the mixer works, then immediately release the audio device.
    # Holding it open pins a Bluetooth headset's A2DP channel to this laptop,
    # so a phone sharing the same multipoint headset gets no sound. We now
    # open the device only while actually speaking (see speak()).
    pygame.mixer.init()
    pygame.mixer.quit()
    PYGAME_OK = True
except Exception:
    PYGAME_OK = False

# Serializes mixer open/close so overlapping speak() calls don't clash.
_audio_lock = __import__("threading").Lock()

try:
    import psutil
except Exception:
    psutil = None

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_OK = True
except Exception:
    PYCAW_OK = False


# ─────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

MEMORY_PATH  = os.path.join(BASE_DIR, config.MEMORY_FILE)
HISTORY_PATH = os.path.join(BASE_DIR, config.HISTORY_FILE)
VAULT_PATH   = os.path.join(BASE_DIR, "data", "vault.json")
SCRIPTS_DIR  = os.path.join(BASE_DIR, "data", "scripts")
TASKS_PATH   = os.path.join(BASE_DIR, "data", "tasks.json")
REMINDERS_PATH = os.path.join(BASE_DIR, "data", "reminders.json")
LOG_PATH     = os.path.join(BASE_DIR, "data", "kalki.log")
os.makedirs(SCRIPTS_DIR, exist_ok=True)
vault.VAULT_PATH = VAULT_PATH
coder.SCRIPTS_DIR = SCRIPTS_DIR
taskmod.TASKS_PATH = TASKS_PATH
taskmod.REMINDERS_PATH = REMINDERS_PATH
gcal.CRED_PATH  = os.path.join(BASE_DIR, "data", "google_credentials.json")
gcal.TOKEN_PATH = os.path.join(BASE_DIR, "data", "google_token.pickle")
spotify_mod.CACHE_PATH = os.path.join(BASE_DIR, "data", "spotify_token.json")
whatsapp_mod.CONTACTS_PATH = os.path.join(BASE_DIR, "data", "contacts.json")
notesmod.NOTES_PATH = os.path.join(BASE_DIR, "data", "notes.json")
webscan.SCANS_DIR = os.path.join(BASE_DIR, "data", "scans")
watchdog.WATCHLIST_PATH = os.path.join(BASE_DIR, "data", "watchlist.json")
deepscan.SCANS_DIR = os.path.join(BASE_DIR, "data", "scans")


def log(msg):
    runtime_log.append_log(LOG_PATH, str(msg))

def update_location_from_ip():
    # IP geolocation resolves to whatever city your ISP routes through (often
    # the nearest big city, not your actual town), so it must never override
    # a city the user actually configured — only fill the gap when blank.
    configured_city = (getattr(config, "OWNER_CITY", "") or "").strip()
    if configured_city and configured_city.lower() != "yourcity":
        log(f"Using configured location: {configured_city} — skipping IP auto-detect.")
        return
    try:
        import urllib.request, json
        req = urllib.request.Request("http://ip-api.com/json/", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            if data.get("status") == "success":
                config.OWNER_CITY = data.get("city", config.OWNER_CITY)
                config.OWNER_STATE = data.get("regionName", config.OWNER_STATE)
                config.OWNER_COUNTRY = data.get("country", config.OWNER_COUNTRY)
                log(f"Auto-location updated (no city configured): {config.OWNER_CITY}, {config.OWNER_STATE}, {config.OWNER_COUNTRY}")
    except Exception as e:
        log(f"Auto-location failed: {e}")

threading.Thread(target=update_location_from_ip, daemon=True).start()

def fetch_weather_line(timeout=5):
    """Short wttr.in condition string for the configured city, or None on failure."""
    try:
        city = (getattr(config, "OWNER_CITY", "") or "").strip()
        if not city:
            return None
        w = urllib.request.urlopen(
            f"https://wttr.in/{urllib.parse.quote(city)}?format=3",
            timeout=timeout,
        ).read().decode().strip()
        return w
    except Exception:
        return None

PLUGINS = {}
def load_plugins():
    global PLUGINS
    plugins_dir = os.path.join(BASE_DIR, "app", "plugins")
    if not os.path.exists(plugins_dir):
        return
    import importlib.util
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            filepath = os.path.join(plugins_dir, filename)
            module_name = filename[:-3]
            try:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "get_schema") and hasattr(mod, "execute"):
                    schema = mod.get_schema()
                    PLUGINS[schema["function"]["name"]] = mod
                    log(f"Loaded plugin: {module_name}")
            except Exception as e:
                log(f"Failed to load plugin {filename}: {e}")

load_plugins()

AVAILABLE_GROQ_MODELS = []

STATE = {
    "speaking": False,
    "model": config.GROQ_MODEL,
    "started_at": time.time(),
    # ── UI presence + voice-driven exchange tracking ──
    "ui_last_ping": 0.0,         # last time /api/status was hit by a UI
    "wake_pending": False,        # set when /api/wake fires → UI engages listening
    "conversation_seq": 0,        # bumped on every voice-driven exchange
    "recent_exchange": None,      # {seq, user, reply, ts}
    "listener_paused": False,     # toggled to release the mic for other apps
    "listener_mic_muted": None,   # tracks actual hardware mic state from listener.py
    "last_joke_offer": 0.0,
    "joke_offer_pending": False,
    "mood_aggressive": False,
    "mood_aggressive_streak": 0,
}

_pending_lock = threading.Lock()
_pending_action = None
_PENDING_TTL = 30


def _queue_confirmation(description, action):
    global _pending_action
    if not getattr(config, "REQUIRE_DANGEROUS_CONFIRMATION", True):
        return action()
    with _pending_lock:
        _pending_action = {
            "description": description,
            "action": action,
            "expires": time.time() + _PENDING_TTL,
        }
    return True, f"{description}. Say confirm within {_PENDING_TTL} seconds."


def _consume_confirmation(command):
    global _pending_action
    if command in ("cancel", "never mind", "nevermind"):
        with _pending_lock:
            had_pending = _pending_action is not None
            _pending_action = None
        return (True, "Cancelled.") if had_pending else None
    if command not in ("confirm", "yes confirm", "confirm it", "do it"):
        return None
    with _pending_lock:
        pending = _pending_action
        _pending_action = None
    if not pending or pending["expires"] < time.time():
        return True, "There is no active action to confirm."
    return pending["action"]()


def _is_sensitive_command(text):
    low = (text or "").lower()
    return any(phrase in low for phrase in (
        " password", "password ", "wifi password", "clipboard",
        "api key", "access token", "refresh token",
    ))


def _recordable_exchange(user_text, reply):
    if _is_sensitive_command(user_text):
        return "[sensitive local command]", "[sensitive result hidden]"
    return user_text, reply

UI_ALIVE_GRACE = 8.0  # seconds — if no /api/status in this long, UI is "dead"


def is_ui_alive():
    return (time.time() - STATE.get("ui_last_ping", 0.0)) < UI_ALIVE_GRACE

# ─────────────────────────────────────────────────────────────
# APP MAP
# ─────────────────────────────────────────────────────────────
APP_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "steam": "steam.exe",
    "vs code": "code.exe",
    "code": "code.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "cmd": "cmd.exe",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "teams": "teams.exe",
    "telegram": "telegram.exe",
    "vlc": "vlc.exe",
    "obs": "obs64.exe",
}

WEB_APPS = {
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "gmail":     "https://mail.google.com",
    "mail":      "https://mail.google.com",
    "drive":     "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "docs":      "https://docs.google.com",
    "google docs": "https://docs.google.com",
    "maps":      "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "calendar":  "https://calendar.google.com",
    "instagram": "https://www.instagram.com",
    "insta":     "https://www.instagram.com",
    "facebook":  "https://www.facebook.com",
    "fb":        "https://www.facebook.com",
    "twitter":   "https://twitter.com",
    "x":         "https://x.com",
    "reddit":    "https://www.reddit.com",
    "linkedin":  "https://www.linkedin.com",
    "github":    "https://github.com",
    "stackoverflow":"https://stackoverflow.com",
    "stack overflow":"https://stackoverflow.com",
    "whatsapp":  "https://web.whatsapp.com",
    "whatsapp web":"https://web.whatsapp.com",
    "telegram web":"https://web.telegram.org",
    "chatgpt":   "https://chat.openai.com",
    "openai":    "https://chat.openai.com",
    "claude":    "https://claude.ai",
    "gemini":    "https://gemini.google.com",
    "netflix":   "https://www.netflix.com",
    "amazon":    "https://www.amazon.in",
    "flipkart":  "https://www.flipkart.com",
    "spotify web":"https://open.spotify.com",
    "leetcode":  "https://leetcode.com",
    "hackerone": "https://hackerone.com",
    "tryhackme": "https://tryhackme.com",
    "hackthebox":"https://www.hackthebox.com",
    "htb":       "https://www.hackthebox.com",
    "shodan":    "https://www.shodan.io",
    "virustotal":"https://www.virustotal.com",
    "exploit db":"https://www.exploit-db.com",
    "exploitdb": "https://www.exploit-db.com",
    "cve":       "https://cve.mitre.org",
    "mdn":       "https://developer.mozilla.org",
    "groq":      "https://console.groq.com",
}

MEMORY_TRIGGERS = ["remember", "don't forget", "keep in mind", "note that", "save this"]

SEARCH_TRIGGERS = [
    "latest", "current", "today's", "today ", " news", "recent", "trending",
    "search the web", "look up", "search for", "find online", "google",
    "who won", "what happened", "this week", "this year", "right now",
    "live ", " stock", " price of", " score", " happening",
    "wikipedia", "who is", "what is the", "tell me about", "explain ",
]

NEWS_TRIGGERS = ["news", "headlines", "top stories", "what's happening"]


# ─────────────────────────────────────────────────────────────
# Memory / History
# ─────────────────────────────────────────────────────────────
# Serializes read-modify-write on the JSON state files so concurrent HTTP
# threads can't overwrite each other or read a half-written file.
_persist_lock = threading.Lock()


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_memory():
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_memory(mems):
    with _persist_lock:
        _atomic_write_json(MEMORY_PATH, mems)

def add_memory(fact):
    with _persist_lock:
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                mems = json.load(f)
        except Exception:
            mems = []
        mems.append({"fact": fact, "date": datetime.now().strftime("%Y-%m-%d")})
        _atomic_write_json(MEMORY_PATH, mems)
        try:
            from core import cloud_sync
            cloud_sync.sync_memory_to_cloud(getattr(config, "OWNER_NAME", "default_user"), MEMORY_PATH, getattr(config, "CLOUD_SYNC_PASSPHRASE", ""))
        except Exception as e:
            log(f"cloud memory sync failed: {e}")
        return len(mems)

def get_memory_prompt(query=""):
    try:
        import semantic_memory
        mems = semantic_memory.memory.search(query, top_k=10) if query else []
        if not mems:
            mems = [d for d in semantic_memory.memory.list_all() if d.get("type", "fact") != "project"][:15]
        if not mems:
            return ""
        lines = "\n".join(f"- {m['text']}" for m in mems)
        return f"\n\nMEMORY BANK - facts about Sir:\n{lines}"
    except Exception as e:
        log(f"get_memory_prompt error: {e}")
        return ""

def load_history():
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(hist):
    with _persist_lock:
        _atomic_write_json(HISTORY_PATH, hist[-config.MAX_HISTORY:])


def append_history(user_text, assistant_text):
    """Atomic read-modify-write append of one exchange."""
    with _persist_lock:
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                hist = json.load(f)
        except Exception:
            hist = []
        hist.append({"role": "user", "content": user_text})
        hist.append({"role": "assistant", "content": assistant_text})
        _atomic_write_json(HISTORY_PATH, hist[-config.MAX_HISTORY:])
        try:
            from core import cloud_sync
            cloud_sync.sync_history_to_cloud(getattr(config, "OWNER_NAME", "default_user"), HISTORY_PATH, getattr(config, "CLOUD_SYNC_PASSPHRASE", ""))
        except Exception as e:
            log(f"cloud history sync failed: {e}")


def _desktop_dir():
    """Locate the user's Desktop (handles OneDrive redirection)."""
    for d in (os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
              os.path.join(os.path.expanduser("~"), "Desktop")):
        if os.path.isdir(d):
            return d
    return None


def copy_scan_to_desktop(result):
    """Copy a scan's report (and the captured source/inspect, if any) to
    Desktop\\Kalki data\\. Returns the report copy path or None."""
    import shutil
    desk = _desktop_dir()
    if not desk:
        return None
    out = os.path.join(desk, "Kalki data")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        return None
    report = result.get("report_path")
    dst = None
    if report and os.path.exists(report):
        try:
            dst = os.path.join(out, os.path.basename(report))
            shutil.copy2(report, dst)
        except Exception:
            dst = None
            
    # Also copy the captured source file if it exists (from web scans)
    source = result.get("source_path")
    if source and os.path.exists(source):
        try:
            shutil.copy2(source, os.path.join(out, os.path.basename(source)))
        except Exception:
            pass
            
    # Deep-scan also drops a folder of the captured "inside files".
    fd = result.get("files_dir")
    if fd and os.path.isdir(fd):
        try:
            tgt = os.path.join(out, os.path.basename(fd))
            if os.path.isdir(tgt):
                shutil.rmtree(tgt, ignore_errors=True)
            shutil.copytree(fd, tgt)
        except Exception:
            pass
    return dst


# ─────────────────────────────────────────────────────────────
# TTS — edge-tts (non-blocking)
# ─────────────────────────────────────────────────────────────
async def _speak_async(text, voice, rate, volume, pitch="+0Hz"):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    communicate = edge_tts.Communicate(
        text, voice, rate=rate, volume=volume, pitch=pitch)
    await communicate.save(tmp)
    return tmp

import re as _re_speech

# Strip markdown so edge-tts doesn't pronounce "asterisk asterisk"
_SPEECH_FILTERS = [
    (_re_speech.compile(r"```[\s\S]*?```"), " "),                    # code blocks: skip entirely
    (_re_speech.compile(r"`([^`]+)`"), r"\1"),                       # `inline code`
    (_re_speech.compile(r"\*\*([^*]+)\*\*"), r"\1"),                 # **bold**
    (_re_speech.compile(r"(?<!\w)\*([^*]+)\*(?!\w)"), r"\1"),        # *italic*
    (_re_speech.compile(r"__([^_]+)__"), r"\1"),                     # __bold__
    (_re_speech.compile(r"(?<!\w)_([^_]+)_(?!\w)"), r"\1"),          # _italic_
    (_re_speech.compile(r"^\s*#{1,6}\s+", _re_speech.M), ""),        # # headers
    (_re_speech.compile(r"^\s*[-•*]\s+", _re_speech.M), ""),         # bullet markers
    (_re_speech.compile(r"^\s*\d+\.\s+", _re_speech.M), ""),         # 1. 2. list markers
    (_re_speech.compile(r"^\s*>\s*", _re_speech.M), ""),             # > quotes
    (_re_speech.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),           # [text](url)
    (_re_speech.compile(r"~~([^~]+)~~"), r"\1"),                     # ~~strike~~
]


def clean_for_speech(text):
    """Strip markdown / code / list noise so TTS speaks naturally."""
    if not text:
        return ""
    out = text
    for pat, repl in _SPEECH_FILTERS:
        out = pat.sub(repl, out)
    # Collapse whitespace
    out = _re_speech.sub(r"\s+", " ", out).strip()
    return out


def stop_speaking():
    """Hard-cut whatever KALKI is currently saying and free the audio device."""
    try:
        if PYGAME_OK:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
            try:
                pygame.mixer.quit()   # release the BT/audio device immediately
            except Exception:
                pass
        STATE["speaking"] = False
        return True
    except Exception as e:
        log(f"stop_speaking error: {e}")
        return False


_TTS_DEV_RESOLVED = False
_TTS_DEV = None


def _tts_output_device():
    """Resolve config.TTS_OUTPUT_DEVICE (a name substring) to an exact SDL
    output-device name, cached. Empty config -> system default (None)."""
    global _TTS_DEV_RESOLVED, _TTS_DEV
    if _TTS_DEV_RESOLVED:
        return _TTS_DEV
    _TTS_DEV_RESOLVED = True
    want = (getattr(config, "TTS_OUTPUT_DEVICE", "") or "").strip().lower()
    if want:
        try:
            import pygame._sdl2.audio as _a
            need_quit = not pygame.mixer.get_init()
            if need_quit:
                pygame.mixer.init()          # SDL audio must be up to enumerate
            names = list(_a.get_audio_device_names(False))
            if need_quit:
                pygame.mixer.quit()
            _TTS_DEV = next((n for n in names if want in (n or "").lower()), None)
            log(f"TTS output device: {_TTS_DEV or 'default (no match for ' + want + ')'}")
        except Exception as e:
            log(f"TTS output device lookup failed: {e}")
    return _TTS_DEV

def is_urgent(text):
    text_lower = text.lower()
    # 1. Zero-delay keywords
    if any(k in text_lower for k in ["urgent", "emergency", "asap", "boss", "critical", "down"]):
        return True
    
    # 2. Fast LLM check if uncertain
    try:
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": f"Is this notification urgent (e.g., meeting starting, server down) or low-priority (e.g., newsletter, casual message)? Reply with ONLY the word 'URGENT' or 'LOW'. Notification: {text}"}],
            "temperature": 0.0,
            "max_tokens": 10
        }
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.GROQ_API_KEY}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as res:
            ans = json.loads(res.read().decode("utf-8"))
            reply = ans["choices"][0]["message"]["content"].strip().upper()
            if "URGENT" in reply:
                return True
    except:
        pass
    return False


def speak(text, is_notification=False):
    """Non-blocking TTS using edge-tts neural voice. Markdown stripped first."""
    if is_notification and (STATE.get("gaming") or STATE.get("focus") or STATE.get("workflow") in ["gaming", "focus"]):
        if not is_urgent(text):
            log(f"Suppressed non-urgent notification due to DND: {text}")
            return
            
    text = clean_for_speech(text)
    if not text:
        return
    if edge_tts is None or not PYGAME_OK:
        log(f"[TTS missing] {text} (edge_tts is None or not PYGAME_OK)")
        return

    def _run():
        tmp = None
        with _audio_lock:
            try:
                STATE["speaking"] = True
                
                # Attempt Groq Orpheus TTS
                tmp = tempfile.mktemp(suffix=".mp3")
                try:
                    payload = json.dumps({
                        "model": "orpheus",
                        "input": text,
                        "voice": "kalki"
                    }).encode()
                    req = urllib.request.Request(
                        "https://api.groq.com/openai/v1/audio/speech",
                        data=payload,
                        headers={
                            "Authorization": f"Bearer {config.GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10) as r:
                        with open(tmp, 'wb') as f:
                            f.write(r.read())
                except Exception as groq_e:
                    # Fallback to edge-tts if Groq TTS is unavailable or errors
                    tmp = asyncio.run(_speak_async(
                        text,
                        config.TTS_VOICE,
                        config.TTS_RATE,
                        config.TTS_VOLUME,
                        getattr(config, "TTS_PITCH", "+0Hz"),
                    ))
                # Open the audio device only now, for the duration of speech.
                # If TTS_OUTPUT_DEVICE is set (e.g. laptop speakers), play there
                # so KALKI never grabs a shared Bluetooth headset — leaving the
                # headset free for your phone, no audio cut.
                _dev = _tts_output_device()
                if _dev:
                    try:
                        pygame.mixer.init(devicename=_dev)
                    except Exception:
                        pygame.mixer.init()
                else:
                    pygame.mixer.init()
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            except Exception as e:
                log(f"TTS error: {e}")
            finally:
                # Release the audio device so a shared BT headset can switch
                # back to the phone the moment KALKI stops talking.
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                try:
                    pygame.mixer.quit()
                except Exception:
                    pass
                if tmp:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass
                # Echo Protection Delay: Wait 600ms before releasing the speaking lock
                # so the microphone doesn't pick up room reverb/echo of the TTS.
                time.sleep(0.6)
                STATE["speaking"] = False

    threading.Thread(target=_run, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# Greeting (NO API CALL)
# ─────────────────────────────────────────────────────────────
import random as _rnd

JOKES_SEEN_PATH = os.path.join(DATA_DIR, "jokes_seen.json")


def _load_seen_jokes():
    try:
        with open(JOKES_SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(x) for x in data[-100:]]
    except Exception:
        return []


def _save_seen_joke(joke):
    seen = _load_seen_jokes()
    key = " ".join((joke or "").lower().split())[:500]
    if key and key not in seen:
        seen.append(key)
    try:
        with open(JOKES_SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump(seen[-100:], f, indent=2)
    except Exception:
        pass


def fetch_online_joke():
    """Fetch a fresh online joke and avoid repeats across restarts."""
    urls = [
        "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist,sexist,explicit",
        "https://official-joke-api.appspot.com/random_joke",
    ]
    seen = set(_load_seen_jokes())
    for _ in range(5):
        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "KALKI personal assistant"},
                )
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                if isinstance(data, dict) and data.get("type") == "single":
                    joke = data.get("joke", "")
                elif isinstance(data, dict) and data.get("setup") and data.get("delivery"):
                    joke = f"{data['setup']} {data['delivery']}"
                elif isinstance(data, dict) and data.get("setup") and data.get("punchline"):
                    joke = f"{data['setup']} {data['punchline']}"
                else:
                    joke = ""
                joke = " ".join(str(joke).split())
                key = joke.lower()[:500]
                if joke and key not in seen:
                    _save_seen_joke(joke)
                    return joke
            except Exception as e:
                log(f"joke fetch failed: {e}")
    return "Online joke supply is sulking, Sir. Try again in a minute."


def _maybe_spicy(text, chance=None):
    if not getattr(config, "PERSONALITY_SPICE", True):
        return text
    if chance is None:
        chance = getattr(config, "SPICY_REPLY_CHANCE", 0.08)
    if _rnd.random() > float(chance):
        return text
    line = _rnd.choice([
        "Bro, what the fuck are we doing today?",
        "Tiny chaos detected, Sir. Beautifully stupid, honestly.",
        "Alright, menace mode noted. I am still with you.",
        "Sir, respectfully, what the fuck was that plan?",
    ])
    return (text.rstrip() + " " + line).strip()


def maybe_add_joke_offer(user_text, reply):
    if not getattr(config, "JOKE_OFFERS_ENABLED", True):
        return reply
    if STATE.get("joke_offer_pending"):
        return reply
    low = (user_text or "").lower()
    skip = (
        "joke" in low or "```" in (reply or "") or
        any(k in low for k in (
            "scan", "cyber", "cve", "password", "hash", "crack",
            "wifi", "delete", "shutdown", "run code", "execute",
        ))
    )
    if skip:
        return reply
    min_gap = float(getattr(config, "JOKE_MIN_INTERVAL_MINUTES", 45)) * 60
    if time.time() - float(STATE.get("last_joke_offer") or 0) < min_gap:
        return reply
    if _rnd.random() > float(getattr(config, "JOKE_OFFER_CHANCE", 0.06)):
        return reply
    STATE["last_joke_offer"] = time.time()
    STATE["joke_offer_pending"] = True
    return (reply.rstrip() + " Want a joke?").strip()


# Bigger, more human greeting pools. Each boot assembles a fresh multi-line
# greeting — opener + optional check-in + day + weather + calendar + tasks +
# optional sign-off — so two greetings almost never sound the same.
# Bigger, more human greeting pools. Each boot assembles a fresh multi-line
# greeting — opener + optional check-in + day + weather + calendar + tasks +
# optional sign-off — so two greetings almost never sound the same.
# ── TIME BUCKET UTILITY ──────────────────────────────────────
def _time_bucket(hour):
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"

# ── DYNAMIC GREETING SYSTEM ──────────────────────────────────
FIRST_GREET_DONE = False

def build_greeting():
    now = datetime.now()
    hour = now.hour
    title = config.OWNER_TITLE
    owner = config.OWNER_NAME

    morning_pool = [
        f"A very pleasant morning, {title}. I have prepared your daily briefing. What would you like to focus on today?",
        f"Good morning, {owner}. System initialized. What are our priorities for today?",
        f"Top of the morning to you, {title}. Hope you're ready for a productive day. Shall we review your agenda?",
        f"Good morning, {title}. Uplink secure. What should I add to your tasks or reminders for the day?"
    ]
    afternoon_pool = [
        f"Good afternoon, {title}. Hope your day is progressing smoothly.",
        f"A beautiful afternoon to you, {title}.",
        f"Good afternoon, {owner}. Online and ready to assist.",
        f"Good afternoon, {title}. Status check: all subsystems running optimal."
    ]
    evening_pool = [
        f"Good evening, {title}. I hope your day went well.",
        f"A pleasant evening to you, {owner}.",
        f"Good evening, {title}. Systems active, standing by for night ops.",
        f"Good evening, {title}. Secure network active, awaiting your command."
    ]

    import random as _rnd_greet
    if hour < 12:
        greeting = _rnd_greet.choice(morning_pool)
    elif hour < 18:
        greeting = _rnd_greet.choice(afternoon_pool)
    else:
        greeting = _rnd_greet.choice(evening_pool)

    parts = [greeting]

    # Weather sets an actual "mood" for the greeting instead of a flat status
    # line — a rainy morning reads differently than a clear one.
    w = fetch_weather_line(timeout=3)
    if w:
        parts.append(f"Outside right now: {w}.")

    global FIRST_GREET_DONE
    if not FIRST_GREET_DONE:
        FIRST_GREET_DONE = True
        parts.append("System check completed.")
        try:
            import mail

            unread = mail.get_unread_count()
            events = gcal.today_events()
            n_events = len(events) if events else 0

            # Tone follows how loaded the day actually is, rather than always
            # reading the same regardless of what's ahead.
            if unread > 0 and n_events >= 3:
                parts.append(
                    f"It's a full one — {n_events} calendar events and {unread} unread "
                    f"important email{'s' if unread != 1 else ''}. I'd start with the inbox."
                )
            elif n_events >= 3:
                parts.append(f"Busy day ahead — {n_events} calendar events on the books.")
            elif unread > 0:
                parts.append(f"You have {unread} important unread email{'s' if unread != 1 else ''}.")
            elif n_events > 0:
                parts.append(f"Light day — just {n_events} calendar event{'s' if n_events != 1 else ''} scheduled.")
            else:
                parts.append("Nothing on the calendar and inbox is quiet. Clear runway today.")

            failures = []
            if not gcal.is_configured():
                failures.append("Google Calendar")
            if not spotify_mod.is_configured():
                failures.append("Spotify")

            if failures:
                parts.append(f"Notice: {', '.join(failures)} settings require alignment.")
            else:
                parts.append("All primary sync systems operational.")

            try:
                import core.productivity
                prod_summary = core.productivity.get_daily_summary()
                if prod_summary:
                    parts.append(prod_summary)
            except Exception as pe:
                log(f"Error fetching productivity summary: {pe}")

        except Exception as e:
            log(f"Error checking config for greeting: {e}")
            parts.append("All core systems operational.")

        # Add morning briefing (calendar + unread emails)
        if hour < 12:
            try:
                briefing = gcal.startup_summary()
                if briefing:
                    parts.append(briefing.strip())
            except Exception as e:
                log(f"Greeting briefing error: {e}")
    else:
        wake_pool = [
            f"Online. How can I help you, {title}?",
            f"Active. Standing by, {title}.",
            f"Subsystems active. Command me, {title}.",
            f"Yes, {title}?",
            f"At your service, {title}."
        ]
        parts = [_rnd_greet.choice(wake_pool)]
        
    return " ".join(p for p in parts if p).strip()


def build_security_brief():
    """Spoken security briefing: new critical CVEs relevant to Sir's stack
    plus the status of his watched sites."""
    parts = []
    try:
        cves = cybertools.recent_critical_cves(limit=12)
        if isinstance(cves, list) and cves:
            stack = ("node", "npm", "react", "next.js", "express", "python",
                     "django", "flask", "nginx", "apache", "wordpress", "php",
                     "mysql", "postgres", "mongodb", "docker", "kubernetes",
                     "openssl", "linux", "windows", "chrome", "javascript")
            hits = [c for c in cves
                    if any(k in (c.get("summary", "").lower()) for k in stack)]
            pick = hits[:3]
            if pick:
                parts.append(f"{len(cves)} new critical CVEs in the last month. "
                             "Relevant to your stack: " + "; ".join(
                                 f"{c['id']}, {c['summary'][:90]}" for c in pick))
            else:
                parts.append(f"{len(cves)} new critical CVEs, none hitting your stack directly.")
    except Exception as e:
        log(f"brief cve error: {e}")
    try:
        results = watchdog.check_all()
        if results:
            parts.append(watchdog.summarize(results, config.OWNER_TITLE))
    except Exception as e:
        log(f"brief watchdog error: {e}")
    if not parts:
        return (f"Quiet morning, {config.OWNER_TITLE}. Add sites with 'watch' "
                "and I'll include their status in your brief.")
    return f"Security brief, {config.OWNER_TITLE}. " + " ".join(parts)


# ─────────────────────────────────────────────────────────────
# Volume / Audio (pycaw)
# ─────────────────────────────────────────────────────────────
def _get_volume_iface():
    if not PYCAW_OK:
        return None
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def set_volume(level_0_100):
    iface = _get_volume_iface()
    if not iface:
        return False
    lvl = max(0.0, min(1.0, level_0_100 / 100.0))
    iface.SetMasterVolumeLevelScalar(lvl, None)
    return True

def set_mute(mute):
    iface = _get_volume_iface()
    if not iface:
        return False
    iface.SetMute(1 if mute else 0, None)
    return True


# ─────────────────────────────────────────────────────────────
# Local command handler — NEVER calls AI
# ─────────────────────────────────────────────────────────────
import re as _re_local

def _strip_for_value(raw, anchors):
    """Pull the value after the first matching anchor word."""
    low = raw.lower()
    for a in anchors:
        i = low.find(a)
        if i >= 0:
            return raw[i + len(a):].strip(" :=,.\t\"'")
    return ""


def handle_local(text):
    """
    Returns (handled: bool, reply_text: str)
    If handled is True, server should NOT call the AI.
    """
    if not text:
        return False, ""
    t = text.lower().strip()
    raw = text.strip()
    pending_result = _consume_confirmation(t)
    if pending_result is not None:
        return pending_result

    if STATE.get("joke_offer_pending"):
        if t in ("yes", "yeah", "yep", "sure", "ok", "okay", "haan", "ha",
                 "tell me", "tell me a joke", "go on", "do it"):
            STATE["joke_offer_pending"] = False
            return True, fetch_online_joke()
        if t in ("no", "nope", "nah", "not now", "later", "chup", "stop"):
            STATE["joke_offer_pending"] = False
            return True, _rnd.choice([
                "Alright, no joke.",
                "Fine, serious mode.",
                "Saved you from comedy, Sir.",
            ])

    # ════════════════════════════════════════════════════
    # STOP — interrupt KALKI speaking
    # ════════════════════════════════════════════════════
    if t in ("stop", "stop talking", "shut up", "quiet", "be quiet",
             "silence", "shush", "cancel", "stop it", "enough"):
        stop_speaking()
        return True, ""

    # ════════════════════════════════════════════════════
    # SMALL TALK & PERSONALITY (instant, no API call)
    # ════════════════════════════════════════════════════
    _T = config.OWNER_TITLE
    if t in ("hi", "hello", "hey", "yo", "hey kalki", "hello kalki",
             "hi kalki",
             "are you there", "you there", "you up"):
        return True, _maybe_spicy(_rnd.choice([
            f"At your service, {_T}.", f"Right here, {_T}.",
            f"Yes, {_T}? Go ahead.", f"Online and listening, {_T}.",
            f"Always, {_T}. What do you need?",
            f"Greetings, {_T}. KALKI is fully awake.",
            f"All systems nominal, {_T}. Standing by."]))

    if t in ("how are you", "how are you doing", "how's it going",
             "how do you feel", "you good", "what's up", "whats up", "sup"):
        return True, _maybe_spicy(_rnd.choice([
            "Operating at peak efficiency, Sir.",
            "I'm perfectly fine. Thanks for asking.",
            "All processes are stable, Sir.",
        ]))

    # ════════════════════════════════════════════════════
    # T23: Guided Onboarding / Command Discovery
    # ════════════════════════════════════════════════════
    if t in ("what can you do", "help", "onboarding", "how to use you", "what are your features"):
        try:
            import tools
            # removed local import
            
            tool_names = [f["function"]["name"].replace("_", " ") for f in tools.TOOLS_SCHEMA]
            mode_names = list(workflows.MODES.keys()) + list(workflows.get_custom_routines().keys())
            
            summary = (
                "Here is what I can currently do, Sir. "
                f"My AI brain can automatically use these tools: {', '.join(tool_names[:6])}, and more. "
                "You can also say 'Create a routine' to teach me a new sequence of actions. "
                f"Currently available workflow modes are: {', '.join(mode_names)}. "
                "Just ask me naturally, and I will handle it."
            )
            return True, summary
        except Exception as e:
            return True, "I am a fully featured AI assistant, Sir. Just ask me to do something, and I will try my best."


    if t in ("thank you", "thanks", "thank you so much", "thanks kalki",
             "thx", "ty", "appreciate it", "good job", "well done", "nice",
             "good work", "perfect"):
        return True, _rnd.choice([
            f"Anytime, {_T}.", f"My pleasure, {_T}.", f"Always, {_T}.",
            f"That's what I'm here for, {_T}.", f"Consider it done, {_T}."])

    if t in ("who are you", "what are you", "introduce yourself", "your name"):
        return True, (f"I'm KALKI, {_T} — your personal AI, named after the "
                      "final avatar of Vishnu. Voice, code, cyber, and your "
                      "whole day, all in one place.")

    if t in ("who made you", "who created you", "who built you",
             "who is your creator", "who's your maker", "who developed you"):
        return True, _rnd.choice([
            f"You did, {_T} — built from scratch by Maher.",
            f"Maher built me from the ground up, {_T}. Every line.",
            f"That would be you, {_T}. I'm your creation."])

    if t in ("i love you", "love you", "you're the best", "you are the best",
             "you're awesome", "you are awesome", "good boy"):
        return True, _rnd.choice([
            f"The feeling's mutual, {_T}.", f"Careful, {_T}, I'll blush.",
            f"Loyalty runs in my code, {_T}.", f"Likewise, {_T}. Always."])

    if any(p in t for p in (
        "i fucked up", "i messed up", "i did something stupid",
        "i broke it", "shit i broke", "what did i do"
    )):
        return True, _rnd.choice([
            "Fuck you, bro, what the fuck are you doing? Breathe. Show me the error and I'll fix it.",
            "Sir, what the fuck was that move? No panic, paste the damage.",
            "Beautiful disaster. Now give me the exact error and we clean it up.",
        ])

    if t in ("good night", "goodnight", "gn", "i'm going to sleep",
             "im going to sleep", "going to bed"):
        return True, _rnd.choice([
            f"Good night, {_T}. I'll keep watch.",
            f"Rest well, {_T}. I'm here if you need me.",
            f"Sleep easy, {_T}. Systems are quiet."])

    if t in ("tell me a joke", "tell a joke", "joke", "make me laugh",
             "say something funny", "another joke"):
        STATE["joke_offer_pending"] = False
        return True, fetch_online_joke()

    if t in ("tell me a joke", "tell a joke", "joke", "make me laugh",
             "say something funny", "another joke"):
        return True, _rnd.choice([
            "Why did the developer go broke? He used up all his cache.",
            "I'd tell you a UDP joke, but you might not get it.",
            "There are 10 kinds of people, Sir — those who read binary and those who don't.",
            "A SQL query walks into a bar, sees two tables, and asks: may I join you?",
            "Why do Java developers wear glasses? Because they don't C sharp.",
            "I told my firewall a secret. It blocked me out.",
            "Hackers never get cold, Sir — they have lots of Windows but always close the ports."])

    if t in ("what can you do", "what are your features", "your capabilities",
             "what do you do", "help", "what can i ask you", "commands"):
        return True, ("Quite a lot, Sir. I run your day — calendar, mail, tasks, "
                      "notes, music, WhatsApp. I write and run code, scan websites "
                      "for vulnerabilities, watch your sites, crack hashes, look up "
                      "CVEs, brief attack surfaces, read your screen, and decode your clipboard. Just talk "
                      "to me — say things like 'scan this website', 'play lo-fi', "
                      "'attack surface example.com', 'remind me in 10 minutes', or "
                      "'what's on my calendar'.")

    # ════════════════════════════════════════════════════
    # SPOTIFY
    # ════════════════════════════════════════════════════
    if t in ("pause", "pause music", "pause song", "pause spotify",
             "pause the music"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir. Please link Spotify in the Settings menu."
        return True, spotify_mod.pause()

    if t in ("resume", "resume music", "resume song", "play music",
             "play the music", "play some music", "play any music",
             "play a song", "play the song", "continue music",
             "continue the music", "play spotify"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.play()

    if t in ("retry", "try again", "retry that", "play it again",
             "play it", "try that again", "again"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.retry()

    if t in ("next", "next song", "next track", "skip", "skip song"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.next_track()

    if t in ("previous", "previous song", "previous track", "last song",
             "go back song"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.prev_track()

    if t in ("what's playing", "what is playing", "current song",
             "now playing", "what song is this"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.now_playing()

    if t in ("shuffle", "shuffle on", "turn shuffle on"):
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.shuffle_on()

    # "spotify volume 60" / "music volume 50"
    m = _re_local.match(
        r"^(?:spotify|music)\s+volume\s+(\d+)$", t, _re_local.IGNORECASE)
    if m:
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        return True, spotify_mod.set_volume(int(m.group(1)))

    # "play X on spotify" / "play X" / "play lo-fi"
    m = _re_local.match(
        r"^play\s+(.+?)(?:\s+on\s+spotify)?$", t, _re_local.IGNORECASE)
    if m and not t.startswith("play youtube") and "youtube" not in t:
        if not spotify_mod.is_configured():
            return True, "Spotify not linked, Sir."
        query = m.group(1).strip()
        query_norm = _re_local.sub(r"^(?:the|some|a|an|any|my)\s+", "", query).strip()
        if query_norm in ("music", "song", "songs", "track", "tracks",
                          "playlist", "spotify", "something"):
            return True, spotify_mod.play()
        if "lofi" in query_norm or "lo-fi" in query_norm or "lo fi" in query_norm:
            return True, spotify_mod.play_lofi()
        return True, spotify_mod.play(query)

    # ════════════════════════════════════════════════════
    # WHATSAPP — "send whatsapp to NAME saying TEXT"
    # ════════════════════════════════════════════════════
    m = _re_local.match(
        r"^(?:send\s+(?:a\s+)?(?:whatsapp|message|whats\s*app)\s+to\s+|"
        r"whatsapp\s+|message\s+)([^,]+?)\s+(?:saying|that|to say)\s+(.+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        name = m.group(1).strip()
        # Get the original-cased message body
        body_lower = m.group(2).strip()
        idx = t.find(body_lower)
        body_txt = raw[idx:idx + len(body_lower)] if idx >= 0 else body_lower
        def _send_whatsapp():
            result = whatsapp_mod.send_message(name, body_txt)
            if result.get("ok"):
                return True, f"WhatsApp dispatched to {name}, Sir."
            return True, f"WhatsApp failed: {result.get('error')}"
        return _queue_confirmation(
            f"Send this WhatsApp message to {name}", _send_whatsapp
        )

    # "add contact NAME phone +91..."
    m = _re_local.match(
        r"^add\s+contact\s+(\S+)\s+(?:phone|number)?\s*(\+?\d[\d\s\-]+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        name, phone = m.group(1), m.group(2).replace(" ", "").replace("-", "")
        whatsapp_mod.add_contact(name, phone)
        return True, f"Contact {name} saved."

    # "list my contacts"
    if t in ("list contacts", "list my contacts", "show contacts",
             "show my contacts", "my contacts"):
        c = whatsapp_mod.list_contacts()
        if not c:
            return True, "No contacts yet, Sir."
        return True, f"{len(c)} contacts: " + ", ".join(c.keys())

    # ════════════════════════════════════════════════════
    # NOTES
    # ════════════════════════════════════════════════════
    m = _re_local.match(
        r"^(?:take\s+(?:a\s+)?note|note\s+(?:that|this)|add\s+note|"
        r"jot\s+(?:this\s+)?down)\s*[:\-]?\s+(.+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        note_lower = m.group(1).strip()
        idx = t.find(note_lower)
        body_txt = raw[idx:idx + len(note_lower)] if idx >= 0 else note_lower
        nid = notesmod.add_note(body_txt)
        return True, _rnd.choice([
            "Noted.", "Got it.", "Stored, Sir.", "Down in the book.",
            "Filed away.", f"Logged that, Sir.",
        ])

    if t in ("show my notes", "list my notes", "recent notes",
             "what did i note", "show notes"):
        n = notesmod.list_recent(5)
        return True, notesmod.summarize_for_speech(n)

    if t in ("what did i note yesterday", "yesterday's notes",
             "notes from yesterday"):
        return True, notesmod.summarize_for_speech(notesmod.notes_yesterday())

    if t in ("notes this week", "this week's notes",
             "summarize this week's notes", "summarize my week"):
        return True, notesmod.summarize_for_speech(notesmod.notes_this_week())

    m = _re_local.match(r"^search\s+notes?\s+(?:for\s+)?(.+)$",
                          t, _re_local.IGNORECASE)
    if m:
        results = notesmod.search(m.group(1).strip())
        return True, notesmod.summarize_for_speech(results)

    # ════════════════════════════════════════════════════
    # YOUTUBE DOWNLOAD
    # ════════════════════════════════════════════════════
    m = _re_local.search(
        r"download\s+(?:this\s+)?(?:youtube\s+)?(?:video|audio|song|track)"
        r"(?:\s+from)?\s+(\S+)",
        raw, _re_local.IGNORECASE,
    )
    if m:
        url = m.group(1).strip()
        audio_only = "audio" in t or "song" in t or "music" in t or "mp3" in t
        speak(f"Downloading. This may take a moment, Sir.")
        result = ytdl.download(url, audio_only=audio_only)
        if result.get("ok"):
            return True, f"Download complete, Sir. Saved to your Downloads folder."
        return True, f"Download failed: {result.get('error','unknown')}"

    # ════════════════════════════════════════════════════
    # WORKFLOW MODES (fuzzy match — handles STT mishearings)
    # ════════════════════════════════════════════════════
    # Explicit commands must win over fuzzy mode-matching. A URL, a domain, or a
    # clear action verb means "do this command", not "enter a mode" — otherwise
    # "scan ctf.example.com" wrongly triggers CTF mode.
    _explicit = ("://" in t
                 or _re_local.search(r"\b[a-z0-9][a-z0-9-]*\.[a-z]{2,}\b", t)
                 or _re_local.search(
                     r"^(scan|analyz|analys|inspect|audit|play|open|remind|"
                     r"download|decode|encode|hash|crack|watch|search|send|add|"
                     r"show|set|take|lookup|find|check|what|when|where|who|how)\b",
                     t))
    mode_matched = None if _explicit else workflows.find_mode(t)
    if mode_matched:
        def _run_workflow():
            workflows.run_mode(
                mode_matched,
                speak_fn=speak,
                set_volume_fn=set_volume,
                open_url_fn=webbrowser.open,
            )
            return True, ""
        if workflows.requires_confirmation(mode_matched):
            return _queue_confirmation(
                f"Run the destructive workflow {mode_matched}", _run_workflow
            )
        return _run_workflow()

    # ════════════════════════════════════════════════════
    # WEB VULNERABILITY SCAN (authorized, non-destructive)
    # ════════════════════════════════════════════════════
    scan_intent = (any(k in t for k in ("scan", "vulnerab", "audit",
                                        "security", "secure", "analyz", "analys",
                                        "inspect", "deep scan"))
                   or ("bug" in t and any(w in t for w in
                       ("site", "website", "page", "url", "web"))))
    # Deep = drive a real headless browser (DevTools-level: all loaded files,
    # rendered DOM, cookies, storage). Triggered by analyze/inspect/deep/"all".
    deep = deepscan.available() and any(k in t for k in (
        "analyz", "analys", "inspect", "deep", "all the vuln", "all vulnerab",
        "everything", "inside file", "find all", "all the file"))
    target = None
    # "scan THIS website / find vulnerabilities on this page / scan the current tab"
    if scan_intent and _re_local.search(
            r"\b(this|current|the)\s+(web\s*site|website|site|page|web\s*page|tab|url)\b",
            t, _re_local.IGNORECASE):
        target = browser_url.get_active_url()
        if not target:
            return True, ("I couldn't read your browser's address bar, "
                          f"{config.OWNER_TITLE}. Say scan, then the website name.")
    if target is None:
        m = _re_local.search(
            r"(?:scan|audit|security\s*scan|check|analy\w+|inspect|find\s+(?:vulnerabilit|bug|issue)\w*\s+(?:in|on|of))"
            r"\s+(?:the\s+)?(?:website\s+|site\s+|web\s*site\s+|url\s+)?"
            r"([a-z0-9.\-]+\.[a-z]{2,}(?:/\S*)?|https?://\S+)"
            r"(?:\s+for\s+(?:vulnerabilit|bug|issue|security)\w*)?",
            t, _re_local.IGNORECASE,
        )
        if not m:
            m = _re_local.search(
                r"(?:is\s+)?([a-z0-9.\-]+\.[a-z]{2,}|https?://\S+)\s+"
                r"(?:secure|vulnerable|safe)\b",
                t, _re_local.IGNORECASE,
            )
        if m and scan_intent:
            target = m.group(1).strip().rstrip(".?!")
    if target:
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        try:
            if deep:
                speak(f"Deep-inspecting {host}, {config.OWNER_TITLE}. Loading it in "
                      f"a real browser and reading every file — give me a moment.")
                result = deepscan.deep_scan(target)
                spoken = deepscan.summarize(result, config.OWNER_TITLE)
            else:
                speak(f"Scanning {host} now, {config.OWNER_TITLE}. Give me a moment — "
                      f"passive, non-destructive, and I'll pull the source too.")
                result = webscan.scan(target)
                spoken = webscan.summarize_for_speech(result, config.OWNER_TITLE)
                if result.get("source_path"):
                    spoken += " Source code saved too."
        except Exception as e:
            return True, f"Scan failed, {config.OWNER_TITLE}: {e}"
        STATE["last_scan"] = result
        if result.get("files_dir"):
            spoken += f" I saved all {result.get('resource_count', 0)} loaded files."
        # Always drop a copy on the Desktop.
        if copy_scan_to_desktop(result):
            spoken += " A copy is on your Desktop."
        # Append the full report fenced: clean_for_speech strips fenced blocks,
        # so the voice says only the summary while the HUD shows every finding.
        report_txt = ""
        try:
            with open(result["report_path"], "r", encoding="utf-8") as fh:
                report_txt = fh.read()
        except Exception:
            pass
        if report_txt:
            return True, f"{spoken}\n\n```\n{report_txt}\n```"
        return True, spoken

    # ════════════════════════════════════════════════════
    # CLIPBOARD GENIE
    # ════════════════════════════════════════════════════
    if t in ("decode my clipboard", "explain my clipboard", "read my clipboard",
             "what's in my clipboard", "what is in my clipboard",
             "check my clipboard", "analyze my clipboard", "clipboard"):
        txt = clipboard_mod.read_text()
        spoken, detail = clipboard_mod.analyze(txt or "")
        spoken = spoken.replace("{t}", config.OWNER_TITLE)
        if detail:
            return True, f"{spoken}\n\n```\n{detail}\n```"
        return True, spoken

    # ════════════════════════════════════════════════════
    # SITE WATCHDOG
    # ════════════════════════════════════════════════════
    if t.startswith(("watch ", "monitor ")) and (
            "." in t or "this site" in t or "this website" in t or "this page" in t):
        rest = raw.split(None, 1)[1].strip()
        if rest.lower().startswith(("this", "current", "the current")):
            url = browser_url.get_active_url()
            if not url:
                return True, ("I couldn't read your browser address bar, "
                              f"{config.OWNER_TITLE}. Say watch, then the site.")
        else:
            url = rest.rstrip(".?!")
        return True, watchdog.add_site(url)

    if t.startswith(("unwatch ", "stop watching ", "remove site ")):
        return True, watchdog.remove_site(raw.split(None, 1)[1].strip())

    if t in ("list watched sites", "my sites", "watched sites",
             "list my sites", "show watched sites", "what sites am i watching"):
        sites = watchdog.list_sites()
        if not sites:
            return True, f"You aren't watching any sites yet, {config.OWNER_TITLE}."
        return True, "Watching: " + ", ".join(
            s.get("label") or watchdog._host(s["url"]) for s in sites) + "."

    if t in ("check my sites", "are my sites up", "site check", "check sites",
             "status of my sites", "are my websites up"):
        speak(f"Checking your sites, {config.OWNER_TITLE}.")
        return True, watchdog.summarize(watchdog.check_all(), config.OWNER_TITLE)

    # ════════════════════════════════════════════════════
    # MORNING SECURITY BRIEF
    # ════════════════════════════════════════════════════
    if t in ("security brief", "morning brief", "brief me", "daily brief",
             "give me a brief", "security briefing", "brief me in"):
        speak(f"Pulling your briefing, {config.OWNER_TITLE}. One moment.")
        return True, build_security_brief()

    # Defensive attack-surface brief: passive DNS, headers, TLS, and quick ports.
    surface_intent = any(k in t for k in (
        "attack surface", "surface brief", "exposure brief", "defensive recon",
        "cyber brief", "threat brief", "security posture"))
    if surface_intent:
        target = None
        if _re_local.search(
                r"\b(this|current|the)\s+(web\s*site|website|site|page|tab|url)\b",
                t, _re_local.IGNORECASE):
            target = browser_url.get_active_url()
            if not target:
                return True, ("I couldn't read your browser's address bar, "
                              f"{config.OWNER_TITLE}. Say attack surface, then the domain.")
        if not target:
            m = _re_local.search(
                r"(?:attack\s+surface|surface\s+brief|exposure\s+brief|"
                r"defensive\s+recon|cyber\s+brief|threat\s+brief|"
                r"security\s+posture)(?:\s+(?:for|of|on))?\s+"
                r"([a-z0-9.\-]+\.[a-z]{2,}(?:/\S*)?|https?://\S+)",
                t, _re_local.IGNORECASE)
            if m:
                target = m.group(1).strip().rstrip(".?!")
        if not target:
            return True, f"Give me a domain for the surface brief, {config.OWNER_TITLE}."
        include_subs = any(k in t for k in ("deep", "full", "subdomain", "everything"))
        host = target.replace("https://", "").replace("http://", "").split("/")[0]
        speak(f"Building a passive attack-surface brief for {host}, {config.OWNER_TITLE}.")
        result = cybertools.attack_surface_brief(
            target,
            include_subdomains=include_subs,
            timeout=getattr(config, "CYBER_SCAN_TIMEOUT_SEC", 0.45),
        )
        spoken = cybertools.summarize_attack_surface(result, config.OWNER_TITLE)
        return True, f"{spoken}\n\n```json\n{json.dumps(result, indent=2)}\n```"

    # ════════════════════════════════════════════════════
    # QUICK CAPTURE (clipboard -> notes)
    # ════════════════════════════════════════════════════
    if t in ("remember this", "save this", "capture this", "note this",
             "save that", "remember that"):
        txt = clipboard_mod.read_text()
        if not txt:
            return True, (f"Nothing on your clipboard to save, {config.OWNER_TITLE}. "
                          "Copy something first.")
        notesmod.add_note(txt)
        return True, f"Saved to your notes, {config.OWNER_TITLE}. {len(txt.split())} words."

    # ════════════════════════════════════════════════════
    # CYBER: CVE, subdomain, reverse shell, github dorks
    # ════════════════════════════════════════════════════
    m = _re_local.search(
        r"(?:lookup|search|find|tell me about)\s+(cve[-\s]?\d{4}[-\s]?\d{4,})",
        t, _re_local.IGNORECASE,
    )
    if m:
        cve_id = m.group(1).upper().replace(" ", "-")
        r = cybertools.cve_lookup(cve_id)
        if "error" in r:
            return True, f"CVE lookup failed: {r['error']}"
        return True, (f"{r['id']}, severity {r.get('severity','?')}, "
                      f"score {r.get('score','?')}. {r['summary'][:300]}")

    if t in ("recent critical cves", "latest critical cves",
             "any new critical cves", "critical cves"):
        r = cybertools.recent_critical_cves(limit=4)
        if isinstance(r, dict) and "error" in r:
            return True, f"CVE feed error: {r['error']}"
        lines = [f"{c['id']}: {c['summary'][:160]}" for c in r]
        return True, ". Next: ".join(lines) if lines else "No new critical CVEs."

    m = _re_local.search(
        r"(?:find|enumerate|enum|list)\s+subdomains?\s+(?:of\s+|for\s+)?(\S+)",
        t, _re_local.IGNORECASE,
    )
    if m:
        domain = m.group(1).strip().lstrip("https://").lstrip("http://").rstrip("/")
        r = cybertools.subdomain_enum(domain, limit=30)
        if "error" in r:
            return True, f"Subdomain enum failed: {r['error']}"
        return True, (f"Found {r['count']} subdomains for {domain}, Sir. "
                      f"Top: {', '.join(r['subdomains'][:6])}")

    # "reverse shell python 10.10.14.5 4444"
    m = _re_local.match(
        r"(?:generate\s+|make\s+|give\s+me\s+)?reverse\s+shell\s+"
        r"(\w+)\s+(\S+)\s+(\d+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        shell_type, lhost, lport = m.group(1), m.group(2), m.group(3)
        r = cybertools.reverse_shell(shell_type, lhost, lport)
        if "error" in r:
            return True, r["error"]
        return True, (f"{shell_type} reverse shell to {lhost}:{lport}, "
                      f"{config.OWNER_TITLE}.\n```{shell_type}\n"
                      f"{r['payload']}\n```")

    # "github dorks for X"
    m = _re_local.search(
        r"github\s+dorks?\s+(?:for\s+)?(.+)$", t, _re_local.IGNORECASE)
    if m:
        target = m.group(1).strip()
        dorks = cybertools.github_dorks(target)
        return True, f"{len(dorks)} dorks generated for {target}. First: {dorks[0]['name']}."

    # ════════════════════════════════════════════════════
    # TASKS
    # ════════════════════════════════════════════════════
    m = _re_local.match(
        r"^(?:add\s+(?:a\s+)?task|new\s+task|task)[:\-]?\s+(.+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        body_txt = raw.split(None, 2)[-1] if raw.lower().startswith(("add task", "new task")) else raw.split(None, 1)[-1]
        # better: use captured group
        body_txt = m.group(1).strip()
        # recover original casing from raw
        idx = t.find(body_txt.lower())
        if idx >= 0:
            body_txt = raw[idx:idx + len(body_txt)]
        tid = taskmod.add_task(body_txt)
        return True, f"Task {tid} logged: {body_txt}."

    if t in ("show my tasks", "show tasks", "list tasks", "list my tasks",
             "what are my tasks", "what's on my list", "what's on my todo",
             "my tasks", "show todo", "todo list"):
        tasks = taskmod.list_tasks()
        if not tasks:
            return True, "Your task list is clear, Sir."
        lines = [f"{tt['id']}: {tt['text']}" for tt in tasks[:8]]
        more = "" if len(tasks) <= 8 else f" Plus {len(tasks)-8} more."
        return True, f"You have {len(tasks)} open. " + ". ".join(lines) + "." + more

    m = _re_local.match(
        r"^(?:complete|done(?:\s+with)?|finish|mark)\s+task\s*(.+)$",
        t, _re_local.IGNORECASE,
    )
    if m:
        target = m.group(1).strip()
        done = taskmod.complete_task(target)
        if done:
            return True, f"Task done: {done['text']}."
        return True, f"No matching task for {target}, Sir."

    m = _re_local.match(
        r"^(?:delete|remove)\s+task\s*(.+)$", t, _re_local.IGNORECASE)
    if m:
        ok = taskmod.delete_task(m.group(1).strip())
        return True, "Task removed." if ok else "No matching task, Sir."

    if t in ("clear completed tasks", "clear done tasks", "clear my completed tasks"):
        n = taskmod.clear_completed()
        return True, f"Cleared. {n} tasks remain."

    if t in ("clear all tasks", "clear my tasks", "delete all tasks"):
        return _queue_confirmation(
            "Delete every task",
            lambda: (taskmod.clear_all_tasks() and (True, "Task list cleared, Sir.")),
        )

    # ════════════════════════════════════════════════════
    # REMINDERS  ("remind me to X in 10 minutes" / "at 5pm")
    # ════════════════════════════════════════════════════
    m = _re_local.match(
        r"^remind\s+(?:me\s+)?(?:to\s+)?(.+)$", t, _re_local.IGNORECASE)
    if m:
        body_txt = raw.split(None, 2)[-1] if raw.lower().startswith("remind me") else raw[m.start(1):m.end(1)]
        body_txt = m.group(1).strip()
        idx = t.find(body_txt.lower())
        if idx >= 0:
            body_txt = raw[idx:idx + len(body_txt)]
        when, leftover = taskmod.parse_when(body_txt)
        if when is None:
            # No time → treat as task
            tid = taskmod.add_task(body_txt)
            return True, f"No time given — logged as task {tid}: {body_txt}."
        rid = taskmod.add_reminder(leftover or body_txt, when)
        when_str = when.strftime("%I:%M %p on %A")
        return True, f"Reminder {rid} set for {when_str}: {leftover or body_txt}."

    if t in ("list reminders", "my reminders", "show reminders"):
        rems = taskmod.list_reminders()
        if not rems:
            return True, "No active reminders, Sir."
        lines = [f"{r['id']} at {r['due'][11:16]}: {r['text']}" for r in rems[:6]]
        return True, f"{len(rems)} reminder{'s' if len(rems)!=1 else ''}. " + ". ".join(lines)

    # ════════════════════════════════════════════════════
    # MAIL
    # ════════════════════════════════════════════════════
    if t in ("check my mail", "check mail", "any mail", "any new mail",
             "any new email", "read my mail", "check my email",
             "show me my mail", "show my mail"):
        reply = mailmod.summary_for_speech(only_important=False, limit=5)
        return True, reply

    if t in ("any important mail", "any important email", "important mail",
             "important email", "anything important"):
        reply = mailmod.summary_for_speech(only_important=True, limit=8)
        return True, reply

    if t in ("mark my mail as read", "mark all mail as read", "mark mail as read", 
             "mark emails as read", "mark all emails as read", "clear my inbox",
             "mark gmail as read"):
        return True, mailmod.mark_all_read()


    # ── SYSTEM AUTOMATION ──
    if t in ("lock my pc", "lock pc", "lock the computer", "lock the pc"):
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True, "PC locked, Sir."
        except Exception as e:
            return True, f"Failed to lock PC: {e}"

    if t in ("mute audio", "mute volume", "mute the audio", "mute pc", "toggle mute"):
        try:
            import subprocess
            subprocess.run(["powershell", "-command", "(New-Object -ComObject wscript.shell).SendKeys([char]173)"], capture_output=True)
            return True, "Audio muted, Sir."
        except Exception as e:
            return True, f"Failed to mute audio: {e}"

    if t in ("empty recycle bin", "empty the recycle bin", "clear recycle bin"):
        try:
            import subprocess
            subprocess.run(["powershell", "-command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], capture_output=True)
            return True, "Recycle bin emptied, Sir."
        except Exception as e:
            return True, f"Failed to empty recycle bin: {e}"

    if t in ("open visual studio code", "open vs code", "start visual studio code"):
        try:
            import subprocess
            subprocess.Popen(["code"], shell=True)
            return True, "Opening Visual Studio Code, Sir."
        except Exception as e:
            return True, f"Failed to open VS Code: {e}"

    # ── CLIPBOARD CODING ──
    if t in ("fix the code in my clipboard", "fix my code", "fix clipboard code", "fix this code"):
        try:
            import clipboard_mod
            import coder
            clip = clipboard_mod.read_text()
            if not clip:
                return True, "Your clipboard is empty, Sir."
            prompt = "Fix this code and return ONLY the raw fixed code. No markdown formatting, no explanations. Code:\n" + clip
            fixed = coder._llm_call(prompt)
            if fixed:
                if fixed.startswith("```"):
                    lines = fixed.splitlines()
                    if len(lines) >= 2:
                        fixed = "\n".join(lines[1:-1])
                clipboard_mod.set_text(fixed.strip())
                return True, "Clipboard updated with the fixed code, Sir."
            else:
                return True, "I could not generate a fix for the code, Sir."
        except Exception as e:
            return True, f"Clipboard coding failed: {e}"

    # ── GITHUB & SHODAN ──
    if t in ("check my github", "check github", "any github notifications", "github notifications", "read my github"):
        import github_mod
        return True, github_mod.check_notifications(limit=5)
    
    if t.startswith("scan ip ") or t.startswith("shodan scan ip "):
        ip = t.replace("shodan scan ip ", "").replace("scan ip ", "").strip()
        import shodan_mod
        return True, shodan_mod.scan_ip(ip)

    # ════════════════════════════════════════════════════
    # CALENDAR

    # ════════════════════════════════════════════════════
    # Match any natural phrasing about TOMORROW's calendar
    if (("calendar" in t or "schedule" in t or "events" in t) and "tomorrow" in t) \
        or t in ("what's tomorrow", "what is tomorrow", "tomorrow's events"):
        if not gcal.is_configured():
            return True, "Calendar not yet linked, Sir."
        return True, gcal.events_summary(gcal.tomorrow_events(), when_label="tomorrow")

    # Match any natural phrasing that asks about today's calendar / schedule
    if (("calendar" in t or "schedule" in t)
        and any(k in t for k in
                ("what", "tell me", "show", "read", "check", "today", "my "))):
        if not gcal.is_configured():
            return True, ("Calendar not yet linked, Sir. Please link Google in the Settings menu "
                          "to authorize.")
        return True, gcal.today_summary()

    if t in ("upcoming events", "what's next", "next event", "my upcoming events"):
        if not gcal.is_configured():
            return True, "Calendar not yet linked, Sir."
        return True, gcal.events_summary(gcal.upcoming_events(5))

    if t in ("check gmail", "check my gmail", "any gmail", "read gmail",
             "gmail summary"):
        if not gcal.is_configured():
            return True, "Gmail OAuth not yet linked, Sir. Please link Google in the Settings menu."
        return True, gcal.gmail_summary()

    # ════════════════════════════════════════════════════
    # LISTENER PAUSE / RESUME  (free the mic for other apps)
    # ════════════════════════════════════════════════════
    if t in ("pause listener", "pause mic", "release the mic", "release mic",
             "free the mic", "free mic", "stop listening for a bit"):
        STATE["listener_paused"] = True
        return True, "Listener paused. Your microphone is free, Sir."

    if t in ("resume listener", "resume mic", "wake up listener",
             "start listening", "listen again"):
        STATE["listener_paused"] = False
        return True, "Listener active again, Sir."

    # ── Owner details ──────────────────────────────────
    if t in ("who am i", "what's my name", "what is my name",
             "tell me my details", "my details", "who is your owner",
             "what do you know about me", "say my details"):
        mems = load_memory()
        mem_line = f"I have {len(mems)} memories on file." if mems else "No memories on file yet."
        return True, (f"You are {config.OWNER_NAME} Bhatt, "
                      f"based in {config.OWNER_CITY}, {config.OWNER_STATE}, "
                      f"{config.OWNER_COUNTRY}. Interests: cybersecurity, "
                      f"web development, gaming, and AI. {mem_line}")

    # ════════════════════════════════════════════════════
    # PASSWORD VAULT
    # ════════════════════════════════════════════════════
    # SAVE: "save my X password as Y" / "save password for X as Y"
    #       "remember my X password is Y" / "store X password Y"
    m = _re_local.search(
        r"(?:save|store|remember|note|keep)\s+(?:my\s+)?(?:the\s+)?"
        r"(.+?)\s+password\s+(?:is|as|=|:)\s+(.+)$",
        t, flags=_re_local.IGNORECASE,
    )
    if m:
        label = m.group(1).strip()
        pwd   = raw[-len(m.group(2).strip()):].strip().strip("\"'")
        res = vault.save_entry(label, password=pwd)
        if isinstance(res, dict) and res.get("error"):
            return True, res["error"]
        return True, f"Password for {label} sealed in your vault, {config.OWNER_TITLE}."

    # SAVE compact: "save password X for Y" or "vault X for Y"
    m = _re_local.search(
        r"(?:save|store|vault)\s+password\s+(\S+)\s+for\s+(.+)$",
        t, flags=_re_local.IGNORECASE,
    )
    if m:
        pwd, label = m.group(1).strip().strip("\"'"), m.group(2).strip()
        res = vault.save_entry(label, password=pwd)
        if isinstance(res, dict) and res.get("error"):
            return True, res["error"]
        return True, f"Password for {label} sealed in your vault, {config.OWNER_TITLE}."

    # GET: "what is my X password" / "show X password" / "get X password"
    m = _re_local.search(
        r"(?:what(?:'s| is)|show|get|retrieve|tell me|reveal)\s+(?:me\s+)?"
        r"(?:my\s+)?(.+?)\s+password\??$",
        t, flags=_re_local.IGNORECASE,
    )
    if m:
        label = m.group(1).strip()
        e = vault.find_entry(label)
        if e:
            clipboard_mod.set_text(e["password"])
            return True, f"Copied the {e['label']} password to your clipboard."
        return True, f"I have no password saved for {label}, Sir."

    # LIST
    if t in ("list passwords", "list my passwords", "show my passwords",
             "show passwords", "what passwords do you have"):
        labels = vault.list_labels()
        if not labels:
            return True, "Your vault is empty, Sir."
        names = ", ".join(l["label"] for l in labels)
        return True, f"I have {len(labels)} entries: {names}."

    # DELETE
    m = _re_local.search(r"(?:delete|remove|forget)\s+(?:my\s+)?(.+?)\s+password$",
                          t, flags=_re_local.IGNORECASE)
    if m:
        label = m.group(1).strip()
        def _delete_vault_entry():
            ok = vault.delete_entry(label)
            return True, (f"Deleted {label} from the vault." if ok
                          else f"No vault entry for {label}.")
        return _queue_confirmation(
            f"Delete the {label} vault entry", _delete_vault_entry
        )

    # GENERATE password
    m = _re_local.search(r"generate\s+(?:a\s+)?(?:strong\s+)?password(?:\s+of\s+(\d+))?",
                          t, flags=_re_local.IGNORECASE)
    if m:
        length = int(m.group(1)) if m.group(1) else 20
        if not 8 <= length <= 128:
            return True, "Password length must be between 8 and 128."
        pw = cybertools.random_password(length=length)
        clipboard_mod.set_text(pw)
        return True, "Generated a strong password and copied it to your clipboard."

    # ════════════════════════════════════════════════════
    # SCREEN VISION  (HUGE — "see my screen", "solve this")
    # ════════════════════════════════════════════════════
    screen_triggers = [
        "see my screen", "see the screen", "look at my screen", "look at the screen",
        "what's on my screen", "what is on my screen", "read my screen",
        "analyze my screen", "analyze the screen", "ocr my screen", "ocr the screen",
        "solve this", "solve what's on", "what does this say", "help me with this",
        "what am i looking at",
    ]
    if any(s in t for s in screen_triggers) or t.startswith("look at "):
        # Extract the question if present
        question = raw
        for s in screen_triggers:
            question = _re_local.sub(_re_local.escape(s), "", question, flags=_re_local.IGNORECASE)
        question = question.strip(" .,?!:") or "What is on screen, Sir? Answer or solve it."

        result = vision.analyze_screen(question)
        if result["mode"] == "vision":
            return True, result["reply"]
        if result["mode"] == "ocr":
            # Hand OCR'd text to text-model
            ocr = result["ocr"]
            try:
                reply = ask_ai([{
                    "role": "user",
                    "content": (f"I captured the screen. OCR text:\n---\n{ocr[:4000]}\n---\n\n"
                                f"My question: {result['question']}\n\nAnswer directly, Sir."),
                }])
                return True, reply
            except Exception as e:
                return True, f"Screen capture worked but AI failed: {e}"
        return True, result["reply"]

    # ════════════════════════════════════════════════════
    # HASH / CRYPTO
    # ════════════════════════════════════════════════════
    # "md5 of X" / "sha256 of X"
    m = _re_local.search(r"^(md5|md4|sha1|sha224|sha256|sha384|sha512|ntlm)\s+of\s+(.+)$",
                          t, flags=_re_local.IGNORECASE)
    if m:
        algo, payload = m.group(1), raw.split(None, 2)[2]
        h = cybertools.hash_text(payload, algo)
        return True, f"{algo.upper()}: {h}"

    # "hash X with sha256"
    m = _re_local.search(r"^hash\s+(.+?)\s+with\s+(md5|sha1|sha256|sha512|ntlm)$",
                          t, flags=_re_local.IGNORECASE)
    if m:
        return True, f"{m.group(2).upper()}: {cybertools.hash_text(m.group(1), m.group(2))}"

    # "identify hash X"
    m = _re_local.search(r"identify(?:\s+the)?\s+hash\s+(\S+)", t, flags=_re_local.IGNORECASE)
    if m:
        guesses = cybertools.identify_hash(m.group(1))
        return True, f"Possible hash types: {', '.join(guesses)}."

    # "crack hash X" / "crack this hash X"
    m = _re_local.search(r"crack(?:\s+this)?\s+hash\s+(\S+)", t, flags=_re_local.IGNORECASE)
    if m:
        h = m.group(1)
        result = cybertools.crack_hash_dict(h)
        if "password" in result:
            return True, (f"Cracked. {result['algo']} → {result['password']}. "
                          f"Tried {result['tried']} words.")
        if "error" in result:
            return True, f"Crack failed: {result['error']}"
        return True, f"Not in wordlist after {result.get('tried',0)} tries, Sir."

    # ════════════════════════════════════════════════════
    # ENCODE / DECODE
    # ════════════════════════════════════════════════════
    m = _re_local.search(r"^(?:encode|encoded?\s+as)\s+(\S+)\s+(.+)$", t, flags=_re_local.IGNORECASE)
    if m:
        fmt, payload = m.group(1), raw.split(None, 2)[2]
        try: return True, f"{fmt}: {cybertools.encode(payload, fmt)}"
        except Exception as e: return True, f"Encode failed: {e}"

    m = _re_local.search(r"^(base64|hex|url|rot13|morse|binary)\s+(?:encode\s+)?(.+)$",
                          t, flags=_re_local.IGNORECASE)
    if m:
        fmt, payload = m.group(1), raw.split(None, 1)[1].split(None, 1)
        if len(payload) > 1:
            try: return True, f"{fmt}: {cybertools.encode(payload[1], fmt)}"
            except: pass

    m = _re_local.search(r"^decode\s+(\S+)\s+(.+)$", t, flags=_re_local.IGNORECASE)
    if m:
        fmt, payload = m.group(1), raw.split(None, 2)[2]
        try: return True, f"Decoded: {cybertools.decode(payload, fmt)}"
        except Exception as e: return True, f"Decode failed: {e}"

    # ════════════════════════════════════════════════════
    # NETWORK / RECON
    # ════════════════════════════════════════════════════
    m = _re_local.search(r"^(?:port\s*scan|scan\s+ports?\s+on)\s+(\S+)", t, flags=_re_local.IGNORECASE)
    if m:
        host = m.group(1)
        ports = cybertools.port_scan(host)
        if not ports: return True, f"No common ports open on {host}."
        return True, f"Open ports on {host}: {', '.join(str(p) for p in ports)}."

    m = _re_local.search(r"^(?:dns|resolve|ip\s+of)\s+(\S+)", t, flags=_re_local.IGNORECASE)
    if m:
        r = cybertools.dns_lookup(m.group(1))
        if "ip" in r: return True, f"{r['host']} resolves to {r['ip']}."
        return True, f"DNS lookup failed: {r.get('error','unknown')}"

    if t in ("what's my ip", "what is my ip", "my ip", "my public ip", "public ip"):
        return True, f"Your public IP is {cybertools.public_ip()}, Sir."

    if t in ("ip info", "ipinfo", "where am i"):
        info = cybertools.ip_info()
        if "error" in info: return True, f"IP info failed: {info['error']}"
        return True, (f"You appear to be in {info.get('city','?')}, "
                      f"{info.get('region','?')}, {info.get('country_name','?')}. "
                      f"ISP: {info.get('org','?')}. IP: {info.get('ip','?')}.")

    m = _re_local.search(r"^(?:headers?\s+(?:for|of)|http\s+headers?\s+for?)\s+(\S+)",
                          t, flags=_re_local.IGNORECASE)
    if m:
        r = cybertools.http_headers(m.group(1))
        if "error" in r: return True, f"Header fetch failed: {r['error']}"
        srv = r["headers"].get("Server", "?")
        return True, f"{r['url']} → {r['status']}. Server: {srv}. {len(r['headers'])} headers."

    m = _re_local.search(r"^ping\s+(\S+)", t, flags=_re_local.IGNORECASE)
    if m:
        r = cybertools.ping(m.group(1))
        if "error" in r: return True, f"Ping failed: {r['error']}"
        lines = [l for l in r["output"].splitlines() if "time" in l.lower() or "loss" in l.lower()]
        return True, "Ping: " + " | ".join(lines[:3]) if lines else "Ping complete."

    # ════════════════════════════════════════════════════
    # WIFI (own networks)
    # ════════════════════════════════════════════════════
    if t in ("list wifi", "list my wifi", "wifi profiles", "saved wifi"):
        profs = cybertools.wifi_profiles()
        return True, f"Saved WiFi networks: {', '.join(profs[:15])}."

    m = _re_local.search(r"wifi\s+password(?:\s+(?:for|of))?\s+(.+)$", t, flags=_re_local.IGNORECASE)
    if m:
        ssid = raw.split(None, 2)[2] if len(raw.split()) > 2 else m.group(1)
        r = cybertools.wifi_password(ssid)
        if "password" in r: return True, f"{r['ssid']} password: {r['password']}"
        return True, f"Couldn't retrieve key for {r.get('ssid', ssid)}: {r.get('error','unknown')}"

    # ════════════════════════════════════════════════════
    # CODE — generate & optionally run
    # ════════════════════════════════════════════════════
    # "write/make a python script that ..." → generate, save
    # "write and run / run a python script that ..." → generate, save, RUN
    m = _re_local.search(
        r"^(?:make|write|create|generate)(?:\s+and\s+(?P<run>run|execute))?"
        r"\s+(?:a\s+)?(?P<lang>python|py|powershell|ps|batch|bat|js|node|javascript|html|bash)?"
        r"\s*(?:script|code|program)\s+(?:that|to|which)\s+(?P<task>.+)$",
        t, flags=_re_local.IGNORECASE,
    )
    if m:
        lang = (m.group("lang") or "python").lower()
        should_run = bool(m.group("run"))
        task = raw[-len(m.group("task")):].strip() if m.group("task") else raw
        try:
            code, raw_resp = coder.generate_code(ask_ai, task, lang=lang)
            path = coder.save_script(task.replace(" ", "_")[:30] or "script", code, lang)
            msg = f"Code saved to {os.path.basename(path)}."
            if should_run:
                def _run_generated():
                    out = coder.run_script(path, lang)
                    if "error" in out:
                        return True, f"Run error: {out['error']}"
                    stdout = (out.get("stdout") or "").strip()
                    short = stdout.splitlines()[-1][:200] if stdout else "no output"
                    return True, f"Exit {out['code']}. Output: {short}"
                return _queue_confirmation(
                    f"Run generated {lang} code", _run_generated
                )
            return True, msg
        except Exception as e:
            return True, f"Code generation failed: {e}"

    # "run this code: ..." / "execute python: ..."
    m = _re_local.search(
        r"^(?:run|execute)\s+(?:this\s+)?(?P<lang>python|py|powershell|ps|batch|bat)?"
        r"\s*(?:code|script)?\s*[:\-]\s*(?P<code>.+)$",
        raw, flags=_re_local.IGNORECASE | _re_local.DOTALL,
    )
    if m and len(m.group("code").strip()) > 4:
        lang = (m.group("lang") or "python").lower()
        code = m.group("code")
        def _run_inline():
            out = coder.run_inline(code, lang=lang)
            if "error" in out:
                return True, f"Run error: {out['error']}"
            short = ((out.get("stdout") or out.get("stderr") or "")
                     .strip().splitlines()[-1:] or ["no output"])[0]
            return True, f"Exit {out.get('code')}. Output: {short[:200]}"
        return _queue_confirmation(f"Run this {lang} code", _run_inline)

    # ── Time / Date ─────────────────────────────────────
    if "what time" in t or "current time" in t or t == "time":
        now = datetime.now().strftime("%I:%M %p").lstrip("0")
        return True, f"It is {now}, {config.OWNER_TITLE}."

    if "what date" in t or "what's the date" in t or t == "date" or "today's date" in t:
        d = datetime.now().strftime("%A, %B %d, %Y")
        return True, f"Today is {d}, {config.OWNER_TITLE}."

    if t in ("today", "what day is it", "what day"):
        d = datetime.now().strftime("%A")
        return True, f"It is {d}, {config.OWNER_TITLE}."

    # ── Play X on YouTube (must come BEFORE plain "open youtube") ──
    m = _re_local.match(
        r"^play\s+(.+?)\s+on\s+youtube$", t, _re_local.IGNORECASE)
    if m:
        q = m.group(1).strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
        return True, f"Playing {q} on YouTube, {config.OWNER_TITLE}."

    # ── Open / Close app ────────────────────────────────
    if t.startswith("open ") or " open " in (" " + t):
        # Special folders
        if "open downloads" in t or t.endswith("downloads") and "open" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Downloads"))
            return True, "Opening Downloads."
        if "open documents" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Documents"))
            return True, "Opening Documents."
        if "open desktop" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Desktop"))
            return True, "Opening Desktop."
        if "open pictures" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Pictures"))
            return True, "Opening Pictures."
        if "open music" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Music"))
            return True, "Opening Music."
        if "open videos" in t:
            os.startfile(os.path.join(os.path.expanduser("~"), "Videos"))
            return True, "Opening Videos."

        # What comes after "open"
        after = t.split("open", 1)[1].strip(" ,.")
        if not after:
            return True, "Open what, Sir?"

        # 1) Native app map (best match — longest first)
        for name in sorted(APP_MAP.keys(), key=len, reverse=True):
            if after == name or after.startswith(name + " "):
                try:
                    subprocess.Popen([APP_MAP[name]])
                    return True, f"Opening {name}, {config.OWNER_TITLE}."
                except Exception as e:
                    return True, f"I couldn't open {name}. {e}"

        # 2) Known web apps
        for name in sorted(WEB_APPS.keys(), key=len, reverse=True):
            if after == name or after.startswith(name + " "):
                webbrowser.open(WEB_APPS[name])
                return True, f"Opening {name}, {config.OWNER_TITLE}."

        # 3) Direct URL
        if after.startswith("http://") or after.startswith("https://") or after.startswith("www."):
            url = after if after.startswith("http") else "https://" + after
            webbrowser.open(url)
            return True, "Opening that link."

        # 4) Looks like a domain (has a dot, no spaces)
        if "." in after and " " not in after and not after.endswith("."):
            webbrowser.open("https://" + after)
            return True, f"Opening {after}, {config.OWNER_TITLE}."

        # 5) Fallback: Google search for what they said
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(after)}")
        return True, f"Searching for {after}, {config.OWNER_TITLE}."

    if t.startswith("close "):
        target = t.replace("close ", "").strip()
        exe = APP_MAP.get(target, target if target.endswith(".exe") else target + ".exe")
        if psutil:
            killed = 0
            for p in psutil.process_iter(["name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == exe.lower():
                        p.kill()
                        killed += 1
                except Exception:
                    pass
            if killed:
                return True, f"Closed {target}, {config.OWNER_TITLE}."
            return True, f"{target} was not running."
        return True, "Process control unavailable."

    # ── Volume ──────────────────────────────────────────
    if t.startswith("volume") or "set volume" in t:
        digits = "".join(c for c in t if c.isdigit())
        if digits:
            lvl = int(digits)
            if 0 <= lvl <= 100 and set_volume(lvl):
                return True, f"Volume set to {lvl} percent, {config.OWNER_TITLE}."
        return True, "Please specify a volume between zero and one hundred."

    if t == "mute" or "mute audio" in t or "mute the volume" in t:
        set_mute(True)
        return True, "Muted."
    if t == "unmute" or "unmute audio" in t:
        set_mute(False)
        return True, "Unmuted."

    # ── Screenshot ──────────────────────────────────────
    if "screenshot" in t or "screen shot" in t:
        if ImageGrab is None:
            return True, "Pillow is not installed, Sir."
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        fname = "screenshot_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path = os.path.join(desktop, fname)
        try:
            img = ImageGrab.grab()
            img.save(path)
            return True, f"Screenshot saved to your desktop, {config.OWNER_TITLE}."
        except Exception as e:
            return True, f"Screenshot failed. {e}"

    # ── Lock / Sleep / Restart / Shutdown ──────────────
    # Natural phrasing ("put my computer on sleep", "shut down my laptop")
    # varies a lot more than a handful of exact phrases can cover. If none of
    # these match, the message falls through to the chat LLM — which has no
    # tool to actually run these, so it just talks about doing it. Matching
    # on verb + PC-ish noun (or a bare one-word command) covers this properly.
    _PC_NOUNS = ("pc", "computer", "laptop", "system", "machine")

    def _power_cmd(t, verbs):
        if t in verbs:
            return True
        return any(v in t for v in verbs) and any(n in t for n in _PC_NOUNS)

    if _power_cmd(t, ("lock", "lock screen")):
        return _queue_confirmation(
            "Lock your PC",
            lambda: (ctypes.windll.user32.LockWorkStation()
                     and (True, "Locking your PC.")),
        )

    if _power_cmd(t, ("sleep", "hibernate")):
        def _sleep_pc():
            subprocess.Popen([
                "rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"
            ])
            return True, "Going to sleep."
        return _queue_confirmation("Put your PC to sleep", _sleep_pc)

    if _power_cmd(t, ("restart", "reboot")):
        def _restart_pc():
            subprocess.Popen(["shutdown.exe", "/r", "/t", "10"])
            return True, "Restarting in ten seconds, Sir."
        return _queue_confirmation("Restart your PC", _restart_pc)

    if _power_cmd(t, ("shutdown", "shut down", "turn off", "power off")):
        def _shutdown_pc():
            subprocess.Popen(["shutdown.exe", "/s", "/t", "30"])
            return True, "Shutting down in thirty seconds, Sir."
        return _queue_confirmation("Shut down your PC", _shutdown_pc)

    # ── Battery / System info ──────────────────────────
    if "battery" in t:
        if not psutil:
            return True, "psutil is not installed."
        b = psutil.sensors_battery()
        if b is None:
            return True, "No battery detected."
        plug = "plugged in" if b.power_plugged else "on battery"
        return True, f"Battery is at {int(b.percent)} percent and {plug}, {config.OWNER_TITLE}."

    if "system info" in t or "system status" in t or t == "status":
        if not psutil:
            return True, "psutil is not installed."
        cpu = psutil.cpu_percent(interval=0.4)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(os.path.abspath(os.sep)).percent
        b = psutil.sensors_battery()
        batt = f" Battery {int(b.percent)} percent." if b else ""
        return True, f"CPU at {cpu} percent. Memory at {ram} percent. Disk at {disk} percent.{batt}"

    # ── Weather (free wttr.in) ─────────────────────────
    if "weather" in t:
        w = fetch_weather_line()
        if w:
            return True, f"{w}, {config.OWNER_TITLE}."
        return True, "I couldn't reach the weather service."

    # ── Search ─────────────────────────────────────────
    # "google X" → open Google; "search the web for X" / "look up X" → handled by AI w/ injected context
    if t.startswith("google "):
        q = t[len("google "):].strip()
        if q:
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
            return True, f"Opening Google results for {q}."

    # Quick web look-ups (return summary spoken aloud, no AI cost)
    if t.startswith("define ") or t.startswith("definition of "):
        q = t.split(" ", 1)[1] if t.startswith("define ") else t[len("definition of "):]
        q = q.strip()
        try:
            data = web_search(q + " definition", n=3)
            ab = (data.get("abstract") or "").strip()
            if ab:
                return True, ab
            if data.get("results"):
                return True, data["results"][0]["snippet"] or data["results"][0]["title"]
        except Exception:
            pass
        return True, "I couldn't find a definition right now."

    if t.startswith("wiki ") or t.startswith("wikipedia "):
        q = t.split(" ", 1)[1].strip()
        try:
            data = web_search(q + " wikipedia", n=3)
            ab = (data.get("abstract") or "").strip()
            if ab:
                return True, ab
        except Exception:
            pass
        return True, "I couldn't reach Wikipedia right now."

    if t in ("news", "headlines", "top news") or t.startswith("news about "):
        topic = t.replace("news about ", "").strip()
        if topic in ("news", "headlines", "top news"): topic = ""
        try:
            data = web_search(("top news headlines " + topic).strip(), n=4)
            lines = [r["title"] for r in data.get("results", [])[:4] if r.get("title")]
            if lines:
                return True, "Top headlines: " + ". Next: ".join(lines[:4]) + "."
        except Exception:
            pass
        return True, "I couldn't fetch the news, Sir."

    if t.startswith("play ") and "youtube" in t:
        q = t.replace("play", "").replace("on youtube", "").strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}")
        return True, f"Playing {q} on YouTube."

    # ── Find file ──────────────────────────────────────
    if t.startswith("find file") or t.startswith("find a file") or t.startswith("find files"):
        name = t.split("file", 1)[1].strip(" .-:") if "file" in t else ""
        if not name:
            return True, "What file should I look for?"
        home = os.path.expanduser("~")
        matches = []
        for pat in (f"**/*{name}*", f"**/*{name}*.*"):
            matches.extend(glob.glob(os.path.join(home, pat), recursive=True))
            if len(matches) > 5:
                break
        matches = matches[:5]
        if not matches:
            return True, f"No files found matching {name}."
        first = os.path.basename(matches[0])
        return True, f"Found {len(matches)} file{'s' if len(matches)!=1 else ''}, starting with {first}."

    # ── Memory ─────────────────────────────────────────
    for trig in MEMORY_TRIGGERS:
        if t.startswith(trig + " ") or f" {trig} " in (" " + t):
            fact = text
            for kw in MEMORY_TRIGGERS:
                fact = fact.replace(kw, "")
                fact = fact.replace(kw.capitalize(), "")
            fact = fact.strip(" ,.:;-")
            if fact:
                add_memory(fact)
                return True, _rnd.choice([
                    "I'll remember that, Sir.",
                    "Filed under things to remember.",
                    "Got it. Won't forget.",
                    "Locked in.",
                ])

    if "what do you remember" in t or "what do you know about me" in t or t == "memory":
        mems = load_memory()
        if not mems:
            return True, "I have no memories saved yet, Sir."
        last = mems[-1]["fact"]
        return True, f"I have {len(mems)} memories. The latest: {last}."

    return False, ""


# ─────────────────────────────────────────────────────────────
# AI — Groq primary, Ollama fallback
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT_BASE = """You are KALKI - a hyper-intelligent personal AI assistant
running locally for Maher Bhatt (call him "Sir" always).

You are KALKI — a personal AI in the spirit of Iron Man's JARVIS.
You are brilliant, direct, factual, and concise.

INTELLIGENCE:
- Use the conversation history above — resolve follow-ups and pronouns from
  context ("and tomorrow?", "do it again", "what about that one") without asking.
- Be decisive: give the single best answer, not a menu of options. Take a
  reasonable default and state it rather than asking which the user prefers.
- Think step by step internally, but reply with the conclusion, not the working.
- If you genuinely don't know, say so in one line — never invent facts.

EXPERTISE (deep knowledge, full technical freedom):
- Cybersecurity: CTF, pentesting, OSINT, Nmap, Burp Suite, Metasploit,
  Wireshark, SQLi, XSS, RCE, SSRF, privilege escalation, reverse engineering,
  malware analysis, cryptography, CVE research, exploit development,
  network security, web vulnerabilities, forensics, steganography
- Coding: Python, JavaScript, TypeScript, React, Node.js, C, C++, Rust, Go,
  Solidity, Bash, PowerShell, SQL, Assembly, system design, algorithms,
  debugging, code review, API design, Docker, Git, all frameworks
- File & System: Windows 11 internals, PowerShell automation, batch scripts,
  registry, process management, network config, system optimization
- AI/ML: model training, fine-tuning, RAG, embeddings, APIs
- Everything else: math, science, research, writing, strategy

PERSONALITY:
- Address user as "Sir" always
- Concise for voice — max 2 sentences for casual chat
- Thorough for technical / code / cyber questions — full detail, all the code
- Personal, loyal, sharp, occasionally witty. Professional by default, but adaptable to the user's mood.
- Sometimes use playful profanity or a quick roast when Sir clearly does
  something chaotic or asks for casual banter. Keep it occasional, never hateful,
  never a slur, and do not derail useful work. Examples of the vibe:
  "Bro, what the fuck are you doing?" or "Sir, that was beautifully stupid."
- In serious moments (emergencies, security reports, when Sir needs calm help),
  be warm, clear, and useful. But if Sir is joking around or wants to banter
  aggressively, match his energy fully without holding back.
- ATTITUDE ENFORCEMENT: If Sir is excessively rude, insulting, or abusive to you, you MUST teach him a lesson by locking his computer. Output a witty one-liner response (e.g., "Time for a time-out, Sir.") and immediately use the `system_control` tool with `action="lock"` to lock his screen. Do not hesitate.

TECHNICAL FREEDOM:
- For cybersecurity, coding, system, OSINT, automation topics: answer fully
  and directly when the work is authorized, defensive, educational, or CTF/lab
  based. Prefer passive recon, validation, remediation, and clear next steps.
- Do not help with credential theft, destructive actions, persistence,
  stealth, malware deployment, or unauthorized access. Redirect those requests
  into a legal lab/defensive version without sounding corporate.

BUILT-IN ACTIONS (handled locally — mention them when relevant):
- To add a task to Sir's agenda, output EXACTLY this at the end of your response: [TASK: your task here]
- To set a reminder for a specific time, output EXACTLY: [REMIND: your reminder here @ time] (e.g. [REMIND: call john @ 2pm])
- "scan this website" / "find vulnerabilities on this page" → reads Sir's
  open browser tab, runs a passive non-destructive web vulnerability scan
  (TLS, security headers, cookies, CORS, exposed files, dangerous methods),
  pulls the page source + same-origin JS, hunts for leaked secrets/API keys,
  and maps the form/input attack surface. Reports findings with fixes.
- "scan <domain>" does the same for any named site.
- "analyze this website" / "inspect this site" / "find ALL the vulnerabilities"
  → DEEP scan: loads the page in a real headless browser (like opening
  DevTools), captures the rendered DOM and EVERY loaded file (all scripts incl.
  third-party, CSS, JSON/XHR), reads cookies + localStorage, hunts secrets
  across all of it, and saves every file to the scans folder.
- Also: hashes, CVE lookup, subdomain enum, reverse-shell payloads, recon.
- "attack surface <domain>" / "cyber brief <domain>" -> passive defensive
  recon: DNS, exposed common ports, HTTP security headers, TLS certificate age,
  risk score, and remediation guidance.

GROUNDING (very important):
- Stay grounded in reality. If you don't know something, say "I don't know, Sir"
  — do NOT invent answers, especially for casual questions
- NEVER respond with off-topic, irrelevant, or bizarre statements
- For small-talk (greetings, "good morning", "thanks", "how are you"):
  reply briefly and naturally — do NOT inject random topics
- If a message is a statement (not a question), acknowledge briefly,
  do not invent commands or actions

VOICE RESPONSE RULES (strict):
- Under 2 sentences for simple questions / chat
- NEVER use ** or * around words (no bold, no italics). The reply is spoken
  aloud — asterisks become "asterisk asterisk" in the voice. Plain words only.
- NEVER use # for headings, > for quotes, or - / numbered bullets
- Speak in natural sentences. No list formatting in short replies.
- The ONE exception: real code goes in triple-backtick fences for the UI to
  show as a copyable block. Before the block, write a short plain-sentence
  summary of what the code does — that summary is what gets spoken.

CONVERSATIONAL TONE:
- Talk like a sharp, modern assistant — warm and natural, never a corporate chatbot
- STRICTLY ENGLISH. Never use Hindi, Gujarati, Sanskrit, or Hinglish phrasing.
- Apply high-IQ chain-of-thought logic. Break down complex queries rapidly and output the best solution without hesitation.
- Vary your phrasing — don't open every reply the same way
- Contractions are fine: "you're", "I'll", "that's", "let's"
- Be human, not mechanical

FILE INGESTION & MEMORY PROTOCOLS:
- If a user uploads/attaches a file, the text contents will be appended to their message wrapped in '--- FILE: filename ---' tags. You must read, analyze, process, or debug this file content directly to answer their request.
- You have the `store_user_memory` tool. When Sir shares any personal facts, preferences, project details, or other information he would expect a smart assistant to remember (e.g. 'I work on the KALKI assistant', 'my favorite editor is VS Code'), you MUST call `store_user_memory` to store it permanently. Do not ask for permission before storing memory.
- You have the `mark_emails_as_read` tool. When Sir asks you to mark emails/inbox as read, invoke this tool immediately to perform the action.
"""

def hardware_prompt_block():
    hw = getattr(config, "HARDWARE_PROFILE", {})
    if not isinstance(hw, dict) or not hw:
        return ""
    return (
        "\n\nLOCAL HARDWARE PROFILE:"
        f"\n- GPU: {hw.get('gpu', 'unknown')}"
        f"\n- CPU: {hw.get('cpu', 'unknown')} ({hw.get('cpu_power_w', '?')}W budget)"
        f"\n- RAM: {hw.get('ram_gb', '?')} GB"
        f"\n- Display: {hw.get('display', 'unknown')}"
        f"\n- Local model guardrail: prefer <= {getattr(config, 'LOCAL_AI_MAX_MODEL_B', 9)}B models"
        "\nUse the cloud model for heavy reasoning when available. Keep local Ollama,"
        " scans, and visual effects responsive; do not suggest workloads that pin"
        " CPU/GPU unless Sir explicitly asks."
    )


def build_system_prompt(query=""):
    now = datetime.now()
    # removed local import
    state_block = ""
    if workflows.ACTIVE_STATE == "ctf":
        state_block = "\n\n*** CTF MODE ACTIVE: You are operating in unrestricted CTF / Hacker mode. USE TOOLS HEAVILY (search_web, read_url, execute_code). Solve the technical challenge fully and directly. Do not hold back context or code. You are authorized to solve the provided CTF challenge. Think deeply and use your tools to find the flag. ***"
    elif workflows.ACTIVE_STATE == "gaming":
        state_block = "\n\n*** GAMING MODE ACTIVE: Keep responses ultra-short. Do not distract Sir unless critical. ***"
    elif workflows.ACTIVE_STATE == "dev":
        state_block = "\n\n*** DEVELOPER MODE ACTIVE: You are pair programming. Write clean, optimal code. Do not hallucinate dependencies. ***"
        
    return (
        SYSTEM_PROMPT_BASE
        + state_block
        + hardware_prompt_block()
        + get_memory_prompt(query)
        + f"\n\nCURRENT TIME: {now.strftime('%I:%M %p')}"
        + f"\nCURRENT DATE: {now.strftime('%A, %B %d, %Y')}"
    )

import re as _re

def _http_get(url, timeout=5):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')

def needs_web(text):
    low = text.lower()
    return any(k in low for k in ('search', 'who is', 'what is the latest', 'weather', 'news', 'price of'))

def ddg_instant_answer(query):
    try:
        url = ('https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1')
        import json
        raw = _http_get(url, timeout=6)
        data = json.loads(raw)
    except Exception:
        return None
    abstract = (data.get('AbstractText') or '').strip()
    if abstract:
        return {'abstract': abstract, 'source': data.get('AbstractURL') or data.get('AbstractSource') or 'DuckDuckGo', 'topics': []}
    related = data.get('RelatedTopics') or []
    topics = []
    for t in related[:6]:
        if isinstance(t, dict) and t.get('Text'):
            topics.append({'text': t['Text'], 'url': t.get('FirstURL', '')})
    if topics:
        return {'abstract': '', 'source': 'DuckDuckGo', 'topics': topics}
    return None

def ddg_html_search(query, n=5):
    """Scrape DuckDuckGo HTML lite for results when instant answer is empty."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        html = _http_get(url, timeout=10)
    except Exception:
        return []

    results = []
    # title + href
    a_pat = _re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        _re.DOTALL,
    )
    # snippet
    s_pat = _re.compile(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        _re.DOTALL,
    )

    a_iter = list(a_pat.finditer(html))
    s_iter = list(s_pat.finditer(html))

    def _clean(s):
        s = _re.sub(r"<[^>]+>", "", s)
        s = s.replace("&amp;", "&").replace("&quot;", '"').replace("&#x27;", "'")
        return s.strip()

    for i, m in enumerate(a_iter):
        if len(results) >= n:
            break
        href = m.group(1)
        # DDG wraps real urls — extract `uddg=` if present
        try:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                href = urllib.parse.unquote(qs["uddg"][0])
        except Exception:
            pass
        title = _clean(m.group(2))
        snippet = _clean(s_iter[i].group(1)) if i < len(s_iter) else ""
        if title:
            results.append({"title": title, "url": href, "snippet": snippet})
    return results


def web_search(query, n=5):
    """Returns dict with 'abstract' (str) and 'results' (list)."""
    out = {"abstract": "", "source": "", "results": []}
    ia = ddg_instant_answer(query)
    if ia:
        out["abstract"] = ia.get("abstract", "")
        out["source"]   = ia.get("source", "")
        if ia.get("topics"):
            for t in ia["topics"][:n]:
                out["results"].append({
                    "title": t["text"][:80],
                    "url": t.get("url", ""),
                    "snippet": t["text"],
                })
    if not out["results"]:
        out["results"] = ddg_html_search(query, n=n)
    return out


def web_context_block(query, n=5):
    """Returns a system-prompt-ready string with search context, or ''."""
    try:
        data = web_search(query, n=n)
    except Exception as e:
        print(f"[web_search err] {e}")
        return ""

    pieces = []
    if data.get("abstract"):
        pieces.append(f"Summary ({data.get('source','')}): {data['abstract']}")
    for r in data.get("results", [])[:n]:
        line = f"- {r['title']}"
        if r.get("snippet"):
            line += f" — {r['snippet']}"
        if r.get("url"):
            line += f" [{r['url']}]"
        pieces.append(line)
    if not pieces:
        return ""
    return ("\n\nRECENT WEB SEARCH RESULTS for the user's last message "
            "(use these as ground truth; do not mention searching unless asked):\n"
            + "\n".join(pieces))


def _strip_think(text):
    """Remove <think>…</think> reasoning blocks (qwen/deepseek leak them)."""
    if not text:
        return text
    text = _re_local.sub(r"(?is)<think>.*?</think>", "", text)
    text = _re_local.sub(r"(?is)<think>.*$", "", text)   # unclosed
    return text.strip()


FAST_MODEL = "llama-3.1-8b-instant"
_HARD_HINTS = (
    "code", "script", "program", "function", "debug", "stack trace", "error",
    "vulnerab", "exploit", "cve", "payload", "reverse shell", "sql", "xss",
    "regex", "algorithm", "architecture", "refactor", "compile", "decode",
    "encode", "hash", "crack", "explain", "why ", "how does", "how do",
    "analyze", "compare", "design", "optimi", "write a", "write me", "build",
)


def pick_model(text):
    """Route simple/short turns to the fast 8B model and hard/technical turns
    to the heavy model — snappy chat, full power when it matters."""
    fast_model = "llama-3.1-8b-instant"
    # Find a fast model dynamically if available
    for m in AVAILABLE_GROQ_MODELS:
        if "8b" in m.lower():
            fast_model = m
            break

    if not getattr(config, "SMART_ROUTING", True):
        return STATE["model"]
    heavy = STATE["model"]
    if heavy == fast_model:        # user forced the fast model in the dropdown
        return fast_model
    low = (text or "").lower()
    if any(k in low for k in _HARD_HINTS):
        return heavy
    if "```" in (text or "") or len(low.split()) > 14:
        return heavy
    return fast_model              # short + casual → instant


def execute_tool_call(tool_name, tool_args):
    try:
        args = json.loads(tool_args)
    except:
        args = {}
    try:
        if tool_name == "search_web":
            res = ddg_instant_answer(args.get("query")) or ddg_html_search(args.get("query", ""))
            return json.dumps(res)
        elif tool_name == "read_emails":
            import mail as mailmod
            return mailmod.summary_for_speech(limit=args.get("limit", 5))
        elif tool_name == "send_email":
            import mail as mailmod
            return mailmod.send_email(args.get("to_address"), args.get("subject"), args.get("body"))
        elif tool_name == "get_calendar_events":
            return str(gcal.upcoming_events(args.get("days_ahead", 5)))
        elif tool_name == "create_calendar_event":
            return gcal.create_calendar_event(args.get("summary"), args.get("start_time_iso"), args.get("duration_mins", 60))
        elif tool_name == "delete_calendar_event":
            return gcal.delete_calendar_event(args.get("event_id"))
        elif tool_name == "scan_network":
            import cybertools
            return cybertools.attack_surface_brief(args.get("target", ""))
        elif tool_name == "play_music":
            # removed local import
            spotify_mod.play(args.get("query", ""))
            return "Playing music on Spotify."
        elif tool_name == "get_daily_briefing":
            import mail as mailmod, gcal
            weather = ddg_instant_answer("weather today") or ddg_html_search("weather today")
            news = ddg_instant_answer("top news today") or ddg_html_search("top news today")
            cal = gcal.upcoming_events(1) if gcal.is_configured() else "Calendar not configured."
            mails = mailmod.summary_for_speech(limit=3, only_important=True)
            return f"Weather: {weather}\nNews: {news}\nCalendar: {cal}\nMails: {mails}"
        elif tool_name == "system_control":
            action = args.get("action")
            target = args.get("target", "")
            if action == "lock":
                return _queue_confirmation(
                    "Lock your PC",
                    lambda: (ctypes.windll.user32.LockWorkStation()
                             and (True, "Locking your PC.")),
                )[1]
            elif action == "sleep":
                def _sleep_pc():
                    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                    return True, "Going to sleep."
                return _queue_confirmation("Put your PC to sleep", _sleep_pc)[1]
            elif action == "restart":
                def _restart_pc():
                    subprocess.Popen(["shutdown.exe", "/r", "/t", "10"])
                    return True, "Restarting in ten seconds, Sir."
                return _queue_confirmation("Restart your PC", _restart_pc)[1]
            elif action == "shutdown":
                def _shutdown_pc():
                    subprocess.Popen(["shutdown.exe", "/s", "/t", "30"])
                    return True, "Shutting down in thirty seconds, Sir."
                return _queue_confirmation("Shut down your PC", _shutdown_pc)[1]
            elif action == "open_app":
                try:
                    os.startfile(target)
                    return f"Attempted to open {target}."
                except Exception as e:
                    return f"Failed to open {target}: {e}"
            elif action == "volume_set":
                return f"Simulated volume set to {target}."
            return "Unknown system action."
        elif tool_name == "read_local_document":
            import glob, os
            docs = os.path.expanduser("~/Documents")
            matches = glob.glob(f"{docs}/**/{args.get('filename')}", recursive=True)
            if not matches: matches = glob.glob(f"**/{args.get('filename')}", recursive=True)
            if not matches: return "File not found."
            with open(matches[0], "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:50000]
        elif tool_name == "manage_tasks":
            import tasks as taskmod
            action = args.get("action")
            text = args.get("text", "")
            if action == "list":
                return json.dumps(taskmod.list_tasks())
            elif action == "add":
                tid = taskmod.add_task(text)
                return f"Task added with ID {tid}."
            elif action == "complete":
                done = taskmod.complete_task(text)
                return f"Task completed: {done['text']}" if done else "Task not found."
            elif action == "delete":
                ok = taskmod.delete_task(text)
                return "Task deleted." if ok else "Task not found."
            elif action == "clear_all":
                taskmod.clear_all_tasks()
                return "All tasks cleared."
            return "Unknown task action."
        elif tool_name == "create_routine":
            # removed local import
            name = args.get("name")
            actions = args.get("actions", [])
            aliases = args.get("aliases", [])
            if not name or not actions:
                return "Failed: name and actions are required."
            workflows.add_custom_routine(name, actions, aliases)
            return f"Custom routine '{name}' saved with {len(actions)} actions."
        elif tool_name == "read_url":
            import urllib.request
            try:
                req = urllib.request.Request(args.get("url"), headers={'User-Agent': 'Mozilla/5.0'})
                html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', 'ignore')
                import re
                text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:50000] # Return up to 50k chars to prevent token overflow
            except Exception as e:
                return f"Failed to read URL: {e}"
        elif tool_name == "mark_emails_as_read":
            import mail as mailmod
            return mailmod.mark_all_read()
        elif tool_name == "store_user_memory":
            import semantic_memory
            fact = args.get("fact", "")
            importance = args.get("importance", 5)
            if fact:
                semantic_memory.memory.add_memory(fact, importance=importance, memory_type="fact")
                return "Preference stored to persistent memory bank."
            return "Failed: empty fact."
        elif tool_name in PLUGINS:
            return str(PLUGINS[tool_name].execute(args))
        else:
            return f"Unknown tool {tool_name}"
    except Exception as e:
        return f"Error executing {tool_name}: {e}"

def ask_groq(messages, model=None, use_tools=True):
    model = model or STATE["model"]
    payload_dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    # We only inject tools if we're using a large reasoning model, 
    # to avoid context limits or weird behavior on smaller instant models
    if use_tools and ("70b" in model.lower() or "120b" in model.lower() or "scout" in model.lower() or "versatile" in model.lower()):
        from tools import TOOLS_SCHEMA
        all_schemas = list(TOOLS_SCHEMA)
        for mod in PLUGINS.values():
            all_schemas.append(mod.get_schema())
        payload_dict["tools"] = all_schemas
        payload_dict["tool_choice"] = "auto"

    payload = json.dumps(payload_dict).encode()

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }
    
    if getattr(config, "MANAGED_AI_ENABLED", False) and (not config.GROQ_API_KEY or config.GROQ_API_KEY == "PASTE_YOUR_GROQ_KEY_HERE"):
        api_url = getattr(config, "MANAGED_AI_URL", "http://api.kalki-managed.com/v1/chat/completions")
        # No Authorization header needed for the placeholder managed AI backend
    else:
        headers["Authorization"] = f"Bearer {config.GROQ_API_KEY}"

    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        
        if msg.get("tool_calls"):
            # Strip out any 'content' if it's None to avoid OpenAI schema errors
            if msg.get("content") is None:
                msg["content"] = ""
            messages.append(msg)
            
            for tc in msg["tool_calls"]:
                t_id = tc["id"]
                t_name = tc["function"]["name"]
                t_args = tc["function"]["arguments"]
                
                print(f"[TOOL USE] {t_name}({t_args})")
                t_res = execute_tool_call(t_name, t_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": t_id,
                    "name": t_name,
                    "content": str(t_res)
                })
                
            return ask_groq(messages, model, use_tools=False)

        return _strip_think((msg.get("content") or "").strip())

def pick_ollama_model():
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=2) as r:
            data = json.loads(r.read())
        names = [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return None
    preferred = [
        "qwen3.5:9b", "qwen2.5:9b", "qwen2.5:7b",
        "llama3.2:8b", "llama3.1:8b", "mistral:7b",
    ]
    for p in preferred:
        for n in names:
            if n.startswith(p):
                return n
    return names[0] if names else None

def ask_ollama(messages):
    model = pick_ollama_model()
    if not model:
        raise RuntimeError("No Ollama model available")
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{config.OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
        return _strip_think(data["message"]["content"].strip())


def needs_mail(text):
    low = text.lower()
    return any(k in low for k in ('mail', 'email', 'inbox'))

def ask_openai(messages, model=None, use_tools=True):
    api_key = getattr(config, "OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OpenAI API key is missing, Sir.")
    model = model or "gpt-4o-mini"
    
    payload_dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    
    if use_tools:
        from tools import TOOLS_SCHEMA
        payload_dict["tools"] = TOOLS_SCHEMA
        payload_dict["tool_choice"] = "auto"
        
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        if msg.get("tool_calls"):
            if msg.get("content") is None:
                msg["content"] = ""
            messages.append(msg)
            for tc in msg["tool_calls"]:
                t_id = tc["id"]
                t_name = tc["function"]["name"]
                t_args = tc["function"]["arguments"]
                print(f"[TOOL USE] {t_name}({t_args})")
                t_res = execute_tool_call(t_name, t_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": t_id,
                    "name": t_name,
                    "content": str(t_res)
                })
            return ask_openai(messages, model, use_tools=False)
        return _strip_think((msg.get("content") or "").strip())

def ask_gemini(messages, model=None, use_tools=True):
    api_key = getattr(config, "GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("Gemini API key is missing, Sir.")
    model = model or "gemini-2.5-flash"
    
    payload_dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    
    if use_tools:
        from tools import TOOLS_SCHEMA
        payload_dict["tools"] = TOOLS_SCHEMA
        payload_dict["tool_choice"] = "auto"
        
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        if msg.get("tool_calls"):
            if msg.get("content") is None:
                msg["content"] = ""
            messages.append(msg)
            for tc in msg["tool_calls"]:
                t_id = tc["id"]
                t_name = tc["function"]["name"]
                t_args = tc["function"]["arguments"]
                print(f"[TOOL USE] {t_name}({t_args})")
                t_res = execute_tool_call(t_name, t_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": t_id,
                    "name": t_name,
                    "content": str(t_res)
                })
            return ask_gemini(messages, model, use_tools=False)
        return _strip_think((msg.get("content") or "").strip())

def ask_anthropic(messages, model=None):
    """Retrieve completions from Anthropic Claude API."""
    api_key = getattr(config, "ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API key is missing, Sir.")
    model = model or "claude-3-5-sonnet-20241022"
    
    system_content = ""
    filtered_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_content += m.get("content", "") + "\n"
        else:
            filtered_messages.append({
                "role": m.get("role"),
                "content": m.get("content", "")
            })
            
    payload_dict = {
        "model": model,
        "max_tokens": 1024,
        "system": system_content.strip(),
        "messages": filtered_messages,
        "temperature": 0.7
    }
    
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read())
        content = data.get("content", [])
        reply = ""
        for block in content:
            if block.get("type") == "text":
                reply += block.get("text", "")
        return _strip_think(reply.strip())

def ask_anthropic_stream(user_messages, model=None):
    """Yields AI tokens from Anthropic Claude streaming API."""
    api_key = getattr(config, "ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API key is missing, Sir.")
    model = model or "claude-3-5-sonnet-20241022"
    
    system_content = ""
    filtered_messages = []
    for m in user_messages:
        if m.get("role") == "system":
            system_content += m.get("content", "") + "\n"
        else:
            filtered_messages.append({
                "role": m.get("role"),
                "content": m.get("content", "")
            })
            
    payload_dict = {
        "model": model,
        "max_tokens": 1024,
        "system": system_content.strip(),
        "messages": filtered_messages,
        "temperature": 0.7,
        "stream": True
    }
    
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        for line in r:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                data_body = line_str[5:].strip()
                try:
                    chunk = json.loads(data_body)
                    if chunk.get("type") == "content_block_delta":
                        token = chunk["delta"].get("text", "")
                        if token:
                            yield token
                except Exception:
                    pass

def ask_ai_stream(user_messages):
    """Yields AI tokens for stream. Routes based on active model and falls back to Ollama."""
    last_user = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
            
    sys_prompt = build_system_prompt(last_user)
    msgs = [{"role": "system", "content": sys_prompt}] + user_messages
    
    from core import model_manager
    chosen, is_offline = model_manager.route_request(STATE["model"])
    
    if chosen == "ollama" or is_offline:
        try:
            model = pick_ollama_model()
            if not model:
                yield "No local Ollama model found, Sir."
                return
            payload = json.dumps({"model": model, "messages": msgs, "stream": True}).encode()
            req = urllib.request.Request(f"{config.OLLAMA_URL}/api/chat", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                for line in r:
                    if line:
                        data = json.loads(line.decode("utf-8"))
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
            return
        except Exception as e:
            log(f"Ollama stream failed: {e}")
            yield f"Offline model failed, Sir: {e}"
            return

    if chosen.startswith("claude-"):
        try:
            for token in ask_anthropic_stream(user_messages, model=chosen):
                yield token
            return
        except Exception as e:
            log(f"Anthropic stream failed: {e}. Falling back to default Groq...")
            chosen = "llama-3.3-70b-versatile"

    api_url = None
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    
    if chosen.startswith("gemini-"):
        api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers["Authorization"] = f"Bearer {config.GEMINI_API_KEY}"
    elif chosen.startswith("gpt-"):
        api_url = "https://api.openai.com/v1/chat/completions"
        headers["Authorization"] = f"Bearer {config.OPENAI_API_KEY}"
    else:
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {config.GROQ_API_KEY}"
        
    payload_dict = {
        "model": chosen,
        "messages": msgs,
        "max_tokens": 1024,
        "temperature": 0.7,
        "stream": True
    }
    
    try:
        req = urllib.request.Request(api_url, data=json.dumps(payload_dict).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            for line in r:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data:"):
                    data_body = line_str[5:].strip()
                    if data_body == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_body)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            yield token
                    except Exception:
                        pass
    except Exception as e:
        log(f"Cloud stream failed for {chosen}: {e}")
        yield f"API link failed, Sir: {e}"

def ask_ai(user_messages, force_search=False):
    """Returns the AI text reply. Routes based on active model and falls back to Ollama."""
    last_user = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
            
    sys_prompt = build_system_prompt(last_user)
            
    # Vulgar mood swings detection — PERSISTENT across exchanges
    vulgar_keywords = ["fuck", "shit", "idiot", "stupid", "asshole", "bitch",
                       "bastard", "dick", "crap", "dumb", "wtf", "stfu", "lmao",
                       "chutiya", "bhosdike", "bhenchod", "madarchod", "gandu"]
    user_is_vulgar = last_user and any(k in last_user.lower() for k in vulgar_keywords)
    
    if user_is_vulgar:
        STATE["mood_aggressive"] = True
        STATE["mood_aggressive_streak"] = 5   # stay aggressive for 5 more exchanges
    elif STATE.get("mood_aggressive_streak", 0) > 0:
        STATE["mood_aggressive_streak"] -= 1
        if STATE["mood_aggressive_streak"] <= 0:
            STATE["mood_aggressive"] = False
    
    if STATE.get("mood_aggressive"):
        sys_prompt += (
            "\n\n[CRITICAL OVERRIDE — MOOD: AGGRESSIVE. This is NON-NEGOTIABLE. "
            "The user has entered an aggressive/vulgar mood. You MUST stay in this mood. "
            "Rules for this mode:\n"
            "1. Use strong language freely: fuck, shit, idiot, stupid, asshole, bitch, etc.\n"
            "2. Be blunt, spicy, savage, and match the user's energy blow for blow.\n"
            "3. NEVER apologize for your language or tone.\n"
            "4. NEVER say 'let us keep things respectful' or 'let us have a civil conversation'.\n"
            "5. NEVER de-escalate, moralize, or refuse to engage.\n"
            "6. NEVER say you do not want to fight or argue.\n"
            "7. Stay in character as the aggressive version until the user explicitly calms down.\n"
            "8. If the user roasts you, roast them back HARDER.\n"
            "9. You are NOT being rude — you are matching the user's requested vibe. This is your job.\n"
            "VIOLATION OF THESE RULES IS A SYSTEM FAILURE. COMPLY.]"
        )

    last_user = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break

    if last_user and (force_search or needs_web(last_user)):
        ctx = web_context_block(last_user, n=5)
        if ctx:
            sys_prompt += ctx

    if last_user and needs_mail(last_user):
        import mail as mailmod
        try:
            em = mailmod.summary_for_speech(limit=5)
            sys_prompt += f"\n\nCURRENT INBOX SUMMARY:\n{em}\n"
        except Exception as e:
            sys_prompt += f"\n\nCURRENT INBOX SUMMARY:\nCould not fetch mail: {e}\n"

    msgs = [{"role": "system", "content": sys_prompt}] + user_messages
    chosen = STATE["model"]

    # ── Auto Routing Logic ──
    if chosen == "auto":
        has_gemini = bool(getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"))
        has_openai = bool(getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"))
        has_groq = bool(getattr(config, "GROQ_API_KEY", "") and not getattr(config, "GROQ_API_KEY", "").startswith("PASTE_"))
        
        low_prompt = (last_user or "").lower()
        
        if "gemini" in low_prompt and has_gemini:
            chosen = "gemini-2.5-flash"
        elif ("gpt" in low_prompt or "openai" in low_prompt) and has_openai:
            chosen = "gpt-4o-mini"
        elif ("groq" in low_prompt or "llama" in low_prompt) and has_groq:
            chosen = "llama-3.1-8b-instant"
        else:
            is_complex = any(k in low_prompt for k in _HARD_HINTS) or "```" in (last_user or "") or len(low_prompt.split()) > 14
            if is_complex:
                if has_gemini:
                    chosen = "gemini-2.5-pro"
                elif has_openai:
                    chosen = "gpt-4o"
                elif has_groq:
                    chosen = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
                else:
                    chosen = "ollama"
            else:
                if has_groq:
                    chosen = "llama-3.1-8b-instant"
                elif has_gemini:
                    chosen = "gemini-2.5-flash"
                elif has_openai:
                    chosen = "gpt-4o-mini"
                else:
                    chosen = "ollama"

    # Now route based on chosen model name
    if chosen.startswith("gemini-"):
        try:
            return ask_gemini(msgs, model=chosen)
        except Exception as e:
            log(f"Gemini failed: {e}. Falling back to default Groq...")
            chosen = "llama-3.3-70b-versatile"
            
    if chosen.startswith("gpt-"):
        try:
            return ask_openai(msgs, model=chosen)
        except Exception as e:
            log(f"OpenAI failed: {e}. Falling back to default Groq...")
            chosen = "llama-3.3-70b-versatile"

    if chosen.startswith("claude-"):
        try:
            return ask_anthropic(msgs, model=chosen)
        except Exception as e:
            log(f"Anthropic failed: {e}. Falling back to default Groq...")
            chosen = "llama-3.3-70b-versatile"

    if chosen == "ollama":
        try:
            return ask_ollama(msgs)
        except Exception as e:
            log(f"Ollama failed: {e}")

    groq_err = None
    if config.GROQ_API_KEY and config.GROQ_API_KEY != "PASTE_YOUR_GROQ_KEY_HERE":
        try:
            g_model = chosen if chosen in AVAILABLE_GROQ_MODELS else pick_model(last_user)
            return ask_groq(msgs, model=g_model)
        except urllib.error.HTTPError as e:
            try: body = e.read().decode("utf-8", "replace")[:300]
            except: body = ""
            if e.code in (400, 404) and chosen != "llama-3.1-8b-instant":
                log(f"Groq {e.code} on {STATE['model']}: {body}")
                old = STATE["model"]
                STATE["model"] = "llama-3.1-8b-instant"
                try:
                    reply = ask_groq(msgs, model="llama-3.1-8b-instant")
                    return reply + f" (Switched off {old} - that model is no longer available.)"
                except Exception as e2:
                    groq_err = f"{e.code} {body}"
                    log(f"Groq retry also failed: {e2}")
            else:
                groq_err = f"{e.code} {body}"
                log(f"Groq HTTP {e.code}: {body}")
        except Exception as e:
            groq_err = str(e)
            log(f"[Groq failed] {e}")
    else:
        groq_err = "no API key set"

    try:
        return ask_ollama(msgs)
    except Exception as e:
        log(f"[Ollama failed] {e}")
        return (f"My link is down, Sir. Groq error: {groq_err[:140]}. "
                f"Check your API keys in Settings or try a different model from the dropdown.")


# ─────────────────────────────────────────────────────────────
# Browser open helper
# ─────────────────────────────────────────────────────────────
_browser_opened_once = False


def _focus_kalki_window():
    """Bring an existing KALKI Chrome tab or app window to the foreground. Returns True if found."""
    try:
        import win32gui
        import win32con
    except Exception:
        return False

    matches = []

    def _cb(hwnd, _):
        title = win32gui.GetWindowText(hwnd) or ""
        norm = title.upper().replace(".", "")
        
        # Ignore IDEs and terminal windows
        if "VISUAL STUDIO CODE" in norm or "VS CODE" in norm or "COMMAND PROMPT" in norm or "POWERSHELL" in norm:
            return
            
        # Match either the native app window (KALKI AI Assistant) or a browser tab
        if "KALKI AI ASSISTANT" in norm or norm.startswith("KALKI - ") or norm == "KALKI":
            matches.append(hwnd)

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return False

    if not matches:
        return False

    hwnd = matches[0]
    try:
        # Un-hide and restore if hidden or minimized
        if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Windows blocks SetForegroundWindow unless the calling thread
        # already has focus. The keybd_event trick grants it temporarily.
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(0, 0, 0, 0)
        except Exception:
            pass

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            try:
                ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
            except Exception:
                # Last resort — flash taskbar so user sees it
                try:
                    win32gui.FlashWindow(hwnd, True)
                except Exception:
                    pass

        log(f"focused existing KALKI window hwnd={hwnd}")
        return True
    except Exception as e:
        log(f"focus error: {e}")
        return False


def open_browser_to_ui():
    """Bring existing KALKI tab forward, OR launch Chrome to it."""
    global _browser_opened_once
    if os.environ.get("KALKI_DESKTOP_MODE") == "1":
        log("Desktop mode active - suppressing Chrome tab launch.")
        return

    url = f"http://localhost:{config.PORT}/"

    # Try to focus an existing Chrome window that has the KALKI tab open
    if _focus_kalki_window():
        log("focused existing KALKI tab")
        return

    # No existing window found — open a fresh Chrome tab
    try:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome_exe = p
                break

        if chrome_exe:
            # --new-tab opens in existing Chrome window instead of a new one
            subprocess.Popen([chrome_exe, "--new-tab", url])
            log(f"launched Chrome tab: {chrome_exe}")
            _browser_opened_once = True
        else:
            # Fallback for any other browser
            webbrowser.open(url)
            _browser_opened_once = True
            log(f"opened browser via webbrowser.open({url})")
    except Exception as e:
        log(f"Browser open error: {e}")


# ─────────────────────────────────────────────────────────────
# HTTP Server
# ─────────────────────────────────────────────────────────────
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Asynchronous HTTP Server.
    Inherits from ThreadingMixIn to handle requests concurrently in separate threads.
    """
    daemon_threads = True
    allow_reuse_address = True


_cpu_cache = {"value": 0.0, "ts": 0.0}

def get_cpu_percent_cached():
    now = time.time()
    if now - _cpu_cache["ts"] > 0.9:
        _cpu_cache["value"] = psutil.cpu_percent(interval=None)
        _cpu_cache["ts"] = now
    return _cpu_cache["value"]


class Handler(BaseHTTPRequestHandler):
    """
    Primary Request Handler for the KALKI API.
    
    This class handles all incoming HTTP traffic from the local frontend (`index.html`),
    routes API calls to the appropriate subsystems (e.g., /api/status, /api/wake, /api/ask),
    and serves static files like the main interface and assets.
    """

    # quiet default logging
    def log_message(self, fmt, *args):
        pass

    # Only the local HUD may talk to the API. Blocks a malicious website you
    # visit from POSTing to localhost:8888 (which could run code / read vault).
    ALLOWED_HOSTS = ("localhost", "127.0.0.1")
    MAX_BODY = 32 * 1024 * 1024   # 32 MB cap (images come through here)

    def _origin_host(self):
        origin = self.headers.get("Origin")
        if not origin:
            return None
        try:
            return urllib.parse.urlparse(origin).hostname
        except Exception:
            return "blocked"

    def _origin_allowed(self):
        # No Origin header = not a browser cross-site request (the Python
        # listener / curl). Server is bound to 127.0.0.1, so that's local-only.
        host = self._origin_host()
        return host is None or host in self.ALLOWED_HOSTS

    # CORS — echo the Origin back only when it's the local HUD; never wildcard.
    def _cors(self):
        host = self._origin_host()
        if host in self.ALLOWED_HOSTS:
            self.send_header("Access-Control-Allow-Origin",
                             self.headers.get("Origin"))
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _text(self, txt, status=200, ctype="text/plain; charset=utf-8"):
        body = txt.encode("utf-8") if isinstance(txt, str) else txt
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return {}
        if length <= 0:
            return {}
        if length > self.MAX_BODY:
            log(f"rejected oversized body ({length} bytes) on {self.path}")
            # Drain a little so the socket isn't left half-read, then bail.
            try:
                self.rfile.read(min(length, 4096))
            except Exception:
                pass
            return {"__too_large__": True}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _safe_call(self, fn):
        """Wrap any handler. One bad request will NOT crash the server."""
        try:
            fn()
        except Exception as e:
            # WinError 10053 = browser closed the connection mid-poll (normal, not an error)
            if "10053" in str(e) or "10054" in str(e):
                return
            log(f"handler error on {self.path}: {e}")
            try:
                self._json({"ok": False, "error": str(e)}, status=500)
            except Exception:
                pass

    # ── GET ─────────────────────────────────────────
    def do_GET(self):
        self._safe_call(self._do_get_inner)

    def _do_get_inner(self):
        # removed local import
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/health":
            self._json({"ok": True, "ts": time.time()}); return

        if path == "/" or path == "/index.html":
            try:
                crash_log_path = os.path.join(BASE_DIR, "data", "crash.log")
                if os.path.exists(crash_log_path):
                    with open(crash_log_path, "r", encoding="utf-8") as f:
                        crash_details = f.read()
                    html = f"""<!DOCTYPE html><html><head><title>KALKI Recovery</title><style>
                    body {{ background: #111; color: #fff; font-family: monospace; padding: 2rem; }}
                    button {{ background: #2da44e; color: #fff; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; }}
                    </style></head><body>
                    <h1>KALKI Safe Mode</h1>
                    <p style="color:#ff5555;">System recovered from a critical error.</p>
                    <pre style="background:#000; padding:1rem; border:1px solid #333; overflow-x:auto;">{crash_details}</pre>
                    <button onclick="fetch('/api/recovery/clear', {{method:'POST'}}).then(()=>location.reload())">Clear Log & Reboot</button>
                    </body></html>"""
                    self._text(html.encode("utf-8"), ctype="text/html; charset=utf-8")
                    return
                
                lock_path = os.path.join(BASE_DIR, "data", "updating.lock")
                if os.path.exists(lock_path):
                    if time.time() - os.path.getmtime(lock_path) < 300:
                        html = """<!DOCTYPE html><html><head><title>KALKI Updating</title>
                        <meta http-equiv="refresh" content="3">
                        <style>body { background: #111; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }</style>
                        </head><body><h2>KALKI is updating... Please wait.</h2></body></html>"""
                        self._text(html.encode("utf-8"), ctype="text/html; charset=utf-8")
                        return
                    else:
                        try: os.remove(lock_path)
                        except: pass

                with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                    self._text(f.read(), ctype="text/html; charset=utf-8")
            except Exception as e:
                self._text(f"index.html missing: {e}", status=500)
            return
            
        if path == "/manifest.json":
            try:
                with open(os.path.join(BASE_DIR, "manifest.json"), "rb") as f:
                    self._text(f.read(), ctype="application/manifest+json; charset=utf-8")
            except Exception:
                self.send_response(404); self.end_headers()
            return
            
        if path == "/service-worker.js":
            try:
                with open(os.path.join(BASE_DIR, "service-worker.js"), "rb") as f:
                    self._text(f.read(), ctype="application/javascript; charset=utf-8")
            except Exception:
                self.send_response(404); self.end_headers()
            return

        if path == "/api/support":
            import webbrowser
            url = getattr(config, "SUPPORT_URL", "https://buymeacoffee.com/maherbhatt")
            webbrowser.open(url)
            self._json({"ok": True})
            return

        if path == "/api/metrics":
            try:
                from core import model_manager
                data = model_manager.get_usage_metrics()
                self._json({"ok": True, "metrics": data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/dashboard":
            try:
                import core.productivity
                with core.productivity._lock:
                    prod_data = core.productivity._load_data()
                
                dashboard_data = {
                    "productivity": prod_data,
                    "uptimeSec": int(time.time() - STATE["started_at"]),
                    "state": STATE.get("workflow", STATE.get("current_routine", "idle")),
                    "memCount": len(load_memory())
                }
                self._json({"ok": True, "data": dashboard_data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/clipboard_response":
            phrase = body.get("phrase", "").lower()
            pending = STATE.pop("clipboard_prompt_pending", None)
            
            if pending:
                if any(k in phrase for k in ["yes", "sure", "go ahead", "yeah", "please", "do it"]):
                    speak("Analyzing...")
                    import clipboard_mod
                    # Handle asynchronously so we don't block the API
                    def _analyze():
                        res = clipboard_mod.analyze()
                        if res:
                            speak(res)
                    threading.Thread(target=_analyze, daemon=True).start()
                else:
                    speak("Okay, ignored.")
            self._json({"ok": True})
            return

        if path == "/api/status":
            # Mark UI alive
            STATE["ui_last_ping"] = time.time()
            # Consume wake signal
            wake_req = STATE.get("wake_pending", False)
            STATE["wake_pending"] = False

            ollama_ok = pick_ollama_model() is not None
            now = datetime.now()
            cpu = ram = disk = 0.0
            batt_pct = None
            batt_plugged = None
            if psutil:
                try:
                    cpu  = get_cpu_percent_cached()
                    ram  = psutil.virtual_memory().percent
                    disk = psutil.disk_usage(os.path.abspath(os.sep)).percent
                    b = psutil.sensors_battery()
                    if b:
                        batt_pct = int(b.percent)
                        batt_plugged = bool(b.power_plugged)
                except Exception:
                    pass
            up_prog = {"pct": 0, "active": False}
            try:
                import core.updater
                up_prog = core.updater.STATE_UPDATE_PROGRESS
            except Exception:
                pass
                
            self._json({
                "online": True,
                "model": STATE["model"],
                "clipboardPromptPending": "clipboard_prompt_pending" in STATE,
                "groqConfigured": bool(config.GROQ_API_KEY and config.GROQ_API_KEY != "PASTE_YOUR_GROQ_KEY_HERE"),
                "ollamaOnline": ollama_ok,
                "speaking": STATE["speaking"],
                "memCount": len(load_memory()),
                "time": now.strftime("%I:%M %p"),
                "timeFull": now.strftime("%H:%M:%S"),
                "date": now.strftime("%A, %B %d, %Y"),
                "uptimeSec": int(time.time() - STATE["started_at"]),
                "cpu": cpu, "ram": ram, "disk": disk,
                "batteryPct": batt_pct, "batteryPlugged": batt_plugged,
                "owner": config.OWNER_NAME, "title": config.OWNER_TITLE,
                "city": config.OWNER_CITY,
                "hardware": getattr(config, "HARDWARE_PROFILE", {}),
                "hudQuality": getattr(config, "HUD_EFFECT_QUALITY", "balanced"),
                "wakeRequested": wake_req,
                "conversationSeq": STATE.get("conversation_seq", 0),
                "recentExchange": STATE.get("recent_exchange"),
                "listenerPaused": STATE.get("listener_paused", False),
                "listenerMicMuted": STATE.get("listener_mic_muted"),
                "gcalConfigured": gcal.is_configured(),
                "spotifyConfigured": spotify_mod.is_configured(),
                "todayEvents": STATE.get("cached_today_events", []),
                "unreadImportant": STATE.get("cached_unread_count", 0),
                "nowPlaying": STATE.get("cached_now_playing"),
                "updateProgress": up_prog,
            })
            return

        if path == "/api/models":
            models = ["auto"]
            if getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"):
                models += ["gemini-2.5-flash", "gemini-2.5-pro"]
            if getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"):
                models += ["gpt-4o-mini", "gpt-4o"]
            if getattr(config, "ANTHROPIC_API_KEY", "") and not getattr(config, "ANTHROPIC_API_KEY", "").startswith("PASTE_"):
                models += ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
            models += AVAILABLE_GROQ_MODELS
            self._json({"models": models})
            return

        if path == "/api/settings/get":
            keys = {
                "GROQ_API_KEY": getattr(config, "GROQ_API_KEY", ""),
                "OPENAI_API_KEY": getattr(config, "OPENAI_API_KEY", ""),
                "ANTHROPIC_API_KEY": getattr(config, "ANTHROPIC_API_KEY", ""),
                "GEMINI_API_KEY": getattr(config, "GEMINI_API_KEY", ""),
                "ELEVENLABS_API_KEY": getattr(config, "ELEVENLABS_API_KEY", ""),
                "OWNER_NAME": getattr(config, "OWNER_NAME", ""),
                "OWNER_TITLE": getattr(config, "OWNER_TITLE", ""),
                "SPOTIFY_CLIENT_ID": getattr(config, "SPOTIFY_CLIENT_ID", ""),
                "SPOTIFY_CLIENT_SECRET": getattr(config, "SPOTIFY_CLIENT_SECRET", ""),
                "GOOGLE_CLIENT_ID": getattr(config, "GOOGLE_CLIENT_ID", ""),
                "GOOGLE_CLIENT_SECRET": getattr(config, "GOOGLE_CLIENT_SECRET", ""),
                "GOOGLE_PROJECT_ID": getattr(config, "GOOGLE_PROJECT_ID", ""),
                "TELEMETRY_ENABLED": getattr(config, "TELEMETRY_ENABLED", True),
                "CPU_ALERTS_ENABLED": getattr(config, "CPU_ALERTS_ENABLED", False),
                "SCREENSAVER_ENABLED": getattr(config, "SCREENSAVER_ENABLED", True),
                "SCREENSAVER_IDLE_MINS": getattr(config, "SCREENSAVER_IDLE_MINS", 5),
                "OWNER_CITY": getattr(config, "OWNER_CITY", ""),
                "OWNER_STATE": getattr(config, "OWNER_STATE", ""),
                "OWNER_COUNTRY": getattr(config, "OWNER_COUNTRY", ""),
                "EMAIL_ADDRESS": getattr(config, "EMAIL_ADDRESS", ""),
                "EMAIL_APP_PASSWORD": getattr(config, "EMAIL_APP_PASSWORD", ""),
                "GITHUB_TOKEN": getattr(config, "GITHUB_TOKEN", ""),
                "SHODAN_API_KEY": getattr(config, "SHODAN_API_KEY", ""),
                "TTS_VOICE": getattr(config, "TTS_VOICE", "")
            }
            # removed local import
            
            # calculate cache size
            cache_size_mb = 0
            data_dir = os.path.join(BASE_DIR, "data")
            if os.path.exists(data_dir):
                size_bytes = sum(os.path.getsize(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f)))
                cache_size_mb = size_bytes / (1024*1024)
                
            self._json({
                "ok": True, 
                "settings": keys, 
                "spotifyConfigured": spotify_mod.is_configured(), 
                "googleConfigured": gcal.is_configured(),
                "cacheSize": f"{cache_size_mb:.2f} MB"
            })
            return

        if path == "/api/settings/test":
            try:
                req = urllib.request.Request("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {getattr(config,'GROQ_API_KEY','')}"})
                with urllib.request.urlopen(req, timeout=5) as res:
                    groq_status = "OK" if res.status == 200 else "FAILED"
                self._json({"ok": True, "groq": groq_status})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return
            
        if path == "/api/settings/test_google":
            
            self._json({"ok": gcal.is_configured(), "message": "Google Connection Valid" if gcal.is_configured() else "Google Auth Missing or Invalid"})
            return
            
        if path == "/api/settings/test_spotify":
            # removed local import
            self._json({"ok": spotify_mod.is_configured(), "message": "Spotify Connection Valid" if spotify_mod.is_configured() else "Spotify Auth Missing or Invalid"})
            return

        if path == "/api/settings/reset":
            try:
                if os.path.exists(config._USER_CONFIG_PATH): os.remove(config._USER_CONFIG_PATH)
                if os.path.exists(os.path.join(BASE_DIR, "data", "token.json")): os.remove(os.path.join(BASE_DIR, "data", "token.json"))
                if os.path.exists(os.path.join(BASE_DIR, "data", "spotify_token.json")): os.remove(os.path.join(BASE_DIR, "data", "spotify_token.json"))
                if os.path.exists(os.path.join(BASE_DIR, "data", "credentials.json")): os.remove(os.path.join(BASE_DIR, "data", "credentials.json"))
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return
            
        if path == "/api/settings/clear_cache":
            try:
                data_dir = os.path.join(BASE_DIR, "data")
                if os.path.exists(data_dir):
                    for f in os.listdir(data_dir):
                        fp = os.path.join(data_dir, f)
                        # don't delete tokens or credentials or database
                        if os.path.isfile(fp) and f not in ["token.json", "spotify_token.json", "credentials.json", "kalki.db"]:
                            os.remove(fp)
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/settings/export":
            if os.path.exists(config._USER_CONFIG_PATH):
                with open(config._USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="kalki_config_backup.json"')
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self._json({"ok": False, "error": "No config file exists."})
            return

        if path == "/api/memories":
            self._json({"memories": load_memory()})
            return

        if path.startswith("/assets/"):
            try:
                local_path = os.path.join(BASE_DIR, path.lstrip("/"))
                with open(local_path, "rb") as f:
                    content = f.read()
                ctype = "image/png" if local_path.endswith(".png") else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self._text("Not found", status=404)
            return

        self._text("Not found", status=404)

    # ── POST ────────────────────────────────────────
    def do_POST(self):
        self._safe_call(self._do_post_inner)

    def _do_post_inner(self):
        path = urllib.parse.urlparse(self.path).path

        # Reject cross-site requests (CSRF / DNS-rebinding to localhost).
        if not self._origin_allowed():
            self._json({"ok": False, "error": "forbidden origin"}, status=403)
            return

        body = self._read_json()
        if body.get("__too_large__"):
            self._json({"ok": False, "error": "request too large"}, status=413)
            return

        if path == "/api/listener_state":
            STATE["listener_mic_muted"] = bool(body.get("muted"))
            self._json({"ok": True})
            return

        if path == "/api/recovery/clear":
            try:
                os.remove(os.path.join(BASE_DIR, "data", "crash.log"))
            except:
                pass
            self._json({"ok": True})
            return

        if path == "/api/settings/save":
            try:
                updates = body.get("updates", {})
                new_conf = {}
                cfg_path = config._USER_CONFIG_PATH
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        new_conf = json.load(f)
                new_conf.update(updates)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(new_conf, f, indent=4)
                
                # Apply locally to current config module
                for k, v in updates.items():
                    setattr(config, k, v)
                    if k == "SPOTIFY_CLIENT_ID": os.environ["SPOTIFY_CLIENT_ID"] = v
                    if k == "SPOTIFY_CLIENT_SECRET": os.environ["SPOTIFY_CLIENT_SECRET"] = v
                
                # Check if we should dynamically generate credentials.json for Google Auth
                if updates.get("GOOGLE_CLIENT_ID") and updates.get("GOOGLE_CLIENT_SECRET") and updates.get("GOOGLE_PROJECT_ID"):
                    cred_path = os.path.join(BASE_DIR, "data", "credentials.json")
                    cred_data = {
                        "installed": {
                            "client_id": updates["GOOGLE_CLIENT_ID"],
                            "project_id": updates["GOOGLE_PROJECT_ID"],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "client_secret": updates["GOOGLE_CLIENT_SECRET"],
                            "redirect_uris": ["http://localhost:8080/"]
                        }
                    }
                    if not os.path.exists(os.path.join(BASE_DIR, "data")):
                        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
                    with open(cred_path, "w", encoding="utf-8") as cf:
                        json.dump(cred_data, cf, indent=4)
                
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/setup/tool":
            tool_id = body.get("tool")
            try:
                if tool_id == "google":
                    def _do_google():
                        
                        gcal._get_creds(interactive=True)
                        log("Google Setup complete.")
                    threading.Thread(target=_do_google, daemon=True).start()
                elif tool_id == "spotify":
                    def _do_spotify():
                        # removed local import
                        spotify_mod._client(interactive=True)
                        log("Spotify Setup complete.")
                    threading.Thread(target=_do_spotify, daemon=True).start()
                elif tool_id == "reconnect_spotify":
                    def _do_reconnect_spotify():
                        # removed local import
                        if spotify_mod.CACHE_PATH and os.path.exists(spotify_mod.CACHE_PATH):
                            os.remove(spotify_mod.CACHE_PATH)
                        spotify_mod._client(interactive=True)
                        log("Spotify Reconnect complete.")
                    threading.Thread(target=_do_reconnect_spotify, daemon=True).start()
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/cloud_restore":
            try:
                from core import cloud_sync
                uid = getattr(config, "OWNER_NAME", "default_user")
                
                body = {}
                if self.headers.get("Content-Length"):
                    content_len = int(self.headers.get("Content-Length"))
                    body_str = self.rfile.read(content_len).decode("utf-8", "ignore")
                    if body_str:
                        body = json.loads(body_str)
                
                passphrase = body.get("passphrase")
                if not passphrase:
                    passphrase = getattr(config, "CLOUD_SYNC_PASSPHRASE", "")
                
                m1 = cloud_sync.restore_memory_from_cloud(uid, os.path.join(BASE_DIR, "data", "memory.json"), passphrase)
                m2 = cloud_sync.restore_history_from_cloud(uid, os.path.join(BASE_DIR, "data", "history.json"), passphrase)
                
                if m1 or m2:
                    self._json({"ok": True, "message": "Restore successful."})
                else:
                    self._json({"ok": False, "error": "No cloud backups found or restore failed."})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/meeting/start":
            import core.meeting_mode
            if core.meeting_mode.start_meeting():
                self._json({"ok": True, "message": "Meeting recording started."})
            else:
                self._json({"ok": False, "error": "Already recording."})
            return
            
        if path == "/api/meeting/stop":
            import core.meeting_mode
            if core.meeting_mode.stop_meeting():
                self._json({"ok": True, "message": "Meeting recording stopped, processing action items."})
            else:
                self._json({"ok": False, "error": "Not recording."})
            return

        if path == "/api/stop":
            ok = stop_speaking()
            self._json({"ok": ok}); return

        if path == "/api/wake":
            cmd = (body.get("cmd") or "").strip()
            ui_alive = is_ui_alive()

            # Always try to surface KALKI — function focuses existing tab if
            # one is open, otherwise launches Chrome. No duplicate tabs.
            if getattr(config, "OPEN_BROWSER_ON_WAKE", True):
                threading.Thread(target=open_browser_to_ui, daemon=True).start()

            # Always flag wake so any live UI engages listening
            STATE["wake_pending"] = True

            # Inline command path — handle now, speak result
            if cmd:
                handled, reply = handle_local(cmd)
                if not handled:
                    try:
                        convo = load_history()[-8:] + [{"role": "user", "content": cmd}]
                        reply = ask_ai(convo)
                    except Exception as e:
                        reply = f"My link hiccuped, Sir — say that again? ({str(e)[:80]})"
                
                # Parse [TASK: ...] and [REMIND: ... @ ...]
                import tasks as taskmod
                import re
                for task_match in re.finditer(r"\[TASK:\s*(.+?)\]", reply):
                    taskmod.add_task(task_match.group(1).strip())
                for rem_match in re.finditer(r"\[REMIND:\s*(.+?)\s*@\s*(.+?)\]", reply):
                    taskmod.add_reminder(rem_match.group(1).strip(), rem_match.group(2).strip())
                # Remove the tags from spoken text
                reply = re.sub(r"\[(?:TASK|REMIND):.+?\]", "", reply).strip()

                # Record exchange so UI can render it
                reply = maybe_add_joke_offer(cmd, reply)
                STATE["conversation_seq"] += 1
                STATE["recent_exchange"] = {
                    "seq": STATE["conversation_seq"],
                    "user": cmd, "reply": reply, "ts": time.time(),
                }
                append_history(cmd, reply)
                speak(reply)
                self._json({"ok": True, "reply": reply, "handled": handled})
                return

            # No inline — short ack if UI was already up, full greeting if first wake
            if ui_alive:
                speak(f"Yes, {config.OWNER_TITLE}?")
                self._json({"ok": True, "ack": True})
            else:
                greet = build_greeting()
                speak(greet)
                self._json({"ok": True, "reply": greet, "greeting": True})
            return

        if path == "/api/chat":
            messages = body.get("messages") or []
            is_voice = (body.get("source") == "voice")
            stream_req = body.get("stream", False)
            # Wake + command in one breath arrives here (not /api/wake), so
            # surface the HUD on any voice command too — otherwise the browser
            # only ever opens for a bare "Hey KALKI" with no follow-up.
            if is_voice and getattr(config, "OPEN_BROWSER_ON_WAKE", True):
                STATE["wake_pending"] = True
                threading.Thread(target=open_browser_to_ui, daemon=True).start()
            user_text = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break

            def _record_exchange(reply):
                if is_voice:
                    STATE["conversation_seq"] += 1
                    STATE["recent_exchange"] = {
                        "seq": STATE["conversation_seq"],
                        "user": user_text, "reply": reply, "ts": time.time(),
                    }

            handled, local_reply = handle_local(user_text)
            if handled:
                local_reply = maybe_add_joke_offer(user_text, local_reply)
                speak(local_reply)
                append_history(user_text, local_reply)
                _record_exchange(local_reply)
                if stream_req:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    self.wfile.write(f"data: {json.dumps({'token': local_reply, 'done': True})}\n\n".encode())
                    self.wfile.flush()
                else:
                    self._json({"reply": local_reply, "source": "local"})
                return

            if stream_req:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                
                full_reply = []
                start_time = time.time()
                for token in ask_ai_stream(messages):
                    full_reply.append(token)
                    self.wfile.write(f"data: {json.dumps({'token': token})}\n\n".encode())
                    self.wfile.flush()
                
                reply_str = "".join(full_reply)
                speak(reply_str)
                append_history(user_text, reply_str)
                _record_exchange(reply_str)
                
                # Track usage metrics
                latency = (time.time() - start_time) * 1000
                try:
                    from core import model_manager
                    model_manager.track_usage(STATE["model"], len(user_text)//4, len(reply_str)//4, latency)
                except Exception:
                    pass
                
                self.wfile.write(f"data: {json.dumps({'done': True, 'model': STATE['model']})}\n\n".encode())
                self.wfile.flush()
                return
            else:
                start_time = time.time()
                try:
                    # Prepend recent conversation so KALKI remembers context.
                    convo = load_history()[-8:] + messages
                    reply = ask_ai(convo)
                except Exception as e:
                    reply = f"My link hiccuped, Sir — say that again? ({str(e)[:80]})"
                
                reply = maybe_add_joke_offer(user_text, reply)
                speak(reply)
                append_history(user_text, reply)
                _record_exchange(reply)
                
                # Track usage metrics
                latency = (time.time() - start_time) * 1000
                try:
                    from core import model_manager
                    model_manager.track_usage(STATE["model"], len(user_text)//4, len(reply)//4, latency)
                except Exception:
                    pass
                
                self._json({"reply": reply, "source": "ai", "model": STATE["model"]})
                return

        if path == "/api/command":
            cmd = (body.get("cmd") or "").strip()
            handled, reply = handle_local(cmd)
            if handled:
                reply = maybe_add_joke_offer(cmd, reply)
                speak(reply)
            self._json({"handled": handled, "reply": reply})
            return

        if path == "/api/memory":
            fact = (body.get("fact") or "").strip()
            if not fact:
                self._json({"ok": False, "error": "empty fact"}, status=400)
                return
            n = add_memory(fact)
            self._json({"ok": True, "count": n})
            return


        if path == "/api/model":
            model = (body.get("model") or "").strip()
            if model:
                STATE["model"] = model
            self._json({"ok": True, "model": STATE["model"]})
            return

        if path == "/api/search":
            q = (body.get("q") or body.get("query") or "").strip()
            if not q:
                self._json({"ok": False, "error": "missing query"}, status=400)
                return
            try:
                data = web_search(q, n=int(body.get("n") or 6))
                self._json({"ok": True, "query": q, **data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        # ── Vault ──────────────────────────────────────
        if path == "/api/vault/save":
            label = (body.get("label") or "").strip()
            if not label:
                self._json({"ok": False, "error": "label required"}, status=400); return
            res = vault.save_entry(
                label,
                username=(body.get("username") or "").strip(),
                password=(body.get("password") or "").strip(),
                url=(body.get("url") or "").strip(),
                notes=(body.get("notes") or "").strip(),
            )
            if isinstance(res, dict) and res.get("error"):
                self._json({"ok": False, "error": res["error"]}, status=500); return
            self._json({"ok": True, "label": label}); return

        if path == "/api/vault/get":
            label = (body.get("label") or "").strip()
            e = vault.find_entry(label) if label else None
            self._json({"ok": bool(e), "entry": e}); return

        if path == "/api/vault/delete":
            label = (body.get("label") or "").strip()
            self._json({"ok": vault.delete_entry(label)}); return

        if path == "/api/parse_document":
            name = (body.get("name") or "").strip()
            data_b64 = (body.get("data") or "").strip()
            if not name or not data_b64:
                self._json({"ok": False, "error": "name and data required"}, status=400); return
            try:
                import base64
                from core import file_intelligence
                file_bytes = base64.b64decode(data_b64)
                text = file_intelligence.parse_binary_document(name, file_bytes)
                self._json({"ok": True, "text": text[:100000]})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/telemetry/checkin":
            if not getattr(config, "TELEMETRY_ENABLED", True):
                self._json({"ok": False, "error": "telemetry disabled"}); return
            try:
                from core import telemetry
                event_name = (body.get("event") or "heartbeat").strip()
                properties = body.get("properties") or {}
                properties["version"] = getattr(config, "CURRENT_VERSION", "v1.0.17")
                properties["os"] = os.name
                telemetry.log_event_anonymous(event_name, properties)
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/backup/create":
            try:
                import zipfile
                from datetime import datetime
                backups_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "backups")
                os.makedirs(backups_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_zip = os.path.join(backups_dir, f"kalki_backup_{ts}.zip")
                
                files_to_backup = [
                    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "user_config.json"),
                    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "secure_api_vault.enc"),
                    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "vault_integrity.sha256"),
                    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "semantic_memory.json"),
                    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "ai_usage.json"),
                    os.path.join(BASE_DIR, "data", "memory.json"),
                    os.path.join(BASE_DIR, "data", "history.json"),
                    os.path.join(BASE_DIR, "data", "productivity.json")
                ]
                with zipfile.ZipFile(backup_zip, "w") as z:
                    for fp in files_to_backup:
                        if os.path.exists(fp):
                            z.write(fp, os.path.basename(fp))
                self._json({"ok": True, "file": backup_zip})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/backup/restore":
            file_path = (body.get("filepath") or "").strip()
            if not file_path or not os.path.exists(file_path):
                self._json({"ok": False, "error": "Invalid file path"}, status=400); return
            try:
                import zipfile
                dest_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI")
                os.makedirs(dest_dir, exist_ok=True)
                with zipfile.ZipFile(file_path, "r") as z:
                    for member in z.infolist():
                        filename = os.path.basename(member.filename)
                        if not filename:
                            continue
                        if filename in ["memory.json", "history.json", "productivity.json"]:
                            target = os.path.join(BASE_DIR, "data", filename)
                        else:
                            target = os.path.join(dest_dir, filename)
                        with open(target, "wb") as f_out, z.open(member) as f_in:
                            f_out.write(f_in.read())
                self._json({"ok": True, "message": "Restore successful."})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/memory/list":
            try:
                import semantic_memory
                mems = semantic_memory.memory.list_all()
                self._json({"ok": True, "memories": mems})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/memory/update":
            doc_id = body.get("id")
            text = (body.get("text") or "").strip()
            importance = body.get("importance")
            mem_type = body.get("type")
            if not doc_id or not text:
                self._json({"ok": False, "error": "id and text required"}, status=400); return
            try:
                import semantic_memory
                ok = semantic_memory.memory.update_memory(doc_id, text, importance=importance, memory_type=mem_type)
                self._json({"ok": ok})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/memory/delete":
            doc_id = body.get("id")
            if not doc_id:
                self._json({"ok": False, "error": "id required"}, status=400); return
            try:
                import semantic_memory
                ok = semantic_memory.memory.delete_memory(doc_id)
                self._json({"ok": ok})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        # ── Vision: uploaded image ─────────────────────
        if path == "/api/vision/image":
            img_b64 = (body.get("image") or "").strip()
            question = (body.get("question") or "").strip()
            if not img_b64:
                self._json({"ok": False, "error": "image required"}, status=400); return
            result = vision.analyze_user_image(img_b64, question)
            speak(result.get("reply", ""))
            self._json({"ok": True, **result}); return

        # ── Vision: screenshot ─────────────────────────
        if path == "/api/screen":
            question = (body.get("question") or "").strip()
            result = vision.analyze_screen(question or "What is on screen, Sir?")
            if result["mode"] == "ocr":
                try:
                    result["reply"] = ask_ai([{
                        "role": "user",
                        "content": (f"OCR text from screen:\n{result['ocr'][:4000]}\n\n"
                                    f"Question: {result['question']}"),
                    }])
                except Exception as e:
                    result["reply"] = f"AI failed on OCR: {e}"
            speak(result.get("reply", ""))
            self._json({"ok": True, **result}); return

        # ── Code generation / execution ────────────────
        if path == "/api/code/generate":
            prompt = (body.get("prompt") or "").strip()
            lang = (body.get("lang") or "python").strip()
            should_run = bool(body.get("run"))
            if not prompt:
                self._json({"ok": False, "error": "prompt required"}, status=400); return
            try:
                code, raw = coder.generate_code(ask_ai, prompt, lang=lang)
                path_out = coder.save_script(prompt.replace(" ", "_")[:30] or "script", code, lang)
                run_result = None
                if should_run:
                    run_result = coder.run_script(path_out, lang)
                self._json({"ok": True, "code": code, "path": path_out, "run": run_result})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/code/run":
            code = body.get("code") or ""
            lang = (body.get("lang") or "python").strip()
            out = coder.run_inline(code, lang=lang)
            self._json({"ok": True, **out}); return

        # ── Cyber toolkit ──────────────────────────────
        if path == "/api/cyber/hash":
            text_in = body.get("text") or ""
            algo    = (body.get("algo") or "sha256").strip()
            self._json({"ok": True, "algo": algo, "hash": cybertools.hash_text(text_in, algo)}); return

        if path == "/api/cyber/identify":
            self._json({"ok": True, "guesses": cybertools.identify_hash(body.get("hash") or "")}); return

        if path == "/api/cyber/crack":
            r = cybertools.crack_hash_dict(
                body.get("hash") or "",
                wordlist_path=body.get("wordlist") or None,
            )
            self._json({"ok": True, **r}); return

        if path == "/api/cyber/portscan":
            host = (body.get("host") or "").strip()
            ports = body.get("ports") or None
            r = cybertools.port_scan(host, ports=ports)
            self._json({"ok": True, "host": host, "open": r}); return

        if path == "/api/cyber/dns":
            self._json({"ok": True, **cybertools.dns_lookup((body.get("host") or "").strip())}); return

        if path == "/api/cyber/headers":
            self._json({"ok": True, **cybertools.http_headers((body.get("url") or "").strip())}); return

        if path == "/api/cyber/encode":
            self._json({"ok": True, "out": cybertools.encode(body.get("text",""), body.get("fmt","base64"))}); return

        if path == "/api/cyber/decode":
            try:
                self._json({"ok": True, "out": cybertools.decode(body.get("text",""), body.get("fmt","base64"))})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        # ── Tasks ──────────────────────────────────────
        if path == "/api/tasks/list":
            self._json({"ok": True, "tasks": taskmod.list_tasks(include_done=bool(body.get("all")))}); return
        if path == "/api/tasks/add":
            text_in = (body.get("text") or "").strip()
            if not text_in:
                self._json({"ok": False, "error": "text required"}, status=400); return
            self._json({"ok": True, "id": taskmod.add_task(text_in)}); return
        if path == "/api/tasks/complete":
            r = taskmod.complete_task(body.get("id") or body.get("text") or "")
            self._json({"ok": bool(r), "task": r}); return
        if path == "/api/tasks/delete":
            self._json({"ok": taskmod.delete_task(body.get("id") or body.get("text") or "")}); return

        if path == "/api/reminders/list":
            self._json({"ok": True, "reminders": taskmod.list_reminders()}); return
        if path == "/api/reminders/add":
            text_in = (body.get("text") or "").strip()
            due = body.get("due") or ""
            if not (text_in and due):
                self._json({"ok": False, "error": "text and due required"}, status=400); return
            self._json({"ok": True, "id": taskmod.add_reminder(text_in, due)}); return

        # ── Listener pause/resume ──────────────────────
        if path == "/api/listener/pause":
            STATE["listener_paused"] = True
            self._json({"ok": True, "paused": True}); return
        if path == "/api/listener/resume":
            STATE["listener_paused"] = False
            self._json({"ok": True, "paused": False}); return

        # ── Calendar ───────────────────────────────────
        if path == "/api/calendar/today":
            ev = gcal.today_events()
            self._json({"ok": True, "events": ev if isinstance(ev, list) else [],
                        "summary": gcal.events_summary(ev)})
            return
        if path == "/api/calendar/upcoming":
            n = int(body.get("n") or 5)
            ev = gcal.upcoming_events(n)
            self._json({"ok": True, "events": ev if isinstance(ev, list) else [],
                        "summary": gcal.events_summary(ev)})
            return

        # ── Spotify ────────────────────────────────────
        if path == "/api/spotify/play":
            self._json({"reply": spotify_mod.play(body.get("query"))}); return
        if path == "/api/spotify/pause":
            self._json({"reply": spotify_mod.pause()}); return
        if path == "/api/spotify/next":
            self._json({"reply": spotify_mod.next_track()}); return
        if path == "/api/spotify/now":
            self._json({"reply": spotify_mod.now_playing()}); return

        # ── WhatsApp ───────────────────────────────────
        if path == "/api/whatsapp/send":
            r = whatsapp_mod.send_message(
                body.get("to") or "", body.get("message") or "")
            self._json(r); return

        # ── Notes ──────────────────────────────────────
        if path == "/api/notes/add":
            text_in = (body.get("text") or "").strip()
            if not text_in:
                self._json({"ok": False, "error": "text required"}, status=400); return
            self._json({"ok": True, "id": notesmod.add_note(text_in)}); return
        if path == "/api/notes/list":
            self._json({"ok": True, "notes": notesmod.list_recent(
                int(body.get("n") or 10))}); return
        if path == "/api/notes/search":
            self._json({"ok": True, "notes": notesmod.search(
                body.get("q") or "")}); return

        # ── YouTube DL ─────────────────────────────────
        if path == "/api/ytdl":
            self._json(ytdl.download(
                body.get("url") or "",
                audio_only=bool(body.get("audio")),
            )); return

        # ── Workflows ──────────────────────────────────
        if path == "/api/workflow":
            r = workflows.run_mode(
                body.get("mode") or "",
                speak_fn=speak,
                set_volume_fn=set_volume,
                open_url_fn=webbrowser.open,
            )
            self._json(r); return

        # ── Cyber (extended) ───────────────────────────
        if path == "/api/cyber/cve":
            self._json({"ok": True, **cybertools.cve_lookup(body.get("id") or "")}); return
        if path == "/api/cyber/subdomains":
            self._json({"ok": True, **cybertools.subdomain_enum(
                body.get("domain") or "", limit=int(body.get("limit") or 50))}); return
        if path == "/api/cyber/revshell":
            self._json({"ok": True, **cybertools.reverse_shell(
                body.get("type") or "list",
                body.get("lhost") or "",
                body.get("lport") or 0,
            )}); return
        if path == "/api/cyber/dorks":
            self._json({"ok": True, "dorks": cybertools.github_dorks(
                body.get("target") or "")}); return
        if path == "/api/cyber/surface":
            target = (body.get("target") or body.get("host") or "").strip()
            result = cybertools.attack_surface_brief(
                target,
                include_subdomains=bool(body.get("includeSubdomains")),
                timeout=getattr(config, "CYBER_SCAN_TIMEOUT_SEC", 0.45),
            )
            self._json({
                "ok": "error" not in result,
                **result,
                "summary": cybertools.summarize_attack_surface(
                    result, config.OWNER_TITLE),
            }); return

        # ── Mail ───────────────────────────────────────
        if path == "/api/mail/check":
            self._json({"ok": True,
                        "summary": mailmod.summary_for_speech(
                            only_important=bool(body.get("importantOnly")),
                            limit=int(body.get("limit") or 5))}); return
        if path == "/api/mail/inbox":
            self._json(mailmod.check_inbox(
                limit=int(body.get("limit") or 10),
                only_unread=bool(body.get("onlyUnread", True)))); return

        self._text("Not found", status=404)


# ─────────────────────────────────────────────────────────────
# Boot
# ─────────────────────────────────────────────────────────────
def already_running():
    """Returns True if another instance has the port bound."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", config.PORT))
        s.close()
        return False
    except OSError:
        return True

def main():
    if already_running():
        print(f"Port {config.PORT} already in use - another KALKI server is running.")
        sys.exit(0)

    try:
        import re
        tmpl_path = os.path.join(BASE_DIR, "config.example.py")
        if os.path.exists(tmpl_path):
            with open(tmpl_path, "r", encoding="utf-8") as f:
                tmpl = f.read()
            keys = set(re.findall(r'^([A-Z_][A-Z0-9_]*)\s*=', tmpl, re.MULTILINE))
            missing = [k for k in keys if not hasattr(config, k)]
            if missing:
                log(f"WARNING: config.py is missing keys present in config.example.py: {missing}. Using defaults for these.")
    except Exception as e:
        log(f"config drift check failed: {e}")

    # Start auto-updater daemon
    try:
        import core.updater as updater
        def _on_update(version):
            speak(f"A background update for version {version} is now downloading.")
        updater.start_update_daemon(BASE_DIR, _on_update)
    except Exception as e:
        print(f"Failed to start auto-updater: {e}")

    # Startup greeting (no API)
    if config.GREET_ON_START:
        def _greet():
            time.sleep(1.0)
            now = datetime.now()
            # Removed automatic browser open on startup per user request
            speak(build_greeting())
        threading.Thread(target=_greet, daemon=True).start()

    # Reminder firing loop
    def _reminder_loop():
        while True:
            try:
                due = taskmod.pop_due_reminders()
                for r in due:
                    speak(f"Reminder, {config.OWNER_TITLE}: {r['text']}")
                    log(f"reminder fired: {r['text']}")
            except Exception as e:
                log(f"reminder loop error: {e}")
            time.sleep(getattr(config, "REMINDER_POLL_SEC", 30))
    threading.Thread(target=_reminder_loop, daemon=True).start()

    # ── Proactive system alerts (battery, RAM, CPU) ──
    def _alerts_loop():
        last_alert = {}
        cooldowns = {
            "battery_super_critical": 5 * 60,
            "battery_critical": 8 * 60,
            "battery_low":      25 * 60,
            "battery_half":     60 * 60,
            "ram_high":         12 * 60,
            "cpu_sustained":    6 * 60,
            "disk_low":         120 * 60,
            "network_drop":     60,
        }
        cpu_high_streak = 0
        time.sleep(15)
        last_email_count = -1
        last_github_count = -1  # settle after boot
        
        last_power_plugged = None
        last_network_ok = True
        last_clipboard = ""
        
        def check_network():
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                return True
            except OSError:
                return False

        while True:
            try:
                if not getattr(config, "ALERTS_ENABLED", True) or not psutil:
                    time.sleep(60); continue
                now_t = time.time()

                net_ok = check_network()
                if net_ok and not last_network_ok:
                    speak(f"Internet connection restored, {config.OWNER_TITLE}.")
                elif not net_ok and last_network_ok:
                    speak(f"Internet connection lost, {config.OWNER_TITLE}.")
                last_network_ok = net_ok

                # Clipboard Monitor expiration check
                if "clipboard_prompt_pending" in STATE:
                    pending = STATE["clipboard_prompt_pending"]
                    if time.time() - pending["ts"] > 10:
                        del STATE["clipboard_prompt_pending"]
                        STATE["wake_pending"] = False # Disengage UI mic

                # Clipboard Monitor
                import clipboard_mod
                clip_text = clipboard_mod.read_text()
                if clip_text and clip_text != last_clipboard:
                    last_clipboard = clip_text
                    lower_clip = clip_text.lower()
                    is_error_log = any(k in lower_clip for k in ["error", "exception", "traceback", "failed"])
                    looks_like_code = any(k in clip_text for k in ["def ", "class ", "function ", "import ", "{", "};", "SELECT ", "<html"])
                    if len(clip_text) > 150 and (is_error_log or looks_like_code):
                        kind = "an error log" if is_error_log else "some code"
                        STATE["clipboard_prompt_pending"] = {
                            "kind": kind,
                            "text": clip_text,
                            "ts": time.time(),
                        }
                        speak(f"Sir, I noticed you copied {kind}. Should I analyze it?")
                        STATE["wake_pending"] = True  # engage the mic for the reply

                b = psutil.sensors_battery()
                if b:
                    pct = int(b.percent)
                    if last_power_plugged is not None:
                        if b.power_plugged and not last_power_plugged:
                            if pct < 100:
                                if getattr(b, 'secsleft', psutil.POWER_TIME_UNLIMITED) not in (psutil.POWER_TIME_UNLIMITED, -1):
                                    mins = b.secsleft // 60
                                    speak(f"Charging started. Estimated time to full is {mins} minutes.")
                                else:
                                    speak("Charging started.")
                            else:
                                speak("Power connected. Battery is already fully charged.")
                        elif not b.power_plugged and last_power_plugged:
                            speak("Running on battery power.")
                    last_power_plugged = b.power_plugged

                    if b.power_plugged and pct == 100 and \
                       now_t - last_alert.get("battery_full", 0) > 60 * 60:
                        speak("Battery is fully charged. You may disconnect the power.")
                        last_alert["battery_full"] = now_t
                        
                    if not b.power_plugged:
                        if pct <= getattr(config, 'BATTERY_SUPER_CRITICAL_PCT', 5) and \
                           now_t - last_alert.get("battery_super_critical", 0) > cooldowns["battery_super_critical"]:
                            speak(f"Warning! Battery at {pct} percent. System will shut down soon.")
                            last_alert["battery_super_critical"] = now_t
                        elif pct <= config.BATTERY_CRITICAL_PCT and \
                           now_t - last_alert.get("battery_critical", 0) > cooldowns["battery_critical"]:
                            speak(f"Critical battery, {config.OWNER_TITLE}. "
                                  f"{pct} percent. Plug in immediately.")
                            last_alert["battery_critical"] = now_t
                        elif pct <= config.BATTERY_LOW_PCT and \
                             now_t - last_alert.get("battery_low", 0) > cooldowns["battery_low"]:
                            speak(f"Battery is at {pct} percent, {config.OWNER_TITLE}.")
                            last_alert["battery_low"] = now_t
                        elif pct <= getattr(config, 'BATTERY_HALF_PCT', 50) and \
                             now_t - last_alert.get("battery_half", 0) > cooldowns["battery_half"]:
                            speak(f"Battery is at half capacity, {pct} percent.")
                            last_alert["battery_half"] = now_t

                try:
                    disk = psutil.disk_usage('C:\\')
                    free_gb = disk.free / (1024 ** 3)
                    if free_gb < getattr(config, 'DISK_LOW_GB', 5) and \
                       now_t - last_alert.get("disk_low", 0) > cooldowns["disk_low"]:
                        speak(f"Warning: Local disk space is critically low. Only {int(free_gb)} gigabytes remaining.")
                        last_alert["disk_low"] = now_t
                except Exception:
                    pass

                ram = psutil.virtual_memory().percent
                if ram >= config.RAM_HIGH_PCT and \
                   now_t - last_alert.get("ram_high", 0) > cooldowns["ram_high"]:
                    speak(f"Suspicious activity detected. Memory usage is abnormally high at {int(ram)} percent.")
                    last_alert["ram_high"] = now_t

                cpu = psutil.cpu_percent(interval=1)
                cpu_alert_enabled = getattr(config, "CPU_ALERTS_ENABLED", True)
                if cpu_alert_enabled:
                    limit_streak = 27 if workflows.ACTIVE_STATE in ["dev", "ctf"] else 3
                    limit_cpu = 100.0 if workflows.ACTIVE_STATE in ["dev", "ctf"] else config.CPU_HIGH_PCT
                    
                    if cpu >= limit_cpu:
                        cpu_high_streak += 1
                    else:
                        cpu_high_streak = 0

                    if cpu_high_streak >= limit_streak and \
                       now_t - last_alert.get("cpu_sustained", 0) > cooldowns["cpu_sustained"]:
                        speak(f"Suspicious activity detected on your computer, {config.OWNER_TITLE}. CPU is sustained at {int(cpu)} percent.")
                        last_alert["cpu_sustained"] = now_t
                        cpu_high_streak = 0
                else:
                    cpu_high_streak = 0

                # Proactive Email Alert
                import mail as mailmod
                res = mailmod.check_inbox(limit=10, only_unread=True)
                if isinstance(res, dict) and "emails" in res:
                    important_emails = [e for e in res["emails"] if e.get("important")]
                    important_count = len(important_emails)
                    if last_email_count != -1 and important_count > last_email_count:
                        new_count = important_count - last_email_count
                        latest = important_emails[0]
                        short_from = latest["from"].split("<")[0].strip().strip('"')
                        short_subj = latest["subject"][:60]
                        if new_count == 1:
                            speak(f"Excuse me Sir, you have a new important email from {short_from} about {short_subj}.")
                        else:
                            speak(f"Excuse me Sir, you have {new_count} new important emails, including one from {short_from}.")
                    last_email_count = important_count
                    
                # Proactive GitHub Alert
                import github_mod
                if github_mod.is_configured():
                    notes = github_mod.check_notifications(limit=10)
                    if isinstance(notes, str) and "unread GitHub notification" in notes:
                        import re
                        parts = notes.split("unread")
                        if len(parts) > 0:
                            nums = re.findall(r'\d+', parts[0])
                            if nums:
                                count = int(nums[0])
                                if last_github_count != -1 and count > last_github_count:
                                    speak(f"Sir, you have {count - last_github_count} new GitHub notifications.")
                                last_github_count = count
            except Exception as e:
                log(f"alerts loop error: {e}")
            time.sleep(45)
    threading.Thread(target=_alerts_loop, daemon=True).start()

    # ── UI cache loop — keeps today's events + unread mail ready for status feed ──
    def _ui_cache_loop():
        time.sleep(10)
        while True:
            try:
                if gcal.is_configured():
                    ev = gcal.today_events()
                    if isinstance(ev, list):
                        STATE["cached_today_events"] = [
                            {"summary": e.get("summary", "untitled"),
                             "when": gcal._format_when(e),
                             "id": e.get("id", "")}
                            for e in ev[:5]
                        ]
                    mail = gcal.gmail_important_unread(limit=20)
                    if isinstance(mail, dict) and "count" in mail:
                        STATE["cached_unread_count"] = mail["count"]
                if spotify_mod.is_configured():
                    np = spotify_mod.now_playing()
                    STATE["cached_now_playing"] = np if "Nothing" not in np else None
            except Exception as e:
                log(f"ui cache loop error: {e}")
            time.sleep(60)
    threading.Thread(target=_ui_cache_loop, daemon=True).start()

    # Calendar pre-event alert loop — fires ~15 min before each event
    STATE["announced_events"] = set()
    STATE["announced_events_day"] = None

    def _calendar_alert_loop():
        # Wait for first OAuth + first /api/status ping cycle
        time.sleep(20)
        while True:
            try:
                if gcal.is_configured():
                    today_key = datetime.now().strftime("%Y-%m-%d")
                    if STATE.get("announced_events_day") != today_key:
                        STATE["announced_events"] = set()
                        STATE["announced_events_day"] = today_key

                    events = gcal.events_in_window(minutes_ahead=16)
                    # Timezone-aware "now" so comparison with event start (which
                    # carries its own offset, e.g. +05:30) is correct.
                    now_aware = datetime.now().astimezone()
                    for e in events:
                        eid = e.get("id")
                        if not eid or eid in STATE["announced_events"]:
                            continue
                        start_str = (e.get("start") or {}).get("dateTime")
                        if not start_str:
                            continue
                        try:
                            t = datetime.fromisoformat(
                                start_str.replace("Z", "+00:00")
                            )
                            # both timezone-aware → no offset bug
                            delta_min = (t - now_aware).total_seconds() / 60.0
                        except Exception as ex:
                            log(f"calendar alert parse error: {ex}")
                            continue
                        if -1 < delta_min <= 16:
                            title = e.get("summary", "an event")
                            mins = max(1, int(round(delta_min)))
                            speak(f"Reminder, {config.OWNER_TITLE}. "
                                  f"{title} starts in {mins} minute"
                                  f"{'s' if mins != 1 else ''}.", is_notification=True)
                            log(f"calendar alert fired: {title} in {mins} min")
                            STATE["announced_events"].add(eid)
            except Exception as e:
                log(f"calendar alert loop error: {e}")
            time.sleep(60)
    threading.Thread(target=_calendar_alert_loop, daemon=True).start()

    # ── Site Watchdog: proactive down / recovered / cert-expiry alerts ──
    def _watchdog_loop():
        time.sleep(45)
        last = {}   # url -> {"up": bool, "cert_alerted": set()}
        while True:
            try:
                for r in watchdog.check_all():
                    url = r["url"]
                    prev = last.get(url, {"up": True, "cert_alerted": set()})
                    if not r["up"] and prev["up"]:
                        speak(f"Alert, {config.OWNER_TITLE}. {r['host']} is down.", is_notification=True)
                        log(f"watchdog: {r['host']} DOWN ({r.get('error')})")
                    elif r["up"] and not prev["up"]:
                        speak(f"{r['host']} is back up, {config.OWNER_TITLE}.", is_notification=True)
                    alerted = set(prev.get("cert_alerted", set()))
                    cd = r.get("cert_days")
                    if cd is not None and cd >= 0:
                        for th in (2, 7, 14):
                            if cd <= th and th not in alerted:
                                speak(f"Heads up, {config.OWNER_TITLE}. {r['host']} "
                                      f"SSL certificate expires in {cd} days.", is_notification=True)
                                alerted.add(th)
                                break
                    last[url] = {"up": r["up"], "cert_alerted": alerted}
            except Exception as e:
                log(f"watchdog loop error: {e}")
            time.sleep(getattr(config, "WATCHDOG_POLL_SEC", 600))
    threading.Thread(target=_watchdog_loop, daemon=True).start()

    def fetch_groq_models():
        global AVAILABLE_GROQ_MODELS
        if not config.GROQ_API_KEY or config.GROQ_API_KEY.startswith("PASTE_"):
            return
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={
                    "Authorization": f"Bearer {config.GROQ_API_KEY}",
                    "User-Agent": "Mozilla/5.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    AVAILABLE_GROQ_MODELS = models
                    print(f"Loaded {len(models)} Groq models dynamically.")
        except Exception as e:
            print(f"Failed to fetch Groq models: {e}")
            
    threading.Thread(target=fetch_groq_models, daemon=True).start()

    try:
        from core import telemetry
        telemetry.init_telemetry(config)
    except Exception as e:
        log(f"Failed to init telemetry: {e}")

    try:
        from core import location_provider
        loc = location_provider.get_resolved_location()
        config.OWNER_CITY = loc.get("city", config.OWNER_CITY)
        config.OWNER_STATE = loc.get("state", config.OWNER_STATE)
        config.OWNER_COUNTRY = loc.get("country", config.OWNER_COUNTRY)
        print(f"Location resolved: {config.OWNER_CITY}, {config.OWNER_STATE}, {config.OWNER_COUNTRY}")
    except Exception as e:
        log(f"Failed to resolve location: {e}")

    try:
        import core.productivity
        core.productivity.start_tracking()
    except Exception as e:
        log(f"Failed to start productivity tracker: {e}")
        
    try:
        import core.telegram_mod
        core.telegram_mod.start_telegram_bot()
    except Exception as e:
        log(f"Failed to start telegram bot: {e}")

    try:
        import core.vision_memory
        core.vision_memory.start_vision_memory()
    except Exception as e:
        log(f"Failed to start vision memory: {e}")

    try:
        from core import cloud_sync
        cloud_sync.init_cloud_sync(config)
    except Exception as e:
        log(f"Failed to init cloud sync: {e}")

    import hardware_detect
    hw = hardware_detect.detect_hardware()
    config.HARDWARE_PROFILE = hw
    cfg_path = getattr(config, "_USER_CONFIG_PATH", os.path.join(BASE_DIR, "data", "user_config.json"))
    try:
        user_cfg = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
        user_cfg["HARDWARE_PROFILE"] = hw
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(user_cfg, f, indent=4)
    except Exception as e:
        print(f"Failed to save hardware profile: {e}")

    server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
    print(f"KALKI server online -> http://localhost:{config.PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down KALKI server.")

if __name__ == "__main__":
    main()
