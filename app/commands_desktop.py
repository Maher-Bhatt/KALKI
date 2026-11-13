"""Clipboard, note capture, site watching and PC control quick commands, moved out of
handle_local. Each function returns (handled, reply) or None."""

import re
import shutil
import subprocess
from typing import Any, Callable, Dict, Optional, Tuple

import config

Reply = Optional[Tuple[bool, str]]

_CLIPBOARD = ("decode my clipboard", "explain my clipboard", "read my clipboard", "what's in my clipboard",
              "what is in my clipboard", "check my clipboard", "analyze my clipboard", "clipboard")
_SITES = ("list watched sites", "my sites", "watched sites", "list my sites", "show watched sites",
          "what sites am i watching")
_CHECK_SITES = ("check my sites", "are my sites up", "site check", "check sites", "status of my sites",
                "are my websites up")
_CAPTURE = ("remember this", "save this", "capture this", "note this", "save that", "remember that")
_LOCK = ("lock", "lock pc", "lock my pc", "lock screen", "lock the screen", "lock computer", "lock the computer",
         "lock workstation", "lock the workstation")
_SHUTDOWN = ("shut down the pc", "shut down pc", "shutdown pc", "shut down", "shutdown the pc")
_MUTE = ("mute audio", "mute volume", "mute the audio", "mute pc", "toggle mute")
_RECYCLE = ("empty recycle bin", "empty the recycle bin", "clear recycle bin")
_VSCODE = ("open visual studio code", "open vs code", "start visual studio code")
_FIX_CODE = ("fix the code in my clipboard", "fix my code", "fix clipboard code", "fix this code")

# "remember that ...", "remember this: ...", "save note: ...", "note that ...". A bare "save X"
# isn't a note: "save my work" is something else.
_NOTE = re.compile(r"^(?:remember\s+(?:that\s+|this\s*:\s*|to\s+)?|save\s+(?:this|note|that)\s*:\s*|"
                   r"note\s+(?:that\s+|this\s*:\s*)?|take\s+a\s+note\s*:\s*)(.+)$", re.IGNORECASE)
_SITE_TARGET = re.compile(r"(?:https?://|\b[a-z0-9][a-z0-9-]*\.[a-z]{2,}\b)|\bthis (?:site|website|page)\b")


def _title() -> str:
    return str(getattr(config, "OWNER_TITLE", "") or "").strip()


def _done(sentence: str) -> str:
    title = _title()
    return f"{sentence[:-1]}, {title}." if title and sentence.endswith(".") else sentence


def _preview(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def clipboard_and_sites_command(t: str, raw: str, deps: Dict[str, Any]) -> Reply:
    """deps: clipboard, watchdog, browser_url, speak."""
    if t in _CLIPBOARD:
        spoken, detail = deps["clipboard"].analyze(deps["clipboard"].read_text() or "")
        spoken = spoken.replace("{t}", _title())
        return True, f"{spoken}\n\n```\n{detail}\n```" if detail else spoken

    watchdog = deps["watchdog"]
    if t.startswith(("watch ", "monitor ")) and _SITE_TARGET.search(t):
        rest = raw.split(None, 1)[1].strip()
        if rest.lower().startswith(("this", "current", "the current")):
            url = deps["browser_url"].get_active_url()
            if not url:
                return True, _done("I couldn't read your browser's address bar. Say watch, then the site.")
        else:
            url = rest.rstrip(".?!")
        return True, watchdog.add_site(url)
    if t.startswith(("unwatch ", "stop watching ", "remove site ")):
        return True, watchdog.remove_site(raw.split(None, 1)[1].strip())
    if t in _SITES:
        sites = watchdog.list_sites()
        if not sites:
            return True, _done("You aren't watching any sites yet.")
        return True, "Watching: " + ", ".join(s.get("label") or watchdog._host(s["url"]) for s in sites) + "."
    if t in _CHECK_SITES:
        deps["speak"](_done("Checking your sites."))
        return True, watchdog.summarize(watchdog.check_all(), _title())
    return None


def capture_command(t: str, text: str, state: Dict[str, Any], deps: Dict[str, Any]) -> Reply:
    """deps: notes, memory, clipboard, log. Saves notes, and what KALKI asked you for."""
    notes, memory, log = deps["notes"], deps["memory"], deps["log"]

    def save(content: str) -> None:
        notes.add_note(content)
        try:
            memory.add_memory(content, tags=["Personal"], importance=4)
        except Exception as exc:
            log(f"couldn't save note to memory: {exc}")

    if state.get("pending_note_capture"):
        state["pending_note_capture"] = False
        save(text)
        return True, _done(f"Saved to your notes: '{_preview(text)}'.")

    m = _NOTE.match(t)
    if m:
        content = m.group(1).strip()
        if len(content) > 1 and content.lower() not in ("this", "that", "it"):
            # The same words with the capitals you typed.
            start = text.lower().find(content)
            original = text[start:start + len(content)] if start >= 0 else content
            save(original)
            return True, _done(f"Saved to your notes: '{_preview(original)}'.")

    if t in _CAPTURE:
        clip = (deps["clipboard"].read_text() or "").strip()
        if clip:
            notes.add_note(clip)
            return True, _done(f"Saved your clipboard to notes: '{_preview(clip)}' ({len(clip.split())} words).")
        state["pending_note_capture"] = True
        return True, _done("Your clipboard is empty. What would you like me to remember?")
    return None


def pc_control_command(t: str, deps: Dict[str, Any]) -> Reply:
    """deps: lock, queue, clipboard, fix_code. Risky actions wait for approval."""
    queue = deps["queue"]
    if t in _LOCK:
        try:
            deps["lock"]()
        except Exception as exc:
            return True, f"I couldn't lock the PC: {exc}"
        return True, _done("Locking your PC now.")
    if t in _SHUTDOWN:
        def shutdown():
            subprocess.Popen(["shutdown.exe", "/s", "/t", "30"])
            return True, _done("Shutting down in thirty seconds.")
        return queue("Shut down your PC", shutdown)
    if t in _MUTE:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(New-Object -ComObject wscript.shell).SendKeys([char]173)"],
                           capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            return True, f"I couldn't toggle mute: {exc}"
        return True, "Toggled mute."
    if t in _RECYCLE:
        def empty():
            result = subprocess.run(["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction Stop"],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return True, f"The recycle bin wasn't emptied: {(result.stderr or result.stdout).strip()[:200]}"
            return True, _done("Recycle bin emptied.")
        return queue("Empty the recycle bin", empty)
    if t in _VSCODE:
        code = shutil.which("code")
        if not code:
            return True, "I couldn't find VS Code. Install it, or add it to PATH from VS Code's command palette."
        try:
            subprocess.Popen([code])
        except OSError as exc:
            return True, f"I couldn't open VS Code: {exc}"
        return True, _done("Opening Visual Studio Code.")
    if t in _FIX_CODE:
        clip = deps["clipboard"].read_text()
        if not clip:
            return True, _done("Your clipboard is empty.")
        try:
            fixed = deps["fix_code"]("Fix this code and return ONLY the raw fixed code. No markdown formatting, "
                                     "no explanations. Code:\n" + clip)
        except Exception as exc:
            return True, f"I couldn't fix the code: {exc}"
        if not fixed:
            return True, "I couldn't produce a fix for that code."
        if fixed.startswith("```"):
            lines = fixed.splitlines()
            fixed = "\n".join(lines[1:-1]) if len(lines) >= 2 else fixed
        deps["clipboard"].set_text(fixed.strip())
        return True, _done("Your clipboard now has the fixed code.")
    return None
