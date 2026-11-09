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

import runtime_security

runtime_security.TOKEN_PATH = os.path.join(_runtime.user_data_dir, "data", "api_token.txt")

# Isolate WebView2 profile so pet never collides with main KALKI instance
pet_profile_dir = os.path.join(_runtime.user_data_dir, "pet_webview_profile")
os.makedirs(pet_profile_dir, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = pet_profile_dir

import config
import webview

CARD_WIDTH = 280


class PetApi:
    # pywebview exposes public attributes to the page, so these stay private.
    _window = None
    _pet = None
    _card_open = False
    _card_height = 200

    def show_frame(self, rgba_base64):
        """Draw one frame of the pet in its see-through window."""
        return bool(self._pet and self._pet.show(rgba_base64))

    def has_native_pet(self):
        return bool(self._pet and self._pet.hwnd)

    def place_card(self, is_open, height=200):
        """Show the card next to the pet, or park it off screen.

        It's parked rather than hidden because a hidden page stops running, and the page
        is what keeps the pet up to date.
        """
        self._card_open = bool(is_open)
        self._card_height = int(height)
        return self._position_card()

    def _position_card(self):
        import ctypes
        import pet_window
        pet_window.use_real_pixels()
        hwnd = ctypes.windll.user32.FindWindowW(None, "KALKI Desktop Companion")
        if not hwnd or not self._pet:
            return False
        user32 = ctypes.windll.user32
        SWP_NOACTIVATE, SWP_NOSIZE = 0x0010, 0x0001
        HWND_TOPMOST = ctypes.c_void_p(-1)
        if not self._card_open:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, -32000, -32000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
            return True
        ratio = (user32.GetDpiForWindow(hwnd) or 96) / 96
        size = (round(CARD_WIDTH * ratio), round(self._card_height * ratio))
        x, y = pet_window.card_position(self._pet.rect(), size, self._pet.work_area(), gap=round(6 * ratio))
        user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, size[0], size[1], 0)
        user32.SetForegroundWindow(hwnd)
        return True

    def _local_json(self, path, body=None, timeout=3):
        import urllib.request
        port = getattr(config, "PORT", 8888)
        headers = {runtime_security.TOKEN_HEADER: runtime_security.get_api_token()}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_status(self):
        """What the pet should show. KALKI not running is reported, never raised."""
        try:
            return self._local_json("/api/pet/status")
        except Exception:
            return {"ok": False, "pet": self.get_pet_state()}

    def save_pet(self, patch):
        """Save through KALKI when it's running, so the app and the pet stay in step."""
        try:
            self._local_json("/api/pet", patch)
            return True
        except Exception:
            state = self.get_pet_state()
            state.update({k: v for k, v in patch.items() if k in ("species", "name", "sound")})
            return self.save_pet_state(state)

    def send_command(self, cmd):
        """Send a typed quick command to KALKI with the local token."""
        import json
        import urllib.request
        port = getattr(config, "PORT", 8888)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/command",
            data=json.dumps({"cmd": str(cmd or "")}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                runtime_security.TOKEN_HEADER: runtime_security.get_api_token(),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"ok": False, "reply": f"KALKI isn't responding: {exc}"}

    def open_main_app(self):
        """Brings the main KALKI window to foreground or launches it."""
        # 1. Trigger local server wake endpoint
        try:
            import urllib.request
            port = getattr(config, "PORT", 8888)
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/wake",
                data=b'{"cmd":""}',
                headers={
                    "Content-Type": "application/json",
                    runtime_security.TOKEN_HEADER: runtime_security.get_api_token(),
                },
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

    def get_pet_state(self):
        """Loads pet state from user data or defaults."""
        for pf in [
            os.path.join(_runtime.user_data_dir, "data", "pet_state.json"),
            os.path.join(_runtime.user_data_dir, "pet_state.json")
        ]:
            if os.path.exists(pf):
                try:
                    with open(pf, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {"species": "gobi", "name": "Gobi", "sound": True, "enabled": True}

    def save_pet_state(self, state_dict):
        """Saves pet state to user data directory."""
        success = False
        for folder in [_runtime.user_data_dir, os.path.join(_runtime.user_data_dir, "data")]:
            try:
                os.makedirs(folder, exist_ok=True)
                pf = os.path.join(folder, "pet_state.json")
                import safe_json
                safe_json.write_json(pf, state_dict)
                success = True
            except Exception as e:
                print(f"[DesktopPet] Failed saving state to {folder}: {e}")
        return success

    def quit_pet(self):
        """Closes the desktop pet window."""
        os._exit(0)

def _apply_window_styles():
    """Keep the pet off the taskbar."""
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
                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW)
                user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
                )
                return

    threading.Thread(target=_worker, daemon=True, name="kalki-pet-window").start()


def main():
    import pet_window

    api = PetApi()
    port = getattr(config, "PORT", 8888)

    # Load local HTML directly as native desktop software
    local_html = os.path.join(BASE_DIR, "ui", "pet_overlay.html")
    load_url = local_html if os.path.exists(local_html) else f"http://127.0.0.1:{port}/pet_overlay"

    _apply_window_styles()

    # The page keeps running while the card is off screen, because it draws the pet.
    keep_running = " ".join((
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-features=CalculateNativeWinOcclusion",
    ))
    existing = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "").strip()
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{existing} {keep_running}".strip()

    window = webview.create_window(
        title="KALKI Desktop Companion",
        url=load_url,
        width=CARD_WIDTH,
        height=200,
        x=-32000,
        y=-32000,
        frameless=True,
        on_top=True,
        background_color="#15181c",
        min_size=(200, 100),
        js_api=api
    )
    api._window = window

    def clicked():
        window.evaluate_js("window.__petClicked && window.__petClicked()")

    api._pet = pet_window.PetWindow(on_click=clicked, on_moved=api._position_card)
    api._pet.start()

    webview.start(gui="edgechromium", private_mode=False)

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
