import os
import sys
import json
import time
import subprocess
import webview
import psutil

# --- Auto-bootstrap config.py from config.example.py on first run -----------
# Without this, a fresh clone has no config.py (it's gitignored) and the
# `import config` below throws ModuleNotFoundError before the Setup Wizard
# (which is supposed to run first) ever gets a chance to start.
_boot_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
_cfg_path = os.path.join(_boot_dir, "config.py")
_example_path = os.path.join(_boot_dir, "config.example.py")
if not os.path.exists(_cfg_path) and os.path.exists(_example_path):
    import shutil
    shutil.copy(_example_path, _cfg_path)

os.chdir(_boot_dir)
sys.path.insert(0, _boot_dir)

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


BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
USER_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI")
USER_CONFIG_PATH = os.path.join(USER_DATA_DIR, "user_config.json")

def get_exe_path(name):
    if getattr(sys, "frozen", False):
        # In the distributed installer, everything is in the root directory
        return os.path.join(BASE_DIR, f"{name}.exe")
    else:
        return f'{sys.executable} "{os.path.join(BASE_DIR, f"{name}.py")}"'

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
    server_process = subprocess.Popen(server_cmd, shell=shell, creationflags=flags)
    
    # Give the server a moment to start
    time.sleep(3)
    
    print("Starting KALKI Listener...")
    listener_process = subprocess.Popen(listener_cmd, shell=shell, creationflags=flags)

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
    window.hide()
    return False  # Prevent the window from actually being destroyed

if __name__ == '__main__':
    _lock = acquire_single_instance()
    if _lock is None:
        print("KALKI is already running - exiting to avoid a duplicate instance.")
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
        if getattr(config, "AUTO_START", True):
            add_to_startup()
    except Exception as e:
        print(f"Error checking startup configuration: {e}")
    
    # 2. Start background services
    start_services()
    
    # 3. Open Native Application Window
    print("Opening KALKI Desktop Interface...")
    window = webview.create_window(
        title='KALKI AI Assistant', 
        url='http://127.0.0.1:8888', 
        width=1280, 
        height=800,
        min_size=(800, 600),
        background_color='#121212'
    )
    
    window.events.closing += on_closing
    
    # Start the system tray in a background thread
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # Start the webview event loop
    webview.start(private_mode=False)
