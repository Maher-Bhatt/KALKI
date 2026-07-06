import os
import json
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Optional

import config

# Fallback values
DEFAULT_LOCATION = {
    "city": "Ahmedabad",
    "state": "Gujarat",
    "country": "India"
}


def _query_gps_coordinates() -> Optional[tuple[float, float]]:
    """Query the native Windows Geolocation API via PowerShell WinRT bridge."""
    if os.name != "nt":
        return None
    try:
        # PowerShell script using Windows Geolocation API
        ps_cmd = (
            "[void][Windows.Devices.Geolocation.Geolocator, Windows.Devices.Geolocation, ContentType=WindowsRuntime]; "
            "$locator = New-Object Windows.Devices.Geolocation.Geolocator; "
            "$pos = $locator.GetGeopositionAsync().GetAwaiter().GetResult(); "
            "Write-Output ($pos.Coordinate.Point.Position.Latitude.ToString() + ',' + $pos.Coordinate.Point.Position.Longitude.ToString())"
        )
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
            startupinfo=startupinfo
        )
        if res.returncode == 0 and res.stdout:
            parts = res.stdout.strip().split(",")
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
    except Exception:
        pass
    return None


def _reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, str]]:
    """Convert coordinates to city/state/country using OpenStreetMap Nominatim."""
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KALKI-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            address = data.get("address", {})
            city = address.get("city") or address.get("town") or address.get("village") or address.get("suburb") or ""
            state = address.get("state") or ""
            country = address.get("country") or ""
            if city or state:
                return {
                    "city": city,
                    "state": state,
                    "country": country
                }
    except Exception:
        pass
    return None


def _query_ip_location() -> Optional[Dict[str, str]]:
    """Query location using IP Geolocation."""
    try:
        req = urllib.request.Request("http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read())
            if data.get("status") == "success":
                return {
                    "city": data.get("city", ""),
                    "state": data.get("regionName", ""),
                    "country": data.get("country", "")
                }
    except Exception:
        pass
    return None


def get_resolved_location() -> Dict[str, str]:
    """
    Resolve location using prioritized providers:
    1. Manual Override (Config)
    2. Native GPS Coordinates (Windows Geolocation API)
    3. IP Geolocation API
    4. Default Fallback
    """
    # 1. Check manual config override (make sure they aren't placeholder strings)
    cfg_city = getattr(config, "OWNER_CITY", "").strip()
    cfg_state = getattr(config, "OWNER_STATE", "").strip()
    cfg_country = getattr(config, "OWNER_COUNTRY", "").strip()
    
    # Ignore default placeholder values
    if cfg_city and cfg_city.lower() != "yourcity":
        return {
            "city": cfg_city,
            "state": cfg_state,
            "country": cfg_country
        }

    # 2. Try native GPS
    coords = _query_gps_coordinates()
    if coords:
        gps_loc = _reverse_geocode(coords[0], coords[1])
        if gps_loc:
            return gps_loc

    # 3. Try IP geolocation
    ip_loc = _query_ip_location()
    if ip_loc:
        return ip_loc

    # 4. Final default
    return DEFAULT_LOCATION
