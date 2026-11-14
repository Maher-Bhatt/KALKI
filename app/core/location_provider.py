"""Where this PC is, from Windows location (GPS, Wi-Fi or cell), never from your IP address.

Used for the weather. Off until you turn on "Use this PC's location" (USE_DEVICE_LOCATION).
Windows decides how the position is found and asks for permission in its own settings;
KALKI only reads the result. The coordinates stay in memory: they go to Open-Meteo for the
weather and to OpenStreetMap once to name your city, and aren't saved anywhere.
"""

import json
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

import config

REFRESH_SECONDS = 30 * 60
_lock = threading.Lock()
_last: Dict[str, Any] = {}

# Windows PowerShell 5 can't await Windows Runtime calls directly, so convert them to .NET tasks.
_PS = r"""
$ErrorActionPreference = 'Stop'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
  [void][Windows.Devices.Geolocation.Geolocator, Windows.Devices.Geolocation, ContentType = WindowsRuntime]
  $accessTask = $asTask.MakeGenericMethod([Windows.Devices.Geolocation.GeolocationAccessStatus]).Invoke($null, @([Windows.Devices.Geolocation.Geolocator]::RequestAccessAsync()))
  [void]$accessTask.Wait(10000)
  if ($accessTask.Result -ne 'Allowed') { Write-Output ('ACCESS:' + $accessTask.Result); exit 0 }
  $g = New-Object Windows.Devices.Geolocation.Geolocator
  $g.DesiredAccuracyInMeters = 100
  $task = $asTask.MakeGenericMethod([Windows.Devices.Geolocation.Geoposition]).Invoke($null, @($g.GetGeopositionAsync()))
  if (-not $task.Wait(20000)) { Write-Output 'TIMEOUT'; exit 0 }
  $c = $task.Result.Coordinate
  Write-Output ('OK:{0},{1},{2},{3}' -f $c.Point.Position.Latitude.ToString([Globalization.CultureInfo]::InvariantCulture), $c.Point.Position.Longitude.ToString([Globalization.CultureInfo]::InvariantCulture), [int]$c.Accuracy, $c.PositionSource)
} catch {
  Write-Output ('ERROR:' + $_.Exception.GetBaseException().Message)
}
"""

ACCESS_HELP = ("Windows location is off, or apps aren't allowed to use it. Turn it on in Windows Settings > "
               "Privacy & security > Location, including \"Let desktop apps access your location\".")


def parse(output: str) -> Dict[str, Any]:
    """Read the PowerShell result."""
    line = (output or "").strip().splitlines()[-1] if (output or "").strip() else ""
    if line.startswith("OK:"):
        try:
            lat, lon, acc, source = line[3:].split(",")
            return {"ok": True, "latitude": float(lat), "longitude": float(lon), "accuracy_m": int(acc),
                    "source": source.strip()}
        except ValueError:
            return {"ok": False, "reason": "Windows gave a location KALKI couldn't read."}
    if line.startswith("ACCESS:"):
        return {"ok": False, "reason": ACCESS_HELP, "access": line[7:]}
    if line == "TIMEOUT":
        return {"ok": False, "reason": "Windows couldn't find this PC's location in time. Try again in a moment."}
    if line.startswith("ERROR:"):
        return {"ok": False, "reason": f"Windows location didn't work: {line[6:].strip()}"}
    return {"ok": False, "reason": "Windows location didn't answer."}


def device_location(timeout: int = 40) -> Dict[str, Any]:
    """Ask Windows where this PC is. Takes a few seconds."""
    if os.name != "nt":
        return {"ok": False, "reason": "Device location is only available on Windows."}
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS],
                             capture_output=True, text=True, timeout=timeout,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "Windows couldn't find this PC's location in time. Try again in a moment."}
    except OSError as e:
        return {"ok": False, "reason": f"Couldn't ask Windows for the location ({e.strerror or e})."}
    return parse(res.stdout)


def place_name(lat: float, lon: float) -> Optional[Dict[str, str]]:
    """City, state and country for coordinates, from OpenStreetMap."""
    query = urllib.parse.urlencode({"format": "json", "lat": f"{lat:.3f}", "lon": f"{lon:.3f}", "zoom": 10})
    try:
        req = urllib.request.Request(f"https://nominatim.openstreetmap.org/reverse?{query}",
                                     headers={"User-Agent": "KALKI-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            address = json.loads(r.read()).get("address", {})
    except (OSError, ValueError):
        return None
    city = address.get("city") or address.get("town") or address.get("village") or address.get("suburb") or ""
    if not (city or address.get("state")):
        return None
    return {"city": city, "state": address.get("state", ""), "country": address.get("country", "")}


def enabled() -> bool:
    return bool(getattr(config, "USE_DEVICE_LOCATION", False))


def refresh(force: bool = False, name_place: bool = True) -> Dict[str, Any]:
    """Get a fresh fix if location is on and the last one is old, and use it for the weather.
    Returns the latest result (from now or from the last successful fix)."""
    if not enabled() and not force:
        return {"ok": False, "reason": "Using this PC's location is off."}
    with _lock:
        if not force and _last.get("ok") and time.time() - _last.get("at", 0) < REFRESH_SECONDS:
            return dict(_last)
    fix = device_location()
    if not fix["ok"]:
        with _lock:
            _last.update(error=fix["reason"])
        return fix
    fix["at"] = time.time()
    config.LATITUDE, config.LONGITUDE = fix["latitude"], fix["longitude"]
    if name_place:
        place = place_name(fix["latitude"], fix["longitude"])
        if place:
            fix.update(place)
            current = (getattr(config, "OWNER_CITY", "") or "").strip()
            if not current or current.lower() == "yourcity" or _last.get("city") == current:
                config.OWNER_CITY, config.OWNER_STATE, config.OWNER_COUNTRY = place["city"], place["state"], place["country"]
    with _lock:
        _last.clear()
        _last.update(fix)
    return dict(fix)


def last() -> Dict[str, Any]:
    with _lock:
        return dict(_last)


def get_resolved_location() -> Dict[str, str]:
    """City, state and country for greetings and the dashboard. A city you typed in Settings
    wins; otherwise this PC's location if that's on. Never your IP address."""
    cfg = {k: (getattr(config, f"OWNER_{k.upper()}", "") or "").strip() for k in ("city", "state", "country")}
    if cfg["city"] and cfg["city"].lower() != "yourcity":
        return cfg
    if enabled():
        fix = refresh()
        if fix.get("ok") and fix.get("city"):
            return {"city": fix["city"], "state": fix.get("state", ""), "country": fix.get("country", "")}
    return cfg


def location_route(body: Dict[str, Any]):
    """POST /api/location/device: find this PC now (the Settings test button), or report the last fix."""
    if body.get("refresh"):
        result = refresh(force=True)
    else:
        result = last() or {"ok": False, "reason": "No location yet."}
    return {"enabled": enabled(), **result, "ok": bool(result.get("ok"))}, 200


POST_ROUTES = {"/api/location/device": location_route}
