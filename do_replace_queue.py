import os, re

server_path = "e:/KALKI-main/app/server.py"
with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace _queue_confirmation block
pattern = r"_pending_lock = threading\.Lock\(\)\n_pending_action = None\n_PENDING_TTL = 30.*?(?=\n\n\ndef _is_sensitive_command)"
new_queue = """_pending_lock = threading.Lock()
_pending_approvals = {}
_approval_id_seq = 0
_PENDING_TTL = 30

_activity_log = []
_activity_id_seq = 0
_activity_lock = threading.Lock()

def add_activity(action, source, reversible=False, undo_fn=None):
    global _activity_id_seq
    with _activity_lock:
        _activity_id_seq += 1
        act = {
            "id": str(_activity_id_seq),
            "action": action,
            "source": source,
            "time": time.time(),
            "reversible": reversible,
            "undo_fn": undo_fn,
        }
        _activity_log.append(act)
        if len(_activity_log) > 500:
            _activity_log.pop(0)

def _queue_confirmation(description, action):
    global _approval_id_seq
    if not getattr(config, "REQUIRE_DANGEROUS_CONFIRMATION", True):
        return action()
    with _pending_lock:
        _approval_id_seq += 1
        aid = str(_approval_id_seq)
        _pending_approvals[aid] = {
            "id": aid,
            "description": description,
            "action": action,
            "expires": time.time() + _PENDING_TTL,
        }
    return True, f"{description}. Say confirm within {_PENDING_TTL} seconds."

def _consume_confirmation(command):
    global _pending_approvals
    
    clean_command = "".join(c for c in command if c not in ".,!?").strip().lower()
    
    if clean_command in ("cancel", "never mind", "nevermind"):
        with _pending_lock:
            had_pending = len(_pending_approvals) > 0
            _pending_approvals.clear()
        return (True, "Cancelled.") if had_pending else None
    if clean_command not in ("confirm", "yes confirm", "confirm it", "do it"):
        return None
        
    with _pending_lock:
        if not _pending_approvals:
            return True, "There is no active action to confirm."
        # Confirm the most recent one
        aid = max(_pending_approvals.keys(), key=lambda k: int(k))
        pending = _pending_approvals.pop(aid)
        
    if pending["expires"] < time.time():
        return True, "There is no active action to confirm."
    return pending["action"]()"""

content, count = re.subn(pattern, new_queue, content, flags=re.DOTALL)
print(f"Replaced {count} times")

with open(server_path, "w", encoding="utf-8") as f:
    f.write(content)
