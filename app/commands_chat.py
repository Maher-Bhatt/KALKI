"""Small talk, help, PC stats and mail quick commands, moved out of handle_local.

Replies say only what's true: no claims about engines or percentages that nothing
measured. Each function returns a reply, or None if the text isn't its command.
"""

import os
import platform
import random
from typing import Callable, Iterable, Optional

import config

_GREETINGS = ("hi", "hello", "hey", "yo", "hey kalki", "hello kalki", "hi kalki", "are you there", "you there", "you up")
_HOW_ARE_YOU = ("how are you", "how are you doing", "how's it going", "how do you feel", "you good", "what's up",
                "whats up", "sup")
_HELP = ("what can you do", "help", "onboarding", "how to use you", "what are your features", "your capabilities",
         "what do you do", "what can i ask you", "commands")
_THANKS = ("thank you", "thanks", "thank you so much", "thanks kalki", "thx", "ty", "appreciate it", "good job",
           "well done", "nice", "good work", "perfect")
_WHO_ARE_YOU = ("who are you", "what are you", "introduce yourself", "your name")
_WHO_MADE_YOU = ("who made you", "who created you", "who built you", "who is your creator", "who's your maker",
                 "who developed you")
_KIND_WORDS = ("i love you", "love you", "you're the best", "you are the best", "you're awesome", "you are awesome",
               "good boy")
_MESSED_UP = ("i fucked up", "i messed up", "i did something stupid", "i broke it", "shit i broke", "what did i do")
_GOOD_NIGHT = ("good night", "goodnight", "gn", "i'm going to sleep", "im going to sleep", "going to bed")
_PC_STATS = ("system stats", "hardware status", "ram usage", "cpu usage", "system info", "specs", "hardware telemetry")
_PROCESSES = ("list processes", "running processes", "top processes", "tasklist", "show processes", "active tasks")
_FILES = ("list files", "dir", "ls", "show files", "current files", "workspace files")
_MAIL = ("check my mail", "check mail", "any mail", "any new mail", "any new email", "read my mail", "check my email",
         "show me my mail", "show my mail")
_IMPORTANT_MAIL = ("any important mail", "any important email", "important mail", "important email", "anything important")
_MARK_READ = ("mark my mail as read", "mark all mail as read", "mark mail as read", "mark emails as read",
              "mark all emails as read", "clear my inbox", "mark gmail as read")


def _title() -> str:
    return str(getattr(config, "OWNER_TITLE", "") or "").strip()


def _hi(word: str) -> str:
    """'Good morning' becomes 'Good morning, boss' when a title is set."""
    title = _title()
    return f"{word}, {title}" if title else word


def smalltalk_command(t: str, tools: Iterable[str] = (), modes: Iterable[str] = (),
                      spice: Callable[[str], str] = lambda s: s, hour: Optional[int] = None) -> Optional[str]:
    if t in _GREETINGS:
        from datetime import datetime
        hr = datetime.now().hour if hour is None else hour
        part = "Good morning" if 5 <= hr < 12 else "Good afternoon" if 12 <= hr < 17 else "Good evening" if 17 <= hr < 22 else "Hello"
        return spice(random.choice([
            f"{_hi(part)}. What can I do for you?",
            f"{_hi(part)}. I'm here. What are we working on?",
            f"{_hi(part)}. Ready when you are.",
        ]))
    if t in _HOW_ARE_YOU:
        return spice(random.choice([
            f"All good here. What do you need{', ' + _title() if _title() else ''}?",
            "Doing well, and ready to help. What's next?",
        ]))
    if t in _HELP:
        names = [n.replace("_", " ") for n in tools][:6]
        parts = ["I can answer questions, and look after your tasks, reminders, notes, calendar, mail and music."]
        if names:
            parts.append(f"When you ask, I can also use tools like {', '.join(names)}.")
        mode_list = list(modes)
        if mode_list:
            parts.append(f"Your routines: {', '.join(mode_list)}.")
        parts.append("Try 'remind me in 10 minutes', 'what's on my calendar' or 'take a note'.")
        return " ".join(parts)
    if t in _THANKS:
        return random.choice(["Anytime.", "My pleasure.", "Happy to help.", "Glad that worked."])
    if t in _WHO_ARE_YOU:
        return ("I'm KALKI, your personal AI assistant on this PC, named after the final avatar of Vishnu. "
                "I help with your day, your files and code, and keeping your PC safe.")
    if t in _WHO_MADE_YOU:
        return "KALKI was built by Maher Bhatt."
    if t in _KIND_WORDS:
        return random.choice(["That's kind of you.", "Thank you, likewise.", "Glad I could help."])
    if any(p in t for p in _MESSED_UP):
        return random.choice([
            "No panic. Show me the error and we'll fix it together.",
            "It happens. Paste what went wrong and I'll take a look.",
            "Let's sort it out. What changed just before it broke?",
        ])
    if t in _GOOD_NIGHT:
        return random.choice([f"{_hi('Good night')}.", "Rest well. I'll be here tomorrow.", "Sleep well."])
    return None


def pc_command(t: str, workspace: str) -> Optional[str]:
    """Stats, processes and files, measured now."""
    if t in _PC_STATS:
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.2)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            battery = psutil.sensors_battery()
        except Exception as exc:
            return f"I couldn't read this PC's stats: {exc}"
        lines = [
            f"**This PC ({platform.node()})**",
            f"• CPU: {cpu}%",
            f"• Memory: {mem.percent}% used ({round(mem.used / 2**20)} MB of {round(mem.total / 2**20)} MB)",
            f"• Disk: {disk.percent}% used ({round(disk.free / 2**30, 1)} GB free)",
            f"• System: {platform.system()} {platform.release()}",
        ]
        if battery:
            lines.append(f"• Battery: {int(battery.percent)}% ({'charging' if battery.power_plugged else 'on battery'})")
        return "\n".join(lines)
    if t in _PROCESSES:
        import psutil
        found = []
        for process in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = process.info
                mb = round(info["memory_info"].rss / 2**20, 1) if info.get("memory_info") else 0
                found.append((info["name"], info["pid"], mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        found.sort(key=lambda p: p[2], reverse=True)
        return "**Programs using the most memory:**\n" + "\n".join(f"• **{n}** (PID {pid}): {mb} MB" for n, pid, mb in found[:12])
    if t in _FILES:
        try:
            os.makedirs(workspace, exist_ok=True)
            names = sorted(os.listdir(workspace))
        except OSError as exc:
            return f"I couldn't read your workspace: {exc}"
        if not names:
            return f"Your workspace is empty ({workspace})."
        shown = "\n".join(f"• {n}" for n in names[:25])
        more = f"\n…and {len(names) - 25} more." if len(names) > 25 else ""
        return f"**Your workspace ({len(names)} items):**\n{shown}{more}"
    return None


def mail_command(t: str, mail) -> Optional[str]:
    if t in _MAIL:
        return mail.summary_for_speech(only_important=False, limit=5)
    if t in _IMPORTANT_MAIL:
        return mail.summary_for_speech(only_important=True, limit=8)
    if t in _MARK_READ:
        return mail.mark_all_read()
    return None
