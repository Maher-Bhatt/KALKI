import os
import sys
import json
import urllib.request
import threading
import tempfile
import subprocess

REPO = "Maher-Bhatt/KALKI"
CURRENT_VERSION = "v1.0.15"

def check_for_updates():
    """
    Ping GitHub releases to see if a newer version is available.
    Returns (has_update, latest_version, download_url)
    """
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KALKI-AutoUpdater"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            latest = data.get("tag_name", "")
            
            # Simple version check (assumes format v1.0.x)
            if latest and latest.startswith("v"):
                try:
                    curr_parts = [int(x) for x in CURRENT_VERSION.lstrip('v').split('.')]
                    latest_parts = [int(x) for x in latest.lstrip('v').split('.')]
                    is_newer = latest_parts > curr_parts
                except:
                    is_newer = latest != CURRENT_VERSION
                
                if is_newer:
                    # Find the executable asset
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            return True, latest, asset.get("browser_download_url")
                        
            return False, CURRENT_VERSION, None
    except Exception as e:
        print(f"[UPDATER] Failed to check for updates: {e}")
        return False, CURRENT_VERSION, None

STATE_UPDATE_PROGRESS = {"pct": 0, "active": False}

def _progress_hook(block_num, block_size, total_size):
    if total_size > 0:
        STATE_UPDATE_PROGRESS["pct"] = min(100, int(block_num * block_size * 100 / total_size))

def download_and_run_update(download_url, version, base_dir):
    """
    Downloads the new setup exe in the background and executes it.
    """
    try:
        print(f"[UPDATER] Downloading update {version} from {download_url}...")
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, f"KALKI_Setup_{version}.exe")
        
        STATE_UPDATE_PROGRESS["active"] = True
        STATE_UPDATE_PROGRESS["pct"] = 0
        urllib.request.urlretrieve(download_url, installer_path, reporthook=_progress_hook)
        STATE_UPDATE_PROGRESS["pct"] = 100
        
        lock_path = os.path.join(base_dir, "data", "updating.lock")
        import time
        with open(lock_path, "w") as f:
            f.write(str(time.time()))
            
        print(f"[UPDATER] Download complete. Launching installer: {installer_path}")
        
        # Launch installer silently or normally depending on preference
        # Using CREATE_NO_WINDOW if we don't want a console pop-up for the subprocess itself
        cflags = 0x08000000 if os.name == "nt" else 0
        subprocess.Popen([installer_path], creationflags=cflags)
        
        # Shut down current instance so installer can overwrite files
        os._exit(0)
    except Exception as e:
        STATE_UPDATE_PROGRESS["active"] = False
        print(f"[UPDATER] Failed to apply update: {e}")

def start_update_daemon(base_dir, on_update_found=None):
    """
    Starts a background thread that checks for updates on boot.
    """
    def daemon():
        has_update, latest, url = check_for_updates()
        if has_update and url:
            print(f"[UPDATER] Found new version: {latest}. Initiating download...")
            if on_update_found:
                on_update_found(latest)
            download_and_run_update(url, latest, base_dir)
            
    threading.Thread(target=daemon, daemon=True).start()
