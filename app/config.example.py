# ──────────────────────────────────────────────────────────────
# KALKI — Configuration Template
# Copy this file to config.py and fill in your own keys / settings.
# config.py is gitignored so your secrets never get committed.
# ──────────────────────────────────────────────────────────────

import os
import json
from runtime_paths import prepare_runtime

CURRENT_VERSION = "v1.5.0"

# ── INTERNAL PATHS (do not change) ───────────────────────────
# Where the Setup Wizard and hardware auto-detect persist their own data.
# Keep this in sync with USER_DATA_DIR in main_app.py / kalki_setup_wizard.py.
# The resolver uses APPDATA on Windows, Application Support on macOS, and
# XDG_DATA_HOME (or ~/.local/share) on Linux.
_USER_CONFIG_PATH = os.path.join(prepare_runtime().user_data_dir, "user_config.json")

# ── GROQ AI (required for the LLM brain) ────────────────────
# Get a free key at https://console.groq.com
# Best practice: set GROQ_API_KEY in your environment and leave this as-is, so
# the secret never lives in a file. The env var wins if set.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "PASTE_YOUR_GROQ_KEY_HERE")

MANAGED_AI_ENABLED = False
MANAGED_AI_URL = "http://api.kalki-managed.com/v1/chat/completions"

# ── OWNER ───────────────────────────────────────────────────
OWNER_NAME    = "YourName"
OWNER_TITLE   = "Sir"          # or whatever KALKI should call you
OWNER_CITY    = "YourCity"
OWNER_STATE   = "YourState"
OWNER_COUNTRY = "YourCountry"
AUTO_IP_LOCATION = False  # Explicit opt-in only; never sends IP to 3rd party by default

# ── VOICE (edge-tts) ────────────────────────────────────────
# Edge neural TTS is the single supported voice path in the desktop build so
# modes and notifications never switch to a different assistant identity.
TTS_PROVIDER = "edge"
TTS_GROQ_TIMEOUT_SEC = 3
# Expressive neural voice used everywhere (en-US-AndrewMultilingualNeural or en-US-AndrewNeural fallback).
TTS_VOICE  = "en-US-AndrewMultilingualNeural"
TTS_RATE   = "+0%"                # +N% faster, -N% slower
TTS_PITCH  = "+0Hz"               # +/-N Hz to shift pitch
TTS_VOLUME = "+0%"
# Output device for KALKI's voice (name substring). Set to your laptop speakers
# (e.g. "Speakers (Realtek") so KALKI doesn't grab a shared Bluetooth headset
# and interrupt your phone. Leave "" for the system default output.
TTS_OUTPUT_DEVICE = ""

# ── SERVER ──────────────────────────────────────────────────
PORT    = 8888
BROWSER = "chrome"

# ── AI ──────────────────────────────────────────────────────
DEFAULT_MODEL = "auto"         # fast default
GROQ_MODEL    = "llama-3.3-70b-versatile"  # fallback default
OLLAMA_URL  = "http://localhost:11434"     # used only if Groq fails
MAX_HISTORY = 20
REQUIRE_DANGEROUS_CONFIRMATION = True
# Direct host execution is disabled by default; use an isolated runner instead.
ALLOW_HOST_CODE_EXECUTION = False
LOG_TRANSCRIPTS = False

# Personality seasoning. Keep these low so KALKI feels personal, not noisy.
PERSONALITY_SPICE = False
ROAST_MODE = False  # Opt-in humorous roast mode; never locks workstation
SPICY_REPLY_CHANCE = 0.08
JOKE_OFFERS_ENABLED = True
JOKE_OFFER_CHANCE = 0.06
JOKE_MIN_INTERVAL_MINUTES = 45

# Hardware-aware limits. Tune these to your machine so KALKI stays dramatic
# without pinning CPU/GPU.
try:
    from hardware_detect import detect_hardware
    HARDWARE_PROFILE = detect_hardware()
except Exception:
    HARDWARE_PROFILE = {"gpu": "Integrated Graphics", "cpu": "System CPU", "ram_gb": 8, "display": "standard"}
LOCAL_AI_MAX_MODEL_B = 9
CYBER_SCAN_TIMEOUT_SEC = 0.45
CYBER_SCAN_PORT_LIMIT = 64
HUD_EFFECT_QUALITY = "balanced"

# ── APPEARANCE / THEME ───────────────────────────────────────
# These values are editable from Setup & Settings > Theme Lab.
THEME_PRESET = "Obsidian K"
THEME_MODE = "dark"
THEME_PRIMARY = "#b6553f"
THEME_PEACOCK = "#1c6d70"
THEME_INDIGO = "#263a63"
THEME_SAFFRON = "#db7d37"
THEME_MOTION = 0.78
THEME_GLOW = True

# ── WAKE WORDS ──────────────────────────────────────────────
WAKE_WORDS = ["hey kalki", "kalki", "hey sir", "ok kalki"]

# ── LISTEN MODE ─────────────────────────────────────────────
# "always" = hands-free always-on wake word (continuous mic).
# "push"   = push-to-talk (mic off until you tap the HUD mic button). Use this
#            if you share a Bluetooth headset with a phone (no audio cuts).
LISTEN_MODE = "push"

# ── MIC / STT INPUT ─────────────────────────────────────────
# Keep Bluetooth headphones in high-quality A2DP: the listener avoids the
# BT mic (which forces muffled HFP mode) and uses the built-in mic instead.
STT_AVOID_BLUETOOTH = True
STT_INPUT_DEVICE    = "microsoft sound mapper - input"   # name substring to force a device, else auto
STT_ENGINE          = "auto"          # auto | vosk (offline) | google (cloud)
STT_LANGUAGE        = "en-IN"         # Google STT language. Default en-IN for Indian English/Hinglish.
VOSK_MODEL_PATH     = "data/vosk-model"

# ── STARTUP ─────────────────────────────────────────────────
AUTO_START = False
GREET_ON_START       = True
OPEN_BROWSER_ON_WAKE = True

# ── MEMORY / HISTORY (paths inside data/) ───────────────────
MEMORY_FILE  = "data/memory.json"
HISTORY_FILE = "data/history.json"

# ── VISION RECALL ───────────────────────────────────────────
# Takes periodic screenshots and runs local OCR for semantic search.
# Disabled by default for privacy. Requires pytesseract.
VISION_RECALL_ENABLED = False
VISION_RETENTION_DAYS = 7

# ── CLOUD SYNC ──────────────────────────────────────────────
# Set this once; you'll need to re-enter it on a new machine to restore your data. 
# Not the same as your vault password — this one has to leave the machine.
CLOUD_SYNC_PASSPHRASE = ""

# ── EMAIL (optional, IMAP route — Gmail App Password) ───────
# OAuth Gmail is set up separately via setup_google.py.
# Leave blank to disable IMAP.
EMAIL_ADDRESS      = ""
EMAIL_APP_PASSWORD = ""
IMAP_SERVER        = "imap.gmail.com"
IMAP_PORT          = 993

# ── REMINDER LOOP ───────────────────────────────────────────
REMINDER_POLL_SEC = 30

# ── SPOTIFY (optional) ──────────────────────────────────────
# Create app at https://developer.spotify.com/dashboard
# Redirect URI MUST be: http://127.0.0.1:8889/callback
SPOTIFY_CLIENT_ID     = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REDIRECT_URI  = "http://127.0.0.1:8889/callback"

# ── PROACTIVE ALERTS ────────────────────────────────────────
ALERTS_ENABLED       = True
BATTERY_LOW_PCT      = 20
BATTERY_CRITICAL_PCT = 10
RAM_HIGH_PCT         = 90
CPU_HIGH_PCT         = 95

# -- Integrations --
GITHUB_TOKEN = "your_personal_access_token"
SHODAN_API_KEY = "your_shodan_api_key"

# -- New Config Options v1.0.17 --
SUPPORT_URL = "https://buymeacoffee.com/maherbhatt"
CPU_ALERTS_ENABLED = False
SCREENSAVER_ENABLED = True
SCREENSAVER_IDLE_MINS = 5
TELEMETRY_ENABLED = False

# -- Dynamic User Config and Secure Vault Loading --
try:
    import json
    ALLOWED_CONFIG_KEYS = {
        "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY",
        "OWNER_NAME", "OWNER_TITLE", "OWNER_CITY", "OWNER_STATE", "OWNER_COUNTRY",
        "LATITUDE", "LONGITUDE", "AUTO_IP_LOCATION",
        "TTS_PROVIDER", "TTS_VOICE", "TTS_RATE", "TTS_PITCH", "TTS_VOLUME", "TTS_OUTPUT_DEVICE",
        "PORT", "BROWSER", "DEFAULT_MODEL", "GROQ_MODEL", "OLLAMA_URL", "MAX_HISTORY",
        "REQUIRE_DANGEROUS_CONFIRMATION", "ALLOW_HOST_CODE_EXECUTION", "LOG_TRANSCRIPTS",
        "PERSONALITY_SPICE", "SPICY_REPLY_CHANCE", "JOKE_OFFERS_ENABLED", "JOKE_OFFER_CHANCE",
        "JOKE_MIN_INTERVAL_MINUTES", "ROAST_MODE",
        "THEME_PRESET", "THEME_MODE", "THEME_PRIMARY", "THEME_PEACOCK", "THEME_INDIGO",
        "THEME_SAFFRON", "THEME_MOTION", "THEME_GLOW",
        "WAKE_WORDS", "LISTEN_MODE", "STT_AVOID_BLUETOOTH", "STT_INPUT_DEVICE", "STT_ENGINE",
        "STT_LANGUAGE", "VOSK_MODEL_PATH", "AUTO_START", "GREET_ON_START", "OPEN_BROWSER_ON_WAKE",
        "MEMORY_FILE", "HISTORY_FILE", "VISION_RECALL_ENABLED", "VISION_RETENTION_DAYS",
        "CLOUD_SYNC_PASSPHRASE", "EMAIL_ADDRESS", "EMAIL_APP_PASSWORD", "IMAP_SERVER", "IMAP_PORT",
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI",
        "ALERTS_ENABLED", "BATTERY_LOW_PCT", "BATTERY_CRITICAL_PCT", "RAM_HIGH_PCT", "CPU_HIGH_PCT",
        "GITHUB_TOKEN", "SHODAN_API_KEY", "SUPPORT_URL", "CPU_ALERTS_ENABLED",
        "SCREENSAVER_ENABLED", "SCREENSAVER_IDLE_MINS", "TELEMETRY_ENABLED",
        "ENABLE_DESKTOP_PET", "PET_SPECIES", "PET_NAME"
    }

    # 1. Load from plaintext user_config.json first with strict key validation
    if os.path.exists(_USER_CONFIG_PATH):
        with open(_USER_CONFIG_PATH, "r", encoding="utf-8-sig") as _f:
            _user_conf = json.load(_f)
        if isinstance(_user_conf, dict):
            for _k, _v in _user_conf.items():
                if _k in ALLOWED_CONFIG_KEYS and not _k.startswith("_"):
                    globals()[_k] = _v

    # 2. Load from secure API Vault (dpapi / keyring / aes) if present
    try:
        from core import api_vault
        api_vault.migrate_settings_to_vault(_USER_CONFIG_PATH)
        for _k, _v in api_vault.list_secrets().items():
            if _k in ALLOWED_CONFIG_KEYS and not _k.startswith("_"):
                globals()[_k] = _v
    except Exception as _vault_err:
        pass
except Exception as _e:
    pass

# Desktop Companion Floating Overlay (False by default for clean single-window taskbar)
ENABLE_DESKTOP_PET = False
