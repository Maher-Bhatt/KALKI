"""What each user setting is allowed to be.

config.py is a copy of a template, so existing installs keep their old loading code.
Validation therefore lives here and runs after config is imported, which makes it
work for every install. A bad value falls back to its default, and never stops KALKI
from starting.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class SettingError(ValueError):
    """The message is safe to show: it never includes the rejected value."""


@dataclass(frozen=True)
class Spec:
    check: Callable[[Any], Any]
    default: Any = None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise SettingError("must be on or off")


def _number(kind: Callable, low: float, high: float) -> Callable[[Any], Any]:
    def check(value: Any) -> Any:
        if isinstance(value, bool):
            raise SettingError("must be a number")
        try:
            number = kind(value)
        except (TypeError, ValueError) as exc:
            raise SettingError("must be a number") from exc
        if not low <= number <= high:
            raise SettingError(f"must be between {low} and {high}")
        return number
    return check


def _text(max_length: int = 2048) -> Callable[[Any], str]:
    def check(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise SettingError("must be text")
        text = str(value)
        if len(text) > max_length:
            raise SettingError(f"must be at most {max_length} characters")
        return text
    return check


def _choice(*options: str) -> Callable[[Any], str]:
    def check(value: Any) -> str:
        if value not in options:
            raise SettingError("must be one of: " + ", ".join(options))
        return value
    return check


def _pattern(regex: str, description: str) -> Callable[[Any], str]:
    compiled = re.compile(regex)
    def check(value: Any) -> str:
        if not isinstance(value, str) or not compiled.fullmatch(value):
            raise SettingError(f"must be {description}")
        return value
    return check


def _url(*schemes: str) -> Callable[[Any], str]:
    def check(value: Any) -> str:
        parsed = urlparse(value) if isinstance(value, str) else None
        if not parsed or parsed.scheme not in schemes or not parsed.hostname:
            raise SettingError("must be a web address starting with " + " or ".join(f"{s}://" for s in schemes))
        return value
    return check


def _optional_float(low: float, high: float) -> Callable[[Any], Optional[float]]:
    number = _number(float, low, high)
    def check(value: Any) -> Optional[float]:
        return None if value in (None, "") else number(value)
    return check


def _phrases(value: Any) -> List[str]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
        raise SettingError("must be a list of phrases")
    return value


_PERCENT = _number(int, 0, 100)
_COLOR = _pattern(r"#[0-9a-fA-F]{6}", "a colour like #1a2b3c")
_SIGNED_PERCENT = _pattern(r"[+-]\d{1,3}%", "a change like +10%")
_SIGNED_HZ = _pattern(r"[+-]\d{1,3}Hz", "a change like +5Hz")

SCHEMA: Dict[str, Spec] = {
    # Secrets. Their values normally live in the vault.
    **{key: Spec(_text()) for key in (
        "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY",
        "EMAIL_APP_PASSWORD", "GITHUB_TOKEN", "SHODAN_API_KEY", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "CLOUD_SYNC_PASSPHRASE",
    )},
    # You.
    "OWNER_NAME": Spec(_text(100), "YourName"),
    "OWNER_TITLE": Spec(_text(50), "Sir"),
    "OWNER_CITY": Spec(_text(100), "YourCity"),
    "OWNER_STATE": Spec(_text(100), "YourState"),
    "OWNER_COUNTRY": Spec(_text(100), "YourCountry"),
    "LATITUDE": Spec(_optional_float(-90, 90)),
    "LONGITUDE": Spec(_optional_float(-180, 180)),
    "AUTO_IP_LOCATION": Spec(_bool, False),
    # Voice.
    "TTS_PROVIDER": Spec(_text(40), "edge"),
    "TTS_VOICE": Spec(_text(100), "en-US-AndrewMultilingualNeural"),
    "TTS_RATE": Spec(_SIGNED_PERCENT, "+0%"),
    "TTS_PITCH": Spec(_SIGNED_HZ, "+0Hz"),
    "TTS_VOLUME": Spec(_SIGNED_PERCENT, "+0%"),
    "TTS_OUTPUT_DEVICE": Spec(_text(200), ""),
    "TTS_GROQ_TIMEOUT_SEC": Spec(_number(float, 1, 10), 3),
    "WAKE_WORDS": Spec(_phrases, ["hey kalki", "kalki"]),
    "LISTEN_MODE": Spec(_choice("always", "push"), "push"),
    "STT_AVOID_BLUETOOTH": Spec(_bool, True),
    "STT_INPUT_DEVICE": Spec(_text(200), ""),
    "STT_ENGINE": Spec(_choice("auto", "google", "vosk"), "auto"),
    "STT_LANGUAGE": Spec(_pattern(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", "a language code like en-IN"), "en-IN"),
    "VOSK_MODEL_PATH": Spec(_text(500), "data/vosk-model"),
    # App.
    "PORT": Spec(_number(int, 1024, 65535), 8888),
    "BROWSER": Spec(_text(40), "chrome"),
    "AUTO_START": Spec(_bool, False),
    "GREET_ON_START": Spec(_bool, True),
    "OPEN_BROWSER_ON_WAKE": Spec(_bool, True),
    "SUPPORT_URL": Spec(_url("https")),
    "ENABLE_DESKTOP_PET": Spec(_bool, False),
    "PET_SPECIES": Spec(_text(40)),
    "PET_NAME": Spec(_text(40)),
    "MEMORY_FILE": Spec(_text(500), "data/memory.json"),
    "HISTORY_FILE": Spec(_text(500), "data/history.json"),
    # AI.
    "DEFAULT_MODEL": Spec(_text(100), "auto"),
    "GROQ_MODEL": Spec(_text(100), "llama-3.3-70b-versatile"),
    "MODEL_CHAT": Spec(_text(100)),
    "MODEL_CODING": Spec(_text(100)),
    "MODEL_VISION": Spec(_text(100)),
    "MODEL_VOICE": Spec(_text(100)),
    "OLLAMA_URL": Spec(_url("http", "https"), "http://localhost:11434"),
    "MAX_HISTORY": Spec(_number(int, 2, 500), 20),
    # Safety and privacy.
    "REQUIRE_DANGEROUS_CONFIRMATION": Spec(_bool, True),
    "MOOD_LOCK_ENABLED": Spec(_bool, True),
    "ALLOW_HOST_CODE_EXECUTION": Spec(_bool, False),
    "LOG_TRANSCRIPTS": Spec(_bool, False),
    "TELEMETRY_ENABLED": Spec(_bool, False),
    "VISION_RECALL_ENABLED": Spec(_bool, False),
    "VISION_RETENTION_DAYS": Spec(_number(int, 1, 3650), 7),
    "CLOUD_SYNC_ENABLED": Spec(_bool, False),
    # Personality.
    "PERSONALITY_SPICE": Spec(_bool, False),
    "SPICY_REPLY_CHANCE": Spec(_number(float, 0, 1), 0.08),
    "JOKE_OFFERS_ENABLED": Spec(_bool, True),
    "JOKE_OFFER_CHANCE": Spec(_number(float, 0, 1), 0.06),
    "JOKE_MIN_INTERVAL_MINUTES": Spec(_number(int, 1, 100000), 45),
    "ROAST_MODE": Spec(_bool, False),
    # Appearance.
    "THEME_PRESET": Spec(_text(40), "Obsidian K"),
    "THEME_MODE": Spec(_choice("dark", "light"), "dark"),
    "THEME_PRIMARY": Spec(_COLOR, "#b6553f"),
    "THEME_PEACOCK": Spec(_COLOR, "#1c6d70"),
    "THEME_INDIGO": Spec(_COLOR, "#263a63"),
    "THEME_SAFFRON": Spec(_COLOR, "#db7d37"),
    "THEME_MOTION": Spec(_number(float, 0, 1), 0.78),
    "THEME_GLOW": Spec(_bool, True),
    "SCREENSAVER_ENABLED": Spec(_bool, True),
    "SCREENSAVER_IDLE_MINS": Spec(_number(int, 1, 1440), 5),
    # Mail and integrations.
    "EMAIL_ADDRESS": Spec(_text(320), ""),
    "IMAP_SERVER": Spec(_text(255), "imap.gmail.com"),
    "IMAP_PORT": Spec(_number(int, 1, 65535), 993),
    "GOOGLE_PROJECT_ID": Spec(_text(100)),
    "SPOTIFY_REDIRECT_URI": Spec(_url("http", "https"), "http://127.0.0.1:8889/callback"),
    # Alerts.
    "ALERTS_ENABLED": Spec(_bool, True),
    "CPU_ALERTS_ENABLED": Spec(_bool, False),
    "BATTERY_LOW_PCT": Spec(_PERCENT, 20),
    "BATTERY_CRITICAL_PCT": Spec(_PERCENT, 10),
    "RAM_HIGH_PCT": Spec(_PERCENT, 90),
    "CPU_HIGH_PCT": Spec(_PERCENT, 95),
}


def validate(key: str, value: Any) -> Any:
    """Return the cleaned value, or raise SettingError."""
    spec = SCHEMA.get(key)
    if spec is None:
        raise SettingError("isn't a setting KALKI knows")
    return spec.check(value)


def validate_updates(updates: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    clean, errors = {}, {}
    for key, value in updates.items():
        try:
            clean[key] = validate(key, value)
        except SettingError as exc:
            errors[key] = str(exc)
    return clean, errors


def read_raw_user_config(path: str) -> Tuple[Dict[str, Any], List[str]]:
    """The whole settings file as saved. An unreadable file is moved aside rather
    than deleted, so nothing is lost and saving works again."""
    if not os.path.exists(path):
        return {}, []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        return data, []
    except (OSError, ValueError) as exc:
        kept = f"{path}.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        try:
            os.replace(path, kept)
        except OSError:
            pass
        return {}, [f"The settings file couldn't be read ({type(exc).__name__}), so it was kept as {os.path.basename(kept)} and defaults are in use."]


def load_user_config(path: str) -> Tuple[Dict[str, Any], List[str]]:
    """Saved settings that are safe to apply. Keys this schema doesn't know are left
    out here but stay in the file: other tools write them, like the setup wizard."""
    data, problems = read_raw_user_config(path)
    values = {}
    for key, value in data.items():
        if key not in SCHEMA:
            continue
        try:
            values[key] = validate(key, value)
        except SettingError as exc:
            problems.append(f"Saved setting {key} {exc}, so it was ignored.")
    return values, problems


def repair_config(config: Any) -> List[str]:
    """Reset any invalid setting on the loaded config module to its default."""
    problems = []
    for key, spec in SCHEMA.items():
        if not hasattr(config, key):
            continue
        try:
            setattr(config, key, spec.check(getattr(config, key)))
        except SettingError as exc:
            setattr(config, key, spec.default)
            problems.append(f"Setting {key} {exc}, so the default is in use.")
    return problems


def apply_user_config(config: Any, path: str) -> List[str]:
    """Apply saved settings over config, then repair anything invalid. Secrets
    aren't re-applied: the vault values already loaded take priority."""
    values, problems = load_user_config(path)
    for key, value in values.items():
        current = getattr(config, key, None)
        if key.endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD")) and current and not str(current).startswith(("PASTE_", "your_")):
            continue
        setattr(config, key, value)
    return problems + repair_config(config)
