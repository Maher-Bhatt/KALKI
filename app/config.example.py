# ──────────────────────────────────────────────────────────────
# KALKI — Configuration Template
# Copy this file to config.py and fill in your own keys / settings.
# config.py is gitignored so your secrets never get committed.
# ──────────────────────────────────────────────────────────────

import os

CURRENT_VERSION = "v1.0.24"

# ── INTERNAL PATHS (do not change) ───────────────────────────
# Where the Setup Wizard and hardware auto-detect persist their own data.
# Keep this in sync with USER_DATA_DIR in main_app.py / kalki_setup_wizard.py —
# without this, server.py's hardware-profile save falls back to a different,
# unused path and never actually lines up with what the wizard writes.
_USER_CONFIG_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "user_config.json"
)

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

# ── VOICE (edge-tts) ────────────────────────────────────────
# Default to Edge TTS for fastest local-feeling playback. Groq TTS is available
# as an opt-in provider, but it has a short timeout and falls back to Edge.
TTS_PROVIDER = "edge"             # edge | groq
TTS_GROQ_TIMEOUT_SEC = 3
# Most human / least robotic: en-US-BrianMultilingualNeural (default),
#   en-US-AndrewMultilingualNeural — newest neural models, very natural.
# British butler (JARVIS vibe): en-GB-RyanNeural, en-GB-ThomasNeural
# Other US males: en-US-GuyNeural, en-US-TonyNeural (deep)
TTS_VOICE  = "en-US-BrianMultilingualNeural"
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
GROQ_MODEL  = "llama-3.3-70b-versatile"   # smart default
OLLAMA_URL  = "http://localhost:11434"     # used only if Groq fails
MAX_HISTORY = 20
REQUIRE_DANGEROUS_CONFIRMATION = True
LOG_TRANSCRIPTS = False

# Personality seasoning. Keep these low so KALKI feels personal, not noisy.
PERSONALITY_SPICE = True
SPICY_REPLY_CHANCE = 0.08
JOKE_OFFERS_ENABLED = True
JOKE_OFFER_CHANCE = 0.06
JOKE_MIN_INTERVAL_MINUTES = 45

# Hardware-aware limits. Tune these to your machine so KALKI stays dramatic
# without pinning CPU/GPU.
HARDWARE_PROFILE = {
    "gpu": "RTX 5060",
    "cpu": "Ryzen 7",
    "cpu_power_w": 250,
    "ram_gb": 32,
    "display": "2K",
}
LOCAL_AI_MAX_MODEL_B = 9
CYBER_SCAN_TIMEOUT_SEC = 0.45
CYBER_SCAN_PORT_LIMIT = 64
HUD_EFFECT_QUALITY = "balanced"

# ── WAKE WORDS ──────────────────────────────────────────────
WAKE_WORDS = ["hey kalki", "kalki", "hey sir", "ok kalki"]

# ── LISTEN MODE ─────────────────────────────────────────────
# "always" = hands-free always-on wake word (continuous mic).
# "push"   = push-to-talk (mic off until you tap the HUD mic button). Use this
#            if you share a Bluetooth headset with a phone (no audio cuts).
LISTEN_MODE = "always"

# ── MIC / STT INPUT ─────────────────────────────────────────
# Keep Bluetooth headphones in high-quality A2DP: the listener avoids the
# BT mic (which forces muffled HFP mode) and uses the built-in mic instead.
STT_AVOID_BLUETOOTH = True
STT_INPUT_DEVICE    = "microsoft sound mapper - input"   # name substring to force a device, else auto
STT_ENGINE          = "auto"          # auto | vosk (offline) | google (cloud)
STT_LANGUAGE        = "en-IN"         # Google STT language. Default en-IN for Indian English/Hinglish.
VOSK_MODEL_PATH     = "data/vosk-model"

# ── STARTUP ─────────────────────────────────────────────────
AUTO_START           = True
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
TELEMETRY_ENABLED = True

# -- Dynamic User Config and Secure Vault Loading --
try:
    import json
    # 1. Load from plaintext user_config.json first
    if os.path.exists(_USER_CONFIG_PATH):
        with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as _f:
            _user_conf = json.load(_f)
        for _k, _v in _user_conf.items():
            globals()[_k] = _v

    # 2. Load from secure API Vault (dpapi / keyring / aes) if present
    try:
        from core import api_vault
        # Auto migrate plaintext settings on first launch of new version
        api_vault.migrate_settings_to_vault(_USER_CONFIG_PATH)
        # Load all decrypted secrets into configuration variables
        for _k, _v in api_vault.list_secrets().items():
            globals()[_k] = _v
    except Exception as _vault_err:
        pass
except Exception as _e:
    pass
