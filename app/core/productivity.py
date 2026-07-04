import os
import json
import time
import threading
from datetime import datetime, date
try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

DATA_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "productivity.json")
_lock = threading.RLock()
_running = False

def _categorize(title):
    title = title.lower()
    if any(k in title for k in ["code", "studio", "nvim", "vim", "sublime", "notepad", "github"]):
        return "Coding"
    if any(k in title for k in ["chrome", "edge", "firefox", "brave", "safari"]):
        return "Browsing"
    if any(k in title for k in ["discord", "slack", "teams", "whatsapp", "telegram"]):
        return "Communication"
    if any(k in title for k in ["youtube", "spotify", "netflix", "vlc", "player"]):
        return "Media"
    if any(k in title for k in ["steam", "epic", "game", "league", "valorant"]):
        return "Gaming"
    return "Other"

def _load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def _tracker_loop():
    global _running
    last_tick = time.time()
    
    while _running:
        time.sleep(5)
        now = time.time()
        elapsed = now - last_tick
        last_tick = now
        
        if not HAS_WIN32:
            continue
            
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title:
                continue
                
            cat = _categorize(title)
            today_str = date.today().isoformat()
            
            with _lock:
                data = _load_data()
                if today_str not in data:
                    data[today_str] = {}
                data[today_str][cat] = data[today_str].get(cat, 0) + elapsed
                _save_data(data)
        except Exception as e:
            pass

def start_tracking():
    global _running
    if not _running and HAS_WIN32:
        _running = True
        threading.Thread(target=_tracker_loop, daemon=True).start()

def get_daily_summary():
    """Returns a short brief for the previous day or today if previous is missing."""
    with _lock:
        data = _load_data()
        
    if not data:
        return ""
        
    # Find the most recent date before today
    today_str = date.today().isoformat()
    dates = sorted([d for d in data.keys() if d != today_str], reverse=True)
    
    target_date = dates[0] if dates else today_str
    day_data = data.get(target_date, {})
    
    if not day_data:
        return ""
        
    parts = []
    for cat, secs in sorted(day_data.items(), key=lambda x: x[1], reverse=True):
        if secs > 300: # only mention > 5 mins
            mins = int(secs / 60)
            if mins >= 60:
                parts.append(f"{mins//60}h {mins%60}m {cat.lower()}")
            else:
                parts.append(f"{mins}m {cat.lower()}")
                
    if not parts:
        return ""
        
    prefix = "Yesterday, you spent " if target_date != today_str else "So far today, you've spent "
    return prefix + ", ".join(parts) + "."
