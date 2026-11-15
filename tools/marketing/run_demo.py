"""KALKI's real app in a throwaway profile, filled with believable demo data, for marketing
screenshots and video. Nothing here touches the real profile. The calendar, weather and
AI replies are scripted so every screen looks complete and the same on every run."""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import json
import os
import sys
import tempfile
import time
import webbrowser
from datetime import datetime, timedelta

APP = str(REPO / "app")
home = tempfile.mkdtemp(prefix="kalki_demo_")
for k in ("HOME", "APPDATA", "LOCALAPPDATA", "USERPROFILE"):
    os.environ[k] = home
os.makedirs(os.path.join(home, "Downloads"), exist_ok=True)
os.environ["KALKI_TEST"] = "1"
sys.path.insert(0, APP)
os.chdir(APP)
webbrowser.open = lambda *a, **k: True

kalki_dir = os.path.join(home, "KALKI")
os.makedirs(os.path.join(kalki_dir, "data"), exist_ok=True)
THEME = os.environ.get("KALKI_DEMO_THEME", "light")
with open(os.path.join(kalki_dir, "user_config.json"), "w", encoding="utf-8") as f:
    json.dump({"OWNER_NAME": "Aarav", "OWNER_TITLE": "", "THEME_MODE": THEME, "SCREEN_TIME_ENABLED": True,
               "BRIEFING_SECTIONS": ["calendar", "reminders", "tasks", "weather"], "ROAST_MODE": False}, f)
with open(os.path.join(kalki_dir, "setup_complete.marker"), "w") as f:
    f.write("demo")

# A believable week of screen time.
week = {}
for i, (c, b, o) in enumerate([(19800, 7200, 2400), (22800, 6000, 3000), (16200, 9000, 1800), (25200, 5400, 3600),
                               (21000, 7800, 2700), (9000, 10800, 1200), (14400, 6600, 2100)]):
    day = (datetime.now().date() - timedelta(days=6 - i)).isoformat()
    week[day] = {"categories": {"Coding": c, "Browsing": b, "Communication": o},
                 "category_apps": {"Coding": {"code.exe": c}, "Browsing": {"msedge.exe": b}, "Communication": {"teams.exe": o}}}
with open(os.path.join(kalki_dir, "data", "productivity.json"), "w", encoding="utf-8") as f:
    json.dump(week, f)

import config  # noqa: E402

config.PORT = int(os.environ.get("KALKI_DEMO_PORT", "10031"))
config.GREET_ON_START = False
config.BRIEFING_ON_START = False
config.TELEGRAM_BOT_TOKEN = ""
import server  # noqa: E402
import briefing  # noqa: E402
import gcal  # noqa: E402
import tasks  # noqa: E402
import notes  # noqa: E402
import focus  # noqa: E402

server.speak = lambda *a, **k: None

# ── Scripted replies, by topic ───────────────────────────────────────────────
REPLIES = [
    (("saturday", "weekend"),
     "Here's a relaxed Saturday that still gets things done:\n\n"
     "**Morning**\n- 7:30: run or gym, 45 minutes\n- 9:00: slow breakfast\n\n"
     "**Midday**\n- 10:30 to 12:30: finish the quarterly report, phone on Do Not Disturb\n- Lunch at home\n\n"
     "**Afternoon and evening**\n- 4:00: coffee with Riya\n- 7:30: dinner with friends at Toit\n\n"
     "Want me to add reminders for the workout and the report?"),
    (("email", "reply", "mail"),
     "Here's a short, friendly reply:\n\n> Hi Priya, thanks for the update. Thursday at 3 PM works for me. "
     "I'll bring the revised numbers so we can finalise the plan. Best, Aarav\n\nShall I send it?"),
    (("focus on today", "focus today"),
     "Start with the quarterly report. It's due Friday and you have a clear hour before standup. "
     "After the design review at two, book the Bengaluru flights while prices are low. I'll keep things quiet while you work."),
    (("explain", "what is", "how does"),
     "In simple terms: a vector database stores meaning, not just words. Each note becomes a list of numbers that captures "
     "what it's about, so a search for \"trip ideas\" also finds \"weekend in Goa\" even though no word matches."),
]
REPLIES.insert(0, (("useless",),
     "Useless? Bro, I've reminded you to drink water three times today and you're still dehydrated. "
     "Your Saturday plan is done, your report's due Friday, and you're here picking fights with your laptop. 💀"))
DEFAULT_REPLY = "Sure. I've got that. Anything else you'd like me to take care of?"


def _reply_for(messages):
    text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            text = str(m.get("content", "")).lower()
            break
    for keys, reply in REPLIES:
        if any(k in text for k in keys):
            return reply
    return DEFAULT_REPLY


def _stream(messages, *a, **k):
    reply = _reply_for(messages)
    for i in range(0, len(reply), 6):
        time.sleep(0.012)
        yield reply[i:i + 6]


server.ask_ai = lambda messages, *a, **k: _reply_for(messages)
server.ask_ai_stream = _stream

# ── Calendar, weather and music for the briefing and panels ─────────────────
today = datetime.now().astimezone()


def _at(h, m):
    return today.replace(hour=h, minute=m, second=0, microsecond=0).isoformat()


EVENTS = [{"summary": "Team standup", "start": {"dateTime": _at(10, 0)}, "end": {"dateTime": _at(10, 15)}},
          {"summary": "Design review", "start": {"dateTime": _at(14, 0)}, "end": {"dateTime": _at(15, 0)}},
          {"summary": "Gym with Kabir", "start": {"dateTime": _at(18, 30)}, "end": {"dateTime": _at(19, 30)}}]
gcal.is_configured = lambda: True
gcal.today_events = lambda: EVENTS
gcal.upcoming_events = lambda n=5: EVENTS[:n]
briefing.BUILDERS["weather"] = lambda: {"text": "Sunny, 27°C now. High 30°, low 21°, 5% chance of rain.", "items": []}

import antivirus  # noqa: E402

antivirus.get_windows_defender_status = lambda: {
    "available": True, "service_enabled": True, "antivirus_enabled": True, "realtime_enabled": True,
    "tamper_protected": True, "signature_age_days": 0, "signatures_updated": today.strftime("%Y-%m-%dT06:10:00"),
    "quick_scan_age_days": 0, "full_scan_age_days": 6, "last_quick_scan": today.strftime("%Y-%m-%dT09:02:00"),
    "version": "4.18.26100.4"}

import media_mod  # noqa: E402

media_mod.now_playing_json = lambda: {"ok": True, "status": "Playing", "title": "Midnight Drive", "artist": "Lo-fi Lounge",
                                       "thumbnail": None, "source": "Spotify", "position": 72.0, "duration": 214.0,
                                       "reply": "Midnight Drive by Lo-fi Lounge (Playing)"}

# ── Your stuff ────────────────────────────────────────────────────────────────
for t in ("Finish the quarterly report", "Book flights to Bengaluru", "Renew car insurance", "Call the plumber about the kitchen sink"):
    tasks.add_task(t)
now = datetime.now()
tasks.add_reminder("Pick up dry cleaning", now.replace(hour=18, minute=0, second=0, microsecond=0) + (timedelta(days=1) if now.hour >= 18 else timedelta()))
tasks.add_reminder("Mom's birthday dinner", (now + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0))
tasks.add_reminder("Stretch and drink water", now + timedelta(minutes=40), repeat="daily")
for n in ("Q4 goals: grow weekly users 3x, ship voice mode, launch on the Microsoft Store #work",
          "Guest Wi-Fi password is on the fridge #home",
          "Gift ideas for Mom: silk scarf, the cookbook she mentioned #family",
          "Book recommendation from Riya: The Psychology of Money #ideas"):
    notes.add_note(n)
t0 = time.time()
focus.start(50, "Quarterly report", now=t0 - 3 * 3600)
focus.pop_finished(t0 - 3600)
focus.start(25, "Inbox zero", now=t0 - 50 * 60)
focus.stop(t0 - 30 * 60)

import core.productivity  # noqa: E402

core.productivity.start_tracking = lambda: None  # keep the demo week, don't record this PC's apps

print(f"KALKI demo studio on http://127.0.0.1:{config.PORT} (profile {home})", flush=True)
server.main()
