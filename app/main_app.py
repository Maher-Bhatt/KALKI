import os

import sys



import json

import time

import subprocess

import psutil

from runtime_paths import prepare_runtime



_runtime = prepare_runtime()



import config

import runtime_security

runtime_security.TOKEN_PATH = os.path.join(_runtime.user_data_dir, "data", "api_token.txt")

import settings_schema

settings_schema.repair_config(config)

DATA_DIR = os.path.join(_runtime.user_data_dir, "data")
WORKSPACE_DIR = os.path.join(DATA_DIR, "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def _validate_safe_path(target_path, write=False):
    """
    Validates that a path is safe and strictly confined to allowed data/workspace directories.
    Rejects path traversal, symlinks pointing outside, and sensitive files.
    """
    if not target_path or not isinstance(target_path, str):
        return None, "Target path is required."
    
    if "\0" in target_path:
        return None, "Invalid path."

    abs_path = os.path.abspath(target_path)
    real_path = os.path.realpath(abs_path)

    basename = os.path.basename(real_path).lower()
    blocked_filenames = {
        "api_token.txt", "vault.json", "credentials.json", "token.json",
        "google_credentials.json", "google_token.pickle", "spotify_token.json",
        "user_config.json", "id_rsa", "id_ed25519", "known_hosts", ".env",
        "config.py", "secure_api_vault.json", "semantic_memory.json",
    }
    if basename in blocked_filenames:
        return None, f"Access to sensitive file '{basename}' is blocked for security."

    win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
    if real_path.lower().startswith(win_dir) or real_path.lower() == "c:\\":
        return None, "Access to system directories is forbidden."

    user_home = os.path.expanduser("~")
    ssh_dir = os.path.join(user_home, ".ssh").lower()
    if real_path.lower().startswith(ssh_dir):
        return None, "Access to SSH credentials is forbidden."

    allowed_roots = [
        os.path.realpath(DATA_DIR),
        os.path.realpath(WORKSPACE_DIR),
    ]
    inside_sandbox = any(
        real_path == root or real_path.startswith(root + os.sep)
        for root in allowed_roots
    )

    if not inside_sandbox:
        return None, f"Access denied: Path '{target_path}' is outside the sandboxed workspace."

    return real_path, None





def remove_from_startup():
    if sys.platform != 'win32':
        return
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "KALKI")
        winreg.CloseKey(key)
    except Exception:
        pass

def add_to_startup():
    if not getattr(config, "AUTO_START", False):
        remove_from_startup()
        return

    if sys.platform != 'win32':
        return

    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    if getattr(sys, 'frozen', False):

        exe_path = sys.executable

    else:

        script_path = os.path.abspath(sys.argv[0])

        exe_path = f'"{sys.executable}" "{script_path}"'

        

    try:

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        formatted_path = f'"{exe_path.strip(chr(34))}"'

        winreg.SetValueEx(key, "KALKI", 0, winreg.REG_SZ, formatted_path)

        winreg.CloseKey(key)

        print("Successfully added KALKI to startup registry.")

    except Exception as e:

        print(f"Failed to add to startup: {e}")



    try:

        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")

        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")

        if os.path.exists(startup_dir):

            shortcut_path = os.path.join(startup_dir, "KALKI.lnk")

            shortcut = shell.CreateShortCut(shortcut_path)

            if getattr(sys, 'frozen', False):

                shortcut.TargetPath = sys.executable

                shortcut.WorkingDirectory = os.path.dirname(sys.executable)

            else:

                shortcut.TargetPath = sys.executable

                shortcut.Arguments = f'"{os.path.abspath(sys.argv[0])}"'

                shortcut.WorkingDirectory = BASE_DIR

            ico = os.path.join(BASE_DIR, "assets", "kalki_icon.ico")

            if os.path.exists(ico):

                shortcut.IconLocation = ico

            shortcut.Description = "KALKI AI Assistant"

            shortcut.save()

            print("Successfully added KALKI to Startup folder shortcut.")

    except Exception as e:

        print(f"Could not create startup folder shortcut: {e}")





BASE_DIR = _runtime.app_root

USER_DATA_DIR = _runtime.user_data_dir

USER_CONFIG_PATH = os.path.join(USER_DATA_DIR, "user_config.json")



def get_exe_path(name):

    if getattr(sys, "frozen", False):

        # Every helper keeps its matching PyInstaller runtime beside it. Do

        # not flatten these directories during packaging: that corrupts the

        # individual executables' dependency sets.

        service_dirs = {

            "KALKI_Server": "server",

            "KALKI_Listener": "listener",

            "KALKI_Setup_Wizard": "setup_wizard",

        }

        service_dir = service_dirs.get(name)

        if service_dir:

            return os.path.join(BASE_DIR, "services", service_dir, f"{name}.exe")

        return os.path.join(BASE_DIR, f"{name}.exe")

    else:

        # Map executable names to source file names for dev mode

        name_map = {

            "KALKI_Server": "server",

            "KALKI_Listener": "listener",

            "KALKI_Setup_Wizard": "kalki_setup_wizard"

        }

        src_name = name_map.get(name, name)

        return f'{sys.executable} "{os.path.join(BASE_DIR, f"{src_name}.py")}"'



def is_setup_complete():

    marker_path = os.path.join(USER_DATA_DIR, "setup_complete.marker")

    return os.path.exists(marker_path)



def run_setup_wizard():

    setup_cmd = get_exe_path("KALKI_Setup_Wizard")

    print(f"Running setup wizard: {setup_cmd}")

    process = subprocess.Popen(setup_cmd, shell=True if not getattr(sys, "frozen", False) else False)

    process.wait()



def kill_process_tree(pid):

    # NOTE: Inactive/Dead code path — pystray tray integration is disabled (see lines 421-427).

    # The active window close handler is on_closing(), which executes taskkill in a background thread.

    # psutil process tree traversal is kept here only for backwards compatibility with quit_app.

    try:

        parent = psutil.Process(pid)

        for child in parent.children(recursive=True):

            child.kill()

        parent.kill()

    except psutil.NoSuchProcess:

        pass

    except Exception as e:

        print(f"Error killing process tree: {e}")



server_process = None

listener_process = None

server_ready = None

_allow_window_close = False



def start_services():
    """Start helpers without blocking the desktop GUI before first paint."""
    global server_process, listener_process, server_ready
    server_ready = threading.Event()
    server_cmd = get_exe_path("KALKI_Server")
    listener_cmd = get_exe_path("KALKI_Listener")
    flags = subprocess.CREATE_NO_WINDOW if getattr(sys, "frozen", False) else 0
    shell = not getattr(sys, "frozen", False)
    os.environ["KALKI_DESKTOP_MODE"] = "1"

    # Pre-flight check: is server already healthy on port?
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{config.PORT}/api/health", timeout=0.5) as probe:
            if probe.status == 200:
                print(f"[KALKI] Server is already active and healthy on port {config.PORT}.")
                server_ready.set()
    except Exception:
        pass

    if not server_ready.is_set():
        print("Starting KALKI Server...")
        try:
            server_process = subprocess.Popen(
                server_cmd,
                shell=shell,
                creationflags=flags,
                cwd=BASE_DIR,
                env=os.environ.copy()
            )
        except (FileNotFoundError, OSError) as e:
            print(f"[KALKI] Failed to start server: {e}")
            server_process = None

    def start_listener_when_ready():
        nonlocal listener_cmd, shell, flags
        import urllib.request
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{config.PORT}/api/health", timeout=0.5) as r:
                    if r.status == 200:
                        print(f"Server is up and verified healthy on port {config.PORT}!")
                        server_ready.set()
                        break
            except Exception:
                time.sleep(0.25)
        else:
            print("WARNING: Server did not respond to health check in time; opening UI anyway.")
            server_ready.set()

        # Start microphone capture after desktop window paints
        time.sleep(6)
        global listener_process
        print("Starting KALKI Listener...")
        try:
            listener_process = subprocess.Popen(
                listener_cmd,
                shell=shell,
                creationflags=flags,
                cwd=BASE_DIR,
                env=os.environ.copy()
            )
        except (FileNotFoundError, OSError) as e:
            print(f"[KALKI] Failed to start listener: {e}")
            listener_process = None

    threading.Thread(target=start_listener_when_ready, name="kalki-service-wait", daemon=True).start()
    threading.Thread(target=_supervise_services, name="kalki-service-supervisor", daemon=True).start()





def _supervise_services():

    """Keep the local helpers alive without blocking the desktop UI."""

    global server_process, listener_process

    time.sleep(15)

    while True:

        try:

            if server_process is not None and server_process.poll() is not None:

                print("[KALKI] server stopped; restarting it")

                server_process = subprocess.Popen(

                    get_exe_path("KALKI_Server"), shell=not getattr(sys, "frozen", False), creationflags=subprocess.CREATE_NO_WINDOW if getattr(sys, "frozen", False) else 0, cwd=BASE_DIR, env=os.environ.copy())

                time.sleep(3)

            listen_mode = (getattr(config, "LISTEN_MODE", "always") or "always").lower()

            if (listener_process is not None and listener_process.poll() is not None

                    and listen_mode == "always"):

                print("[KALKI] listener stopped; retrying in 10 seconds")

                time.sleep(10)

                listener_process = subprocess.Popen(

                    get_exe_path("KALKI_Listener"),

                    shell=not getattr(sys, "frozen", False),

                    creationflags=subprocess.CREATE_NO_WINDOW if getattr(sys, "frozen", False) else 0,

                )

        except Exception as exc:

            print(f"[KALKI] service supervisor warning: {exc}")

        time.sleep(5)



import threading

try:

    import pystray

except Exception:

    pystray = None

try:

    from PIL import Image

except Exception:

    Image = None



def get_icon_image():

    if Image is None:

        return None

    for candidate in [

        os.path.join(BASE_DIR, "assets", "kalki_icon.ico"),

        os.path.join(os.path.dirname(BASE_DIR), "assets", "kalki_icon.ico"),

    ]:

        if os.path.exists(candidate):

            try:

                return Image.open(candidate)

            except Exception:

                pass

    return Image.new('RGB', (64, 64), color=(10, 10, 10))



window = None

tray = None



def show_window(icon=None, item=None):

    if not restore_existing_instance():

        if window:

            try:

                window.show()

                window.restore()

            except Exception:

                pass



def quit_app(icon=None, item=None):

    global _allow_window_close

    _allow_window_close = True

    if icon:

        try:

            icon.stop()

        except Exception:

            pass

    if window:

        try:

            window.destroy()

        except Exception:

            pass

    print("Cleaning up background services...")

    if server_process:

        try:

            subprocess.run(["taskkill", "/F", "/T", "/PID", str(server_process.pid)], capture_output=True)

        except Exception:

            pass

    if listener_process:

        try:

            subprocess.run(["taskkill", "/F", "/T", "/PID", str(listener_process.pid)], capture_output=True)

        except Exception:

            pass

    print("Cleanup complete. Exiting.")

    sys.exit(0)



def setup_tray():

    global tray

    if pystray is None or Image is None:

        print("System tray integration unavailable on this platform.")

        return

    image = get_icon_image()

    if image is None:

        image = Image.new('RGB', (64, 64), color=(30, 30, 30))

    menu = pystray.Menu(

        pystray.MenuItem("Open KALKI", show_window, default=True),

        pystray.MenuItem("Quit", quit_app)

    )

    tray = pystray.Icon("KALKI", image, "KALKI AI Assistant", menu)

    tray.run()



def acquire_single_instance():

    try:

        import win32event

        import win32api

        import winerror

        handle = win32event.CreateMutex(None, False, "Global\\KALKI_App_Instance")

        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:

            return None

        return handle

    except ImportError:

        return True  # pywin32 unavailable - don't block startup

    except Exception:

        return True



def on_closing():

    """Hide window to tray when tray is available; otherwise clean up and exit."""

    global _allow_window_close

    if _allow_window_close:

        return True

    

    if tray is not None:

        try:

            if window:

                window.hide()

            print("KALKI minimized to system tray.")

            return False

        except Exception as e:

            print(f"Error hiding window to tray: {e}")

    

    def _terminate_gracefully(proc, timeout=2.0):
        if not proc:
            return
        try:
            if hasattr(proc, "poll") and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except Exception:
                    proc.kill()
            elif hasattr(proc, "pid"):
                p = psutil.Process(proc.pid)
                p.terminate()
                try:
                    p.wait(timeout=timeout)
                except Exception:
                    p.kill()
        except Exception:
            try:
                if hasattr(proc, "pid"):
                    psutil.Process(proc.pid).kill()
            except Exception:
                pass

    def do_cleanup():
        print("Window closing. Cleaning up background services gracefully...")
        if server_process:
            _terminate_gracefully(server_process)
        if listener_process:
            _terminate_gracefully(listener_process)
        print("Cleanup complete.")
        sys.exit(0)

    

    import threading

    threading.Thread(target=do_cleanup, daemon=True).start()

    return True



def restore_existing_instance():

    try:

        import win32gui

        import win32con

        hwnd = win32gui.FindWindow(None, "KALKI AI Assistant")

        if hwnd:

            try:

                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                win32gui.BringWindowToTop(hwnd)

                win32gui.SetForegroundWindow(hwnd)

            except Exception:

                pass

            return True

    except Exception as e:

        print(f"Error restoring existing window: {e}")

    return False



def global_hotkey_listener(window_obj):

    try:

        import ctypes

        from ctypes import wintypes

        import win32gui

        import win32con

        user32 = ctypes.windll.user32

        

        # Register Alt + Space (VK_SPACE = 0x20, MOD_ALT = 0x0001)

        HOTKEY_ID = 99

        if not user32.RegisterHotKey(None, HOTKEY_ID, 0x0001, 0x20):

            # Fallback to Alt + K (VK_K = 0x4B)

            user32.RegisterHotKey(None, HOTKEY_ID, 0x0001, 0x4B)



        msg = wintypes.MSG()

        is_visible = True

        

        while user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:

            if msg.message == 0x0312:  # WM_HOTKEY

                try:

                    hwnd = win32gui.FindWindow(None, "KALKI AI Assistant")

                    if hwnd:

                        if is_visible:

                            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

                            is_visible = False

                        else:

                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                            win32gui.BringWindowToTop(hwnd)

                            win32gui.SetForegroundWindow(hwnd)

                            is_visible = True

                except Exception as e:

                    print(f"Hotkey toggle error: {e}")

            user32.TranslateMessage(ctypes.byref(msg))

            user32.DispatchMessageA(ctypes.byref(msg))

    except Exception as e:

        print(f"Hotkey listener error: {e}")



if __name__ == '__main__' and sys.platform != 'win32':

    from linux_launcher import main as _linux_main

    raise SystemExit(_linux_main())



if __name__ == '__main__':

    _lock = acquire_single_instance()

    if _lock is None:

        print("KALKI is already running - restoring existing window.")

        restore_existing_instance()

        sys.exit(0)



    # 1. First-time setup check

    if not is_setup_complete():

        print("Setup not complete. Launching Setup Wizard...")

        run_setup_wizard()

        

        if not is_setup_complete():

            print("Setup was cancelled or incomplete. Exiting KALKI.")

            sys.exit(0)

            

    # 1.5 Add to startup if configured

    try:

        is_store = os.path.exists(os.path.join(BASE_DIR, "store_build.txt"))

        # add_to_startup() also removes the entry when AUTO_START is off, so it always runs.
        if not is_store:

            add_to_startup()

    except Exception as e:

        print(f"Error checking startup configuration: {e}")

    

    # 2. Start background services. Wait only briefly so the first paint is

    # not held hostage by a slow provider import or a broken helper.

    start_services()

    if server_ready is not None:
        server_ready.wait(timeout=18.0)

    def _launch_desktop_pet():
        time.sleep(1.0)
        try:
            env = os.environ.copy()
            pet_profile = os.path.join(_runtime.user_data_dir, "pet_webview_profile")
            os.makedirs(pet_profile, exist_ok=True)
            env["WEBVIEW2_USER_DATA_FOLDER"] = pet_profile
            if getattr(sys, "frozen", False):
                pet_exe = os.path.join(BASE_DIR, "services", "pet", "KALKI_Pet.exe")
                if os.path.exists(pet_exe):
                    return subprocess.Popen([pet_exe], cwd=BASE_DIR, env=env)
                elif os.path.exists(os.path.join(BASE_DIR, "KALKI_Pet.exe")):
                    return subprocess.Popen([os.path.join(BASE_DIR, "KALKI_Pet.exe")], cwd=BASE_DIR, env=env)
            else:
                pet_script = os.path.join(BASE_DIR, "desktop_pet.py")
                if os.path.exists(pet_script):
                    return subprocess.Popen([sys.executable, pet_script], cwd=BASE_DIR, env=env)
        except Exception as _e:
            print(f"[MainApp] Desktop pet startup notice: {_e}")
        return None

    # Standalone Desktop Floating Companion Pet
    # Disabled by default so KALKI runs as a single clean taskbar application.
    # Can be toggled on or off from Settings -> Companion Pet at any time.
    if getattr(config, "ENABLE_DESKTOP_PET", False):
        import threading
        threading.Thread(target=_launch_desktop_pet, name="kalki-desktop-pet", daemon=True).start()

    

    # 3. Open Native Application Window

    print("Opening KALKI Desktop Interface...")

    

    class WebApi:
        def minimize(self):
            if window:
                try: window.minimize()
                except Exception: pass

        def toggle_maximize(self):
            if window:
                try: window.toggle_fullscreen()
                except Exception: pass

        def close(self):
            if window:
                if getattr(config, "ENABLE_GLOBAL_HOTKEY", False):
                    try: window.hide()
                    except Exception: pass
                else:
                    try:
                        window.destroy()
                    except Exception:
                        sys.exit(0)

        def toggle_pin(self):
            """Toggle stay on top (pin)."""
            try:
                if window:
                    current = getattr(window, "on_top", False)
                    window.on_top = not current
                    return {"ok": True, "pinned": window.on_top}
            except Exception as e:
                return {"ok": False, "error": str(e)}
            return {"ok": False}

        def toggle_pet(self, enable=None):
            """Toggle or set the floating companion pet overlay state."""
            try:
                import psutil
                pet_procs = []
                for p in psutil.process_iter(['name', 'cmdline']):
                    try:
                        cmd = ' '.join(p.info.get('cmdline') or [])
                        if 'desktop_pet.py' in cmd or 'KALKI_Pet.exe' in cmd:
                            pet_procs.append(p)
                    except Exception:
                        pass

                is_running = len(pet_procs) > 0
                target_state = not is_running if enable is None else bool(enable)

                if not target_state:
                    for p in pet_procs:
                        try:
                            p.kill()
                        except Exception:
                            pass
                    return {"ok": True, "running": False}
                else:
                    if not is_running:
                        _launch_desktop_pet()
                    return {"ok": True, "running": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def exec_command(self, cmd, cwd=None):
            """Execute a terminal command on the host OS only if explicitly permitted by policy."""
            if not getattr(config, "ALLOW_HOST_CODE_EXECUTION", False):
                return {
                    "ok": False,
                    "error": "Host command execution is disabled by policy. Enable ALLOW_HOST_CODE_EXECUTION in settings to permit shell execution."
                }
            cmd_str = (cmd or "").strip()
            if not cmd_str:
                return {"ok": False, "error": "command required"}
            lower_cmd = cmd_str.lower()
            dangerous_patterns = [
                "format ", "del /s", "del /f /s", "rmdir /s /q", "rd /s /q",
                "rm -rf /", "mkfs", "diskpart", ":(){ :|:& };:", "powershell -enc"
            ]
            if any(p in lower_cmd for p in dangerous_patterns):
                return {"ok": False, "error": "Destructive system commands are blocked by endpoint safety policy."}
            try:
                import subprocess, time
                t0 = time.time()
                safe_cwd = cwd if cwd and os.path.exists(cwd) else WORKSPACE_DIR
                res = subprocess.run(
                    cmd_str,
                    shell=True,
                    cwd=safe_cwd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                dur = round((time.time() - t0) * 1000)
                return {
                    "ok": True,
                    "exit_code": res.returncode,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "duration_ms": dur
                }
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "Command timed out after 30 seconds."}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def read_file(self, file_path):
            """Read content of a sandboxed local file."""
            safe_path, err = _validate_safe_path(file_path)
            if err:
                return {"ok": False, "error": err}
            try:
                if not os.path.isfile(safe_path):
                    return {"ok": False, "error": f"File not found: {file_path}"}
                with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return {"ok": True, "path": safe_path, "content": content}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def write_file(self, file_path, content):
            """Write content to a sandboxed local file."""
            safe_path, err = _validate_safe_path(file_path, write=True)
            if err:
                return {"ok": False, "error": err}
            try:
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"ok": True, "path": safe_path, "bytes": len(content)}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def list_directory(self, dir_path=None):
            """List files and folders in a sandboxed local directory."""
            target_path = dir_path or WORKSPACE_DIR
            safe_path, err = _validate_safe_path(target_path)
            if err:
                return {"ok": False, "error": err}
            try:
                if not os.path.isdir(safe_path):
                    return {"ok": False, "error": f"Directory not found: {target_path}"}
                items = []
                for entry in os.scandir(safe_path):
                    try:
                        stat = entry.stat()
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": entry.is_dir(),
                            "size": stat.st_size if not entry.is_dir() else 0,
                            "modified": stat.st_mtime
                        })
                    except Exception:
                        pass
                items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
                return {"ok": True, "path": safe_path, "items": items}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def open_folder_dialog(self):
            """Native folder picker."""
            try:
                if window:
                    res = window.create_file_dialog(webview.FOLDER_DIALOG)
                    if res and len(res) > 0:
                        return {"ok": True, "path": res[0]}
                return {"ok": False, "cancelled": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def open_file_dialog(self):
            """Native file picker."""
            try:
                if window:
                    res = window.create_file_dialog(webview.OPEN_DIALOG)
                    if res and len(res) > 0:
                        return {"ok": True, "path": res[0]}
                return {"ok": False, "cancelled": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def reveal_in_explorer(self, target_path):
            """Reveal file or folder in OS File Manager."""
            try:
                p = os.path.abspath(target_path)
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", f"/select,{p}"])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", p])
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(p)])
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def get_system_telemetry(self):
            """Get live hardware and system telemetry via psutil."""
            try:
                import psutil
                cpu_pct = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                net = psutil.net_io_counters()
                return {
                    "ok": True,
                    "cpu_percent": cpu_pct,
                    "memory": {
                        "total_mb": round(mem.total / (1024*1024)),
                        "used_mb": round(mem.used / (1024*1024)),
                        "percent": mem.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024*1024*1024), 1),
                        "used_gb": round(disk.used / (1024*1024*1024), 1),
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent": net.bytes_sent,
                        "bytes_recv": net.bytes_recv
                    },
                    "os": sys.platform,
                    "hostname": os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "Desktop"))
                }
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def get_process_list(self):
            """Get active running processes sorted by memory/cpu."""
            try:
                import psutil
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                    try:
                        info = p.info
                        mem_mb = round(info['memory_info'].rss / (1024*1024), 1) if info.get('memory_info') else 0
                        procs.append({
                            "pid": info['pid'],
                            "name": info['name'],
                            "mem_mb": mem_mb,
                            "cpu": info.get('cpu_percent', 0.0)
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                procs.sort(key=lambda x: x["mem_mb"], reverse=True)
                return {"ok": True, "processes": procs[:50]}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def kill_process(self, pid):
            """Terminate a process by PID."""
            try:
                import psutil
                proc = psutil.Process(int(pid))
                proc.kill()
                return {"ok": True, "message": f"Killed process {pid}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def say_text(self, text):
            """Speak a short UI-triggered command without exposing a shell bridge."""
            import urllib.request
            import json as _json
            payload = _json.dumps({"cmd": str(text or "")}).encode("utf-8")
            request = urllib.request.Request(
                f"http://127.0.0.1:{config.PORT}/api/command",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    runtime_security.TOKEN_HEADER: runtime_security.get_api_token(),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=5):
                    return True
            except Exception as exc:
                print(f"[KALKI] quick action failed: {exc}")
                return False

    api = WebApi()



    # Prefer a conservative WebView2 renderer for packaged Windows builds.

    # KALKI is intentionally CSS-only now; disabling GPU compositing avoids

    # driver-specific WebView hangs after first paint while preserving the

    # full dashboard interaction model.

    if sys.platform == "win32":
        # Keep WebView2 arguments clean and stable to prevent GPU process crashes / black screens
        existing_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "").strip()
        for bad_flag in ["--enable-gpu-rasterization", "--enable-zero-copy", "--disable-gpu"]:
            if bad_flag in existing_args:
                existing_args = existing_args.replace(bad_flag, "").strip()
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = existing_args

    import webview

    window = webview.create_window(

        title='KALKI AI Assistant', 

        url=f'http://127.0.0.1:{config.PORT}',

        width=1440,

        height=900,

        min_size=(960, 680),

        # Painted before index.html loads, so it's what the user sees for the

        # first frame. Must track --surface-void in ui/tokens.css or every

        # launch flashes the old cream theme before the page takes over.

        background_color='#070809',

        resizable=True,

        # Use the native frame for reliable Windows message handling. The

        # frameless WebView drag path has been removed because it can leave the

        # packaged process marked "not responding" after first paint.

        frameless=False,

        easy_drag=False,

        js_api=api

    )

    # CRITICAL: Do NOT do api.window = window.

    # PyWebView's inject_pywebview reflects across js_api; referencing the window

    # object creates an infinite recursion in WinForms COM properties (Bounds.Empty...)

    # which hangs the STA UI thread and causes Windows '(Not Responding)' freezes.

    

    window.events.closing += on_closing

    

    # Start the system tray integration so KALKI is visible in the taskbar notification overflow

    def _start_tray():

        time.sleep(1)

        setup_tray()

    threading.Thread(target=_start_tray, name="kalki-tray", daemon=True).start()

    

    # Global Windows hotkeys run outside PyWebView's event loop and can

    # interfere with a frameless window. Keep this opt-in until it has a

    # dedicated, native-safe dispatcher.

    if getattr(config, "ENABLE_GLOBAL_HOTKEY", False):

        threading.Thread(target=global_hotkey_listener, args=(window,), daemon=True).start()

    

    # Start the webview event loop

    webview.start(private_mode=False)

