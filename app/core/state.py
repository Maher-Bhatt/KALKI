import time
import threading

import config

STATE = {
    "speaking": False,
    "model": getattr(config, "GROQ_MODEL", "llama3-70b-8192"),
    "started_at": time.time(),
    # UI presence + voice-driven exchange tracking
    "ui_last_ping": 0.0,
    "wake_pending": False,
    "conversation_seq": 0,
    "recent_exchange": None,
    "listener_paused": False,
    "last_joke_offer": 0.0,
    "joke_offer_pending": False,
    
    # System metrics
    "cpu": 0.0,
    "ram": 0.0,
    "disk": 0.0,
    
    # Events
    "announced_events_day": None,
    "announced_events": set(),
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
