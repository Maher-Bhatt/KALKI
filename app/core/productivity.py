import os
import json
import time
import threading
from datetime import datetime, date
try:
    import win32gui
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

DATA_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "productivity.json")
_lock = threading.RLock()
_running = False

# Categorized by the actual process (.exe) name, not the window title — a
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
        return "Coding", exe_name or title
    if any(k in low for k in ["chrome", "edge", "firefox", "brave", "safari"]):
        return "Browsing", exe_name or title
    if any(k in low for k in ["discord", "slack", "teams", "whatsapp", "telegram"]):
        return "Communication", exe_name or title
    if any(k in low for k in ["youtube", "spotify", "netflix", "vlc", "player"]):
        return "Media / Music", exe_name or title

    # Genuinely unrecognized — keep the real app name rather than "Other",
    # so the daily summary can name it instead of hiding it.
    display = (exe_name or title or "Unknown").replace(".exe", "")
    return "Other", display

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

            exe_name = None
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                exe_name = psutil.Process(pid).name()
            except Exception:
                pass

            cat, app_display = _categorize(exe_name, title)
            today_str = date.today().isoformat()

            with _lock:
                data = _load_data()
                day = data.setdefault(today_str, {"categories": {}, "category_apps": {}})
                day["categories"][cat] = day["categories"].get(cat, 0) + elapsed
                apps_in_cat = day["category_apps"].setdefault(cat, {})
                apps_in_cat[app_display] = apps_in_cat.get(app_display, 0) + elapsed
                _save_data(data)
        except Exception:
            pass

def start_tracking():
    global _running
    if not _running and HAS_WIN32:
        _running = True
        threading.Thread(target=_tracker_loop, daemon=True).start()

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
        # "Other" is exactly the bucket that used to be a black box — always
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
