import json
import os
import time

def get_data_dir():
    import runtime_paths
    return runtime_paths.prepare_runtime().user_data_dir

def get_alerts_file():
    return os.path.join(get_data_dir(), "oversight_alerts.json")

def record_alert(kind: str, message: str, severity: str = "info"):
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
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass

def recent_alerts(limit: int = 20):
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
