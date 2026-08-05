import re

with open(r'E:\PROJECT\KALKI-main\app\server.py', 'r', encoding='utf-8') as f:
    code = f.read()

replacement = """                "todayEvents": STATE.get("cached_today_events", []),
                "unreadImportant": STATE.get("cached_unread_count", 0),
                "nowPlaying": STATE.get("cached_now_playing"),
                "updateProgress": up_prog,
                "terminalLogs": _get_recent_logs()
            })
            return"""

code = code.replace("""                "todayEvents": STATE.get("cached_today_events", []),
                "unreadImportant": STATE.get("cached_unread_count", 0),
                "nowPlaying": STATE.get("cached_now_playing"),
                "updateProgress": up_prog,
            })
            return""", replacement)

log_helper = """
def _get_recent_logs():
    try:
        if not os.path.exists(LOG_PATH): return []
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [l.strip() for l in lines[-15:] if l.strip()]
    except:
        return []

UI_ALIVE_GRACE = 8.0  # seconds — if no /api/status in this long, UI is "dead"
"""

code = code.replace('UI_ALIVE_GRACE = 8.0  # seconds — if no /api/status in this long, UI is "dead"', log_helper)

with open(r'E:\PROJECT\KALKI-main\app\server.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("server.py patched for api/status logs")
