import os
import sys
import hashlib
import uuid

try:
    import sentry_sdk
    import posthog
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

_posthog_client = None
_anon_id = None


def _get_anon_id():
    """Generates a stable anonymous client ID unique to the system."""
    global _anon_id
    if _anon_id:
        return _anon_id
    try:
        # Try to resolve a stable hardware uuid
        if os.name == "nt":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            _anon_id = hashlib.sha256(guid.encode()).hexdigest()[:12]
        else:
            # Fallback to mac / user folder hash
            user_path = os.path.expanduser("~")
            _anon_id = hashlib.sha256(user_path.encode()).hexdigest()[:12]
    except Exception:
        _anon_id = str(uuid.uuid4())[:8]
    return _anon_id


def init_telemetry(config):
    """
    Initialize crash reporting and product analytics anonymized and strictly with opt-out checks.
    """
    global _posthog_client
    if not TELEMETRY_AVAILABLE:
        return

    # Check opt-out setting
    if not getattr(config, "TELEMETRY_ENABLED", True):
        return

    # 1. Crash Reporting (Sentry) - Anonymized
    sentry_dsn = getattr(config, "SENTRY_DSN", None)
    if sentry_dsn and not sentry_dsn.startswith("PASTE_"):
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=0.2,
                profiles_sample_rate=0.2,
                environment="production" if getattr(sys, "frozen", False) else "development",
                release=f"kalki@{getattr(config, 'CURRENT_VERSION', 'v1.0.17')}"
            )
            # Remove PII from crash reports
            with sentry_sdk.configure_scope() as scope:
                scope.set_user({"id": _get_anon_id()})
        except Exception as e:
            print(f"[TELEMETRY] Sentry init failed: {e}")

    # 2. Product Analytics (PostHog) - Anonymized
    posthog_key = getattr(config, "POSTHOG_API_KEY", None)
    posthog_host = getattr(config, "POSTHOG_HOST", "https://app.posthog.com")
    
    if posthog_key and not posthog_key.startswith("PASTE_"):
        try:
            _posthog_client = posthog.Posthog(posthog_key, host=posthog_host)
            log_event_anonymous("app_started", {
                "version": getattr(config, "CURRENT_VERSION", "v1.0.17"),
                "os": os.name
            })
        except Exception as e:
            print(f"[TELEMETRY] PostHog init failed: {e}")


def log_event_anonymous(event_name, properties=None):
    """Safely log an event without any personal identifiers."""
    global _posthog_client
    import config
    
    # Check opt-out setting
    if not getattr(config, "TELEMETRY_ENABLED", True):
        return

    if not TELEMETRY_AVAILABLE or not _posthog_client:
        return

    # Scrub sensitive data to enforce privacy
    props = properties or {}
    clean_props = {}
    
    # List of keys we refuse to transmit
    blocklist = ["key", "secret", "token", "password", "prompt", "conversation", 
                 "file", "memory", "location", "lat", "lon", "address", "email", 
                 "phone", "name", "username"]
                 
    for k, v in props.items():
        k_lower = k.lower()
        if any(b in k_lower for b in blocklist):
            continue  # Skip PII
        clean_props[k] = v

    try:
        _posthog_client.capture(event_name, distinct_id=_get_anon_id(), properties=clean_props)
    except Exception:
        pass
