import json
import os
import time
import threading

_lock = threading.RLock()

def get_data_dir():
    import runtime_paths
    return runtime_paths.prepare_runtime().user_data_dir

def get_alerts_file():
    return os.path.join(get_data_dir(), "oversight_alerts.json")

def record_alert(kind: str, message: str, severity: str = "info"):
    with _lock:
        file_path = get_alerts_file()
        entries = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                pass
                
        entries.append({
            "ts": time.time(),
            "kind": kind,
            "message": message,
            "severity": severity
        })
        
        entries = entries[-50:]
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            tmp = file_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, file_path)
        except Exception:
            pass

def recent_alerts(limit: int = 20):
    with _lock:
        file_path = get_alerts_file()
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
            return entries[::-1][:limit]
        except Exception:
            return []

def get_status():
    import config
    import psutil
    
    return {
        "alerts": recent_alerts(),
        "watchedSites": getattr(config, 'WATCHED_SITES', []),
        "thresholds": getattr(config, 'THRESHOLDS', {})
    }
