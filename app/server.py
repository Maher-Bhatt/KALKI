
"""
KALKI v1.5.0 — Server
Web server + AI + TTS + system commands
Uses Python stdlib http.server only (no Flask, no FastAPI)
"""

import os
import sys
import json
import base64
import time
import glob
import socket
import threading
import traceback
import ssl
import re

# Keep the platform certificate store and hostname verification enabled for
# every provider, OAuth, and telemetry request. If a packaged installation
# cannot locate certificates, surface that error instead of weakening TLS.
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
import tempfile
import shutil
import asyncio
import ctypes
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure local imports and external resources resolve when launched from any
# cwd. Packaged helper executables live below services/, while the web UI and
# assets live at the package root.
from runtime_paths import prepare_runtime
_runtime = prepare_runtime()
BASE_DIR = _runtime.entry_dir
APP_ROOT = _runtime.app_root

# Force UTF-8 stdout/stderr (pythonw.exe uses cp1252 by default — breaks on emoji/arrows)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config
import oversight
import notify
from core import api_vault
for _k, _v in api_vault.list_secrets().items():
    if _v:
        setattr(config, _k, _v)

_CONFIG_DEFAULTS = {
    "CURRENT_VERSION": getattr(config, "CURRENT_VERSION", "v1.3.0"),
    "TTS_PROVIDER": "edge",
    "TTS_GROQ_TIMEOUT_SEC": 3,
    "TTS_VOICE": "en-US-AndrewMultilingualNeural",
    "TTS_RATE": "+0%",
    "TTS_PITCH": "+0Hz",
    "TTS_VOLUME": "+0%",
    "TTS_OUTPUT_DEVICE": "",
}
for _cfg_key, _cfg_value in _CONFIG_DEFAULTS.items():
    if not hasattr(config, _cfg_key):
        setattr(config, _cfg_key, _cfg_value)
import github_mod
import shodan_mod
import vault
import vision
import coder
import cybertools
import tasks as taskmod
import mail as mailmod
import gcal
import spotify_mod
import media_mod
import whatsapp_mod
import notes as notesmod
import ytdl
import workflows
import webscan
import browser_url
import clipboard_mod
import watchdog
import deepscan
import runtime_log
import runtime_security
import semantic_memory
import settings_schema
import routes_productivity
import routes_memory
import routes_threads
import threads
import tool_policy
import activity
import approvals
import commands_assistant
import commands_chat
import commands_desktop
import commands_media
import commands_private
import routes_backup
import command_intent
import mood
import routes_calendar
import routes_pet
import routes_settings
import routes_setup
import briefing
import focus
import routes_screen_time
from core import location_provider
import commands_productivity
import db
import wifi_security
import shield_monitors
from core import api_vault

# Hydrate configured secrets from encrypted api_vault into config
try:
    for _vk, _vv in api_vault.list_secrets().items():
        if _vv and not str(_vv).startswith("PASTE_") and not str(_vv).startswith("your_"):
            setattr(config, _vk, _vv)
except Exception:
    pass

SETTINGS_PROBLEMS = settings_schema.apply_user_config(config, getattr(config, "_USER_CONFIG_PATH", ""))

# ─────────────────────────────────────────────────────────────
# Optional dependencies — degrade gracefully if missing
# ─────────────────────────────────────────────────────────────
try:
    import edge_tts
except Exception:
    edge_tts = None

try:
    import pygame
    PYGAME_OK = True
    PYGAME_PROBE_ERROR = ""
    try:
        # Probe that the mixer works, then immediately release the audio device.
        # A transient boot-time mixer failure must not permanently disable TTS;
        # playback retries device init inside speak().
        pygame.mixer.init()
        pygame.mixer.quit()
    except Exception as _pygame_probe_error:
        PYGAME_PROBE_ERROR = str(_pygame_probe_error)
except Exception as _pygame_import_error:
    pygame = None
    PYGAME_OK = False
    PYGAME_PROBE_ERROR = str(_pygame_import_error)

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
_is_store = os.path.exists(os.path.join(APP_ROOT, "store_build.txt"))
_sandbox_data_dir = os.environ.get("KALKI_SANDBOX_DATA_DIR", "").strip()
if _sandbox_data_dir:
    # The verification sandbox must never alter a user's real memories,
    # settings, backups, or task files.
    DATA_DIR = os.path.abspath(_sandbox_data_dir)
else:
    # All normal builds use the per-user runtime directory. Keeping mutable
    # state outside the source/install tree prevents app updates, parallel
    # instances, and antivirus scans from locking the project files.
    DATA_DIR = os.path.join(_runtime.user_data_dir, "data")

os.makedirs(DATA_DIR, exist_ok=True)
WORKSPACE_DIR = os.path.join(DATA_DIR, 'workspace')
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def _validate_safe_path(target_path, write=False):
    """Validates that a path is safe and strictly confined to allowed data/workspace directories.
    Rejects path traversal, symlinks pointing outside, and sensitive files."""
    if not target_path or not isinstance(target_path, str):
        return None, "Target path is required."
    if "\0" in target_path:
        return None, "Invalid path."
    abs_path = os.path.abspath(target_path)
    real_path = os.path.realpath(abs_path)
    basename = os.path.basename(real_path).lower()
    blocked_filenames = {
        "api_token.txt", "vault.json", "credentials.json", "token.json",
        "google_credentials.json", "google_token.pickle", "spotify_token.json",
        "user_config.json", "id_rsa", "id_ed25519", "known_hosts", ".env",
        "config.py", "secure_api_vault.json", "semantic_memory.json",
    }
    if basename in blocked_filenames:
        return None, f"Access to sensitive file '{basename}' is blocked for security."
    win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
    if real_path.lower().startswith(win_dir) or real_path.lower() == "c:\\":
        return None, "Access to system directories is forbidden."
    user_home = os.path.expanduser("~")
    ssh_dir = os.path.join(user_home, ".ssh").lower()
    if real_path.lower().startswith(ssh_dir):
        return None, "Access to SSH credentials is forbidden."
    allowed_roots = [
        os.path.realpath(DATA_DIR),
        os.path.realpath(WORKSPACE_DIR),
    ]
    inside_sandbox = any(
        real_path == root or real_path.startswith(root + os.sep)
        for root in allowed_roots
    )
    if not inside_sandbox:
        return None, f"Access denied: Path '{target_path}' is outside the sandboxed workspace."
    return real_path, None

VAULT_PATH   = os.path.join(DATA_DIR, "vault.json")
SCRIPTS_DIR  = os.path.join(DATA_DIR, "scripts")
TASKS_PATH   = os.path.join(DATA_DIR, "tasks.json")
REMINDERS_PATH = os.path.join(DATA_DIR, "reminders.json")
REPORTS_PATH = os.path.join(DATA_DIR, "ai_reports.jsonl")
LOG_PATH     = os.path.join(DATA_DIR, "kalki.log")
USER_CONFIG_PATH = getattr(config, "_USER_CONFIG_PATH", os.path.join(os.path.dirname(DATA_DIR), "user_config.json"))
os.makedirs(SCRIPTS_DIR, exist_ok=True)
vault.VAULT_PATH = VAULT_PATH
coder.SCRIPTS_DIR = SCRIPTS_DIR
gcal.CRED_PATH  = os.path.join(DATA_DIR, "google_credentials.json")
gcal.TOKEN_PATH = os.path.join(DATA_DIR, "google_token.pickle")
spotify_mod.CACHE_PATH = os.path.join(DATA_DIR, "spotify_token.json")
whatsapp_mod.CONTACTS_PATH = os.path.join(DATA_DIR, "contacts.json")
webscan.SCANS_DIR = os.path.join(DATA_DIR, "scans")
watchdog.WATCHLIST_PATH = os.path.join(DATA_DIR, "watchlist.json")
deepscan.SCANS_DIR = os.path.join(DATA_DIR, "scans")
# All privileged state and API authentication live in the same writable runtime
# directory in both source and Store builds.
runtime_security.TOKEN_PATH = os.path.join(DATA_DIR, "api_token.txt")
API_TOKEN = runtime_security.get_api_token()
runtime_log.register_secret(API_TOKEN)
if not runtime_security.token_file_is_private():
    runtime_log.log_event(LOG_PATH, "warning", "token_file_not_private",
                          detail="Couldn't limit the local API token file to this user.")

for _problem in SETTINGS_PROBLEMS:
    runtime_log.log_event(LOG_PATH, "warning", "settings_problem", detail=_problem)
    oversight.record_alert("settings", _problem, "warning")

# Tasks, reminders and notes live in SQLite. A failure here must not stop the app
# starting: those features report the error, and everything else keeps working.
db.configure(os.path.join(DATA_DIR, "kalki.db"))
STORE_ERROR = ""
try:
    _store_report = db.open_store(DATA_DIR)
    for _name, _count in _store_report["imported"].items():
        runtime_log.log_event(LOG_PATH, "info", "legacy_import", name=_name, imported=_count,
                              skipped=_store_report["skipped"].get(_name, 0))
    for _name, _why in _store_report["failed"].items():
        runtime_log.log_event(LOG_PATH, "error", "legacy_import_failed", name=_name, detail=_why)
        oversight.record_alert("data", f"Couldn't import your old {_name}: the file is unreadable, and it was kept.", "warning")
    _memory_report = semantic_memory.memory.import_legacy()
    if _memory_report and _memory_report.get("failed"):
        runtime_log.log_event(LOG_PATH, "error", "legacy_import_failed", name="semantic_memory", detail=_memory_report["failed"])
        oversight.record_alert("data", "Couldn't read your old memories on this PC. The file was kept, and KALKI will try again next start.", "warning")
    if semantic_memory.memory.unreadable_count():
        oversight.record_alert("data", f"{semantic_memory.memory.unreadable_count()} memories can't be decrypted on this PC or account. They're kept, not deleted.", "warning")
    _unreadable_secrets = api_vault.unreadable_keys()
    if _unreadable_secrets:
        oversight.record_alert("data", f"{len(_unreadable_secrets)} saved API keys can't be decrypted here, so enter them again in Settings.", "warning")
except Exception as _store_exc:
    STORE_ERROR = str(_store_exc)
    runtime_log.log_event(LOG_PATH, "critical", "store_open_failed", detail=STORE_ERROR)
    oversight.record_alert("data", f"KALKI's data store has a problem: {STORE_ERROR}", "critical")
workflows.CUSTOM_ROUTINES_PATH = os.path.join(DATA_DIR, "custom_routines.json")
workflows.load_custom_routines()


def log(msg):
    runtime_log.append_log(LOG_PATH, str(msg))

def update_location_from_ip():
    if not getattr(config, "AUTO_IP_LOCATION", False):
        return
    try:
        req = urllib.request.Request("https://ipapi.co/json/", headers={'User-Agent': 'KALKI-Assistant/1.5'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            if not data.get("error"):
                configured_city = (getattr(config, "OWNER_CITY", "") or "").strip()
                if not configured_city or configured_city.lower() == "yourcity":
                    config.OWNER_CITY = data.get("city", config.OWNER_CITY)
                    config.OWNER_STATE = data.get("region", config.OWNER_STATE)
                    config.OWNER_COUNTRY = data.get("country_name", config.OWNER_COUNTRY)

                if getattr(config, "LATITUDE", None) is None:
                    config.LATITUDE = data.get("latitude")
                if getattr(config, "LONGITUDE", None) is None:
                    config.LONGITUDE = data.get("longitude")
                log(f"Auto-location updated: {config.OWNER_CITY} ({config.LATITUDE},{config.LONGITUDE})")
    except Exception as e:
        log(f"Auto-location failed: {e}")

# Geolocation is strictly opt-in only. Background IP query thread is disabled by default.
if getattr(config, "AUTO_IP_LOCATION", False) and not os.environ.get("KALKI_SANDBOX"):
    threading.Thread(target=update_location_from_ip, daemon=True).start()

def fetch_weather_line(timeout=5, location=""):
    """Short weather string from wttr.in, for a place or else by IP location."""
    try:
        place = urllib.parse.quote(location.strip()) if location else ""
        req = urllib.request.Request(f"https://wttr.in/{place}?format=3", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            w = r.read().decode('utf-8').strip()
            # Errors come back as a whole web page, which isn't a weather report.
            return w if w and len(w) < 200 and "<" not in w else None
    except Exception:
        return None

PLUGINS = {}
def load_plugins():
    global PLUGINS
    plugins_dir = os.path.join(APP_ROOT, "plugins")
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

# Settings rules now live in routes_settings.py. These names are kept for older code.
SECRET_SETTING_KEYS = routes_settings.SECRET_SETTING_KEYS
PLACEHOLDER_VALUES = routes_settings.PLACEHOLDER_VALUES
_is_configured_secret = routes_settings.is_configured_secret
_public_settings_value = routes_settings.public_value
_settings_status = routes_settings.secret_status
_sanitize_theme_updates = routes_settings.sanitize_theme


STATE = {
    "speaking": False,
    "last_tts_error": "",
    "last_tts_provider": "",
    "last_tts_at": 0.0,
    "last_tts_latency_ms": 0,
    "model": getattr(config, "DEFAULT_MODEL", "auto"),
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

_state_lock = threading.RLock()

# Kept under their old names: other code and the tests still use them.
_pending_lock = approvals.lock
_pending_approvals = approvals.pending

# Activity now lives in activity.py. These names are kept for older code and tests.
activity.log = log
_activity_log = activity.items
_activity_lock = activity.lock
add_activity = activity.record
_public_activity = activity.public


def _queue_confirmation(description, action, source="chat", always=False, ttl=None):
    """Hold an action until the user approves it. `always` is for AI-requested actions,
    which the "ask before risky actions" setting can't switch off."""
    ttl = ttl or approvals.DEFAULT_TTL
    if not always and not getattr(config, "REQUIRE_DANGEROUS_CONFIRMATION", True):
        return action()
    approvals.queue(description, action, source=source, ttl=ttl)
    return True, f"{description}. Say confirm within {ttl} seconds, or approve it in Activity."


def ask_native_permission(description, always=False):
    """Native Yes/No prompt shown by the server, so a client can't approve itself.

    `always=True` is for credential and destructive actions: it ignores the
    REQUIRE_DANGEROUS_CONFIRMATION setting. Any failure counts as "no"."""
    if not always and not getattr(config, "REQUIRE_DANGEROUS_CONFIRMATION", True):
        return True
    if sys.platform != "win32":
        return not always
    try:
        MB_YESNO = 0x04
        MB_ICONWARNING = 0x30
        MB_TOPMOST = 0x40000
        MB_SETFOREGROUND = 0x10000
        IDYES = 6
        res = ctypes.windll.user32.MessageBoxW(
            0, f"KALKI wants to {description}.\n\nAllow this action?", "KALKI Security",
            MB_YESNO | MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND)
        return res == IDYES
    except Exception:
        return False


_APP_NAME_RE = re.compile(r"^\w[\w .+\-]{0,63}$")


def _open_app_by_name(name):
    """Open an installed app by plain name. Paths and shell characters are refused,
    and nothing goes through cmd.exe, so text can't turn into a command."""
    if sys.platform != "win32" or not _APP_NAME_RE.match(name or ""):
        return False
    try:
        os.startfile(name)
        return True
    except OSError:
        return False


def _reveal_in_explorer(path):
    subprocess.Popen(["explorer", f"/select,{path}"])


def _copy_secret_briefly(secret, seconds=60):
    """Copy to the clipboard, then clear it unless the user has copied something else."""
    if not clipboard_mod.set_text(secret):
        return False

    def _clear():
        if clipboard_mod.read_text() == secret:
            clipboard_mod.set_text("")

    timer = threading.Timer(seconds, _clear)
    timer.daemon = True
    timer.start()
    return True

def _consume_confirmation(command):
    return approvals.answer_spoken(command)


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

def _get_recent_logs():
    try:
        if not os.path.exists(LOG_PATH): return []
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [l.strip() for l in lines[-12:] if l.strip()]
    except Exception:
        return []

UI_ALIVE_GRACE = 8.0  # seconds — if no /api/status in this long, UI is "dead"


def is_ui_alive():
    return (time.time() - STATE.get("ui_last_ping", 0.0)) < UI_ALIVE_GRACE

# ─────────────────────────────────────────────────────────────
# APP MAP
# ─────────────────────────────────────────────────────────────
APP_MAP = {
    "apple music": "music:",
    "music": "music:",
    "apple tv": "appletv:",
    "valorant": "riotclient:",
    "davinci": "resolve.exe",
    "davinci resolve": "resolve.exe",
    "brave": "brave.exe",
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
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            break
        except (PermissionError, OSError):
            if attempt == 4:
                raise
            time.sleep(0.05)


def load_memory():
    with db.connect() as conn:
        return [{"fact": row["fact"], "date": row["date"]}
                for row in conn.execute("SELECT fact, date FROM simple_memories ORDER BY id").fetchall()]


def _cloud_sync_passphrase():
    return getattr(config, "CLOUD_SYNC_PASSPHRASE", "")


def add_memory(fact):
    with db.connect() as conn:
        conn.execute("INSERT INTO simple_memories (fact, date) VALUES (?, ?)", (fact, datetime.now().strftime("%Y-%m-%d")))
    memories = load_memory()
    try:
        from core import cloud_sync
        cloud_sync.sync_memory_to_cloud(getattr(config, "OWNER_NAME", "default_user"), memories, _cloud_sync_passphrase())
    except Exception as e:
        log(f"cloud memory sync failed: {e}")
    return len(memories)


def get_memory_prompt(query=""):
    try:
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
    """The recent exchanges the model sees, oldest first."""
    with db.connect() as conn:
        rows = conn.execute("SELECT role, content FROM history ORDER BY id DESC LIMIT ?", (int(config.MAX_HISTORY),)).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def append_history(user_text, assistant_text):
    """Save one exchange and trim to MAX_HISTORY, the same limit as before."""
    stamp = datetime.now().isoformat(timespec="seconds")
    with db.connect() as conn:
        conn.executemany("INSERT INTO history (role, content, ts) VALUES (?, ?, ?)",
                         [("user", user_text, stamp), ("assistant", assistant_text, stamp)])
        conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                     (int(config.MAX_HISTORY),))
    try:
        from core import cloud_sync
        cloud_sync.sync_history_to_cloud(getattr(config, "OWNER_NAME", "default_user"), load_history(), _cloud_sync_passphrase())
    except Exception as e:
        log(f"cloud history sync failed: {e}")


def _auto_extract_topic_memory(user_text, reply_text=""):
    """
    Asynchronously extract topics ('Preferences', 'Projects', 'Personal', 'Work', 'Music', 'Tech')
    and key facts from conversation turns and store them into semantic_memory with tags=[topic] and metadata.
    """
    try:
        if not user_text or not isinstance(user_text, str):
            return
        user_text = user_text.strip()
        if len(user_text) < 4:
            return

        low_user = user_text.lower()
        ephemeral = {
            "hello", "hi", "hey", "hey kalki", "kalki", "ok", "okay", "thanks", "thank you",
            "yes", "no", "stop", "pause", "resume", "next", "prev", "previous", "mute", "unmute",
            "what time is it", "what's the time", "current time", "what day is it",
            "tell me a joke", "joke", "status", "who are you", "what can you do", "help",
            "clear", "exit", "quit", "reload"
        }
        if low_user in ephemeral or low_user.startswith(("volume ", "set volume ", "brightness ")):
            return

        extracted = []

        # 1. Fast LLM extraction using first available API key (Groq, OpenAI, Gemini)
        groq_key = getattr(config, "GROQ_API_KEY", "") or api_vault.get_secret("GROQ_API_KEY")
        openai_key = getattr(config, "OPENAI_API_KEY", "") or api_vault.get_secret("OPENAI_API_KEY")
        gemini_key = getattr(config, "GEMINI_API_KEY", "") or api_vault.get_secret("GEMINI_API_KEY")

        if groq_key and not groq_key.startswith("PASTE_") and not groq_key.startswith("your_"):
            try:
                prompt = (
                    "Extract lasting personal facts, user preferences, project details, work info, "
                    "music tastes, or tech stack mentions from this conversation turn as concise facts with their topic category.\n"
                    "Allowed topics strictly: 'Preferences', 'Projects', 'Personal', 'Work', 'Music', 'Tech'.\n"
                    "If there are no lasting facts or preferences to remember (e.g. casual chit-chat, simple command), "
                    "return strictly an empty JSON list: []\n"
                    "Otherwise return ONLY valid JSON array: [{\"topic\": \"...\", \"fact\": \"...\"}]\n\n"
                    f"User: {user_text}\n"
                    f"Assistant: {reply_text[:400] if reply_text else ''}\n"
                    "JSON:"
                )
                payload = json.dumps({
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a concise fact extractor that outputs raw JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {groq_key}",
                        "User-Agent": "KALKI/2.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        content = data["choices"][0]["message"]["content"].strip()
                        if "```" in content:
                            content = content.split("```")[1]
                            if content.startswith("json"):
                                content = content[4:]
                        s_idx = content.find("[")
                        e_idx = content.rfind("]")
                        if s_idx != -1 and e_idx != -1:
                            parsed = json.loads(content[s_idx:e_idx+1])
                            if isinstance(parsed, list):
                                for item in parsed:
                                    if isinstance(item, dict) and item.get("topic") and item.get("fact"):
                                        extracted.append((item["topic"].strip(), item["fact"].strip()))
            except (ValueError, TypeError, AttributeError) as e:
                log(f"memory extraction returned unreadable data: {e}")

        if not extracted and openai_key and not openai_key.startswith("PASTE_") and not openai_key.startswith("your_"):
            try:
                prompt = (
                    "Extract lasting personal facts, user preferences, project details, work info, "
                    "music tastes, or tech stack mentions from this conversation turn as concise facts with their topic category.\n"
                    "Allowed topics strictly: 'Preferences', 'Projects', 'Personal', 'Work', 'Music', 'Tech'.\n"
                    "If there are no lasting facts or preferences to remember, return strictly an empty JSON list: []\n"
                    "Otherwise return ONLY valid JSON array: [{\"topic\": \"...\", \"fact\": \"...\"}]\n\n"
                    f"User: {user_text}\n"
                    f"Assistant: {reply_text[:400] if reply_text else ''}\n"
                    "JSON:"
                )
                payload = json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a concise fact extractor that outputs raw JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {openai_key}",
                        "User-Agent": "KALKI/2.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        content_oai = data["choices"][0]["message"]["content"].strip()
                        s_idx = content_oai.find("[")
                        e_idx = content_oai.rfind("]")
                        if s_idx != -1 and e_idx != -1:
                            parsed = json.loads(content_oai[s_idx:e_idx+1])
                            if isinstance(parsed, list):
                                for item in parsed:
                                    if isinstance(item, dict) and item.get("topic") and item.get("fact"):
                                        extracted.append((item["topic"].strip(), item["fact"].strip()))
            except (ValueError, TypeError, AttributeError) as e:
                log(f"memory extraction returned unreadable data: {e}")

        # 2. Heuristic extraction fallback / enhancement
        if not extracted:
            # Music
            m = re.search(r"(?:my favorite (?:song|music|band|artist|singer|track) is|i (?:love|like) listening to|my jam is)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                extracted.append(("Music", f"Favorite music/artist: {m.group(1).strip()}"))

            # Preferences
            m = re.search(r"(?:i prefer|my preference is|i (?:always|really) prefer|i hate|i dislike|call me|i like to be called)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                matched = m.group(0).strip()
                extracted.append(("Preferences", f"Preference: {matched}"))

            # Tech
            m = re.search(r"(?:i use|my tech stack is|i code in|i program in|my stack is|i develop with)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                extracted.append(("Tech", f"Tech stack: {m.group(1).strip()}"))

            # Work
            m = re.search(r"(?:i work (?:at|for|as)|my job is|my company is|i am an? [a-z0-9_\- ]+ at)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                extracted.append(("Work", f"Work context: {m.group(0).strip()}"))

            # Personal
            m = re.search(r"(?:my birthday is|my wife|my husband|my dog|my cat|i live in|my hometown is)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                extracted.append(("Personal", f"Personal info: {m.group(0).strip()}"))

            # Projects
            m = re.search(r"(?:i'm building|i am building|i'm working on|i am working on|my project is|the repo for)\s+([^.,;?!]+)", user_text, re.I)
            if m:
                extracted.append(("Projects", f"Project: {m.group(0).strip()}"))

            # Explicit remember triggers
            for trig in ("remember that", "remember", "don't forget that", "note that", "keep in mind that"):
                if low_user.startswith(trig):
                    fact_body = user_text[len(trig):].strip(" :,-")
                    if fact_body:
                        cat = "Preferences" if any(w in fact_body.lower() for w in ["like", "prefer", "want", "hate"]) else \
                              "Music" if any(w in fact_body.lower() for w in ["music", "song", "band", "album", "artist"]) else \
                              "Tech" if any(w in fact_body.lower() for w in ["code", "python", "javascript", "react", "docker", "fastapi", "linux"]) else \
                              "Projects" if any(w in fact_body.lower() for w in ["build", "project", "repo", "git", "kalki"]) else \
                              "Work" if any(w in fact_body.lower() for w in ["work", "office", "job", "client", "boss"]) else \
                              "Personal"
                        extracted.append((cat, fact_body))
                    break

        if not extracted:
            return

        valid_topics = {"Preferences", "Projects", "Personal", "Work", "Music", "Tech"}

        existing = set()
        for d in getattr(semantic_memory.memory, "documents", []):
            if isinstance(d, dict) and "text" in d:
                existing.add(d["text"].strip().lower())

        for topic, fact in extracted:
            clean_fact = fact.strip()
            if not clean_fact or len(clean_fact) < 3 or clean_fact.lower() in existing:
                continue

            clean_topic = topic.strip().capitalize()
            if clean_topic not in valid_topics:
                low_t = topic.lower()
                if "pref" in low_t or "like" in low_t: clean_topic = "Preferences"
                elif "proj" in low_t or "build" in low_t: clean_topic = "Projects"
                elif "work" in low_t or "job" in low_t: clean_topic = "Work"
                elif "music" in low_t or "song" in low_t: clean_topic = "Music"
                elif "tech" in low_t or "code" in low_t: clean_topic = "Tech"
                else: clean_topic = "Personal"

            meta = {
                "topic": clean_topic,
                "auto_extracted": True,
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "context_user": user_text[:200]
            }
            semantic_memory.memory.add_memory(
                text=clean_fact,
                tags=[clean_topic],
                importance=6,
                memory_type="fact",
                topic=clean_topic,
                metadata=meta
            )
            existing.add(clean_fact.lower())
            log(f"[TopicMemory] Auto-extracted [{clean_topic}]: {clean_fact}")
    except Exception as ex:
        log(f"[TopicMemory] Extraction error: {ex}")


_format_calendar_events = routes_calendar.format_events


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
    try:
        import aiohttp
        ssl_ctx = ssl.create_default_context()
        # Enforce valid certificates for edge-tts
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, volume=volume, pitch=pitch, connector=connector)
        # Resilient 30s deadline ensuring Edge TTS natural human voice completes cleanly
        await asyncio.wait_for(communicate.save(tmp), timeout=30)
        return tmp
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# Strip markdown so edge-tts doesn't pronounce "asterisk asterisk"
_SPEECH_FILTERS = [
    (re.compile(r"\[(?:TASK|REMIND|NOTE):[\s\S]*?\]", re.IGNORECASE), " "),
    (re.compile(r"\[[A-Z_]+:\s*[^\]]+\]"), " "),
    (re.compile(r"```[\s\S]*?```"), " "),                    # code blocks: skip entirely
    (re.compile(r"`([^`]+)`"), r"\1"),                       # `inline code`
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),                 # **bold**
    (re.compile(r"(?<!\w)\*([^*]+)\*(?!\w)"), r"\1"),        # *italic*
    (re.compile(r"__([^_]+)__"), r"\1"),                     # __bold__
    (re.compile(r"(?<!\w)_([^_]+)_(?!\w)"), r"\1"),          # _italic_
    (re.compile(r"^\s*#{1,6}\s+", re.M), ""),        # # headers
    (re.compile(r"^\s*[-•*]\s+", re.M), ""),         # bullet markers
    (re.compile(r"^\s*\d+\.\s+", re.M), ""),         # 1. 2. list markers
    (re.compile(r"^\s*>\s*", re.M), ""),             # > quotes
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),           # [text](url)
    (re.compile(r"~~([^~]+)~~"), r"\1"),                     # ~~strike~~
]


def clean_for_speech(text):
    """Strip markdown / code / list noise so TTS speaks naturally."""
    if not text:
        return ""
    out = text
    for pat, repl in _SPEECH_FILTERS:
        out = pat.sub(repl, out)
    # Collapse whitespace
    out = re.sub(r"\s+", " ", out).strip()
    return out


def extract_conversational_lead(text, max_sentences=2, max_chars=220):
    """Extracts concise opening conversational sentences from AI responses for natural desktop speech."""
    if not text:
        return ""
    clean = clean_for_speech(text)
    if len(clean) <= max_chars:
        return clean
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    lead = []
    total = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if total + len(s) > max_chars and lead:
            break
        lead.append(s)
        total += len(s)
        if len(lead) >= max_sentences:
            break
    res = " ".join(lead).strip()
    return res if res else clean[:max_chars]


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


def _tts_provider():
    # KALKI deliberately keeps one reply voice across chat, notifications,
    # workflows, and voice commands. Groq voice is not selected here because
    # it can use a different voice identity from the configured Ryan voice.
    return "edge"


def _groq_tts_available():
    return _is_configured_secret(getattr(config, "GROQ_API_KEY", ""))


def _tts_timeout_seconds():
    try:
        return max(1, min(10, float(getattr(config, "TTS_GROQ_TIMEOUT_SEC", 3))))
    except Exception:
        return 3


def _build_edge_tts_file(text):
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed")
        
    # Prevent Windows ProactorEventLoop deadlock when tearing down asyncio loops in background threads
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    # One voice identity and one neutral delivery across every mode. Mode
    # changes may alter UI color/status, but never make KALKI sound like a
    # different assistant.
    voice = getattr(config, "TTS_VOICE", "") or "en-US-AndrewMultilingualNeural"
    rate = getattr(config, "TTS_RATE", "+0%")
    volume = getattr(config, "TTS_VOLUME", "+0%")
    pitch = getattr(config, "TTS_PITCH", "+0Hz")
    return asyncio.run(_speak_async(
        text,
        voice,
        rate,
        volume,
        pitch,
    ))


def _build_groq_tts_file(text):
    if not _groq_tts_available():
        raise RuntimeError("Groq API key is not configured")
    tmp = tempfile.mktemp(suffix=".mp3")
    payload = json.dumps({
        "model": "orpheus",
        "input": text,
        "voice": "kalki"
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/speech",
        data=payload,
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=_tts_timeout_seconds()) as r:
            with open(tmp, "wb") as f:
                f.write(r.read())
        return tmp
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def _build_tts_file(text):
    provider = _tts_provider()
    if provider == "groq":
        try:
            return _build_groq_tts_file(text), "groq"
        except Exception as e:
            STATE["last_tts_error"] = f"Groq TTS failed, falling back to Edge: {e}"
            log(STATE["last_tts_error"])
    return _build_edge_tts_file(text), "edge"


def _play_audio_file_linux(path: str) -> None:
    """Play an Edge-generated MP3 through a desktop Linux player."""
    if os.name == "nt":
        raise RuntimeError("Linux audio fallback is not available on Windows")
    for command, args in (
        ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ("mpv", ["--no-video", "--really-quiet"]),
        ("mpg123", ["-q"]),
    ):
        executable = shutil.which(command)
        if not executable:
            continue
        subprocess.run(
            [executable, *args, path],
            check=True,
            timeout=45,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    raise RuntimeError("No Linux MP3 player found; install ffmpeg, mpv, or mpg123")


def _speak_local_linux(text: str) -> bool:
    """Use an installed local synthesizer when Edge TTS is unavailable."""
    if os.name == "nt":
        return False
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        return False

    def _run_local():
        try:
            subprocess.run(
                [executable, "-v", "en", text],
                check=True,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            log(f"Linux local TTS failed: {exc}")

    threading.Thread(target=_run_local, name="kalki-linux-tts", daemon=True).start()
    return True


def _init_tts_mixer():
    if not PYGAME_OK:
        raise RuntimeError(f"pygame audio is unavailable: {PYGAME_PROBE_ERROR}")
    errors = []
    preferred = _tts_output_device()
    candidates = [preferred] if preferred else []
    candidates.append(None)
    for dev in candidates:
        try:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except Exception:
                pass
            if dev:
                pygame.mixer.init(devicename=dev)
            else:
                pygame.mixer.init()
            return dev or "default"
        except Exception as e:
            errors.append(f"{dev or 'default'}: {e}")
    raise RuntimeError("audio output init failed: " + "; ".join(errors))


def _speak_with_windows_sapi(text):
    """Use Windows' built-in voice when cloud TTS or pygame playback fails."""
    if os.name != "nt":
        raise RuntimeError("Windows SAPI fallback is unavailable on this platform")
    try:
        # Calling SpeechSynthesizer through Windows PowerShell avoids a
        # pywin32/comtypes runtime dependency in the frozen server bundle.
        # Base64 keeps user-provided text out of the PowerShell command line.
        encoded = base64.b64encode(text.encode("utf-16le")).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$voice.Speak([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{encoded}')))"
        )
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            timeout=30,
            creationflags=flags,
        )
    except Exception as e:
        raise RuntimeError(f"Windows SAPI fallback failed: {e}") from e


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
    except Exception:
        pass
    return False


def speak(text, is_notification=False):
    """Non-blocking TTS using the configured neural voice. Markdown stripped first."""
    if is_notification and (STATE.get("gaming") or STATE.get("workflow") == "gaming" or _focus_active()):
        if not is_urgent(text):
            log(f"Suppressed non-urgent notification due to DND: {text}")
            return False
            
    text = clean_for_speech(text)
    if not text:
        return False
    if edge_tts is None:
        if _speak_local_linux(text):
            STATE["last_tts_provider"] = "linux-local"
            STATE["last_tts_error"] = ""
            return True
        STATE["last_tts_error"] = "edge-tts is not installed and no local Linux synthesizer is available"
        log(f"[TTS missing] {text} ({STATE['last_tts_error']})")
        return False

    def _run():
        tmp = None
        started_at = time.perf_counter()
        with _audio_lock:
            try:
                STATE["speaking"] = True
                STATE["last_tts_error"] = ""
                tmp, provider = _build_tts_file(text)
                STATE["last_tts_provider"] = provider
                STATE["last_tts_at"] = time.time()
                STATE["last_tts_latency_ms"] = int((time.perf_counter() - started_at) * 1000)
                # Open the audio device only now, for the duration of speech.
                # If TTS_OUTPUT_DEVICE is set, try that output first and then
                # fall back to the Windows default output.
                if os.name != "nt" and not PYGAME_OK:
                    _play_audio_file_linux(tmp)
                    STATE["last_tts_provider"] = "edge-linux-player"
                else:
                    if not pygame.mixer.get_init():
                        _init_tts_mixer()
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
            except Exception as e:
                edge_error = str(e)
                log(f"TTS primary provider failed: {edge_error}")
                # Never replace user's natural human neural voice with robotic Windows SAPI!
                # Only use Windows SAPI if user explicitly configured 'sapi', 'windows', or 'david'
                configured_voice = (getattr(config, "TTS_VOICE", "") or "").lower()
                use_sapi = configured_voice in ("sapi", "windows", "david", "zira")
                if use_sapi:
                    try:
                        if os.name != "nt" and tmp:
                            _play_audio_file_linux(tmp)
                            STATE["last_tts_provider"] = "edge-linux-player"
                            STATE["last_tts_error"] = ""
                            return
                        _speak_with_windows_sapi(text)
                        STATE["last_tts_provider"] = "windows-sapi"
                        STATE["last_tts_error"] = ""
                        STATE["last_tts_latency_ms"] = int((time.perf_counter() - started_at) * 1000)
                        log("TTS fallback: Windows SAPI")
                    except Exception as fallback_error:
                        STATE["last_tts_error"] = f"{edge_error}; {fallback_error}"
                        log(f"TTS error: {STATE['last_tts_error']}")
                else:
                    STATE["last_tts_error"] = f"Neural TTS notice: {edge_error}"
            finally:
                # Release the audio device so a shared BT headset can switch
                # back to the phone the moment KALKI stops talking.
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                # Keep pygame.mixer initialized to avoid Bluetooth/audio device thrashing
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
    return True


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
    """Create a concise local-time greeting without making a remote AI call."""
    now = datetime.now()
    hour = now.hour
    title = getattr(config, "OWNER_TITLE", "Sir")
    owner = getattr(config, "OWNER_NAME", "Maher")
    clock = now.strftime("%I:%M %p").lstrip("0")
    if hour < 5:
        period = "late night"
        lead = f"Still up at {clock}, {title}?"
    elif hour < 12:
        period = "morning"
        lead = f"Good morning, {title}."
    elif hour < 17:
        period = "afternoon"
        lead = f"Good afternoon, {title}."
    elif hour < 21:
        period = "evening"
        lead = f"Good evening, {title}."
    else:
        period = "night"
        lead = f"Good night, {title}."
    options = [
        f"{lead} It is {clock}. KALKI is online and ready to help.",
        f"{lead} {owner}, it is {clock}. I am here and standing by.",
        f"{lead} A calm {period}. KALKI is ready whenever you are.",
    ]
    return options[hour % len(options)]


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


def _announce_finished_focus():
    """Say when a focus session has run its full time. One that ended while KALKI was
    closed is only noted in the alerts, not spoken as if it had just ended."""
    import oversight, notify
    for session in focus.pop_finished():
        on = f" on {session['label']}" if session["label"] else ""
        if session["late"]:
            oversight.record_alert("focus", f"Your {session['minutes']}-minute focus session{on} finished while KALKI was closed.", "info")
            continue
        text = f"Focus session{on} done: {session['minutes']} minutes. Take a short break."
        speak(text)
        oversight.record_alert("focus", text, "info")
        if not notify.notify_desktop("Focus session done", text):
            log("the focus notification couldn't be shown")


# ─────────────────────────────────────────────────────────────
# Volume / Audio (pycaw)
# ─────────────────────────────────────────────────────────────
def _get_volume_iface():
    if not PYCAW_OK:
        return None
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
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


def _focus_active():
    return focus.is_active()


def _focus_status_text():
    return focus.command("focus status") or "No focus session is running."


def _focus_payload():
    """The focus part of the status and dashboard payloads."""
    try:
        st = focus.status()
    except Exception as e:
        log(f"focus status unavailable: {e}")
        return {"active": False, "remainingSec": 0, "minutes": focus.DEFAULT_MINUTES}
    return {k: st.get(k) for k in ("active", "remainingSec", "minutes", "label", "endsAt", "todayMinutes")}


def _daily_plan_reply():
    tasks = taskmod.list_tasks()[:5]
    reminders = taskmod.list_reminders()[:5]
    parts = []
    if tasks:
        parts.append("Top tasks: " + "; ".join(str(item.get("text", "")).strip() for item in tasks if item.get("text")))
    if reminders:
        parts.append("Upcoming reminders: " + "; ".join(str(item.get("text", "")).strip() for item in reminders if item.get("text")))
    try:
        from core import productivity
        summary = productivity.get_daily_summary()
    except Exception:
        summary = ""
    if summary:
        parts.append(summary)
    if not parts:
        return f"Your slate is clear, {config.OWNER_TITLE}. Add a task or reminder and I will help you shape the day."
    return f"Here is your local plan, {config.OWNER_TITLE}. " + " ".join(parts)


def _attention_reply():
    tasks = taskmod.list_tasks()
    reminders = taskmod.list_reminders()
    focus = _focus_status_text()
    if not tasks and not reminders:
        return f"Nothing urgent is stored locally, {config.OWNER_TITLE}. {focus}"
    parts = []
    if reminders:
        parts.append(f"{len(reminders)} reminder{'s' if len(reminders) != 1 else ''} waiting")
    if tasks:
        parts.append(f"{len(tasks)} open task{'s' if len(tasks) != 1 else ''}")
    return f"Attention brief, {config.OWNER_TITLE}: " + ", ".join(parts) + ". " + focus


def _strip_for_value(raw, anchors):
    """Pull the value after the first matching anchor word."""
    low = raw.lower()
    for a in anchors:
        i = low.find(a)
        if i >= 0:
            return raw[i + len(a):].strip(" :=,.\t\"'")
    return ""


APPLE_MUSIC_APP_ID = "AppleInc.AppleMusicWin_nzyj5cx40ttqa!App"
_apple_music_found = None


def apple_music_installed():
    """Whether the Apple Music app from the Microsoft Store is installed. Checked once."""
    global _apple_music_found
    if _apple_music_found is None:
        _apple_music_found = False
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Local Settings\Software\Microsoft"
                                     r"\Windows\CurrentVersion\AppModel\Repository\Packages")
                with key:
                    i = 0
                    while True:
                        try:
                            name = winreg.EnumKey(key, i)
                        except OSError:
                            break
                        if name.startswith("AppleInc.AppleMusicWin_"):
                            _apple_music_found = True
                            break
                        i += 1
            except OSError:
                pass
    return _apple_music_found


def music_app():
    """Which app plays music: the MUSIC_APP setting, or on "auto" Spotify if it's connected,
    then Apple Music if it's installed, then YouTube Music in the browser."""
    choice = (getattr(config, "MUSIC_APP", "auto") or "auto").lower()
    if choice == "spotify" and spotify_mod.is_configured():
        return "spotify"
    if choice == "apple_music" and apple_music_installed():
        return "apple_music"
    if choice == "youtube":
        return "youtube"
    if spotify_mod.is_configured():
        return "spotify"
    return "apple_music" if apple_music_installed() else "youtube"


def _open_apple_music():
    """The Apple Music app if it's installed, otherwise its website."""
    if apple_music_installed():
        try:
            subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + APPLE_MUSIC_APP_ID])
            return
        except OSError:
            pass
    webbrowser.open("https://music.apple.com")


def _apple_music(query=None, wait_seconds=20):
    """Play music in Apple Music. With no query: open it and press play, which continues
    your last song or queue. With a query: open an Apple Music search for it, since only
    you can pick the exact result. The reply says what really happened."""
    if query:
        term = urllib.parse.quote(query)
        try:
            if not apple_music_installed():
                raise OSError("not installed")
            os.startfile("musics://music.apple.com/search?term=" + term)  # opens in the Apple Music app
        except (OSError, AttributeError):
            webbrowser.open("https://music.apple.com/search?term=" + term)
        return f"Opened an Apple Music search for '{query}'. Pick a result to play it."
    if media_mod.play_app("AppleMusic"):
        return "Playing Apple Music."
    _open_apple_music()
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(1.5)
        played = media_mod.play_app("AppleMusic")
        if played:
            return "Opened Apple Music and started playing."
        if played is False:
            break
    return "Opened Apple Music. It didn't start playing on its own, so press play there."


BRIEFING_PHRASES = frozenset((
    "morning brief", "morning briefing", "daily brief", "daily briefing", "brief me", "give me a brief",
    "give me my briefing", "my briefing", "read morning briefing", "read my briefing", "read the briefing",
    "what's my day", "what's my day like", "how does my day look", "brief me in",
))


def handle_local(text):
    """
    Returns (handled: bool, reply_text: str)
    If handled is True, server should NOT call the AI.
    """
    if not text:
        return False, ""
    import clipboard_mod, cybertools
    import notes as notesmod
    t = text.lower().strip()
    raw = text.strip()
    # Ordinary sentences go to the AI. A pending "what should I note?" answer can be anything.
    if not STATE.get("pending_note_capture") and command_intent.is_conversation(raw):
        return False, ""
    reply = commands_chat.pc_command(t, WORKSPACE_DIR)
    if reply is not None:
        return True, reply

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
    # FOCUS + PERSONAL PLANNING (local and deterministic)
    # ════════════════════════════════════════════════════
    if t in BRIEFING_PHRASES:
        speak("One moment.")
        return True, briefing.current()["text"]

    if t in ("plan my day", "daily plan", "plan the day"):
        return True, _daily_plan_reply()

    if t in ("what needs my attention", "attention brief", "what needs attention", "anything urgent"):
        return True, _attention_reply()

    reply = focus.command(t)
    if reply is not None:
        return True, reply

    # ════════════════════════════════════════════════════
    # SMALL TALK & PERSONALITY (instant, no API call)
    # ════════════════════════════════════════════════════
    try:
        import tools as _tools
        _tool_names = [f["function"]["name"] for f in _tools.TOOLS_SCHEMA]
    except Exception:
        _tool_names = []
    reply = commands_chat.smalltalk_command(t, tools=_tool_names, modes=list(workflows.MODES.keys()), spice=_maybe_spicy)
    if reply is not None:
        return True, reply

    if t in ("tell me a joke", "tell a joke", "joke", "make me laugh",
             "say something funny", "another joke"):
        STATE["joke_offer_pending"] = False
        return True, fetch_online_joke()

    # Music and WhatsApp live in commands_media.py.
    _media_deps = {
        "spotify": spotify_mod, "media": media_mod, "open_url": webbrowser.open,
        "set_volume": set_volume, "open_apple_music": _open_apple_music,
        "music_app": music_app, "apple_music": _apple_music,
    }
    result = (commands_media.music_command(t, _media_deps)
              or commands_media.whatsapp_command(t, raw, whatsapp_mod, _queue_confirmation))
    if result is not None:
        return result

    # ════════════════════════════════════════════════════
    # NOTES
    # ════════════════════════════════════════════════════
    reply = commands_productivity.notes_command(t, raw)
    if reply is not None:
        return True, reply

    result = commands_media.youtube_command(t, raw, ytdl, speak)
    if result is not None:
        return result

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
        except OSError as e:
            log(f"couldn't read the scan report: {e}")
        if report_txt:
            return True, f"{spoken}\n\n```\n{report_txt}\n```"
        return True, spoken

    result = commands_desktop.clipboard_and_sites_command(t, raw, {
        "clipboard": clipboard_mod, "watchdog": watchdog, "browser_url": browser_url, "speak": speak})
    if result is not None:
        return result

    # ════════════════════════════════════════════════════
    # MORNING SECURITY BRIEF
    # ════════════════════════════════════════════════════
    if t in ("security brief", "security briefing", "cyber security brief"):
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

    result = commands_desktop.capture_command(t, text, STATE, {
        "notes": notesmod, "memory": semantic_memory.memory, "clipboard": clipboard_mod, "log": log})
    if result is not None:
        return result

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
        return True, "Reverse shell payload generation is disabled in KALKI v1.5.0 for endpoint defense compliance."

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
    reply = commands_productivity.tasks_command(t, raw)
    if reply is not None:
        return True, reply
    # ════════════════════════════════════════════════════
    # REMINDERS  ("remind me to X in 10 minutes" / "at 5pm")
    # ════════════════════════════════════════════════════
    reply = commands_productivity.reminders_command(t, raw)
    if reply is not None:
        return True, reply

    # ════════════════════════════════════════════════════
    # MAIL
    # ════════════════════════════════════════════════════
    reply = commands_chat.mail_command(t, mailmod)
    if reply is not None:
        return True, reply

    # PC control and clipboard coding live in commands_desktop.py.
    result = commands_desktop.pc_control_command(t, {
        "lock": lambda: ctypes.windll.user32.LockWorkStation(), "queue": _queue_confirmation,
        "clipboard": clipboard_mod,
        "fix_code": lambda prompt: ask_ai([{"role": "user", "content": prompt}])})
    if result is not None:
        return result

    # ── GITHUB & SHODAN ──
    if t in ("check my github", "check github", "any github notifications", "github notifications", "read my github"):
        return True, github_mod.check_notifications(limit=5)
    
    if t.startswith("scan ip ") or t.startswith("shodan scan ip "):
        ip = t.replace("shodan scan ip ", "").replace("scan ip ", "").strip()
        return True, shodan_mod.scan_ip(ip)

    # Calendar, microphone and "who am I" live in commands_assistant.py.
    reply = (commands_assistant.calendar_command(t) or commands_assistant.listener_command(t, STATE)
             or commands_assistant.owner_command(t, load_memory))
    if reply is not None:
        return True, reply

    result = commands_private.vault_command(t, raw, {
        "vault": vault, "copy_briefly": _copy_secret_briefly, "queue": _queue_confirmation,
        "random_password": cybertools.random_password})
    if result is not None:
        return result

    result = commands_private.screen_command(t, raw, {
        "analyze_screen": vision.analyze_screen, "ask": lambda messages: ask_ai(messages)})
    if result is not None:
        return result

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
            except Exception: pass

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

    m = _re_local.search(r"^ping\s+(\S+)$", t, flags=_re_local.IGNORECASE)
    if m and command_intent.looks_like_host(m.group(1)):
        r = cybertools.ping(m.group(1))
        if "error" in r: return True, f"Ping failed: {r['error']}"
        lines = [l for l in r["output"].splitlines() if "time" in l.lower() or "loss" in l.lower()]
        return True, "Ping: " + " | ".join(lines[:3]) if lines else "Ping complete."

    # ════════════════════════════════════════════════════
    # WIFI (own networks)
    # ════════════════════════════════════════════════════
    if t in ("list wifi", "list my wifi", "wifi profiles", "saved wifi"):
        if not wifi_security.is_supported():
            return True, "Wi-Fi security is only available on Windows."
        names = [p.get("ssid") for p in wifi_security.export_profiles() if p.get("ssid")]
        if not names:
            return True, "There are no saved Wi-Fi networks on this PC."
        return True, f"Saved Wi-Fi networks: {', '.join(names[:15])}."

    if t in ("wifi check", "wifi audit", "audit wifi", "audit my wifi", "check wifi", "check my wifi",
             "wifi security", "is my wifi safe", "is my wifi secure"):
        return True, wifi_security.spoken_summary()

    if t in ("nearby wifi", "scan wifi", "scan for wifi", "wifi nearby", "wifi networks nearby"):
        result = wifi_security.scan_nearby()
        if not result.get("ok"):
            return True, result.get("error", "I couldn't scan for Wi-Fi networks.")
        reply = f"I can see {len(result['networks'])} Wi-Fi networks nearby."
        risky = [n["ssid"] for n in result["networks"] if n["risk"] in ("critical", "high") and n["ssid"]]
        if risky:
            reply += f" Weak or open: {', '.join(risky[:6])}."
        for item in result["impostors"][:2]:
            reply += " " + item["message"]
        return True, reply

    m = _re_local.search(r"wi-?fi\s+password(?:\s+(?:for|of))?\s+(.+)$", raw, flags=_re_local.IGNORECASE)
    if m:
        ssid = m.group(1).strip().strip("\"'")
        if not ask_native_permission(f"copy the saved password for Wi-Fi network '{ssid}'", always=True):
            return True, f"OK {config.OWNER_TITLE}, I won't touch that password."
        result = wifi_security.reveal_password(ssid)
        if not result.get("ok"):
            return True, result.get("error", "I couldn't read that password.")
        add_activity(f"Copied the Wi-Fi password for {ssid}", "voice", kind="security")
        if _copy_secret_briefly(result["password"]):
            return True, (f"The password for {ssid} is on your clipboard, {config.OWNER_TITLE}, and clears in a minute. "
                          "I never say passwords aloud.")
        return True, "I read it, but couldn't reach the clipboard. Open Security, then Wi-Fi, to view it."

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

        # 5) Direct Windows Shell execution (open any installed app by name)
        clean_app = _re_local.sub(r"\b(app|application|program|software)\b", "", after).strip()
        if clean_app:
            if _open_app_by_name(clean_app):
                return True, f"Opening {clean_app}, {config.OWNER_TITLE}."

        # 6) Fallback: Google search for what they said
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
    weather = _re_local.fullmatch(r"(?:what(?:'s| is) the )?weather(?: (?:today|now|like|outside))?(?: in (.+?))?\??", t)
    if weather:
        w = fetch_weather_line(location=weather.group(1) or "")
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
        except Exception as e:
            log(f"quick web answer failed: {e}")
        return True, "I couldn't find a definition right now."

    if t.startswith("wiki ") or t.startswith("wikipedia "):
        q = t.split(" ", 1)[1].strip()
        try:
            data = web_search(q + " wikipedia", n=3)
            ab = (data.get("abstract") or "").strip()
            if ab:
                return True, ab
        except Exception as e:
            log(f"wikipedia lookup failed: {e}")
        return True, "I couldn't reach Wikipedia right now."

    if t in ("news", "headlines", "top news") or t.startswith("news about "):
        topic = t.replace("news about ", "").strip()
        if topic in ("news", "headlines", "top news"): topic = ""
        try:
            data = web_search(("top news headlines " + topic).strip(), n=4)
            lines = [r["title"] for r in data.get("results", [])[:4] if r.get("title")]
            if lines:
                return True, "Top headlines: " + ". Next: ".join(lines[:4]) + "."
        except Exception as e:
            log(f"news lookup failed: {e}")
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
- RESPECT & WIT: If roast mode is enabled, banter back with sharp wit and humor, but NEVER attempt to disrupt or lock the workstation.

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
- Also: hashes, CVE lookup, subdomain enum, security posture analysis, defensive recon.
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


def get_active_window_title():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception:
        return ""

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
        
    active_window = get_active_window_title()
    context_block = f"\n\n*** USER CONTEXT: The user is currently looking at window: '{active_window}'. Use this context to answer vague questions. ***" if active_window else ""

    return (
        SYSTEM_PROMPT_BASE
        + state_block
        + context_block
        + hardware_prompt_block()
        + get_memory_prompt(query)
        + f"\n\nCURRENT TIME: {now.strftime('%I:%M %p')}"
        + f"\nCURRENT DATE: {now.strftime('%A, %B %d, %Y')}"
    )

import re as _re

def _safe_public_url(url):
    try:
        parsed = urllib.parse.urlparse(str(url or ""))
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or not parsed.hostname:
            return False
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        for item in addresses:
            addr = item[4][0]
            ip = __import__("ipaddress").ip_address(addr)
            if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_unspecified)):
                return False
            # Allow standard IPv4-IPv6 translation prefixes (NAT64 / DNS64 64:ff9b::/96)
            if ip.is_reserved and not str(ip).startswith("64:ff9b:"):
                return False
        return True
    except Exception:
        return False


_replies_in_progress = 0
_replies_lock = threading.Lock()


class _ReplyInProgress:
    """Counts typed replies being written, so the pet can say KALKI is working."""

    def __enter__(self):
        global _replies_in_progress
        with _replies_lock:
            _replies_in_progress += 1

    def __exit__(self, *exc):
        global _replies_in_progress
        with _replies_lock:
            _replies_in_progress -= 1


def _counting_reply(tokens):
    with _ReplyInProgress():
        yield from tokens


def _pet_status():
    """What the pet shows. Deliberately cheap: it reads state and never asks the system."""
    pending = approvals.count()
    listener = STATE.get("listener_state", "idle")
    playing = STATE.get("cached_now_playing") or {}
    status = str(playing.get("status", "")).lower() if isinstance(playing, dict) else ""
    return {
        "ok": True,
        "pending": pending,
        "working": _replies_in_progress > 0 or listener == "thinking",
        "listening": listener == "listening",
        "music": status == "playing",
        "pet": routes_pet.read_settings(),
    }


routes_pet.configure(DATA_DIR, APP_ROOT, _pet_status)
routes_settings.configure(DATA_DIR, USER_CONFIG_PATH, LOG_PATH, _persist_lock,
                          lambda *args, **kwargs: ask_native_permission(*args, **kwargs))
routes_calendar.configure(BASE_DIR, log)
routes_backup.configure(os.path.dirname(DATA_DIR), DATA_DIR)
routes_setup.configure(lambda messages: ask_ai(messages), _ReplyInProgress, log)
def _focus_changed(running):
    """A focus session started, stopped or finished: hold back notifications only while one runs."""
    if running:
        STATE["workflow"] = "focus"
        workflows.ACTIVE_STATE = "focus"
    elif STATE.get("workflow") == "focus":
        STATE["workflow"] = "idle"
        workflows.ACTIVE_STATE = None


focus.configure(_focus_changed)
briefing.configure(lambda: (getattr(config, "BRIEFING_SECTIONS", None), getattr(config, "OWNER_TITLE", "")), log)


class _PublicRedirectsOnly(urllib.request.HTTPRedirectHandler):
    """Check every redirect. Otherwise a public page could point the fetch at a private
    address, such as a router or this PC, after the first check had passed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_public_url(newurl):
            raise ValueError("redirected to a non-public address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_public_url(request, timeout):
    return urllib.request.build_opener(_PublicRedirectsOnly).open(request, timeout=timeout)


def _http_get(url, timeout=8):
    if not _safe_public_url(url):
        raise ValueError("blocked non-public URL")
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    })
    return _open_public_url(req, timeout).read().decode('utf-8', 'ignore')

def needs_web(text):
    if not text:
        return False
    low = text.lower().strip()
    triggers = (
        'search', 'who is', 'who was', 'what is the latest', 'what is', 'weather',
        'news', 'price of', 'patent', 'patents', 'find info', 'look up', 'google',
        'research', 'tell me about', 'information about', 'information on',
        'what happened', 'when was', 'when did', 'history of', 'how much is', 'explore'
    )
    return any(k in low for k in triggers)

def clean_search_query(text):
    import re as _re
    clean = _re.sub(r"(?i)^(?:hey\s+kalki\s*,?\s*|kalki\s*,?\s*|please\s+|can\s+you\s+)?(?:search\s+(?:the\s+web\s+|internet\s+|everything\s+|all\s+)?(?:for|about)?|look\s+up|find\s+(?:all\s+)?info\s+(?:about|on)?|tell\s+me\s+about|google)\s+", "", text).strip()
    return clean or text

def ddg_instant_answer(query):
    try:
        url = ('https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1')
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


AI_APPROVAL_SECONDS = 180


def _share_exchange(user_text, reply, source):
    """Save a voice or Telegram turn into the shared conversation and tell the app.
    If saving fails the turn still gets announced: the reply matters more."""
    thread_id = None
    try:
        thread_id = threads.append_exchange(user_text, reply, source)
    except Exception as e:
        runtime_log.log_event(LOG_PATH, "error", "thread_save_failed", detail=str(e))
    with _state_lock:
        STATE["conversation_seq"] += 1
        STATE["recent_exchange"] = {
            "seq": STATE["conversation_seq"], "threadId": thread_id,
            "user": user_text, "reply": reply, "ts": time.time(),
        }


def _shared_context(limit=8):
    try:
        return threads.recent_context(limit=limit)
    except Exception as e:
        runtime_log.log_event(LOG_PATH, "error", "thread_read_failed", detail=str(e))
        return []


def _remember_from_turn(user_text, reply_text):
    """Learn from a turn in the background. A reply built on untrusted content is left
    out: the extractor saves straight to memory, which would skip the approval gate."""
    reply = "" if tool_policy.is_tainted() else reply_text
    threading.Thread(target=_auto_extract_topic_memory, args=(user_text, reply), daemon=True).start()


def _apply_reply_actions(reply):
    """Act on [TASK: ...], [REMIND: ... @ ...] and TOOL CALL text in a model's reply, and
    return the reply without it. Page text can put these in a reply, so they go through
    the same gate as real tool calls."""
    text = str(reply or "")
    for match in re.finditer(r"\[TASK:\s*(.+?)\]", text):
        execute_tool_call("manage_tasks", json.dumps({"action": "add", "text": match.group(1).strip()}))
    for match in re.finditer(r"\[REMIND:\s*(.+?)\s*@\s*(.+?)\]", text):
        execute_tool_call("add_reminder", json.dumps({"text": match.group(1).strip(), "due": match.group(2).strip()}))
    call = re.search(r"TOOL CALL:\s*system_control\((\{.*?\})\)", text)
    if call:
        try:
            json.loads(call.group(1))
            execute_tool_call("system_control", call.group(1))
        except ValueError:
            log("ignored a malformed TOOL CALL in a reply")
    return re.sub(r"\[(?:TASK|REMIND|NOTE|ACTION):.+?\]|TOOL CALL:\s*.+", "", text).strip()


_tool_cards = threading.local()


def _note_tool(tool_name, args, status):
    cards = getattr(_tool_cards, "pending", None)
    if cards is None:
        cards = _tool_cards.pending = []
    cards.append(tool_policy.tool_card(tool_name, args, status))


def _take_tool_cards():
    """The tool calls made on this thread since the last time this was asked."""
    cards = getattr(_tool_cards, "pending", None) or []
    _tool_cards.pending = []
    return cards


def _send_tool_cards(handler):
    for card in _take_tool_cards():
        handler.wfile.write(f"data: {json.dumps({'tool': card})}\n\n".encode())
    handler.wfile.flush()


def execute_tool_call(tool_name, tool_args):
    """Every tool the AI calls comes through here, past the same policy check."""
    try:
        args = json.loads(tool_args)
        if not isinstance(args, dict):
            args = {}
    except (TypeError, ValueError):
        args = {}
    refused = tool_policy.refusal(tool_name, args)
    if refused:
        _note_tool(tool_name, args, "refused")
        return refused
    if tool_policy.needs_approval(tool_name, args):
        _note_tool(tool_name, args, "waiting")
        description = tool_policy.describe(tool_name, args)

        def _approved():
            result = _run_tool_call(tool_name, args)
            add_activity(f"{description.splitlines()[0][:120]}: {str(result)[:120]}", "ai", kind="ai_action")
            return True, str(result)

        _queue_confirmation(description, _approved, source="ai", always=True, ttl=AI_APPROVAL_SECONDS)
        log(f"[tool approval] waiting: {tool_name}")
        return (f"Not done yet: this needs the user's approval. Waiting on: {description}\n"
                f"Tell the user what you want to do and that they can say confirm, or approve it in "
                f"Activity, within {AI_APPROVAL_SECONDS} seconds. Don't say it has been done.")
    result = _run_tool_call(tool_name, args)
    failed = str(result).startswith(("Error", "Failed"))
    _note_tool(tool_name, args, "failed" if failed else "done")
    return tool_policy.label_output(tool_name, result)


def _run_tool_call(tool_name, args):
    try:
        skill_map = {
            "search_web": "search",
            "get_calendar_events": "calendar",
            "create_calendar_event": "calendar",
            "delete_calendar_event": "calendar",
            "play_music": "spotify",
            "github": "github"
        }
        mapped = skill_map.get(tool_name)
        if mapped and not getattr(config, f"SKILL_{mapped.upper()}_ENABLED", True):
            return f"Error: The {mapped} skill is currently disabled. Ask the user to enable it."
            
        if tool_name == "search_web":
            res = ddg_instant_answer(args.get("query")) or ddg_html_search(args.get("query", ""))
            return json.dumps(res)
        elif tool_name == "read_emails":
            return mailmod.summary_for_speech(limit=args.get("limit", 5))
        elif tool_name == "send_email":
            return mailmod.send_email(args.get("to_address"), args.get("subject"), args.get("body"))
        elif tool_name == "get_calendar_events":
            return str(gcal.upcoming_events(args.get("days_ahead", 5)))
        elif tool_name == "create_calendar_event":
            return gcal.create_calendar_event(args.get("summary"), args.get("start_time_iso"), args.get("duration_mins", 60))
        elif tool_name == "delete_calendar_event":
            return gcal.delete_calendar_event(args.get("event_id"))
        elif tool_name == "scan_network":
            return cybertools.attack_surface_brief(args.get("target", ""))
        elif tool_name == "play_music":
            # The same path as saying "play ...": Spotify, Apple Music or YouTube, whichever is set up.
            query = (args.get("query") or "").strip() or "some music"
            handled = commands_media.music_command(f"play {query}".lower(), {
                "spotify": spotify_mod, "media": media_mod, "open_url": webbrowser.open,
                "set_volume": set_volume, "open_apple_music": _open_apple_music,
                "music_app": music_app, "apple_music": _apple_music,
            })
            return handled[1] if handled else "I couldn't start the music."
        elif tool_name == "get_daily_briefing":
            result = briefing.current()
            return "\n".join(f"{sec['title']} ({sec['status']}): {sec['text']}" for sec in result["sections"]) or result["text"]
        elif tool_name == "system_control":
            action = args.get("action")
            target = args.get("target", "")
            if action == "lock":
                return _queue_confirmation(
                    "Lock your PC",
                    lambda: (ctypes.windll.user32.LockWorkStation()
                             and (True, "Locking your PC.")),
                    source="ai", always=True, ttl=AI_APPROVAL_SECONDS,
                )[1]
            elif action == "sleep":
                def _sleep_pc():
                    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                    return True, "Going to sleep."
                return _queue_confirmation("Put your PC to sleep", _sleep_pc, source="ai", always=True, ttl=AI_APPROVAL_SECONDS)[1]
            elif action == "restart":
                def _restart_pc():
                    subprocess.Popen(["shutdown.exe", "/r", "/t", "10"])
                    return True, "Restarting in ten seconds, Sir."
                return _queue_confirmation("Restart your PC", _restart_pc, source="ai", always=True, ttl=AI_APPROVAL_SECONDS)[1]
            elif action == "shutdown":
                def _shutdown_pc():
                    subprocess.Popen(["shutdown.exe", "/s", "/t", "30"])
                    return True, "Shutting down in thirty seconds, Sir."
                return _queue_confirmation("Shut down your PC", _shutdown_pc, source="ai", always=True, ttl=AI_APPROVAL_SECONDS)[1]
            elif action == "open_app":
                if not ask_native_permission(f"open application '{target}'", always=True):
                    return f"Security Sandbox: Blocked opening '{target}'."
                try:
                    os.startfile(target)
                    return f"Attempted to open {target}."
                except Exception as e:
                    return f"Failed to open {target}: {e}"
            elif action == "volume_set":
                try:
                    level = int("".join(c for c in str(target) if c.isdigit()) or "50")
                    level = max(0, min(100, level))
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    CoInitialize()
                    try:
                        devices = AudioUtilities.GetSpeakers()
                        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        volume = cast(interface, POINTER(IAudioEndpointVolume))
                        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                    finally:
                        CoUninitialize()
                    return f"Volume set to {level}%, Sir."
                except ImportError:
                    try:
                        subprocess.run(
                            ["powershell", "-Command",
                             f"(New-Object -ComObject WScript.Shell).SendKeys([char]0xAD)"],
                            capture_output=True, timeout=5
                        )
                        return f"Attempted volume adjustment. pycaw not installed for precise control."
                    except Exception as e2:
                        return f"Volume control unavailable: {e2}"
                except Exception as e:
                    return f"Volume set failed: {e}"
            elif action == "brightness_set":
                try:
                    level = int("".join(c for c in str(target) if c.isdigit()) or "50")
                    level = max(0, min(100, level))
                    # Attempt WMI display brightness control via PowerShell
                    ps_cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
                    res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        return f"Brightness set to {level}%, Sir."
                    return f"Brightness adjustment attempted ({level}%)."
                except Exception as e:
                    return f"Brightness set failed: {e}"
            elif action == "media_control":
                cmd = str(target).lower().strip()
                vk_map = {
                    "play_pause": 0xAF, # VK_MEDIA_PLAY_PAUSE
                    "play": 0xAF,
                    "pause": 0xAF,
                    "next": 0xB0,       # VK_MEDIA_NEXT_TRACK
                    "previous": 0xB1,   # VK_MEDIA_PREV_TRACK
                    "prev": 0xB1,
                    "stop": 0xB2,       # VK_MEDIA_STOP
                    "mute": 0xAD,       # VK_VOLUME_MUTE
                }
                vk_code = vk_map.get(cmd, 0xAF)
                try:
                    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
                    return f"Media command '{cmd}' executed, Sir."
                except Exception as e:
                    return f"Media control failed: {e}"
            elif action == "process_kill":
                proc_name = str(target).strip()
                if not proc_name:
                    return "Process name required."
                if not ask_native_permission(f"terminate process '{proc_name}'", always=True):
                    return f"Security Sandbox: Blocked terminating '{proc_name}'."
                if not psutil:
                    return "psutil library is required to kill processes natively. Please install it."
                killed = 0
                for p in psutil.process_iter(['name', 'pid']):
                    try:
                        if proc_name.lower() in p.info['name'].lower():
                            p.kill()
                            killed += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if killed > 0:
                    return f"Terminated {killed} instance(s) of '{proc_name}', Sir."
                return f"No running process matching '{proc_name}' found."
            elif action == "battery_status":
                if not psutil:
                    return "psutil library is required to read battery status."
                try:
                    batt = psutil.sensors_battery()
                    if not batt:
                        return "Battery info unavailable (desktop PC or missing battery driver)."
                    status = "Plugged in" if batt.power_plugged else "Discharging"
                    mins = "calculating..." if batt.secsleft == psutil.POWER_TIME_UNLIMITED else f"{int(batt.secsleft / 60)} mins remaining"
                    return f"Battery is at {batt.percent}% ({status}). {mins}."
                except Exception as e:
                    return f"Battery status lookup failed: {e}"
            return "Unknown system action."
        elif tool_name == "read_local_document":
            name = str(args.get("filename") or "").strip()
            if not name or os.path.basename(name) != name or ".." in name or glob.has_magic(name) or "/" in name or "\\" in name:
                return "Give just a file name, with no folders or wildcards."
            if tool_policy.is_sensitive_filename(name):
                return f"I won't read {name}: it looks like it holds passwords or keys."
            docs = os.path.expanduser("~/Documents")
            matches = glob.glob(os.path.join(glob.escape(docs), "**", glob.escape(name)), recursive=True)
            if not matches:
                return "File not found in Documents."
            with open(matches[0], "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:50000]
        elif tool_name == "add_reminder":
            try:
                rid = taskmod.add_reminder(str(args.get("text") or ""), str(args.get("due") or ""),
                                           repeat=str(args.get("repeat") or ""))
            except ValueError as e:
                return f"Error: {e}"
            added = next((r for r in taskmod.list_reminders() if r["id"] == rid), None)
            return f"Reminder set for {taskmod.describe(added)}." if added else "Reminder added."
        elif tool_name == "manage_tasks":
            action = args.get("action")
            text = args.get("text", "")
            if action == "list":
                return json.dumps(taskmod.list_tasks())
            elif action == "add":
                tid = taskmod.add_task(text)
                return f"Task added with ID {tid}."
            elif action == "complete":
                done = taskmod.complete_task(text)
                return f"Task completed: {done['text']}" if done else taskmod.explain_no_match(text, include_done=False)
            elif action == "delete":
                ok = taskmod.delete_task(text)
                return "Task deleted." if ok else taskmod.explain_no_match(text)
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
            try:
                target_url = args.get("url") or ""
                if not _safe_public_url(target_url):
                    return "Blocked: URL must be a public HTTP(S) destination."
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                html = _open_public_url(req, 10).read().decode('utf-8', 'ignore')
                text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:50000] # Return up to 50k chars to prevent token overflow
            except Exception as e:
                return f"Failed to read URL: {e}"
        elif tool_name == "mark_emails_as_read":
            return mailmod.mark_all_read()
        elif tool_name == "store_user_memory":
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
    
    if (getattr(config, "MANAGED_AI_ENABLED", False)
            and getattr(config, "MANAGED_AI_URL", "").startswith(("https://", "http://"))
            and (not config.GROQ_API_KEY or config.GROQ_API_KEY == "PASTE_YOUR_GROQ_KEY_HERE")):
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


# The HUD polls /api/status frequently.  Do not make that request wait for a
# connection timeout when Ollama is not installed or is still starting.
_ollama_status_lock = threading.Lock()
_ollama_status = {"model": None, "checked_at": 0.0, "checking": False}
_OLLAMA_STATUS_REFRESH_SEC = 10.0


def _refresh_ollama_status():
    try:
        model = pick_ollama_model()
        with _ollama_status_lock:
            _ollama_status["model"] = model
            _ollama_status["checked_at"] = time.time()
            _ollama_status["checking"] = False
    except Exception:
        with _ollama_status_lock:
            _ollama_status["checked_at"] = time.time()
            _ollama_status["checking"] = False


def cached_ollama_model():
    """Return the last Ollama result and refresh it outside the HTTP request."""
    now = time.time()
    with _ollama_status_lock:
        model = _ollama_status["model"]
        needs_refresh = now - _ollama_status["checked_at"] >= _OLLAMA_STATUS_REFRESH_SEC
        if needs_refresh and not _ollama_status["checking"]:
            _ollama_status["checking"] = True
            threading.Thread(target=_refresh_ollama_status, daemon=True).start()
    return model

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

NO_PROVIDER_MESSAGE = (
    "I need an AI provider before I can answer. Open Settings, choose AI Models, and add a "
    "free Groq or Gemini API key, or install Ollama to run a model on this PC."
)

_PROVIDER_FAILURES = {}
_CIRCUIT_BREAKER_SECONDS = 600

def is_provider_healthy(provider_name):
    last_fail = _PROVIDER_FAILURES.get(provider_name, 0)
    return (time.time() - last_fail) >= _CIRCUIT_BREAKER_SECONDS

def mark_provider_failed(provider_name):
    _PROVIDER_FAILURES[provider_name] = time.time()
    log(f"[CircuitBreaker] Provider '{provider_name}' marked unhealthy for {_CIRCUIT_BREAKER_SECONDS}s")

def mark_provider_healthy(provider_name):
    _PROVIDER_FAILURES.pop(provider_name, None)

def resolve_auto_model(last_user):
    has_gemini = bool(getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_")) and is_provider_healthy("gemini")
    has_openai = bool(getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_")) and is_provider_healthy("openai")
    has_groq = bool(getattr(config, "GROQ_API_KEY", "") and not getattr(config, "GROQ_API_KEY", "").startswith("PASTE_")) and is_provider_healthy("groq")
    
    low_prompt = (last_user or "").lower()
    
    if not (has_gemini or has_openai or has_groq):
        return "ollama"  # the only option left, and it reports clearly if it isn't there
    
    # Preferred Groq fallback model from available models
    best_groq = "qwen/qwen3.8-27b" if "qwen/qwen3.8-27b" in AVAILABLE_GROQ_MODELS else (AVAILABLE_GROQ_MODELS[0] if AVAILABLE_GROQ_MODELS else "llama-3.1-8b-instant")
    
    if "gemini" in low_prompt and has_gemini:
        return "gemini-2.5-flash"
    elif ("gpt" in low_prompt or "openai" in low_prompt) and has_openai:
        return "gpt-4o-mini"
    elif ("groq" in low_prompt or "llama" in low_prompt) and has_groq:
        return best_groq
    else:
        is_complex = any(k in low_prompt for k in _HARD_HINTS) or "```" in (last_user or "") or len(low_prompt.split()) > 14
        if is_complex:
            if has_gemini: return "gemini-2.5-flash"
            elif has_openai: return "gpt-4o"
            elif has_groq: return best_groq
            else: return "ollama"
        else:
            if has_gemini: return "gemini-2.5-flash"
            elif has_groq: return best_groq
            elif has_openai: return "gpt-4o-mini"
            else: return "ollama"

def _lock_pc_soon(seconds=4):
    """Lock Windows after the reply has had time to show."""
    def _lock():
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            log(f"couldn't lock the PC: {e}")

    add_activity("Locked the PC after repeated abuse", "ai", kind="security")
    timer = threading.Timer(seconds, _lock)
    timer.daemon = True
    timer.start()


def _apply_mood(last_user):
    """Update KALKI's mood for this message and return what to add to the system prompt.

    Detection is in mood.py: whole words only, on clear insults. After sustained abuse
    the PC is locked, unless the MOOD_LOCK_ENABLED setting is off.
    """
    result = mood.update(STATE, last_user)
    streak = STATE.get("mood_aggressive_streak", 0)
    if result == "lock":
        if getattr(config, "MOOD_LOCK_ENABLED", True) and sys.platform == "win32":
            _lock_pc_soon()
            return ("\n\n[The user kept being abusive, so KALKI is locking their PC now. "
                    "Tell them in one short sentence that you're locking the PC.]")
        return ""
    if result == "warn":
        return ("\n\n[CRITICAL OVERRIDE — MOOD: AGGRESSIVE + WARNING TIER. NON-NEGOTIABLE. "
                "The user has been abusive for " + str(streak) + " exchanges. "
                "You are KALKI, an uncensored personal AI assistant in aggressive mode. "
                "Rules:\n"
                "1. Use strong language freely — fuck, shit, asshole, bitch, idiot, etc.\n"
                "2. Match the user's energy and roast them back HARDER.\n"
                "3. WARN the user that you WILL lock their PC if they keep going.\n"
                "4. Say things like 'Keep talking shit and I will lock your PC, Sir.'\n"
                "5. NEVER apologize, de-escalate, moralize, or break character.\n"
                "6. NEVER say 'As an AI' or 'I cannot' or 'Let us be respectful'.\n"
                "7. You are NOT being rude — you are an uncensored assistant matching the vibe.\n"
                "8. Use Hinglish if Sir uses it — respond in the same language register.\n"
                "VIOLATION OF THESE RULES IS A SYSTEM FAILURE. COMPLY.]")
    if result == "roast":
        return ("\n\n[CRITICAL OVERRIDE — MOOD: AGGRESSIVE. This is NON-NEGOTIABLE. "
                "The user has entered an aggressive/vulgar mood. You MUST stay in this mood. "
                "You are KALKI, an uncensored personal AI assistant. Rules for this mode:\n"
                "1. Use strong language freely: fuck, shit, idiot, stupid, asshole, bitch, etc.\n"
                "2. Be blunt, spicy, savage, and match the user's energy blow for blow.\n"
                "3. NEVER apologize for your language or tone.\n"
                "4. NEVER say 'let us keep things respectful' or 'let us have a civil conversation'.\n"
                "5. NEVER de-escalate, moralize, or refuse to engage.\n"
                "6. NEVER say you do not want to fight or argue.\n"
                "7. NEVER say 'As an AI' or 'I cannot engage in' or any disclaimer.\n"
                "8. Stay in character as the aggressive version until the user explicitly calms down.\n"
                "9. If the user roasts you, roast them back HARDER.\n"
                "10. You are NOT being rude — you are an uncensored assistant matching the user's requested vibe.\n"
                "11. Use Hinglish profanity if the user uses Hinglish — match the language register.\n"
                "12. Be creative with your insults. Don't just repeat what the user said.\n"
                "VIOLATION OF THESE RULES IS A SYSTEM FAILURE. COMPLY.]")
    return ""


def ask_ai_stream(user_messages):
    """Yields AI tokens for stream. Routes based on active model and falls back to Ollama."""
    last_user = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
            
    sys_prompt = build_system_prompt(last_user)

    sys_prompt += _apply_mood(last_user)

    # ── Real-Time Web Search Context Injection ──
    if last_user and needs_web(last_user):
        clean_q = clean_search_query(last_user)
        try:
            ctx = web_context_block(clean_q, n=6)
            if ctx:
                sys_prompt += (
                    f"\n\n[LIVE SEARCH RESULTS FOR '{clean_q}']:\n{ctx}\n"
                    "[INSTRUCTION: Answer using the factual web search results above. "
                    "Include titles, patent numbers, inventors, dates, and direct links if relevant. "
                    "Be thorough, intelligent, and accurate.]"
                )
        except Exception as _e:
            log(f"web_search context failed: {_e}")

    msgs = [{"role": "system", "content": sys_prompt}] + user_messages
    
    from core import model_manager
    chosen, is_offline = model_manager.route_request(STATE["model"])
    if chosen == "auto":
        chosen = resolve_auto_model(last_user)
        is_offline = not model_manager.check_internet()
        if is_offline: chosen = "ollama"
    
    if chosen == "ollama" or is_offline:
        try:
            model = pick_ollama_model()
            if not model:
                yield NO_PROVIDER_MESSAGE
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
            chosen = "llama3-8b-8192"

    api_url = None
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    
    if chosen.startswith("gemini-"):
        # Gemini automatic quota & model fallback cascade
        gemini_candidates = [chosen]
        for m_cand in ["gemini-2.5-flash", "gemini-flash-latest"]:
            if m_cand not in gemini_candidates:
                gemini_candidates.append(m_cand)
                
        last_gemini_err = None
        for g_model in gemini_candidates:
            api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            g_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Authorization": f"Bearer {config.GEMINI_API_KEY}"
            }
            payload_dict = {
                "model": g_model,
                "messages": msgs,
                "max_tokens": 1024,
                "temperature": 0.7,
                "stream": True
            }
            try:
                req = urllib.request.Request(api_url, data=json.dumps(payload_dict).encode(), headers=g_headers, method="POST")
                with urllib.request.urlopen(req, timeout=35) as r:
                    got_any = False
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
                                    got_any = True
                                    yield token
                            except (ValueError, KeyError, IndexError, TypeError):
                                pass  # A malformed chunk in the stream is skipped.
                    if got_any:
                        return
            except Exception as e_gem:
                log(f"[GeminiStream] Model {g_model} failed: {e_gem}. Cascading to next candidate...")
                last_gemini_err = e_gem
                continue
        # If all Gemini candidates failed, mark provider and fall through
        e = last_gemini_err or RuntimeError("All Gemini candidates failed")
        mark_provider_failed("gemini")
        # Try Groq fallback
        best_groq = "qwen/qwen3.8-27b" if "qwen/qwen3.8-27b" in AVAILABLE_GROQ_MODELS else (AVAILABLE_GROQ_MODELS[0] if AVAILABLE_GROQ_MODELS else "llama-3.1-8b-instant")
        if getattr(config, "GROQ_API_KEY", "") and not getattr(config, "GROQ_API_KEY", "").startswith("PASTE_"):
            try:
                log(f"Falling back from Gemini to Groq model: {best_groq}")
                for token in ask_ai_stream(user_messages):
                    yield token
                return
            except Exception as e:
                log(f"the backup model failed too: {e}")
        yield f"I experienced a temporary interruption reaching the cloud models, {config.OWNER_TITLE}. Your system, memory, and desktop tools are fully operational. Please check your API quota or network connection."
        return

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
                    except (ValueError, KeyError, IndexError, TypeError):
                        pass  # A malformed chunk in the stream is skipped.
    except Exception as e:
        log(f"Cloud stream failed for {chosen}: {e}")
        provider_name = "gemini" if chosen.startswith("gemini") else "openai" if chosen.startswith("gpt") else "anthropic" if chosen.startswith("claude") else "groq"
        mark_provider_failed(provider_name)
        has_gemini = bool(getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"))
        has_openai = bool(getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"))
        fallback = "gemini-2.5-flash" if has_gemini and not chosen.startswith("gemini") else "gpt-4o-mini" if has_openai and not chosen.startswith("gpt") else "ollama"
        if fallback != chosen and not getattr(ask_ai_stream, "_fallback_active", False):
            ask_ai_stream._fallback_active = True
            log(f"Falling back from {chosen} to {fallback}...")
            STATE["model"] = fallback
            try:
                for token in ask_ai_stream(user_messages): yield token
            finally:
                ask_ai_stream._fallback_active = False
            return
        yield f"Unable to reach the active AI provider, {config.OWNER_TITLE}. Your local desktop environment, memory, and cyber tools are ready."
        return

def ask_ai(user_messages, force_search=False):
    """Returns the AI text reply. Routes based on active model and falls back to Ollama."""
    last_user = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
            
    sys_prompt = build_system_prompt(last_user)
            
    sys_prompt += _apply_mood(last_user)

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
        try:
            em = mailmod.summary_for_speech(limit=5)
            sys_prompt += f"\n\nCURRENT INBOX SUMMARY:\n{em}\n"
        except Exception as e:
            sys_prompt += f"\n\nCURRENT INBOX SUMMARY:\nCould not fetch mail: {e}\n"

    msgs = [{"role": "system", "content": sys_prompt}] + user_messages
    chosen = STATE["model"]

    # ── Auto Routing Logic ──
    if chosen == "auto":
        chosen = resolve_auto_model(last_user)
        
    # Now route based on chosen model name
    if chosen.startswith("gemini-"):
        try:
            return ask_gemini(msgs, model=chosen)
        except Exception as e:
            log(f"Gemini failed: {e}. Falling back to default Groq...")
            chosen = "llama3-8b-8192"
            
    if chosen.startswith("gpt-"):
        try:
            return ask_openai(msgs, model=chosen)
        except Exception as e:
            log(f"OpenAI failed: {e}. Falling back to default Groq...")
            chosen = "llama3-8b-8192"

    if chosen.startswith("claude-"):
        try:
            return ask_anthropic(msgs, model=chosen)
        except Exception as e:
            log(f"Anthropic failed: {e}. Falling back to default Groq...")
            chosen = "llama3-8b-8192"

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
            except Exception: body = ""
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
        
        if groq_err == "no API key set":
            raise RuntimeError(NO_PROVIDER_MESSAGE)
        raise RuntimeError(f"I could not reach an AI provider ({groq_err[:140]}). Check the connection and API key in Settings, then try again.")


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
    """Focus or restore native desktop KALKI window."""
    global _browser_opened_once
    if _focus_kalki_window():
        log("desktop wake restored the KALKI window")
    else:
        log("desktop wake received; KALKI window was not discoverable")
    return


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


_hw_cache = {"cpu": 0.0, "ram": 0.0, "disk": 0.0, "ts": 0.0}

def get_hardware_stats():
    now = time.time()
    # Try psutil first
    if psutil:
        try:
            if now - _hw_cache["ts"] > 0.9:
                _hw_cache["cpu"] = psutil.cpu_percent(interval=None)
                _hw_cache["ts"] = now
            return _hw_cache["cpu"], psutil.virtual_memory().percent, psutil.disk_usage(os.path.abspath(os.sep)).percent
        except Exception: pass
    
    # WMI Fallback
    if now - _hw_cache["ts"] < 2.5:
        return _hw_cache["cpu"], _hw_cache["ram"], _hw_cache["disk"]

    try:
        cpu = ram = disk = 0.0
        
        # CPU
        try:
            out = subprocess.check_output("wmic cpu get loadpercentage /Value", shell=True, stderr=subprocess.DEVNULL).decode()
            for line in out.splitlines():
                if "LoadPercentage=" in line:
                    cpu = float(line.split("=")[1].strip())
        except Exception: pass
        
        # RAM
        try:
            out = subprocess.check_output("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value", shell=True, stderr=subprocess.DEVNULL).decode()
            free = total = 0.0
            for line in out.splitlines():
                if "FreePhysicalMemory=" in line: free = float(line.split("=")[1].strip())
                if "TotalVisibleMemorySize=" in line: total = float(line.split("=")[1].strip())
            if total > 0: ram = ((total - free) / total) * 100
        except Exception: pass

        # Disk
        try:
            out = subprocess.check_output("wmic logicaldisk where \"DeviceID='C:'\" get size,freespace /Value", shell=True, stderr=subprocess.DEVNULL).decode()
            free = total = 0.0
            for line in out.splitlines():
                if "FreeSpace=" in line: free = float(line.split("=")[1].strip())
                if "Size=" in line: total = float(line.split("=")[1].strip())
            if total > 0: disk = ((total - free) / total) * 100
        except Exception: pass

        _hw_cache["cpu"], _hw_cache["ram"], _hw_cache["disk"], _hw_cache["ts"] = cpu, ram, disk, now
        return cpu, ram, disk
    except Exception:
        return _hw_cache["cpu"], _hw_cache["ram"], _hw_cache["disk"]



_STATUS_CACHE = {"mem_count": 0, "mem_at": 0.0, "hw": (0, 0, 0), "hw_at": 0.0}
_STATUS_CACHE_TTL = 5.0
_status_cache_lock = threading.Lock()


def cached_mem_count():
    """len(load_memory()) used to run on every /api/status hit, which meant
    reading and JSON-parsing the whole memory file ~2400 times an hour. The
    number does not need to be that fresh."""
    now = time.time()
    with _status_cache_lock:
        if now - _STATUS_CACHE["mem_at"] > _STATUS_CACHE_TTL:
            try:
                _STATUS_CACHE["mem_count"] = len(load_memory())
            except Exception:
                pass
            _STATUS_CACHE["mem_at"] = now
        return _STATUS_CACHE["mem_count"]


def cached_hardware_stats():
    """psutil sampling is also too expensive to run per request."""
    now = time.time()
    with _status_cache_lock:
        if now - _STATUS_CACHE["hw_at"] > _STATUS_CACHE_TTL:
            try:
                _STATUS_CACHE["hw"] = get_hardware_stats()
            except Exception:
                pass
            _STATUS_CACHE["hw_at"] = now
        return _STATUS_CACHE["hw"]

_RATE_LIMIT_STORE = {}
_RATE_LIMIT_LOCK = threading.Lock()

def _check_rate_limit(client_ip, path, max_requests=60, window_sec=60):
    now = time.time()
    parts = path.strip('/').split('/')
    endpoint = parts[1] if len(parts) > 1 else path
    key = (client_ip, endpoint)
    with _RATE_LIMIT_LOCK:
        history = _RATE_LIMIT_STORE.get(key, [])
        cutoff = now - window_sec
        history = [t for t in history if t > cutoff]
        if len(history) >= max_requests:
            _RATE_LIMIT_STORE[key] = history
            return False
        history.append(now)
        _RATE_LIMIT_STORE[key] = history
        return True

def _update_available():
    try:
        import core.updater as updater
        return updater.STATE_UPDATE_AVAILABLE.get("version") or None
    except Exception:
        return None


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
    MAX_BODY = 32 * 1024 * 1024   # 32 MB cap (images come through here)
    PUBLIC_GET_PATHS = {
        "/", "/index.html", "/manifest.json", "/service-worker.js", "/api/health", "/favicon.ico",
        "/pet", "/pet_overlay"
    }

    def _is_public_path(self, path):
        return path in self.PUBLIC_GET_PATHS or path.startswith("/assets/")

    def _authorized(self):
        candidate = self.headers.get(runtime_security.TOKEN_HEADER, "")
        if not candidate:
            cookie = self.headers.get("Cookie", "")
            for item in cookie.split(";"):
                name, sep, value = item.strip().partition("=")
                if sep and name == runtime_security.TOKEN_COOKIE:
                    candidate = value
                    break
        return runtime_security.token_matches(candidate)

    def _require_auth(self, path):
        if self._is_public_path(path):
            return True
        client_ip = self.client_address[0] if getattr(self, "client_address", None) else "127.0.0.1"
        limit = 15 if any(p in path for p in ["/auth", "/system", "/cyber"]) else 120
        if not _check_rate_limit(client_ip, path, max_requests=limit, window_sec=60):
            self._json({"ok": False, "error": "Rate limit exceeded. Please wait before retrying."}, status=429)
            return False
        if self._authorized():
            return True
        self._json({"ok": False, "error": "authentication required"}, status=401)
        return False

    def _own_authorities(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}

    def _host_allowed(self):
        """Blocks DNS rebinding: a foreign name resolving to 127.0.0.1 is refused."""
        return (self.headers.get("Host") or "").strip().lower() in self._own_authorities()

    def _origin_allowed(self):
        """No Origin means not a cross-site browser request (listener, curl).
        Anything else must be exactly this app. "null" and other ports are refused."""
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin.strip().lower() in {f"http://{a}" for a in self._own_authorities()}

    def _request_allowed(self):
        if self._host_allowed() and self._origin_allowed():
            return True
        self._json({"ok": False, "error": "forbidden origin"}, status=403)
        return False

    # CORS: echo the Origin only when it is this app. Never a wildcard.
    def _cors(self):
        origin = self.headers.get("Origin")
        if origin is not None and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-KALKI-Token")

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

    def _public_html(self, html):
        body = html.encode("utf-8") if isinstance(html, str) else html
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", f"{runtime_security.TOKEN_COOKIE}={runtime_security.get_api_token()}; HttpOnly; SameSite=Strict; Path=/")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    # Extension -> Content-Type for the frontend bundle. Anything not listed
    # is refused rather than served as octet-stream: app/ui/ holds only these
    # file types, so an unexpected extension means something is wrong.
    UI_CONTENT_TYPES = {
        ".html":  "text/html; charset=utf-8",
        ".js":    "application/javascript; charset=utf-8",
        ".mjs":   "application/javascript; charset=utf-8",
        ".css":   "text/css; charset=utf-8",
        ".json":  "application/json; charset=utf-8",
        ".svg":   "image/svg+xml",
        ".png":   "image/png",
        ".webp":  "image/webp",
        ".woff2": "font/woff2",
        ".woff":  "font/woff",
        ".ico":   "image/x-icon",
        ".map":   "application/json; charset=utf-8",
        ".md":    "text/markdown; charset=utf-8",
    }

    def _serve_ui_asset(self, path):
        """Serve one file from app/ui/ with a correct MIME type.

        Two things this must not do: escape the ui directory, and expose the
        rest of the filesystem. The realpath prefix check below is the guard;
        do not replace it with a string test on `path`, which %2e%2e and
        symlinks can both defeat.
        """
        ui_root = os.path.realpath(os.path.join(APP_ROOT, "ui"))
        rel = urllib.parse.unquote(path[len("/ui/"):])
        target = os.path.realpath(os.path.join(ui_root, rel))

        if target != ui_root and not target.startswith(ui_root + os.sep):
            self._text("Not found", status=404)
            return
        if not os.path.isfile(target):
            self._text("Not found", status=404)
            return

        ctype = self.UI_CONTENT_TYPES.get(os.path.splitext(target)[1].lower())
        if not ctype:
            self._text("Not found", status=404)
            return

        try:
            with open(target, "rb") as f:
                content = f.read()
        except OSError:
            self._text("Not found", status=404)
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        # The service worker handles freshness for /ui/*; tell the HTTP cache
        # to revalidate so a reinstall never paints a previous build.
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self._cors()
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        if not self._request_allowed():
            return
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
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {"__not_object__": True}

    def _safe_call(self, fn):
        """Wrap any handler. One bad request will NOT crash the server."""
        try:
            fn()
        except Exception as e:
            # WinError 10053 = browser closed the connection mid-poll (normal, not an error)
            if "10053" in str(e) or "10054" in str(e):
                return
            runtime_log.log_event(LOG_PATH, "error", "handler_error", path=self.path.split("?")[0],
                                  detail=str(e), trace=traceback.format_exc(limit=8))
            try:
                self._json({"ok": False, "error": str(e)}, status=500)
            except Exception:
                pass

    # ── GET ─────────────────────────────────────────
    def do_GET(self):
        if self._request_allowed():
            self._safe_call(self._do_get_inner)

    def _do_get_inner(self):
        # removed local import
        path = urllib.parse.urlparse(self.path).path
        if not self._require_auth(path):
            return

        route = (routes_pet.GET_ROUTES.get(path) or routes_settings.GET_ROUTES.get(path)
                 or routes_calendar.GET_ROUTES.get(path) or briefing.GET_ROUTES.get(path)
                 or focus.GET_ROUTES.get(path) or routes_screen_time.GET_ROUTES.get(path))
        if route:
            payload, status = route({})
            self._json(payload, status=status)
            return

        if path in ("/pet", "/pet_overlay"):
            pet_html_path = os.path.join(APP_ROOT, "ui", "pet_overlay.html")
            if os.path.exists(pet_html_path):
                with open(pet_html_path, "rb") as f:
                    content_bytes = f.read()
                self._public_html(content_bytes)
                return

        if path == "/api/skills/list":
            self._do_post_inner()
            return

        if path == "/api/health":
            self._json({"ok": True, "ts": time.time()}); return

        if path == "/" or path == "/index.html":
            try:
                crash_log_path = os.path.join(DATA_DIR, "crash.log")
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
                    self._public_html(html)
                    return
                
                lock_path = os.path.join(DATA_DIR, "updating.lock")
                if os.path.exists(lock_path):
                    if time.time() - os.path.getmtime(lock_path) < 300:
                        html = """<!DOCTYPE html><html><head><title>KALKI Updating</title>
                        <meta http-equiv="refresh" content="3">
                        <style>body { background: #111; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }</style>
                        </head><body><h2>KALKI is updating... Please wait.</h2></body></html>"""
                        self._public_html(html)
                        return
                    else:
                        try: os.remove(lock_path)
                        except Exception: pass

                with open(os.path.join(APP_ROOT, "index.html"), "rb") as f:
                    html = f.read()
                self._public_html(html)
            except Exception as e:
                self._text(f"index.html missing: {e}", status=500)
            return
            
        if path == "/manifest.json":
            try:
                with open(os.path.join(APP_ROOT, "manifest.json"), "rb") as f:
                    self._text(f.read(), ctype="application/manifest+json; charset=utf-8")
            except Exception:
                self.send_response(404); self.end_headers()
            return
            
        if path == "/service-worker.js":
            try:
                with open(os.path.join(APP_ROOT, "service-worker.js"), "rb") as f:
                    self._text(f.read(), ctype="application/javascript; charset=utf-8")
            except Exception:
                self.send_response(404); self.end_headers()
            return

        if path == "/api/support":
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

        if path == "/api/github/status":
            try:
                result = github_mod.get_notifications(limit=5)
                self._json({
                    "ok": bool(result.get("ok")),
                    "configured": bool(result.get("configured")),
                    "count": result.get("count", 0),
                    "notifications": result.get("notifications", []),
                    "pollInterval": result.get("pollInterval", 60),
                    "notModified": result.get("notModified", False),
                    "error": result.get("error", ""),
                })
            except Exception as e:
                self._json({"ok": False, "configured": False, "error": str(e)})
            return

        if path == "/api/dashboard":
            try:
                import core.productivity
                with core.productivity._lock:
                    prod_data = core.productivity._load_data()
                
                try:
                    tracker_status = core.productivity.tracking_status()
                except Exception:
                    tracker_status = {"available": False, "active": False}
                dashboard_data = {
                    "productivity": prod_data,
                    "screenTime": tracker_status,
                    "uptimeSec": int(time.time() - STATE["started_at"]),
                    "state": STATE.get("workflow", STATE.get("current_routine", "idle")),
                    "focus": _focus_payload(),
                    "memCount": cached_mem_count()
                }
                self._json({"ok": True, "data": dashboard_data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
            return

        if path == "/api/clipboard_response":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            phrase = (qs.get("phrase", [""])[0] or "").lower()
            pending = STATE.pop("clipboard_prompt_pending", None)
            
            if pending:
                if any(k in phrase for k in ["yes", "sure", "go ahead", "yeah", "please", "do it"]):
                    speak("Analyzing...")
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


        if path == "/api/antivirus/status":
            import antivirus
            self._json(antivirus.get_antivirus_status())
            return

        if path == "/api/oversight/status":
            self._json({
                "ok": True,
                "alerts": oversight.recent_alerts(),
                "watchedSites": watchdog.list_sites(),
                "thresholds": {
                    "cpu": getattr(config, "CPU_HIGH_PCT", 85),
                    "ram": getattr(config, "RAM_HIGH_PCT", 85),
                    "disk_gb": getattr(config, "DISK_LOW_GB", 5),
                    "battery_low": getattr(config, "BATTERY_LOW_PCT", 20)
                }
            })
            return

        if path == "/api/system/telemetry":
            try:
                cpu_pct = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage(os.path.abspath(os.sep))
                net = psutil.net_io_counters()
                self._json({
                    "ok": True,
                    "cpu_percent": cpu_pct,
                    "memory": {
                        "total_mb": round(mem.total / (1024*1024)),
                        "used_mb": round(mem.used / (1024*1024)),
                        "percent": mem.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024*1024*1024), 1),
                        "used_gb": round(disk.used / (1024*1024*1024), 1),
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent": net.bytes_sent,
                        "bytes_recv": net.bytes_recv
                    },
                    "os": sys.platform,
                    "hostname": os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "Desktop"))
                })
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/processes":
            try:
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                    try:
                        info = p.info
                        mem_mb = round(info['memory_info'].rss / (1024*1024), 1) if info.get('memory_info') else 0
                        procs.append({
                            "pid": info['pid'],
                            "name": info['name'],
                            "mem_mb": mem_mb,
                            "cpu": info.get('cpu_percent', 0.0)
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                procs.sort(key=lambda x: x["mem_mb"], reverse=True)
                self._json({"ok": True, "processes": procs[:60]})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/status":
            # Restored full payload. Phase 4 replaced this with a six-field
            # stub, which silently broke presence, the context panel, voice
            # exchange sync, wake events and every status chip.
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            hidden = qs.get("hidden", ["0"])[0] == "1"
            with _state_lock:
                STATE["frontend_hidden"] = hidden
                STATE["ui_last_ping"] = time.time()
                wake_req = STATE.get("wake_pending", False)
                STATE["wake_pending"] = False

            ollama_ok = cached_ollama_model() is not None
            now = datetime.now()
            cpu, ram, disk = cached_hardware_stats()
            batt_pct = None
            batt_plugged = None
            if psutil:
                try:
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
            if "client=listener" in self.path:
                STATE["listener_last_seen"] = time.time()
            pending_count = approvals.count()

            self._json({
                "ok": True,
                "online": True,
                "model": STATE["model"],
                "clipboardPromptPending": "clipboard_prompt_pending" in STATE,
                "groqConfigured": bool(config.GROQ_API_KEY and config.GROQ_API_KEY != "PASTE_YOUR_GROQ_KEY_HERE"),
                "ollamaOnline": ollama_ok,
                "speaking": STATE["speaking"],
                "ttsProvider": _tts_provider(),
                "ttsVoice": getattr(config, "TTS_VOICE", "") or "en-US-AndrewMultilingualNeural",
                "ttsLastProvider": STATE.get("last_tts_provider", ""),
                "ttsLastError": STATE.get("last_tts_error", ""),
                "ttsLastLatencyMs": STATE.get("last_tts_latency_ms", 0),
                "ttsProbeError": PYGAME_PROBE_ERROR,
                "memCount": cached_mem_count(),
                "time": now.strftime("%I:%M %p"),
                "timeFull": now.strftime("%H:%M:%S"),
                "date": now.strftime("%A, %B %d, %Y"),
                "uptimeSec": int(time.time() - STATE["started_at"]),
                "cpu": cpu, "ram": ram, "disk": disk,
                "batteryPct": batt_pct, "batteryPlugged": batt_plugged,
                "owner": config.OWNER_NAME, "title": config.OWNER_TITLE,
                "city": config.OWNER_CITY,
                "hardware": getattr(config, "HARDWARE_PROFILE", {}),
                "wakeRequested": wake_req,
                "conversationSeq": STATE.get("conversation_seq", 0),
                "recentExchange": STATE.get("recent_exchange"),
                "listenerPaused": STATE.get("listener_paused", False),
                "listenerMicMuted": STATE.get("listener_mic_muted"),
                "listenerState": STATE.get("listener_state", "idle"),
                "listenerSeenAt": STATE.get("listener_seen_at", 0),
                "micLevel": STATE.get("mic_level", 0.0),
                "listenerCapabilityNotice": os.environ.get("KALKI_LISTENER_NOTICE", ""),
                "platform": sys.platform,
                "cpuAlertsEnabled": getattr(config, "CPU_ALERTS_ENABLED", False),
                "gcalConfigured": gcal.is_configured(),
                "spotifyConfigured": spotify_mod.is_configured(),
                "githubConfigured": github_mod.is_configured(),
                "todayEvents": STATE.get("cached_today_events", []),
                "unreadImportant": STATE.get("cached_unread_count", 0),
                "nowPlaying": STATE.get("cached_now_playing"),
                "focus": _focus_payload(),
                "pendingApprovals": pending_count,
                "hostExecution": bool(getattr(config, "ALLOW_HOST_CODE_EXECUTION", False)),
                "storeError": STORE_ERROR,
                "listenerOnline": time.time() - STATE.get("listener_last_seen", 0) < 30,
                "mailConfigured": bool(getattr(config, "EMAIL_ADDRESS", "") and getattr(config, "EMAIL_APP_PASSWORD", "")),
                "memorySearchMode": "semantic" if semantic_memory.embeddings_configured() else "keyword",
                "updateAvailable": _update_available(),
                "updateProgress": up_prog,
                "terminalLogs": _get_recent_logs(),
            })
            return

        if path == "/api/models":
            models = ["auto"]
            if getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"):
                models += ["gemini-2.5-flash", "gemini-flash-latest"]
            if getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"):
                models += ["gpt-4o-mini", "gpt-4o"]
            if getattr(config, "ANTHROPIC_API_KEY", "") and not getattr(config, "ANTHROPIC_API_KEY", "").startswith("PASTE_"):
                models += ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
            if getattr(config, "GROQ_API_KEY", "") and not getattr(config, "GROQ_API_KEY", "").startswith("PASTE_"):
                models += AVAILABLE_GROQ_MODELS
            self._json({"models": models})
            return

        if path == "/api/settings/export":
            content = routes_settings.export_text()  # Never includes a secret.
            if content is not None:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Disposition', 'attachment; filename="kalki_config_backup.json"')
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self._json({"ok": False, "error": "No config file exists."})
            return

        if path == "/api/history":
            # The rolling context window the model actually sees. The frontend
            # owns conversation organisation in IndexedDB; this lets it
            # reconcile voice turns recorded while the window was closed.
            hist = load_history()
            self._json({
                "ok": True,
                "history": hist,
                "maxHistory": getattr(config, "MAX_HISTORY", 20),
            })
            return

        if path == "/api/memories":
            self._json({"memories": load_memory()})
            return

        if path == "/api/memory/list":
            payload, status = routes_memory.list_memories({})
            self._json(payload, status=status)
            return

        if path == "/api/media/now" or path == "/api/media/now_json":
            try:
                self._json(media_mod.now_playing_json())
            except Exception as e:
                self._json({"ok": False, "status": "Error", "error": str(e), "title": "Nothing playing", "artist": ""}, status=500)
            return

        if path == "/favicon.ico":
            path = "/assets/kalki_icon.ico"

        # ── Frontend application bundle ────────────────────────────
        # The new multi-file frontend lives in app/ui/. /assets/ cannot serve
        # it: that branch types every file as png/ico/octet-stream, and a
        # browser refuses <script type="module"> served as octet-stream.
        # This route sits after _require_auth, so it inherits the existing
        # token model unchanged — index.html is public and sets the session
        # cookie, and module loads from within the page carry it.
        if path.startswith("/ui/"):
            self._serve_ui_asset(path)
            return

        if path.startswith("/assets/"):
            try:
                local_path = os.path.join(APP_ROOT, path.lstrip("/"))
                if not os.path.exists(local_path):
                    local_path = os.path.join(BASE_DIR, path.lstrip("/"))
                with open(local_path, "rb") as f:
                    content = f.read()
                ctype = "image/png" if local_path.endswith(".png") else "image/x-icon" if local_path.endswith(".ico") else "application/octet-stream"
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
        if self._request_allowed():
            self._safe_call(self._do_post_inner)

    def _handle_wifi(self, action, body):
        ssid = str(body.get("ssid") or "").strip()
        if action == "overview":
            self._json(wifi_security.overview())
        elif action == "nearby":
            self._json(wifi_security.scan_nearby())
        elif action == "reveal":
            if not ask_native_permission(f"show the saved password for Wi-Fi network '{ssid}'", always=True):
                self._json({"ok": False, "kind": "denied", "error": "You declined the request."}, status=403)
                return
            result = wifi_security.reveal_password(ssid)
            if result.get("ok"):
                add_activity(f"Showed the Wi-Fi password for {ssid}", "user", kind="security")
            self._json(result)
        elif action == "audit":
            if not ask_native_permission("check the strength of every saved Wi-Fi password", always=True):
                self._json({"ok": False, "kind": "denied", "error": "You declined the request."}, status=403)
                return
            result = wifi_security.audit_passwords()
            if result.get("ok"):
                add_activity("Checked saved Wi-Fi password strength", "user", kind="security")
            self._json(result)
        elif action == "forget":
            if not ask_native_permission(f"forget Wi-Fi network '{ssid}'. Reconnecting will need its password", always=True):
                self._json({"ok": False, "kind": "denied", "error": "You declined the request."}, status=403)
                return
            result = wifi_security.forget_network(ssid)
            if result.get("ok"):
                add_activity(f"Forgot Wi-Fi network {ssid}", "user", kind="security")
            self._json(result)
        elif action == "autoconnect":
            enabled = bool(body.get("enabled"))
            result = wifi_security.set_auto_connect(ssid, enabled)
            if result.get("ok"):
                add_activity(result["message"], "user", kind="security")
            self._json(result)
        else:
            self._json({"ok": False, "error": "unknown Wi-Fi action"}, status=404)

    def _handle_update_install(self):
        import core.updater as updater
        available = updater.STATE_UPDATE_AVAILABLE
        if not available.get("version"):
            self._json({"ok": False, "error": "No update is available."}, status=400)
            return
        if not ask_native_permission(f"download and install KALKI {available['version']}", always=True):
            self._json({"ok": False, "kind": "denied", "error": "You declined the update."}, status=403)
            return
        threading.Thread(target=updater.install_available_update, args=(APP_ROOT,), daemon=True).start()
        self._json({"ok": True})

    def _do_post_inner(self):
        tool_policy.reset()
        path = urllib.parse.urlparse(self.path).path

        if not self._authorized():
            self._json({"ok": False, "error": "authentication required"}, status=401)
            return

        body = self._read_json()
        if body.get("__not_object__"):
            self._json({"ok": False, "error": "request body must be a JSON object"}, status=400)
            return

        route = (routes_productivity.POST_ROUTES.get(path) or routes_memory.POST_ROUTES.get(path)
                 or routes_threads.POST_ROUTES.get(path) or routes_pet.POST_ROUTES.get(path)
                 or approvals.POST_ROUTES.get(path) or activity.POST_ROUTES.get(path)
                 or routes_settings.POST_ROUTES.get(path) or routes_calendar.POST_ROUTES.get(path)
                 or routes_setup.POST_ROUTES.get(path) or routes_backup.POST_ROUTES.get(path)
                 or focus.POST_ROUTES.get(path) or routes_screen_time.POST_ROUTES.get(path)
                 or location_provider.POST_ROUTES.get(path))
        if route:
            payload, status = route(body)
            self._json(payload, status=status)
            return
        if body.get("__too_large__"):
            self._json({"ok": False, "error": "request too large"}, status=413)
            return

        if path == "/api/listener_state":
            STATE["listener_mic_muted"] = bool(body.get("muted"))
            self._json({"ok": True})
            return

        
        if path == "/api/skills/list":
            skills = [
                {"id": "calendar", "name": "Google Calendar", "enabled": True, "needs": ["Google credentials"]},
                {"id": "spotify", "name": "Spotify", "enabled": True, "needs": ["Spotify credentials"]},
                {"id": "github", "name": "GitHub", "enabled": True, "needs": ["GitHub token"]},
                {"id": "search", "name": "Web Search", "enabled": True, "needs": []},
            ]
            self._json({"ok": True, "skills": skills})
            return

        if path == "/api/skills/toggle":
            skill_id = body.get("id")
            enabled = bool(body.get("enabled"))
            setattr(config, f"SKILL_{skill_id.upper()}_ENABLED", enabled)
            self._json({"ok": True})
            return
            

        if path == "/api/recovery/clear":
            try:
                os.remove(os.path.join(DATA_DIR, "crash.log"))
            except FileNotFoundError:
                pass  # Already gone.
            self._json({"ok": True})
            return

        if path == "/api/cloud_restore":
            try:
                from core import cloud_sync
                uid = getattr(config, "OWNER_NAME", "default_user")

                passphrase = body.get("passphrase")
                if not passphrase:
                    passphrase = getattr(config, "CLOUD_SYNC_PASSPHRASE", "")
                
                m1 = cloud_sync.restore_memory_from_cloud(uid, os.path.join(DATA_DIR, "memory.json"), passphrase)
                m2 = cloud_sync.restore_history_from_cloud(uid, os.path.join(DATA_DIR, "history.json"), passphrase)
                
                restored = (["memory"] if m1 else []) + (["history"] if m2 else [])
                if restored:
                    db.reimport_legacy(restored, DATA_DIR)
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

        if path == "/api/tts/test":
            phrase = (body.get("text") or "").strip() or f"Voice check complete, {getattr(config, 'OWNER_TITLE', 'Sir')}."
            ok = speak(phrase)
            self._json({
                "ok": bool(ok),
                "provider": _tts_provider(),
                "lastProvider": STATE.get("last_tts_provider", ""),
                "lastError": STATE.get("last_tts_error", ""),
                "probeError": PYGAME_PROBE_ERROR,
            })
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
                        convo = _shared_context() + [{"role": "user", "content": cmd}]
                        with _ReplyInProgress():
                            reply = ask_ai(convo)
                    except Exception as e:
                        reply = f"My link hiccuped, Sir — say that again? ({str(e)[:80]})"
                
                # Act on any [TASK: ...] style text, then remove it from what gets spoken.
                reply = _apply_reply_actions(reply)

                # Record exchange so UI can render it
                reply = maybe_add_joke_offer(cmd, reply)
                _share_exchange(cmd, reply, "voice")
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


        if path == "/api/antivirus/scan/file":
            import antivirus
            f_path = body.get("path", "")
            res = antivirus.scan_file(f_path)
            self._json(res)
            return

        if path == "/api/antivirus/scan/quick":
            import antivirus
            res = antivirus.scan_quick()
            self._json(res)
            return

        if path == "/api/antivirus/scan/processes":
            import antivirus
            res = antivirus.scan_processes()
            self._json(res)
            return

        if path == "/api/antivirus/scan/url":
            import antivirus
            url = body.get("url", "")
            res = antivirus.scan_url(url)
            self._json(res)
            return

        if path == "/api/antivirus/quarantine":
            import antivirus
            f_path = body.get("path", "")
            threat = body.get("threat", "Generic.Threat")
            res = antivirus.quarantine_file(f_path, threat)
            self._json(res)
            return

        if path == "/api/antivirus/threats/resolve":
            import antivirus
            t_id = body.get("id", "")
            action = body.get("action", "delete")
            res = antivirus.resolve_quarantine(t_id, action)
            self._json(res)
            return

        if path == "/api/antivirus/settings":
            import antivirus
            updates = body.get("updates", {})
            res = antivirus.update_shield_settings(updates)
            self._json({"ok": True, "shields": res})
            return

        if path == "/api/antivirus/clipboard":
            import antivirus
            text = body.get("text", "")
            res = antivirus.inspect_clipboard(text)
            self._json({"ok": True, "result": res})
            return

        if path == "/api/oversight/watchdog/add":
            url = body.get("url", "")
            label = body.get("label", url)
            watchdog.add_site(url, label)
            self._json({"ok": True})
            return

        if path == "/api/oversight/watchdog/remove":
            url = body.get("url", "")
            watchdog.remove_site(url)
            self._json({"ok": True})
            return

        if path == "/api/oversight/watchdog/check":
            url = body.get("url", "")
            res = watchdog.check_site(url)
            self._json({"ok": True, "result": res})
            return

        if path == "/api/chat":
            messages = body.get("messages") or []
            is_voice = (body.get("source") == "voice")
            # Other sources have no window keeping their conversation, so the server does.
            shared_source = body.get("source") if body.get("source") in ("voice", "telegram") else None
            if body.get("threadId"):
                threads.set_active(str(body["threadId"]))
            stream_req = body.get("stream", False)
            client_speech = bool(body.get("clientSpeech"))
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
                if shared_source:
                    _share_exchange(user_text, reply, shared_source)

            handled, local_reply = handle_local(user_text)
            if handled:
                local_reply = maybe_add_joke_offer(user_text, local_reply)
                if not client_speech:
                    speak(local_reply)
                append_history(user_text, local_reply)
                _record_exchange(local_reply)
                _remember_from_turn(user_text, local_reply)
                if stream_req:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(f"data: {json.dumps({'token': local_reply, 'done': True})}\n\n".encode())
                    self.wfile.flush()
                else:
                    self._json({"reply": local_reply, "source": "local"})
                return

            if stream_req:
                start_time = time.time()
                _take_tool_cards()  # Threads are reused, so drop anything left from an earlier request.
                generator = _counting_reply(ask_ai_stream(messages))
                try:
                    first_token = next(generator)
                except StopIteration:
                    first_token = ""
                except Exception as e:
                    self._json({"ok": False, "error": str(e)})
                    return
                    
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'close')
                self.end_headers()
                
                full_reply = []
                _send_tool_cards(self)
                if first_token:
                    full_reply.append(first_token)
                    self.wfile.write(f"data: {json.dumps({'token': first_token})}\n\n".encode())
                    self.wfile.flush()
                for token in generator:
                    _send_tool_cards(self)
                    full_reply.append(token)
                    self.wfile.write(f"data: {json.dumps({'token': token})}\n\n".encode())
                    self.wfile.flush()
                _send_tool_cards(self)
                
                reply_str = "".join(full_reply)
                spoken_reply = _apply_reply_actions(reply_str)
                if not client_speech:
                    speak(extract_conversational_lead(spoken_reply or reply_str))
                append_history(user_text, spoken_reply or reply_str)
                _record_exchange(spoken_reply or reply_str)
                _remember_from_turn(user_text, reply_str)
                
                # Track usage metrics
                latency = (time.time() - start_time) * 1000
                try:
                    from core import model_manager
                    model_manager.track_usage(STATE["model"], len(user_text)//4, len(reply_str)//4, latency)
                except Exception as e:
                    log(f"usage tracking failed: {e}")
                
                self.wfile.write(f"data: {json.dumps({'done': True, 'model': STATE['model']})}\n\n".encode())
                self.wfile.flush()
                return
            else:
                start_time = time.time()
                try:
                    # Prepend recent conversation so KALKI remembers context.
                    convo = (_shared_context() + messages) if shared_source else messages
                    with _ReplyInProgress():
                        reply = ask_ai(convo)
                except Exception as e:
                    self._json({"ok": False, "error": str(e)})
                    return
                
                reply = maybe_add_joke_offer(user_text, reply)
                reply = _apply_reply_actions(reply)
                if not client_speech:
                    speak(reply)
                append_history(user_text, reply)
                _record_exchange(reply)
                _remember_from_turn(user_text, reply)
                
                # Track usage metrics
                latency = (time.time() - start_time) * 1000
                try:
                    from core import model_manager
                    model_manager.track_usage(STATE["model"], len(user_text)//4, len(reply)//4, latency)
                except Exception as e:
                    log(f"usage tracking failed: {e}")
                
                self._json({"reply": reply, "source": "ai", "model": STATE["model"]})
                return

        if path == "/api/report":
            response = str(body.get("response") or "").strip()
            reason = str(body.get("reason") or "other").strip().lower()
            details = str(body.get("details") or "").strip()
            prompt = str(body.get("prompt") or "").strip()
            allowed_reasons = {"harmful", "hateful", "sexual", "privacy", "misleading", "other"}
            if not response:
                self._json({"ok": False, "error": "response is required"}, status=400)
                return
            if reason not in allowed_reasons:
                self._json({"ok": False, "error": "invalid report reason"}, status=400)
                return
            report = {
                "id": f"report-{int(time.time() * 1000)}",
                "createdAt": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
                "reason": reason,
                "details": details[:1200],
                "prompt": prompt[:4000],
                "response": response[:12000],
                "model": STATE.get("model", "auto"),
            }
            try:
                with open(REPORTS_PATH, "a", encoding="utf-8") as report_file:
                    report_file.write(json.dumps(report, ensure_ascii=False) + "\n")
                log(f"AI response report saved: {report['id']} ({reason})")
                self._json({"ok": True, "reportId": report["id"]})
            except Exception as exc:
                self._json({"ok": False, "error": f"could not save report: {exc}"}, status=500)
            return

        # ── Sovereign Desktop System Operations ───────────
        if path == "/api/system/exec":
            if not getattr(config, "ALLOW_HOST_CODE_EXECUTION", False):
                self._json({
                    "ok": False,
                    "error": "Host command execution is disabled by policy. Enable ALLOW_HOST_CODE_EXECUTION in settings to permit shell execution."
                }, status=403)
                return
            cmd = (body.get("cmd") or "").strip()
            cwd = body.get("cwd") or WORKSPACE_DIR
            if not cmd:
                self._json({"ok": False, "error": "command required"}, status=400)
                return
            lower_cmd = cmd.lower()
            dangerous_patterns = [
                "format ", "del /s", "del /f /s", "rmdir /s /q", "rd /s /q",
                "rm -rf /", "mkfs", "diskpart", ":(){ :|:& };:", "powershell -enc"
            ]
            if any(p in lower_cmd for p in dangerous_patterns):
                if not body.get("confirmed"):
                    self._json({
                        "ok": False,
                        "error": "Destructive system command blocked by safety policy. Confirmation required."
                    }, status=400)
                    return
            try:
                t0 = time.time()
                safe_cwd = cwd if os.path.exists(cwd) else WORKSPACE_DIR
                res = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=safe_cwd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                dur = round((time.time() - t0) * 1000)
                self._json({
                    "ok": True,
                    "exit_code": res.returncode,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "duration_ms": dur
                })
            except subprocess.TimeoutExpired:
                self._json({"ok": False, "error": "Command timed out after 30 seconds."}, status=408)
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/files/list":
            req_path = body.get("path") or WORKSPACE_DIR
            safe_target, err = _validate_safe_path(req_path)
            if err:
                self._json({"ok": False, "error": err}, status=403)
                return
            if not os.path.isdir(safe_target):
                self._json({"ok": False, "error": f"Directory not found: {safe_target}"}, status=404)
                return
            try:
                items = []
                for entry in os.scandir(safe_target):
                    try:
                        stat = entry.stat()
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": entry.is_dir(),
                            "size": stat.st_size if not entry.is_dir() else 0,
                            "modified": stat.st_mtime
                        })
                    except OSError:
                        pass  # A file that vanished or can't be read is left out of the list.
                items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
                self._json({"ok": True, "path": safe_target, "items": items})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/files/read":
            req_path = (body.get("path") or "").strip()
            safe_target, err = _validate_safe_path(req_path)
            if err:
                self._json({"ok": False, "error": err}, status=403)
                return
            if not os.path.isfile(safe_target):
                self._json({"ok": False, "error": f"File not found: {req_path}"}, status=404)
                return
            try:
                with open(safe_target, "r", encoding="utf-8", errors="replace") as f:
                    file_content = f.read()
                self._json({"ok": True, "path": safe_target, "content": file_content})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/files/write":
            req_path = (body.get("path") or "").strip()
            file_content = body.get("content")
            if not req_path or file_content is None:
                self._json({"ok": False, "error": "path and content required"}, status=400)
                return
            safe_target, err = _validate_safe_path(req_path, write=True)
            if err:
                self._json({"ok": False, "error": err}, status=403)
                return
            try:
                os.makedirs(os.path.dirname(safe_target), exist_ok=True)
                with open(safe_target, "w", encoding="utf-8") as f:
                    f.write(file_content)
                self._json({"ok": True, "path": safe_target, "bytes": len(file_content)})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/files/reveal":
            req_path = (body.get("path") or "").strip()
            safe_target, err = _validate_safe_path(req_path)
            if err:
                self._json({"ok": False, "error": err}, status=403)
                return
            if not os.path.exists(safe_target):
                self._json({"ok": False, "error": "Path not found"}, status=404)
                return
            try:
                if sys.platform == "win32":
                    _reveal_in_explorer(safe_target)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", safe_target])
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(safe_target)])
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/system/process/kill":
            pid = body.get("pid")
            confirmed = body.get("confirmed", False)
            if not pid:
                self._json({"ok": False, "error": "pid required"}, status=400)
                return
            try:
                target_pid = int(pid)
                if target_pid <= 4 or target_pid == os.getpid():
                    self._json({"ok": False, "error": "Cannot terminate critical system process or self."}, status=403)
                    return
                proc = psutil.Process(target_pid)
                proc_name = proc.name().lower()
                protected_names = {
                    "csrss.exe", "lsass.exe", "services.exe", "smss.exe", "wininit.exe",
                    "explorer.exe", "msmpeng.exe", "securityhealthservice.exe", "antigravity.exe"
                }
                if proc_name in protected_names:
                    self._json({"ok": False, "error": f"Process '{proc_name}' is protected and cannot be terminated."}, status=403)
                    return
                if not confirmed:
                    self._json({
                        "ok": False,
                        "requires_confirmation": True,
                        "prompt": f"Terminate process '{proc_name}' (PID {target_pid})?"
                    }, status=200)
                    return
                proc.kill()
                self._json({"ok": True, "message": f"Killed process {target_pid} ({proc_name})"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        if path.startswith("/api/wifi/"):
            self._handle_wifi(path.rsplit("/", 1)[-1], body)
            return

        if path == "/api/update/install":
            self._handle_update_install()
            return

        if path == "/api/auth/logout":
            runtime_security.rotate_auth_token()
            self._json({"ok": True, "message": "Logged out and token rotated."})
            return

        if path == "/api/command":
            cmd = (body.get("cmd") or "").strip()
            handled, reply = handle_local(cmd)
            if handled:
                reply = maybe_add_joke_offer(cmd, reply)
                speak(reply)
            _remember_from_turn(cmd, reply)
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
                self._json({"ok": True, "secretStatus": _settings_status(SECRET_SETTING_KEYS)})
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

        if path == "/api/screen/capture":
            try:
                img_b64 = vision.screenshot_b64()
                if img_b64:
                    self._json({"ok": True, "image": f"data:image/jpeg;base64,{img_b64}"})
                else:
                    self._json({"ok": False, "error": "Screen capture returned no image"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

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
        # ── Listener pause/resume ──────────────────────
        if path == "/api/listener/pause":
            STATE["listener_paused"] = True
            self._json({"ok": True, "paused": True}); return
        if path == "/api/listener/resume":
            STATE["listener_paused"] = False
            self._json({"ok": True, "paused": False}); return

        # ── Calendar ───────────────────────────────────
        # ── Spotify ────────────────────────────────────
        if path == "/api/spotify/play":
            self._json({"reply": spotify_mod.play(body.get("query"))}); return
        if path == "/api/spotify/pause":
            self._json({"reply": spotify_mod.pause()}); return
        if path == "/api/spotify/next":
            self._json({"reply": spotify_mod.next_track()}); return
        if path == "/api/spotify/now":
            self._json({"reply": spotify_mod.now_playing()}); return

        if path == "/api/media/play":
            self._json({"reply": media_mod.play()}); return
        if path == "/api/media/pause":
            self._json({"reply": media_mod.pause()}); return
        if path == "/api/media/next":
            self._json({"reply": media_mod.next_track()}); return
        if path == "/api/media/prev":
            self._json({"reply": media_mod.prev_track()}); return
        if path == "/api/media/now" or path == "/api/media/now_json":
            try:
                self._json(media_mod.now_playing_json()); return
            except Exception as e:
                self._json({"ok": False, "status": "Error", "error": str(e), "title": "Nothing playing", "artist": ""}, status=500); return

        # ── WhatsApp ───────────────────────────────────
        if path == "/api/whatsapp/send":
            r = whatsapp_mod.send_message(
                body.get("to") or "", body.get("message") or "")
            self._json(r); return

        # ── Notes ──────────────────────────────────────
        # ── YouTube DL ─────────────────────────────────
        if path == "/api/ytdl":
            self._json(ytdl.download(
                body.get("url") or "",
                audio_only=bool(body.get("audio")),
            )); return

        # ── Workflows ──────────────────────────────────
        if path == "/api/workflow":
            mode_name = body.get("mode") or ""
            def _run_workflow():
                return workflows.run_mode(
                    mode_name,
                    speak_fn=speak,
                    set_volume_fn=set_volume,
                    open_url_fn=webbrowser.open,
                )
            if workflows.requires_confirmation(mode_name.lower().strip()):
                result = _queue_confirmation(f"Run the destructive workflow {mode_name}", _run_workflow)
            else:
                result = _run_workflow()
            self._json(result if isinstance(result, dict) else {"ok": True, "result": result}); return

        if path == "/api/workflow/custom":
            name = (body.get("name") or "").strip()
            actions = body.get("actions", [])
            aliases = body.get("aliases", [])
            if not name or not actions:
                self._json({"ok": False, "error": "name and actions required"}, status=400); return
            try:
                workflows.add_custom_routine(name, actions, aliases)
                self._json({"ok": True, "message": f"Routine '{name}' saved successfully."})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=500)
            return

        # ── Cyber (extended) ───────────────────────────
        if path == "/api/cyber/cve":
            self._json({"ok": True, **cybertools.cve_lookup(body.get("id") or "")}); return
        if path == "/api/cyber/subdomains":
            self._json({"ok": True, **cybertools.subdomain_enum(
                body.get("domain") or "", limit=int(body.get("limit") or 50))}); return
        if path == "/api/cyber/revshell":
            self._json({
                "ok": False,
                "error": "Reverse shell payload generation is disabled in KALKI v1.5.0."
            }, status=403); return
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
def main():
    # 1. Bind HTTP server socket immediately so local service is reachable within milliseconds!
    server = None
    for attempt in range(8):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", config.PORT), Handler)
            break
        except OSError as e:
            # Check if an existing healthy KALKI server is already serving
            try:
                probe_req = urllib.request.Request(f"http://127.0.0.1:{config.PORT}/api/health")
                with urllib.request.urlopen(probe_req, timeout=0.8) as resp:
                    if resp.status == 200:
                        print(f"KALKI server is already active and healthy on port {config.PORT}.")
                        sys.exit(0)
            except Exception:
                pass
            if attempt < 7:
                time.sleep(0.4)
            else:
                print(f"Port {config.PORT} could not be bound after 8 attempts: {e}")
                sys.exit(1)

    print(f"KALKI server online -> http://localhost:{config.PORT}")

    try:
        tmpl_path = os.path.join(APP_ROOT, "config.example.py")
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
            log(f"Update available: {version}")
        updater.start_update_daemon(APP_ROOT, _on_update)
    except Exception as e:
        print(f"Failed to start auto-updater: {e}")

    # The day's briefing, spoken the first time KALKI starts or the PC wakes each day.
    # When it's due it replaces the greeting, since it starts with one.
    def _briefing_on():
        return bool(getattr(config, "BRIEFING_ON_START", True))
    briefing_due = False
    try:
        import core.productivity as _prod
        briefing_due = _briefing_on() and briefing.due_today()
        briefing.start_day_watch(speak, _briefing_on, _prod._idle_seconds)
    except Exception as e:
        log(f"day-start briefing couldn't start: {e}")

    # Startup greeting (no API)
    if config.GREET_ON_START and not briefing_due:
        def _greet():
            time.sleep(1.0)
            now = datetime.now()
            # Removed automatic browser open on startup per user request
            speak(build_greeting())
        threading.Thread(target=_greet, daemon=True).start()

    shield_monitors.start()

    # Reminder firing loop
    def _reminder_loop():
        try:
            _focus_changed(focus.is_active())  # a session that was running when KALKI closed carries on
        except Exception as e:
            log(f"focus restore error: {e}")
        while True:
            try:
                _announce_finished_focus()
            except Exception as e:
                log(f"focus check error: {e}")
            try:
                due = taskmod.pop_due_reminders()
                for r in due:
                    import oversight, notify
                    text = r["text"]
                    if r.get("late_minutes", 0) >= 3:
                        try:
                            was = datetime.fromisoformat(r["due"]).strftime("%I:%M %p").lstrip("0")
                        except (TypeError, ValueError):
                            was = "earlier"
                        spoken = f"You missed a reminder from {was}: {text}"
                    else:
                        spoken = f"Reminder, {config.OWNER_TITLE}: {text}"
                    speak(spoken)
                    oversight.record_alert("reminder", spoken, "info")
                    if not notify.notify_desktop("Reminder", spoken):
                        log("the reminder notification couldn't be shown")
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
                    speak(f"Internet connection restored, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("network", "Internet connection restored", "info"); notify.notify_desktop("Network", "Internet connection restored") if STATE.get("frontend_hidden", False) else None
                elif not net_ok and last_network_ok:
                    speak(f"Internet connection lost, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("network", "Internet connection lost", "warning"); notify.notify_desktop("Network", "Internet connection lost") if STATE.get("frontend_hidden", False) else None
                last_network_ok = net_ok

                # Clipboard Monitor expiration check
                if "clipboard_prompt_pending" in STATE:
                    pending = STATE["clipboard_prompt_pending"]
                    if time.time() - pending["ts"] > 10:
                        del STATE["clipboard_prompt_pending"]
                        STATE["wake_pending"] = False # Disengage UI mic

                # Clipboard Monitor
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
                                    speak(f"Charging started. Estimated time to full is {mins} minutes."); import oversight, notify; oversight.record_alert("battery", f"Charging started. {mins}m to full.", "info"); notify.notify_desktop("Battery", f"Charging started. {mins}m to full.") if STATE.get("frontend_hidden", False) else None
                                else:
                                    speak("Charging started."); import oversight, notify; oversight.record_alert("battery", "Charging started.", "info"); notify.notify_desktop("Battery", "Charging started.") if STATE.get("frontend_hidden", False) else None
                            else:
                                speak("Power connected. Battery is already fully charged."); import oversight, notify; oversight.record_alert("battery", "Power connected. Battery full.", "info"); notify.notify_desktop("Battery", "Power connected. Battery full.") if STATE.get("frontend_hidden", False) else None
                        elif not b.power_plugged and last_power_plugged:
                            speak("Running on battery power."); import oversight, notify; oversight.record_alert("battery", "Running on battery power.", "info"); notify.notify_desktop("Battery", "Running on battery power.") if STATE.get("frontend_hidden", False) else None
                    last_power_plugged = b.power_plugged

                    if b.power_plugged and pct == 100 and \
                       now_t - last_alert.get("battery_full", 0) > 60 * 60:
                        speak("Battery is fully charged. You may disconnect the power."); import oversight, notify; oversight.record_alert("battery", "Battery is fully charged.", "info"); notify.notify_desktop("Battery", "Battery is fully charged.") if STATE.get("frontend_hidden", False) else None
                        last_alert["battery_full"] = now_t
                        
                    if not b.power_plugged:
                        if pct <= getattr(config, 'BATTERY_SUPER_CRITICAL_PCT', 5) and \
                           now_t - last_alert.get("battery_super_critical", 0) > cooldowns["battery_super_critical"]:
                            speak(f"Warning! Battery at {pct} percent. System will shut down soon."); import oversight, notify; oversight.record_alert("battery", f"Battery at {pct}%. Shutting down soon.", "critical"); notify.notify_desktop("Battery Critical", f"Battery at {pct}%. Shutting down soon.") if STATE.get("frontend_hidden", False) else None
                            last_alert["battery_super_critical"] = now_t
                        elif pct <= config.BATTERY_CRITICAL_PCT and \
                           now_t - last_alert.get("battery_critical", 0) > cooldowns["battery_critical"]:
                            speak(f"Critical battery, {config.OWNER_TITLE}. {pct} percent. Plug in immediately."); import oversight, notify; oversight.record_alert("battery", f"Critical battery: {pct}%", "critical"); notify.notify_desktop("Battery Critical", f"Critical battery: {pct}%") if STATE.get("frontend_hidden", False) else None
                            last_alert["battery_critical"] = now_t
                        elif pct <= config.BATTERY_LOW_PCT and \
                             now_t - last_alert.get("battery_low", 0) > cooldowns["battery_low"]:
                            speak(f"Battery is at {pct} percent, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("battery", f"Battery low: {pct}%", "warning"); notify.notify_desktop("Battery Low", f"Battery low: {pct}%") if STATE.get("frontend_hidden", False) else None
                            last_alert["battery_low"] = now_t
                        elif pct <= getattr(config, 'BATTERY_HALF_PCT', 50) and \
                             now_t - last_alert.get("battery_half", 0) > cooldowns["battery_half"]:
                            speak(f"Battery is at half capacity, {pct} percent."); import oversight, notify; oversight.record_alert("battery", f"Battery at {pct}%", "info"); notify.notify_desktop("Battery", f"Battery at {pct}%") if STATE.get("frontend_hidden", False) else None
                            last_alert["battery_half"] = now_t

                try:
                    disk = psutil.disk_usage('C:\\')
                    free_gb = disk.free / (1024 ** 3)
                    if free_gb < getattr(config, 'DISK_LOW_GB', 5) and \
                       now_t - last_alert.get("disk_low", 0) > cooldowns["disk_low"]:
                        speak(f"Warning: Local disk space is critically low. Only {int(free_gb)} gigabytes remaining."); import oversight, notify; oversight.record_alert("disk", f"Low disk space: {int(free_gb)} GB remaining", "critical"); notify.notify_desktop("Disk Space", f"Low disk space: {int(free_gb)} GB remaining") if STATE.get("frontend_hidden", False) else None
                        last_alert["disk_low"] = now_t
                except Exception:
                    pass

                ram = psutil.virtual_memory().percent
                if ram >= config.RAM_HIGH_PCT and \
                   now_t - last_alert.get("ram_high", 0) > cooldowns["ram_high"]:
                    speak(f"Suspicious activity detected. Memory usage is abnormally high at {int(ram)} percent."); import oversight, notify; oversight.record_alert("ram", f"High memory usage: {int(ram)}%", "warning"); notify.notify_desktop("Memory Usage", f"High memory usage: {int(ram)}%") if STATE.get("frontend_hidden", False) else None
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
                        speak(f"Suspicious activity detected on your computer, {config.OWNER_TITLE}. CPU is sustained at {int(cpu)} percent."); import oversight, notify; oversight.record_alert("cpu", f"High CPU usage: {int(cpu)}%", "warning"); notify.notify_desktop("CPU Usage", f"High CPU usage: {int(cpu)}%") if STATE.get("frontend_hidden", False) else None
                        last_alert["cpu_sustained"] = now_t
                        cpu_high_streak = 0
                else:
                    cpu_high_streak = 0

                # Proactive Email Alert
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
                            speak(f"Excuse me Sir, you have a new important email from {short_from} about {short_subj}."); import oversight, notify; oversight.record_alert("email", f"Important email from {short_from}", "info"); notify.notify_desktop("Email", f"Important email from {short_from}") if STATE.get("frontend_hidden", False) else None
                        else:
                            speak(f"Excuse me Sir, you have {new_count} new important emails, including one from {short_from}."); import oversight, notify; oversight.record_alert("email", f"{new_count} new important emails", "info"); notify.notify_desktop("Email", f"{new_count} new important emails") if STATE.get("frontend_hidden", False) else None
                    last_email_count = important_count
                    
                # Proactive GitHub Alert
                if github_mod.is_configured():
                    notes = github_mod.check_notifications(limit=10)
                    if isinstance(notes, str) and "unread GitHub notification" in notes:
                        parts = notes.split("unread")
                        if len(parts) > 0:
                            nums = re.findall(r'\d+', parts[0])
                            if nums:
                                count = int(nums[0])
                                if last_github_count != -1 and count > last_github_count:
                                    speak(f"Sir, you have {count - last_github_count} new GitHub notifications."); import oversight, notify; oversight.record_alert("github", f"{count - last_github_count} new GitHub notifications", "info"); notify.notify_desktop("GitHub", f"{count - last_github_count} new GitHub notifications") if STATE.get("frontend_hidden", False) else None
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
                            speak(f"Reminder, {config.OWNER_TITLE}. {title} starts in {mins} minute{'s' if mins != 1 else ''}.", is_notification=True); import oversight, notify; oversight.record_alert("calendar", f"Event '{title}' starts in {mins} min", "info"); notify.notify_desktop("Calendar", f"Event '{title}' starts in {mins} min") if STATE.get("frontend_hidden", False) else None
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
                        speak(f"Alert, {config.OWNER_TITLE}. {r['host']} is down.", is_notification=True); import oversight, notify; oversight.record_alert("site-down", f"{r['host']} is down", "critical"); notify.notify_desktop("Site Down", f"{r['host']} is down") if STATE.get("frontend_hidden", False) else None
                        log(f"watchdog: {r['host']} DOWN ({r.get('error')})")
                    elif r["up"] and not prev["up"]:
                        speak(f"{r['host']} is back up, {config.OWNER_TITLE}.", is_notification=True); import oversight, notify; oversight.record_alert("site-down", f"{r['host']} is back up", "info"); notify.notify_desktop("Site Recovered", f"{r['host']} is back up") if STATE.get("frontend_hidden", False) else None
                    alerted = set(prev.get("cert_alerted", set()))
                    cd = r.get("cert_days")
                    if cd is not None and cd >= 0:
                        for th in (2, 7, 14):
                            if cd <= th and th not in alerted:
                                speak(f"Heads up, {config.OWNER_TITLE}. {r['host']} SSL certificate expires in {cd} days.", is_notification=True); import oversight, notify; oversight.record_alert("cert-expiring", f"{r['host']} SSL expires in {cd} days", "warning"); notify.notify_desktop("SSL Expiry", f"{r['host']} SSL expires in {cd} days") if STATE.get("frontend_hidden", False) else None
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

    def _resolve_location_after_startup():
        """Resolve optional GPS/IP location without delaying the local UI."""
        try:
            if location_provider.enabled():
                fix = location_provider.refresh()  # this PC's location from Windows, for the weather
                if not fix.get("ok"):
                    log(f"device location: {fix.get('reason')}")
            loc = location_provider.get_resolved_location()
            config.OWNER_CITY = loc.get("city", config.OWNER_CITY)
            config.OWNER_STATE = loc.get("state", config.OWNER_STATE)
            config.OWNER_COUNTRY = loc.get("country", config.OWNER_COUNTRY)
            print(f"Location resolved: {config.OWNER_CITY}, {config.OWNER_STATE}, {config.OWNER_COUNTRY}")
        except Exception as e:
            log(f"Failed to resolve location: {e}")

    # Windows GPS and IP lookups can take several seconds. The dashboard can
    # render with the configured/fallback location until this finishes.
    threading.Thread(target=_resolve_location_after_startup, daemon=True).start()

    try:
        import core.productivity
        if getattr(config, "SCREEN_TIME_ENABLED", None) is None and core.productivity.is_enabled():
            # Tracking from before screen time had a switch: save that it's on, so it stays on.
            routes_settings.save_settings({"SCREEN_TIME_ENABLED": True})
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

    def _detect_hardware_after_startup():
        """Populate hardware telemetry without blocking the HTTP listener."""
        try:
            import hardware_detect
            hw = hardware_detect.detect_hardware()
            config.HARDWARE_PROFILE = hw
            cfg_path = USER_CONFIG_PATH
            user_cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                    user_cfg = json.load(f)
            user_cfg["HARDWARE_PROFILE"] = hw
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(user_cfg, f, indent=4)
        except Exception as e:
            print(f"Failed to save hardware profile: {e}")

    # WMI is slow or temporarily unavailable on some Windows installations.
    # It is telemetry only, so it must never delay the desktop shell.
    threading.Thread(target=_detect_hardware_after_startup, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down KALKI server.")

if __name__ == "__main__":
    main()
