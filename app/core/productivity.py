import os
import json
import time
import threading
from runtime_paths import prepare_runtime
import safe_json

_runtime = prepare_runtime()
from datetime import datetime, date, timedelta
try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

DATA_FILE = os.path.join(_runtime.user_data_dir, "data", "productivity.json")
_lock = threading.RLock()
_running = False

# Categorized by the actual process (.exe) name, not the window title â€” a
# window titled "Untitled - Notepad" and one titled "budget.xlsx - Excel"
# both come from generic titles, but the process name always tells the truth.
_EXE_CATEGORIES = {
    "Coding": (
        "code.exe", "code - insiders.exe", "pycharm64.exe", "pycharm.exe",
        "devenv.exe", "sublime_text.exe", "notepad++.exe", "vim.exe", "nvim.exe",
        "webstorm64.exe", "clion64.exe", "rider64.exe", "androidstudio64.exe",
        "cursor.exe", "windsurf.exe", "idea64.exe", "atom.exe", "eclipse.exe",
    ),
    "Terminal / DevOps": (
        "windowsterminal.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
        "docker desktop.exe", "wsl.exe", "putty.exe", "gitkraken.exe",
        "git-bash.exe", "conemu64.exe",
    ),
    "Browsing": (
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
        "vivaldi.exe", "iexplore.exe",
    ),
    "Communication": (
        "discord.exe", "slack.exe", "teams.exe", "ms-teams.exe", "whatsapp.exe",
        "telegram.exe", "zoom.exe", "skype.exe", "outlook.exe", "thunderbird.exe",
    ),
    "Media / Music": (
        "spotify.exe", "vlc.exe", "wmplayer.exe", "netflix.exe", "musicbee.exe",
        "foobar2000.exe", "itunes.exe", "potplayer64.exe", "potplayermini64.exe",
    ),
    "Gaming": (
        "steam.exe", "epicgameslauncher.exe", "riotclientservices.exe",
        "valorant.exe", "leagueclient.exe", "battle.net.exe", "gta5.exe",
        "csgo.exe", "cs2.exe", "javaw.exe",
    ),
    "Office / Docs": (
        "excel.exe", "winword.exe", "powerpnt.exe", "onenote.exe",
        "acrobat.exe", "acrord32.exe", "notion.exe", "obsidian.exe",
    ),
    "Design / Media Creation": (
        "photoshop.exe", "illustrator.exe", "premiere pro.exe", "figma.exe",
        "blender.exe", "davinci resolve.exe", "audacity.exe", "affinity photo.exe",
    ),
    "File Management": (
        "explorer.exe", "totalcmd64.exe", "7zfm.exe", "winrar.exe",
    ),
}
_EXE_TO_CATEGORY = {exe: cat for cat, exes in _EXE_CATEGORIES.items() for exe in exes}


def _categorize(exe_name, title):
    """Returns (category, display_name). Falls back to title-keyword matching
    if the process name is unrecognized, and to a cleaned-up exe name (rather
    than a flat 'Other') so unrecognized time is still identifiable."""
    exe_l = (exe_name or "").lower()
    if exe_l in _EXE_TO_CATEGORY:
        return _EXE_TO_CATEGORY[exe_l], exe_name

    low = (title or "").lower()
    if any(k in low for k in ["code", "studio", "nvim", "vim", "sublime", "github"]):
        return "Coding", exe_name or "Unknown app"
    if any(k in low for k in ["chrome", "edge", "firefox", "brave", "safari"]):
        return "Browsing", exe_name or "Unknown app"
    if any(k in low for k in ["discord", "slack", "teams", "whatsapp", "telegram"]):
        return "Communication", exe_name or "Unknown app"
    if any(k in low for k in ["youtube", "spotify", "netflix", "vlc", "player"]):
        return "Media / Music", exe_name or "Unknown app"

    # Genuinely unrecognized â€” keep the real app name rather than "Other",
    # so the daily summary can name it instead of hiding it.
    display = (exe_name or "Unknown app").replace(".exe", "")  # never the window title: it can name your documents
    return "Other", display

def _load_data():
    return safe_json.read_json(DATA_FILE, {})

def _save_data(data):
    safe_json.write_json(DATA_FILE, data)


# ── What's tracked, and when ─────────────────────────────────────────────
# Only the app's process name, its category and seconds per day are stored,
# never window titles. Nothing leaves the PC. Time while the PC is idle or
# asleep doesn't count.

TICK_SECONDS = 5
IDLE_SECONDS = 120          # no keyboard or mouse for this long: you're away
MAX_TICK_SECONDS = 15       # a longer gap means the PC slept; don't credit it
FLUSH_SECONDS = 30          # write to disk at most this often
DEFAULT_RETENTION_DAYS = 30

_pending = {}               # {date: {category: {app: seconds}}} not yet written
_last_flush = 0.0
_paused_until = 0.0


def _setting(name, default):
    try:
        import config
        value = getattr(config, name, None)
    except ImportError:
        value = None
    return default if value is None else value


def is_enabled():
    """Screen time is opt-in. An install that was already tracking before the
    setting existed keeps tracking until you turn it off."""
    value = _setting("SCREEN_TIME_ENABLED", None)
    if value is None:
        return bool(_load_data())
    return bool(value)


def excluded_apps():
    return {str(a).strip().lower() for a in (_setting("SCREEN_TIME_EXCLUDED", []) or []) if str(a).strip()}


def retention_days():
    try:
        return max(1, min(365, int(_setting("SCREEN_TIME_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))))
    except (TypeError, ValueError):
        return DEFAULT_RETENTION_DAYS


def paused_until():
    return _paused_until if _paused_until > time.time() else 0.0


def pause(minutes):
    global _paused_until
    minutes = max(1, min(24 * 60, int(minutes)))
    flush(force=True)
    _paused_until = time.time() + minutes * 60
    return _paused_until


def resume():
    global _paused_until
    _paused_until = 0.0


def _idle_seconds():
    """Seconds since the last keyboard or mouse input, or 0 if Windows can't say."""
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except (AttributeError, OSError):
        return 0.0


def record(exe_name, title, elapsed, idle_seconds=0.0, today=None):
    """Count one tick for the window in front. Returns what was counted, or None and why not."""
    if not is_enabled():
        return None, "off"
    if paused_until():
        return None, "paused"
    if idle_seconds >= IDLE_SECONDS:
        return None, "idle"
    if elapsed <= 0 or elapsed > MAX_TICK_SECONDS:
        return None, "gap"
    if (exe_name or "").lower() in excluded_apps():
        return None, "excluded"
    cat, app = _categorize(exe_name, title)
    day = (today or date.today()).isoformat()
    with _lock:
        apps = _pending.setdefault(day, {}).setdefault(cat, {})
        apps[app] = apps.get(app, 0) + elapsed
    return (cat, app), None


def _prune(data, keep_days, today=None):
    cutoff = ((today or date.today()) - timedelta(days=keep_days - 1)).isoformat()
    for day in [d for d in data if d < cutoff]:
        del data[day]


def flush(force=False, today=None):
    """Write pending time to disk, merged into what's stored, and drop days past the retention limit."""
    global _last_flush
    with _lock:
        if not force and time.time() - _last_flush < FLUSH_SECONDS:
            return False
        _last_flush = time.time()
        pending = dict(_pending)
        _pending.clear()
        data = _load_data()
        for day, cats in pending.items():
            stored = data.setdefault(day, {"categories": {}, "category_apps": {}})
            if "categories" not in stored:  # old flat format: {category: seconds}
                stored = data[day] = {"categories": dict(stored), "category_apps": {}}
            for cat, apps in cats.items():
                stored["categories"][cat] = stored["categories"].get(cat, 0) + sum(apps.values())
                bucket = stored["category_apps"].setdefault(cat, {})
                for app, secs in apps.items():
                    bucket[app] = bucket.get(app, 0) + secs
        _prune(data, retention_days(), today)
        if pending or data != _load_data():
            _save_data(data)
        return True


def _tracker_loop():
    global _running
    last_tick = time.time()

    while _running:
        time.sleep(TICK_SECONDS)
        now = time.time()
        elapsed = now - last_tick
        last_tick = now

        if not HAS_WIN32:
            continue

        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if hwnd and title:
                exe_name = None
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    exe_name = psutil.Process(pid).name()
                except (psutil.Error, OSError, ValueError):
                    pass
                record(exe_name, title, elapsed, _idle_seconds())
            flush()
        except Exception as e:  # the tracker must keep running
            print(f"[screen time] tick failed: {e}")


def tracking_status():
    return {"available": HAS_WIN32, "active": _running and is_enabled() and not paused_until(),
            "enabled": is_enabled(), "pausedUntil": paused_until(), "running": _running,
            "retentionDays": retention_days(), "excluded": sorted(excluded_apps()), "dataFile": DATA_FILE}


def start_tracking():
    """Start the background thread. It only counts time while screen time is turned on."""
    global _running
    if not _running and HAS_WIN32:
        _running = True
        import atexit
        atexit.register(lambda: flush(force=True))  # keep the last few seconds when KALKI closes
        threading.Thread(target=_tracker_loop, daemon=True, name="screen-time").start()


# ── Reading and deleting what's stored ───────────────────────────────────

def stored():
    """Everything on disk plus anything not yet written: exactly what KALKI keeps."""
    flush(force=True)
    with _lock:
        return _load_data()


def week(today=None, days=7):
    """Per-day totals and the top apps over the last `days` days, oldest day first."""
    today = today or date.today()
    data = stored()
    out, apps = [], {}
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        day = data.get(d, {})
        cats = day.get("categories", day if "categories" not in day else {})
        cats = {c: s for c, s in cats.items() if isinstance(s, (int, float))}
        out.append({"date": d, "total": round(sum(cats.values())), "categories": {c: round(s) for c, s in cats.items()}})
        for cat, bucket in (day.get("category_apps") or {}).items():
            for app, secs in bucket.items():
                key = (app, cat)
                apps[key] = apps.get(key, 0) + secs
    top = sorted(apps.items(), key=lambda kv: -kv[1])[:10]
    return {"days": out, "total": sum(d["total"] for d in out),
            "topApps": [{"app": a, "category": c, "seconds": round(s)} for (a, c), s in top]}


def _settle_choice():
    """Deleting data must not change whether tracking is on, so pin the inferred choice first."""
    try:
        import config
    except ImportError:
        return
    if getattr(config, "SCREEN_TIME_ENABLED", None) is None:
        config.SCREEN_TIME_ENABLED = is_enabled()


def clear(day=None):
    """Delete all stored screen time, or one day of it. Returns how many days were removed."""
    _settle_choice()
    with _lock:
        if day:
            _pending.pop(day, None)
        else:
            _pending.clear()
        data = _load_data()
        removed = [d for d in data if day is None or d == day]
        for d in removed:
            del data[d]
        _save_data(data)
    return len(removed)


def forget_app(app):
    """Remove one app from every stored day, for example after excluding it."""
    name = str(app).strip().lower()
    short = name[:-4] if name.endswith(".exe") else name
    flush(force=True)
    removed = 0.0
    with _lock:
        data = _load_data()
        for day in data.values():
            for cat, bucket in list((day.get("category_apps") or {}).items()):
                for a in [a for a in bucket if a.lower() in (name, short, short + ".exe")]:
                    secs = bucket.pop(a)
                    removed += secs
                    day["categories"][cat] = max(0, day["categories"].get(cat, 0) - secs)
                    if not day["categories"][cat]:
                        day["categories"].pop(cat)
                if not bucket:
                    day["category_apps"].pop(cat)
        _save_data(data)
    return round(removed)


def _fmt(secs):
    mins = int(secs / 60)
    if mins >= 60:
        return f"{mins//60}h {mins%60}m"
    return f"{mins}m"

def get_daily_summary():
    """Returns a short brief for the previous day or today if previous is missing.
    Names the specific top app inside each category (and inside 'Other'
    specifically) rather than a flat, unhelpful bucket list."""
    with _lock:
        data = _load_data()

    if not data:
        return ""

    today_str = date.today().isoformat()
    dates = sorted([d for d in data.keys() if d != today_str], reverse=True)
    target_date = dates[0] if dates else today_str
    day_data = data.get(target_date, {})

    # Legacy format (pre-detailed-tracking): flat {category: seconds}, no app detail.
    if "categories" not in day_data:
        categories, category_apps = day_data, {}
    else:
        categories = day_data.get("categories", {})
        category_apps = day_data.get("category_apps", {})

    if not categories:
        return ""

    parts = []
    for cat, secs in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if secs <= 300:
            continue
        line = f"{_fmt(secs)} {cat.lower()}"
        apps_here = category_apps.get(cat, {})
        top_apps = sorted(apps_here.items(), key=lambda x: x[1], reverse=True)
        # "Other" is exactly the bucket that used to be a black box â€” always
        # name what was actually in it. For recognized categories, only add
        # the app name if one app clearly dominates (otherwise it's noise).
        if cat == "Other" and top_apps:
            named = ", ".join(a for a, _ in top_apps[:2])
            line += f" ({named})"
        elif top_apps and top_apps[0][1] > secs * 0.6:
            line += f" (mostly {top_apps[0][0]})"
        parts.append(line)

    if not parts:
        return ""

    prefix = "Yesterday, you spent " if target_date != today_str else "So far today, you've spent "
    return prefix + ", ".join(parts) + "."




