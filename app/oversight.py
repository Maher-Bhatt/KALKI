import os
import sys
import time
import threading

import safe_json

_lock = threading.RLock()

def get_data_dir():
    import runtime_paths
    return runtime_paths.prepare_runtime().user_data_dir

def get_alerts_file():
    return os.path.join(get_data_dir(), "oversight_alerts.json")

def record_alert(kind: str, message: str, severity: str = "info"):
    with _lock:
        file_path = get_alerts_file()
        try:
            entries = safe_json.read_json(file_path, [])
            entries.append({
                "ts": time.time(),
                "kind": kind,
                "message": message,
                "severity": severity
            })
            safe_json.write_json(file_path, entries[-50:])
        except OSError as exc:
            # An alert that can't be saved must still show up somewhere.
            sys.stderr.write(f"[KALKI] couldn't save alert ({exc}): [{severity}] {kind}: {message}\n")


def recent_alerts(limit: int = 20):
    with _lock:
        try:
            return safe_json.read_json(get_alerts_file(), [])[::-1][:limit]
        except OSError:
            return []

def get_status():
    import config
    import psutil
    
    return {
        "alerts": recent_alerts(),
        "watchedSites": getattr(config, 'WATCHED_SITES', []),
        "thresholds": getattr(config, 'THRESHOLDS', {})
    }
