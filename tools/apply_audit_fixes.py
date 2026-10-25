import os
import re

def patch_server():
    path = "app/server.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Voice default in _build_edge_tts_file
    old_voice = '    voice = "en-GB-RyanNeural"'
    new_voice = '    voice = getattr(config, "TTS_VOICE", "") or "en-US-AndrewMultilingualNeural"'
    if old_voice in content:
        content = content.replace(old_voice, new_voice, 1)
        print("Patched server.py: voice default to Andrew")
    else:
        print("Warning: old voice line not found in server.py")

    # 2. _SPEECH_FILTERS: strip [TASK:...], [REMIND:...], [NOTE:...], etc.
    old_filter = '_SPEECH_FILTERS = [\n    (_re_speech.compile(r"```[\\s\\S]*?```"), " "),'
    new_filter = '_SPEECH_FILTERS = [\n    (_re_speech.compile(r"\\[(?:TASK|REMIND|NOTE):[\\s\\S]*?\\]", _re_speech.IGNORECASE), " "),\n    (_re_speech.compile(r"\\[[A-Z_]+:\\s*[^\\]]+\\]"), " "),\n    (_re_speech.compile(r"```[\\s\\S]*?```"), " "),'
    if old_filter in content:
        content = content.replace(old_filter, new_filter, 1)
        print("Patched server.py: _SPEECH_FILTERS with action tag strippers")
    else:
        print("Warning: _SPEECH_FILTERS target not found in server.py")

    # 3. _get_volume_iface COM initialization
    old_vol = '''def _get_volume_iface():
    if not PYCAW_OK:
        return None
    devices = AudioUtilities.GetSpeakers()'''
    new_vol = '''def _get_volume_iface():
    if not PYCAW_OK:
        return None
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    devices = AudioUtilities.GetSpeakers()'''
    if old_vol in content:
        content = content.replace(old_vol, new_vol, 1)
        print("Patched server.py: _get_volume_iface with CoInitialize")
    else:
        print("Warning: _get_volume_iface target not found in server.py")

    # 4. /api/chat tag parsing and execution
    old_chat_stream = '''                reply_str = "".join(full_reply)
                if not client_speech:
                    speak(reply_str)
                append_history(user_text, reply_str)
                _record_exchange(reply_str)'''

    new_chat_stream = '''                reply_str = "".join(full_reply)
                import re as _re_act
                for task_match in _re_act.finditer(r"\\[TASK:\\s*(.+?)\\]", reply_str):
                    taskmod.add_task(task_match.group(1).strip())
                for rem_match in _re_act.finditer(r"\\[REMIND:\\s*(.+?)\\s*@\\s*(.+?)\\]", reply_str):
                    taskmod.add_reminder(rem_match.group(1).strip(), rem_match.group(2).strip())
                spoken_reply = _re_act.sub(r"\\[(?:TASK|REMIND|NOTE):.+?\\]", "", reply_str).strip()
                if not client_speech:
                    speak(spoken_reply or reply_str)
                append_history(user_text, spoken_reply or reply_str)
                _record_exchange(spoken_reply or reply_str)'''
    if old_chat_stream in content:
        content = content.replace(old_chat_stream, new_chat_stream, 1)
        print("Patched server.py: /api/chat stream tag extraction")
    else:
        print("Warning: old_chat_stream not found in server.py")

    old_chat_sync = '''                reply = maybe_add_joke_offer(user_text, reply)
                if not client_speech:
                    speak(reply)
                append_history(user_text, reply)
                _record_exchange(reply)'''

    new_chat_sync = '''                reply = maybe_add_joke_offer(user_text, reply)
                import re as _re_act
                for task_match in _re_act.finditer(r"\\[TASK:\\s*(.+?)\\]", reply):
                    taskmod.add_task(task_match.group(1).strip())
                for rem_match in _re_act.finditer(r"\\[REMIND:\\s*(.+?)\\s*@\\s*(.+?)\\]", reply):
                    taskmod.add_reminder(rem_match.group(1).strip(), rem_match.group(2).strip())
                reply = _re_act.sub(r"\\[(?:TASK|REMIND|NOTE):.+?\\]", "", reply).strip()
                if not client_speech:
                    speak(reply)
                append_history(user_text, reply)
                _record_exchange(reply)'''
    if old_chat_sync in content:
        content = content.replace(old_chat_sync, new_chat_sync, 1)
        print("Patched server.py: /api/chat sync tag extraction")
    else:
        print("Warning: old_chat_sync not found in server.py")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def patch_kalki_setup_wizard():
    path = "app/kalki_setup_wizard.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace('"TTS_VOICE": "en-GB-RyanNeural"', '"TTS_VOICE": "en-US-AndrewMultilingualNeural"')
    content = content.replace('self.config_data.get("TTS_VOICE", "en-GB-RyanNeural")', 'self.config_data.get("TTS_VOICE", "en-US-AndrewMultilingualNeural")')
    content = content.replace('"Ryan (British, stable KALKI voice)"', '"Andrew (US, natural male, default)"')
    content = content.replace('current_voice_label = next(\n            (label for label, val in self.voice_options.items() if val == current_voice),\n            "Ryan (British, stable KALKI voice)",\n        )', 'current_voice_label = next(\n            (label for label, val in self.voice_options.items() if val == current_voice),\n            "Andrew (US, natural male, default)",\n        )')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched kalki_setup_wizard.py: Andrew voice default")


def patch_tasks():
    path = "app/tasks.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_add_rem = '''def add_reminder(text: str, due: Union[datetime, str]) -> int:
    """
    Schedule a reminder.
    
    Args:
        text (str): The reminder text.
        due (Union[datetime, str]): The due date/time as a datetime object or ISO string.
        
    Returns:
        int: The assigned reminder ID.
    """
    if isinstance(due, datetime):
        due = due.isoformat(timespec="seconds")
    with _lock:'''

    new_add_rem = '''def add_reminder(text: str, due: Union[datetime, str]) -> int:
    """
    Schedule a reminder.
    
    Args:
        text (str): The reminder text.
        due (Union[datetime, str]): The due date/time as a datetime object or ISO string.
        
    Returns:
        int: The assigned reminder ID.
    """
    if isinstance(due, datetime):
        due = due.isoformat(timespec="seconds")
    elif isinstance(due, str):
        # Validate or parse natural language due strings
        parsed = False
        try:
            datetime.fromisoformat(due)
            parsed = True
        except (ValueError, TypeError):
            parsed = False
        if not parsed:
            dt, _ = parse_when(due)
            if not dt:
                dt, _ = parse_when(f"at {due}")
            if not dt:
                dt, _ = parse_when(f"in {due}")
            if dt:
                due = dt.isoformat(timespec="seconds")
            else:
                due = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
    with _lock:'''

    if old_add_rem in content:
        content = content.replace(old_add_rem, new_add_rem, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched tasks.py: add_reminder natural language parsing")
    else:
        print("Warning: old_add_rem not found in tasks.py")


def patch_main_app():
    path = "app/main_app.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_close = '''        def close(self):
            # The HUD close button is a background/minimize action. The tray
            # Quit command is the explicit full-process exit path.
            if self.window:
                self.window.hide()'''

    new_close = '''        def close(self):
            if self.window:
                if getattr(config, "ENABLE_GLOBAL_HOTKEY", False):
                    self.window.hide()
                else:
                    try:
                        self.window.destroy()
                    except Exception:
                        os._exit(0)'''

    if old_close in content:
        content = content.replace(old_close, new_close, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched main_app.py: WebApi.close destroys window when no hotkey active")
    else:
        print("Warning: old_close not found in main_app.py")


def patch_workflows():
    path = "app/workflows.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add get_custom_routines alias
    if "def get_custom_routines():" not in content:
        content += '''\n\ndef get_custom_routines():
    """Return loaded custom routines dictionary."""
    load_custom_routines()
    if os.path.exists(CUSTOM_ROUTINES_PATH):
        try:
            with open(CUSTOM_ROUTINES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
'''
        print("Patched workflows.py: added get_custom_routines()")

    # 2. Normalize mode names in run_mode
    old_run_mode = '''def run_mode(mode_name, *, speak_fn=None, set_volume_fn=None,
             open_url_fn=None, lock_fn=None):
    """Execute a workflow. Pass in callable hooks from the server."""
    mode_name = mode_name.lower().strip()
    if mode_name not in MODES:'''

    new_run_mode = '''def run_mode(mode_name, *, speak_fn=None, set_volume_fn=None,
             open_url_fn=None, lock_fn=None):
    """Execute a workflow. Pass in callable hooks from the server."""
    mode_name = mode_name.lower().strip()
    if mode_name not in MODES:
        if f"{mode_name} mode" in MODES:
            mode_name = f"{mode_name} mode"
        elif mode_name.endswith(" mode") and mode_name[:-5].strip() in MODES:
            mode_name = mode_name[:-5].strip()
        else:
            matched = find_mode(mode_name)
            if matched:
                mode_name = matched
    if mode_name not in MODES:'''

    if old_run_mode in content:
        content = content.replace(old_run_mode, new_run_mode, 1)
        print("Patched workflows.py: mode normalization in run_mode()")
    else:
        print("Warning: old_run_mode not found in workflows.py")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def patch_vision():
    path = "app/vision.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_models = '''VISION_MODELS = [
    # Groq vision models — ordered by preference (fastest → most capable)
    # llama-4-scout: fast, 16-expert MoE, great for screenshots
    "meta-llama/llama-4-scout-17b-16e-instruct",
    # llama-4-maverick: higher quality, 128-expert MoE, slower
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    # llava fallback: reliable older vision model, always available on Groq
    "llava-v1.5-7b-4096-preview",
]'''

    new_models = '''VISION_MODELS = [
    # Groq active vision models — ordered by preference (fastest → most capable)
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
    # Experimental and preview models
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    # Reliable fallback
    "llava-v1.5-7b-4096-preview",
]'''

    if old_models in content:
        content = content.replace(old_models, new_models, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched vision.py: active Groq vision models added")
    else:
        print("Warning: old_models not found in vision.py")


def patch_notify():
    path = "app/notify.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    new_notify = '''import os
import sys

def notify_desktop(title: str, message: str):
    """
    Shows a native desktop notification using plyer, if available.
    Degrades silently if unsupported.
    """
    try:
        from plyer import notification
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(sys.executable), "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "assets", "kalki_icon.ico")),
        ]
        icon_path = next((p for p in candidates if os.path.exists(p)), None)
        notification.notify(
            title=title,
            message=message,
            app_name="KALKI",
            app_icon=icon_path,
            timeout=5
        )
    except Exception:
        pass
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_notify)
    print("Patched notify.py: robust icon path resolution")


def patch_watchdog():
    path = "app/watchdog.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_host = '''def _host(url):
    u = url.replace("https://", "").replace("http://", "").strip("/")
    return u.split("/")[0]'''

    new_host = '''from urllib.parse import urlsplit

def _parse_host_port(url):
    u = url if "://" in url else "https://" + url
    parsed = urlsplit(u)
    host = parsed.hostname or url
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port

def _host(url):
    h, _ = _parse_host_port(url)
    return h'''

    if old_host in content:
        content = content.replace(old_host, new_host, 1)

    old_cert = '''def cert_days_left(host, port=443):
    """Days until the TLS cert expires, or None."""
    try:
        ctx = ssl.create_default_context()'''

    new_cert = '''def cert_days_left(host, port=443):
    """Days until the TLS cert expires, or None."""
    try:
        if ":" in str(host) and not str(host).startswith("["):
            parts = str(host).split(":", 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass
        ctx = ssl.create_default_context()'''

    if old_cert in content:
        content = content.replace(old_cert, new_cert, 1)

    old_check = '''    if url.startswith("https://"):
        res["cert_days"] = cert_days_left(host)'''

    new_check = '''    if url.startswith("https://"):
        h, p = _parse_host_port(url)
        res["cert_days"] = cert_days_left(h, port=p)'''

    if old_check in content:
        content = content.replace(old_check, new_check, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched watchdog.py: robust host and port parsing")


def patch_oversight():
    path = "app/oversight.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    new_oversight = '''import json
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
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_oversight)
    print("Patched oversight.py: thread lock and atomic file writes")


def patch_semantic_memory():
    path = "app/semantic_memory.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_save = '''    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception:
            pass'''

    new_save = '''    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except Exception:
            pass'''

    if old_save in content:
        content = content.replace(old_save, new_save, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched semantic_memory.py: atomic _save()")
    else:
        print("Warning: old_save not found in semantic_memory.py")


if __name__ == "__main__":
    patch_server()
    patch_kalki_setup_wizard()
    patch_tasks()
    patch_main_app()
    patch_workflows()
    patch_vision()
    patch_notify()
    patch_watchdog()
    patch_oversight()
    patch_semantic_memory()
    print("All backend patches applied successfully!")
