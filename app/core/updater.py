import os
import sys
import json
import urllib.request
import threading
import tempfile
import subprocess
import hashlib
from urllib.parse import urlparse

REPO = "Maher-Bhatt/KALKI"
try:
    from version import VERSION as CURRENT_VERSION
except ImportError:
    CURRENT_VERSION = "v1.3.0"

# Microsoft Store builds must not self-update — the Store handles updates.
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(os.path.abspath(sys.executable))
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_STORE_BUILD = os.path.exists(os.path.join(_BASE, "store_build.txt"))
# Only installed release builds look for updates. Source runs and tests never do.
IS_RELEASE_BUILD = bool(getattr(sys, "frozen", False))

# What the user can choose to install: {"version", "download"}. Empty if nothing.
STATE_UPDATE_AVAILABLE = {}


def is_trusted_download_url(url):
    """Only this project's GitHub release assets, over HTTPS. Exact host, no substring."""
    try:
        parsed = urlparse(str(url or ""))
    except ValueError:
        return False
    return (parsed.scheme == "https"
            and parsed.hostname == "github.com"
            and parsed.path.startswith(f"/{REPO}/releases/download/"))


def check_for_updates():
    """
    Ping GitHub releases to see if a newer version is available.
    Returns (has_update, latest_version, download_url)
    """
    if IS_STORE_BUILD:
        return False, CURRENT_VERSION, None
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
                    # Use an exact release asset name. If GitHub supplies its
                    # artifact digest, carry it through for verification.
                    expected_name = f"KALKI_Setup_v{latest.lstrip('v')}.exe"
                    for asset in data.get("assets", []):
                        if asset.get("name") == expected_name:
                            return True, latest, {
                                "url": asset.get("browser_download_url"),
                                "digest": asset.get("digest", ""),
                                "name": expected_name,
                            }
                        
            return False, CURRENT_VERSION, None
    except Exception as e:
        print(f"[UPDATER] Failed to check for updates: {e}")
        return False, CURRENT_VERSION, None

STATE_UPDATE_PROGRESS = {"pct": 0, "active": False}

def _progress_hook(block_num, block_size, total_size):
    if total_size > 0:
        STATE_UPDATE_PROGRESS["pct"] = min(100, int(block_num * block_size * 100 / total_size))

def download_and_run_update(download, version, base_dir):
    """Download and execute a verified release installer."""
    try:
        if isinstance(download, str):
            download = {"url": download, "digest": ""}
        download_url = download.get("url", "")
        digest = download.get("digest", "")
        if not is_trusted_download_url(download_url):
            raise ValueError("update URL is not an approved GitHub release URL")
        print(f"[UPDATER] Downloading update {version} from {download_url}...")
        installer_path = os.path.join(tempfile.mkdtemp(prefix="kalki_update_"), f"KALKI_Setup_{version}.exe")
        
        STATE_UPDATE_PROGRESS["active"] = True
        STATE_UPDATE_PROGRESS["pct"] = 0
        urllib.request.urlretrieve(download_url, installer_path, reporthook=_progress_hook)
        if digest.startswith("sha256:"):
            expected = digest.split(":", 1)[1].lower()
            actual = hashlib.sha256()
            with open(installer_path, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    actual.update(chunk)
            if actual.hexdigest().lower() != expected:
                raise ValueError("downloaded update failed SHA-256 verification")
        else:
            raise ValueError("release has no SHA-256 digest; refusing to execute update")
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

def install_available_update(base_dir):
    """Install the offered update. Only call this after the user has agreed."""
    available = dict(STATE_UPDATE_AVAILABLE)
    if available.get("version"):
        download_and_run_update(available.get("download"), available["version"], base_dir)


def start_update_daemon(base_dir, on_update_found=None):
    """Check once at startup and remember the result. Never downloads anything:
    the user chooses to install from the banner in the app."""
    if not IS_RELEASE_BUILD:
        return

    def daemon():
        has_update, latest, download = check_for_updates()
        if has_update and download:
            print(f"[UPDATER] Update available: {latest}")
            STATE_UPDATE_AVAILABLE.update({"version": latest, "download": download})
            if on_update_found:
                on_update_found(latest)

    threading.Thread(target=daemon, daemon=True).start()
