import os
import sys

# Attempt to load telemetry libraries
try:
    import sentry_sdk
    import posthog
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

def init_telemetry(config):
    """
    Initialize Sentry for crash reporting and PostHog for product analytics.
    Only activates if keys are present in config.
    """
    if not TELEMETRY_AVAILABLE:
        return

    # 1. Crash Reporting (Sentry)
    sentry_dsn = getattr(config, "SENTRY_DSN", None)
    if sentry_dsn and not sentry_dsn.startswith("PASTE_"):
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
                environment="production" if getattr(sys, "frozen", False) else "development",
                release="kalki@1.0.4"
            )
            print("[TELEMETRY] Sentry Crash Reporting Initialized.")
        except Exception as e:
            print(f"[TELEMETRY] Sentry init failed: {e}")

    # 2. Product Analytics (PostHog)
    posthog_key = getattr(config, "POSTHOG_API_KEY", None)
    posthog_host = getattr(config, "POSTHOG_HOST", "https://app.posthog.com")
    
    if posthog_key and not posthog_key.startswith("PASTE_"):
        try:
            from posthog import Posthog
            global _posthog_client
            _posthog_client = Posthog(posthog_key, host=posthog_host)
            
            user_id = getattr(config, "OWNER_NAME", "Anonymous_User")
            _posthog_client.capture("app_started", distinct_id=user_id, properties={
                "version": "1.0.4",
                "os": os.name
            })
            print("[TELEMETRY] PostHog Analytics Initialized.")
        except Exception as e:
            print(f"[TELEMETRY] PostHog init failed: {e}")

def track_event(config, event_name, properties=None):
    """Safely track an event in PostHog."""
    if not TELEMETRY_AVAILABLE:
        return
        
    posthog_key = getattr(config, "POSTHOG_API_KEY", None)
    if not posthog_key or posthog_key.startswith("PASTE_"):
        return
        
    user_id = getattr(config, "OWNER_NAME", "Anonymous_User")
    try:
        if '_posthog_client' in globals():
            _posthog_client.capture(event_name, distinct_id=user_id, properties=(properties or {}))
    except Exception:
        pass
