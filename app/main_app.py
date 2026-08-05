import os
import sys

import json
import time
import subprocess
import webview
import psutil
from runtime_paths import prepare_runtime

_runtime = prepare_runtime()

import config

def add_to_startup():
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
        formatted_path = exe_path
        if not formatted_path.startswith('"') and ' ' in formatted_path:
            formatted_path = f'"{formatted_path}"'
        winreg.SetValueEx(key, "KALKI", 0, winreg.REG_SZ, formatted_path)
        winreg.CloseKey(key)
        print("Successfully added KALKI to startup registry.")
    except Exception as e:
        print(f"Failed to add to startup: {e}")


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

def start_services():
    global server_process, listener_process
    
    server_cmd = get_exe_path("KALKI_Server")
    listener_cmd = get_exe_path("KALKI_Listener")
    
    flags = subprocess.CREATE_NO_WINDOW if getattr(sys, "frozen", False) else 0
    shell = not getattr(sys, "frozen", False)
    
    print("Starting KALKI Server...")
    os.environ["KALKI_DESKTOP_MODE"] = "1"
    try:
        server_process = subprocess.Popen(server_cmd, shell=shell, creationflags=flags)
    except (FileNotFoundError, OSError) as e:
        print(f"[KALKI] Failed to start server: {e}")
        server_process = None
    
    print("Waiting for server to bind to port...")
    import socket
    start_time = time.time()
    while time.time() - start_time < 20:  # 20 seconds max timeout
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(('127.0.0.1', config.PORT)) == 0:
                print(f"Server is up and listening on {config.PORT}!")
                break
        time.sleep(0.5)
    else:
        print("WARNING: Server did not start listening in time!")    
    print("Starting KALKI Listener...")
    try:
        listener_process = subprocess.Popen(listener_cmd, shell=shell, creationflags=flags)
    except (FileNotFoundError, OSError) as e:
        print(f"[KALKI] Failed to start listener: {e}")
        listener_process = None

import threading
import pystray
from PIL import Image

def get_icon_image():
    # Attempt to load the actual icon, fallback to a simple colored square if missing
    icon_path = os.path.join(BASE_DIR, "assets", "kalki_icon.ico")
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except: pass
    return Image.new('RGB', (64, 64), color=(10, 10, 10))

window = None
tray = None

def show_window(icon, item):
    if window:
        window.show()

def quit_app(icon, item):
    icon.stop()
    if window:
        window.destroy()
    print("Cleaning up background services...")
    if server_process:
        kill_process_tree(server_process.pid)
    if listener_process:
        kill_process_tree(listener_process.pid)
    print("Cleanup complete. Exiting.")
    sys.exit(0)

def setup_tray():
    global tray
    image = get_icon_image()
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
    print("Window close requested. Hiding to system tray instead...")
    # Do not call a native window method from PyWebView's closing callback.
    # On the Edge/WinForms backend that can re-enter the Windows message loop
    # and leave the application marked as "Not responding".  Let the close
    # notification return first, then hide the window on the next tick.
    threading.Timer(0.05, window.hide).start()
    return False  # Prevent the window from actually being destroyed

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
        if getattr(config, "AUTO_START", True) and not is_store:
            add_to_startup()
    except Exception as e:
        print(f"Error checking startup configuration: {e}")
    
    # 2. Start background services
    start_services()
    
    # 3. Open Native Application Window
    print("Opening KALKI Desktop Interface...")
    
    class WebApi:
        def __init__(self):
            self.window = None
        def minimize(self):
            if self.window: self.window.minimize()
        def toggle_maximize(self):
            if self.window: self.window.toggle_fullscreen()
        def close(self):
            if self.window: self.window.destroy()
            
    api = WebApi()
    
    window = webview.create_window(
        title='KALKI AI Assistant', 
        url=f'http://127.0.0.1:{config.PORT}',
        width=1280, 
        height=800,
        min_size=(800, 600),
        background_color='#121212',
        frameless=True,
        js_api=api
    )
    api.window = window
    
    window.events.closing += on_closing
    
    # Start the system tray in a background thread
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # Global Windows hotkeys run outside PyWebView's event loop and can
    # interfere with a frameless window. Keep this opt-in until it has a
    # dedicated, native-safe dispatcher.
    if getattr(config, "ENABLE_GLOBAL_HOTKEY", False):
        threading.Thread(target=global_hotkey_listener, args=(window,), daemon=True).start()
    
    # Start the webview event loop
    webview.start(private_mode=False)
