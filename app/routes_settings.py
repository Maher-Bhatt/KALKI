"""Settings routes and the rules for secrets, moved out of server.py.

Secrets (API keys, passwords, tokens) live in the vault. The screen only ever learns
whether each one is set, and exported settings never include them.
"""

import os
import re
import threading
from typing import Any, Callable, Dict, Optional, Tuple

import config
import gcal
import runtime_log
import safe_json
import settings_schema
import spotify_mod
from core import api_vault

Result = Tuple[Dict[str, Any], int]

SECRET_SETTING_KEYS = {
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "ELEVENLABS_API_KEY",
    "EMAIL_APP_PASSWORD",
    "GITHUB_TOKEN",
    "SHODAN_API_KEY",
    "SPOTIFY_CLIENT_SECRET",
    "GOOGLE_CLIENT_SECRET",
    "CLOUD_SYNC_PASSPHRASE",
    "TELEGRAM_BOT_TOKEN",
}

PLACEHOLDER_VALUES = {"", "PASTE_YOUR_GROQ_KEY_HERE", "your_personal_access_token", "your_shodan_api_key"}

# What the Settings screen shows, with the value used when it isn't set.
SHOWN_SETTINGS = {
    "GROQ_API_KEY": "", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "GEMINI_API_KEY": "", "ELEVENLABS_API_KEY": "",
    "OWNER_NAME": "", "OWNER_TITLE": "", "SPOTIFY_CLIENT_ID": "", "SPOTIFY_CLIENT_SECRET": "",
    "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_PROJECT_ID": "",
    "TELEMETRY_ENABLED": True, "CPU_ALERTS_ENABLED": False, "SCREENSAVER_ENABLED": True, "SCREENSAVER_IDLE_MINS": 5,
    "OWNER_CITY": "", "OWNER_STATE": "", "OWNER_COUNTRY": "", "EMAIL_ADDRESS": "", "EMAIL_APP_PASSWORD": "",
    "GITHUB_TOKEN": "", "SHODAN_API_KEY": "", "CLOUD_SYNC_PASSPHRASE": "",
    "MODEL_CHAT": "auto", "MODEL_VISION": "auto", "MODEL_CODING": "auto", "MODEL_VOICE": "auto",
    "TTS_PROVIDER": "edge", "TTS_VOICE": "", "TTS_RATE": "+0%", "TTS_PITCH": "+0Hz", "TTS_VOLUME": "+0%",
    "TTS_OUTPUT_DEVICE": "", "TTS_GROQ_TIMEOUT_SEC": 3,
    "THEME_PRESET": "Obsidian K", "THEME_MODE": "dark", "THEME_PRIMARY": "#b6553f", "THEME_PEACOCK": "#1c6d70",
    "THEME_INDIGO": "#263a63", "THEME_SAFFRON": "#db7d37", "THEME_MOTION": 0.78, "THEME_GLOW": True,
    "REQUIRE_DANGEROUS_CONFIRMATION": True, "MOOD_LOCK_ENABLED": True, "ENABLE_DESKTOP_PET": False,
    "CLOUD_SYNC_ENABLED": False, "CURRENT_VERSION": "",
}

_THEME_COLOR_KEYS = ("THEME_PRIMARY", "THEME_PEACOCK", "THEME_INDIGO", "THEME_SAFFRON")
_THEME_DEFAULTS = {k: SHOWN_SETTINGS[k] for k in (*_THEME_COLOR_KEYS, "THEME_PRESET", "THEME_MODE", "THEME_MOTION", "THEME_GLOW")}

# Kept when the cache is cleared: sign-ins, the database and KALKI's own token.
_KEEP_ON_CLEAR = {"token.json", "spotify_token.json", "credentials.json", "google_token.pickle", "kalki.db", "api_token.txt"}

_config: Dict[str, Any] = {
    "data_dir": None, "user_config_path": None, "log_path": None,
    "lock": threading.Lock(), "ask_permission": None,
}


def configure(data_dir: str, user_config_path: str, log_path: str, lock, ask_permission: Callable[..., bool]) -> None:
    _config.update(data_dir=data_dir, user_config_path=user_config_path, log_path=log_path,
                   lock=lock, ask_permission=ask_permission)


def is_configured_secret(value: Any) -> bool:
    value = str(value or "").strip()
    return bool(value and value not in PLACEHOLDER_VALUES and not value.startswith("PASTE_"))


def public_value(key: str, value: Any) -> Any:
    """A secret that is set is shown as empty. Only its status says it's there."""
    if key in SECRET_SETTING_KEYS:
        return "" if is_configured_secret(value) else value
    return value


def secret_status(keys=SECRET_SETTING_KEYS) -> Dict[str, bool]:
    try:
        vault_secrets = api_vault.list_secrets()
    except Exception:
        vault_secrets = {}
    return {k: is_configured_secret(getattr(config, k, "") or vault_secrets.get(k, "")) for k in keys}


def sanitize_theme(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Validate appearance settings before saving them."""
    clean = dict(updates or {})
    for key in _THEME_COLOR_KEYS:
        if key in clean:
            value = str(clean[key] or "").strip()
            clean[key] = value.lower() if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else _THEME_DEFAULTS[key]
    if "THEME_MODE" in clean:
        clean["THEME_MODE"] = "light" if str(clean["THEME_MODE"]).strip().lower() == "light" else "dark"
    if "THEME_PRESET" in clean:
        clean["THEME_PRESET"] = str(clean["THEME_PRESET"] or "").strip()[:40] or _THEME_DEFAULTS["THEME_PRESET"]
    if "THEME_MOTION" in clean:
        try:
            clean["THEME_MOTION"] = max(0.25, min(1.0, float(clean["THEME_MOTION"])))
        except (TypeError, ValueError):
            clean["THEME_MOTION"] = _THEME_DEFAULTS["THEME_MOTION"]
    if "THEME_GLOW" in clean:
        clean["THEME_GLOW"] = bool(clean["THEME_GLOW"])
    return clean


def write_google_credentials(path: str, client_id: str, client_secret: str, project_id: str) -> None:
    """The file Google's sign-in library reads. Written atomically."""
    safe_json.write_json(path, {"installed": {
        "client_id": client_id,
        "project_id": project_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": client_secret,
        "redirect_uris": ["http://localhost:8080/"],
    }})


def _cache_size_mb() -> float:
    data_dir = _config["data_dir"]
    if not data_dir or not os.path.isdir(data_dir):
        return 0.0
    total = 0
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        try:
            if os.path.isfile(path):
                total += os.path.getsize(path)
        except OSError:
            continue  # A file removed while counting.
    return total / (1024 * 1024)


def get_settings(body: Dict[str, Any]) -> Result:
    shown = {k: public_value(k, getattr(config, k, default)) for k, default in SHOWN_SETTINGS.items()}
    return {
        "ok": True,
        "settings": shown,
        "secretStatus": secret_status(),
        "spotifyConfigured": spotify_mod.is_configured(),
        "googleConfigured": gcal.is_configured(),
        "cacheSize": f"{_cache_size_mb():.2f} MB",
    }, 200


def export_text() -> Optional[str]:
    """The settings file for download, without any secret in it. None if there's no file."""
    path = _config["user_config_path"]
    if not path or not os.path.exists(path):
        return None
    raw = safe_json.read_json(path, default={})
    clean = {k: v for k, v in raw.items() if k not in SECRET_SETTING_KEYS}
    import json
    return json.dumps(clean, indent=2, ensure_ascii=False)


def test_connections(body: Dict[str, Any]) -> Result:
    """A real call to Groq. Google and Spotify only report whether they're set up."""
    import urllib.request
    try:
        request = urllib.request.Request("https://api.groq.com/openai/v1/models",
                                         headers={"Authorization": f"Bearer {getattr(config, 'GROQ_API_KEY', '')}"})
        with urllib.request.urlopen(request, timeout=5) as response:
            groq = "OK" if response.status == 200 else "FAILED"
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 200
    return {"ok": True, "groq": groq,
            "spotify": "SET UP" if spotify_mod.is_configured() else "NOT LINKED",
            "google": "SET UP" if gcal.is_configured() else "NOT LINKED"}, 200


def test_google(body: Dict[str, Any]) -> Result:
    linked = gcal.is_configured()
    return {"ok": linked, "message": "Google is set up." if linked else "Google isn't connected yet."}, 200


def test_spotify(body: Dict[str, Any]) -> Result:
    linked = spotify_mod.is_configured()
    return {"ok": linked, "message": "Spotify is set up." if linked else "Spotify isn't connected yet."}, 200


def needs_post(body: Dict[str, Any]) -> Result:
    return {"ok": False, "error": "POST required"}, 405


def reset_settings(body: Dict[str, Any]) -> Result:
    data_dir = _config["data_dir"]
    try:
        for path in (_config["user_config_path"], os.path.join(data_dir, "token.json"),
                     os.path.join(data_dir, "spotify_token.json"), os.path.join(data_dir, "credentials.json")):
            if os.path.exists(path):
                os.remove(path)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}, 200
    return {"ok": True, "secretStatus": secret_status()}, 200


def clear_cache(body: Dict[str, Any]) -> Result:
    data_dir = _config["data_dir"]
    try:
        if os.path.isdir(data_dir):
            for name in os.listdir(data_dir):
                path = os.path.join(data_dir, name)
                if os.path.isfile(path) and name not in _KEEP_ON_CLEAR:
                    os.remove(path)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}, 200
    return {"ok": True, "secretStatus": secret_status()}, 200


def save_settings(body: Dict[str, Any]) -> Result:
    raw = body.get("updates") if isinstance(body.get("updates"), dict) else body
    updates, invalid = settings_schema.validate_updates(sanitize_theme(raw) if isinstance(raw, dict) else {})
    if invalid:
        # All or nothing, so a form never half-saves.
        summary = "; ".join(f"{k} {why}" for k, why in invalid.items())
        return {"ok": False, "error": f"Not saved: {summary}", "fields": invalid}, 400

    # A token isn't enough to weaken safety: the prompt comes from the server.
    ask = _config["ask_permission"]
    if updates.get("ALLOW_HOST_CODE_EXECUTION") is True and not getattr(config, "ALLOW_HOST_CODE_EXECUTION", False):
        if not ask("let apps and tools run code directly on this PC", always=True):
            return {"ok": False, "kind": "denied", "error": "You declined the change."}, 403
    if updates.get("REQUIRE_DANGEROUS_CONFIRMATION") is False and getattr(config, "REQUIRE_DANGEROUS_CONFIRMATION", True):
        if not ask("stop asking before risky actions", always=True):
            return {"ok": False, "kind": "denied", "error": "You declined the change."}, 403

    path = _config["user_config_path"]
    applied = {}
    try:
        with _config["lock"]:
            saved, problems = settings_schema.read_raw_user_config(path)
            for problem in problems:
                runtime_log.log_event(_config["log_path"], "warning", "settings_problem", detail=problem)
            for key, value in updates.items():
                if key in SECRET_SETTING_KEYS:
                    if str(value or "").strip():
                        api_vault.set_secret(key, value)
                        applied[key] = value
                    saved.pop(key, None)  # Never kept in the plain settings file.
                else:
                    saved[key] = value
                    applied[key] = value
            safe_json.write_json(path, saved)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 200

    for key, value in applied.items():
        setattr(config, key, value)
        if key in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"):
            os.environ[key] = value

    client_id = getattr(config, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(config, "GOOGLE_CLIENT_SECRET", "")
    project_id = getattr(config, "GOOGLE_PROJECT_ID", "")
    if client_id and client_secret and project_id and {"GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_PROJECT_ID"} & set(applied):
        try:
            write_google_credentials(os.path.join(_config["data_dir"], "credentials.json"), client_id, client_secret, project_id)
        except OSError as exc:
            return {"ok": False, "error": f"Saved, but Google's sign-in file couldn't be written: {exc}"}, 200
    return {"ok": True, "secretStatus": secret_status()}, 200


GET_ROUTES = {
    "/api/settings/get": get_settings,
    "/api/settings/test": test_connections,
    "/api/settings/test_google": test_google,
    "/api/settings/test_spotify": test_spotify,
    "/api/settings/reset": needs_post,
    "/api/settings/clear_cache": needs_post,
}

POST_ROUTES = {
    "/api/settings/reset": reset_settings,
    "/api/settings/clear_cache": clear_cache,
    "/api/settings/save": save_settings,
}
