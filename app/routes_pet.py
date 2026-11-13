"""HTTP routes for the pet, moved out of server.py.

Covers the pet's settings, the floating desktop pet process and what the pet shows.
server.py calls configure() once with the paths and the status function, so nothing
here imports the server.
"""

import os
import subprocess
import sys
from typing import Any, Callable, Dict, Optional, Tuple

import safe_json

Result = Tuple[Dict[str, Any], int]

SPECIES = ("gobi", "kittu", "byte", "draco", "kitsu", "nova")
_OLD_NAMES = {"cat": "kittu", "chibi": "gobi", "dog": "byte", "dragon": "draco", "drone": "nova", "fox": "kitsu"}
DEFAULTS = {"species": "gobi", "name": "Gobi", "sound": False, "enabled": True}
_PET_PROCESS_MARKERS = ("desktop_pet.py", "KALKI_Pet.exe")

_config: Dict[str, Any] = {"data_dir": None, "app_dir": None, "status": None}


def configure(data_dir: str, app_dir: str, status: Callable[[], Dict[str, Any]]) -> None:
    _config.update(data_dir=data_dir, app_dir=app_dir, status=status)


def _settings_paths():
    data_dir = _config["data_dir"]
    # The floating pet also reads the copy one folder up, so both are kept in step.
    return os.path.join(data_dir, "pet_state.json"), os.path.join(os.path.dirname(data_dir), "pet_state.json")


def clean_settings(values: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only valid settings. Anything unknown or malformed is dropped, not stored."""
    out: Dict[str, Any] = {}
    species = str(values.get("species") or "").strip().lower()
    species = _OLD_NAMES.get(species, species)
    if species in SPECIES:
        out["species"] = species
    if isinstance(values.get("name"), str) and values["name"].strip():
        out["name"] = values["name"].strip()[:24]
    for key in ("sound", "enabled"):
        if isinstance(values.get(key), bool):
            out[key] = values[key]
    return out


def read_settings() -> Dict[str, Any]:
    settings = dict(DEFAULTS)
    saved = safe_json.read_json(_settings_paths()[0], default={})
    if isinstance(saved, dict):
        settings.update(clean_settings(saved))
    return settings


def get_pet(body: Dict[str, Any]) -> Result:
    return {"ok": True, "pet": read_settings()}, 200


def save_pet(body: Dict[str, Any]) -> Result:
    changes = clean_settings(body)
    if not changes:
        return {"ok": False, "error": "Nothing valid to save."}, 400
    settings = read_settings()
    settings.update(changes)
    main_path, mirror_path = _settings_paths()
    try:
        os.makedirs(os.path.dirname(main_path), exist_ok=True)
        safe_json.write_json(main_path, settings)
    except OSError as exc:
        return {"ok": False, "error": f"The pet settings couldn't be saved: {exc}"}, 500
    try:
        safe_json.write_json(mirror_path, settings)
    except OSError:
        pass  # The main copy is saved. The floating pet falls back to KALKI's copy.
    return {"ok": True, "pet": settings}, 200


def _pet_processes():
    import psutil
    found = []
    for process in psutil.process_iter(["cmdline"]):
        try:
            command = " ".join(process.info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(marker in command for marker in _PET_PROCESS_MARKERS):
            found.append(process)
    return found


def overlay_running() -> bool:
    return bool(_pet_processes())


def _start_overlay() -> Optional[str]:
    """Start the floating pet. Returns an error message, or None if it started."""
    app_dir = _config["app_dir"]
    exe = os.path.join(app_dir, "KALKI_Pet.exe")
    script = os.path.join(app_dir, "desktop_pet.py")
    try:
        if os.path.exists(exe):
            subprocess.Popen([exe], cwd=app_dir)
        elif os.path.exists(script):
            subprocess.Popen([sys.executable, script], cwd=app_dir)
        else:
            return "The desktop pet isn't installed."
    except OSError as exc:
        return f"The desktop pet couldn't start: {exc}"
    return None


def _stop_overlay() -> None:
    import psutil
    for process in _pet_processes():
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def set_overlay(enable: bool) -> Result:
    running = overlay_running()
    if not enable:
        if running:
            _stop_overlay()
        return {"ok": True, "running": False}, 200
    if running:
        return {"ok": True, "running": True}, 200  # Never start a second copy.
    problem = _start_overlay()
    if problem:
        return {"ok": False, "error": problem}, 500
    return {"ok": True, "running": True}, 200


def overlay_status(body: Dict[str, Any]) -> Result:
    return {"ok": True, "running": overlay_running()}, 200


def overlay_post(body: Dict[str, Any]) -> Result:
    if body.get("toggle"):
        return set_overlay(not overlay_running())
    if isinstance(body.get("enabled"), bool):
        return set_overlay(body["enabled"])
    return overlay_status(body)


def toggle(body: Dict[str, Any]) -> Result:
    return set_overlay(not overlay_running())


def status(body: Dict[str, Any]) -> Result:
    return _config["status"](), 200


GET_ROUTES = {
    "/api/pet": get_pet,
    "/api/pet/overlay": overlay_status,
    "/api/pet/status": status,
}

POST_ROUTES = {
    "/api/pet": save_pet,
    "/api/pet/overlay": overlay_post,
    "/api/pet/toggle": toggle,
}
