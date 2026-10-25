"""KALKI Desktop Companion Pet — Always-On-Top Floating Overlay.

Stays on the screen corner even when the main app is closed or minimized.
Reacts to system music (dancing), provides quick voice/text prompt bubble on click,
and enables instant one-click access to KALKI features.
"""

import os
import sys
import time
import json
import subprocess

if sys.argv and sys.argv[0]:
    try:
        sys.argv[0] = os.path.abspath(sys.argv[0])
    except Exception:
        pass

try:
    import ctypes
    user32 = ctypes.windll.user32
    SCREEN_WIDTH = user32.GetSystemMetrics(0)
    SCREEN_HEIGHT = user32.GetSystemMetrics(1)
except Exception:
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080

from runtime_paths import prepare_runtime
_runtime = prepare_runtime()
BASE_DIR = _runtime.app_root

# Isolate WebView2 profile so pet never collides with main KALKI instance
pet_profile_dir = os.path.join(_runtime.user_data_dir, "pet_webview_profile")
os.makedirs(pet_profile_dir, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = pet_profile_dir

import config
import webview

class PetApi:
    def open_main_app(self):
        """Brings the main KALKI window to foreground or launches it."""
        # 1. Trigger local server wake endpoint
        try:
            import urllib.request
            port = getattr(config, "PORT", 8888)
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/wake",
                data=b'{"cmd":""}',
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=1.5)
        except Exception:
            pass

        # 2. Find and foreground native window via Win32
        try:
            import win32gui
            import win32con
            import win32process
            import win32api
            target_hwnds = []
            def _enum_cb(h, _):
                if win32gui.IsWindowVisible(h):
                    title = win32gui.GetWindowText(h)
                    if "KALKI AI Assistant" in title or title == "KALKI":
                        target_hwnds.append(h)
            win32gui.EnumWindows(_enum_cb, None)
            for hwnd in target_hwnds:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                try:
                    fore_hwnd = win32gui.GetForegroundWindow()
                    fore_tid, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                    cur_tid = win32api.GetCurrentThreadId()
                    if fore_tid != cur_tid:
                        win32process.AttachThreadInput(cur_tid, fore_tid, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.BringWindowToTop(hwnd)
                        win32process.AttachThreadInput(cur_tid, fore_tid, False)
                    else:
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.BringWindowToTop(hwnd)
                except Exception:
                    win32gui.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass

        # 3. If not open, launch main KALKI app process
        try:
            if getattr(sys, "frozen", False):
                main_exe = os.path.join(BASE_DIR, "KALKI.exe")
                if os.path.exists(main_exe):
                    subprocess.Popen([main_exe], cwd=BASE_DIR)
                    return True
            else:
                main_script = os.path.join(BASE_DIR, "main_app.py")
                subprocess.Popen([sys.executable, main_script], cwd=BASE_DIR)
                return True
        except Exception as e:
            print(f"[DesktopPet] Failed opening main app: {e}")
        return False

    def get_music_state(self):
        """Polls active Windows Media Control session directly in native Python."""
        try:
            import media_mod
            return media_mod.now_playing_json()
        except Exception:
            return {"status": "stopped", "title": ""}

    def get_pet_state(self):
        """Loads pet state from user data or defaults."""
        try:
            pet_file = os.path.join(_runtime.user_data_dir, "pet_state.json")
            if os.path.exists(pet_file):
                with open(pet_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"species": "gobi", "name": "Gobi", "sound": True, "enabled": True}

    def save_pet_state(self, state_dict):
        """Saves pet state to user data directory."""
        try:
            pet_file = os.path.join(_runtime.user_data_dir, "pet_state.json")
            os.makedirs(_runtime.user_data_dir, exist_ok=True)
            with open(pet_file, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"[DesktopPet] Failed saving state: {e}")
            return False

    def quit_pet(self):
        """Closes the desktop pet window."""
        os._exit(0)

def _apply_stealth_window_styles():
    """Removes the window from the Windows taskbar so it behaves as an overlay."""
    if sys.platform != "win32":
        return
    import ctypes
    import threading
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080
    SWP_FRAMECHANGED = 0x0020
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    SWP_NOZORDER = 0x0004

    def _worker():
        for _ in range(40):
            time.sleep(0.15)
            hwnd = user32.FindWindowW(None, "KALKI Desktop Companion")
            if hwnd:
                try:
                    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    if (style & WS_EX_APPWINDOW) or not (style & WS_EX_TOOLWINDOW):
                        new_style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
                        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                        user32.SetWindowPos(
                            hwnd, 0, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
                        )
                    break
                except Exception:
                    pass

    threading.Thread(target=_worker, daemon=True, name="kalki-pet-stealth").start()

def main():
    api = PetApi()
    
    # Calculate bottom-right corner docking
    pet_w = 260
    pet_h = 320
    pos_x = max(20, SCREEN_WIDTH - pet_w - 20)
    pos_y = max(20, SCREEN_HEIGHT - pet_h - 60) # Leave room for Windows taskbar

    port = getattr(config, "PORT", 8888)

    # Load local HTML directly as native desktop software
    local_html = os.path.join(BASE_DIR, "ui", "pet_overlay.html")
    load_url = local_html if os.path.exists(local_html) else f"http://127.0.0.1:{port}/pet_overlay"

    _apply_stealth_window_styles()

    window = webview.create_window(
        title="KALKI Desktop Companion",
        url=load_url,
        width=pet_w,
        height=pet_h,
        x=pos_x,
        y=pos_y,
        frameless=True,
        on_top=True,
        transparent=True,
        background_color="#000000",
        easy_drag=True,
        js_api=api
    )

    webview.start(private_mode=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as _e:
        err_log = os.path.join(os.path.expanduser("~"), ".kalki_pet_err.log")
        try:
            import traceback
            with open(err_log, "w") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
