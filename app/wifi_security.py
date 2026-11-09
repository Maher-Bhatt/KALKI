"""Wi-Fi security for this PC: saved networks, the live connection, what's nearby.

Scope: networks this Windows account already saved, plus the public information
every device can see over the air. It never attacks, joins, or captures traffic
from anyone's network.

Saved-profile data comes from `netsh wlan export profile`. Its XML is the same on
every Windows display language, unlike `netsh wlan show ...` text. The live
connection and nearby scan have no XML form, so those two parse English labels and
return "unknown" fields on other display languages rather than guessing.

Keys only leave this module through reveal_password(). Callers must get the user's
approval first, and must never log, store, or pass a key to an AI model.
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

LOCATION_HELP = (
    "Windows only shares Wi-Fi details with apps when location access is on. "
    "Open Settings > Privacy & security > Location, turn on Location services and "
    "'Let desktop apps access your location', then try again."
)
ADMIN_HELP = "Windows needs administrator rights for this. Run KALKI as administrator and try again."

_RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "unknown": 3, "ok": 4, "good": 5}

_WEAK_WORDS = ("password", "passw0rd", "12345678", "87654321", "qwerty", "admin", "welcome",
               "letmein", "iloveyou", "wifi", "internet", "11111111", "00000000", "abcd1234")


def is_supported() -> bool:
    return os.name == "nt"


def _unsupported() -> Dict[str, Any]:
    return {"ok": False, "kind": "unavailable", "error": "Wi-Fi security is only available on Windows."}


def _netsh(args: List[str], timeout: int = 15) -> Tuple[int, str]:
    """Run `netsh wlan ...` with an argument list: never through a shell."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", *args],
            capture_output=True, timeout=timeout, creationflags=_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return 1, "netsh timed out"
    except OSError as exc:
        return 1, f"netsh could not start: {exc}"
    raw = result.stdout or result.stderr or b""
    for encoding in ("oem", "utf-8"):
        try:
            return result.returncode, raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return result.returncode, raw.decode("utf-8", "replace")


def _location_blocked(text: str) -> bool:
    low = (text or "").lower()
    return "location" in low and ("permission" in low or "services" in low)


def _needs_elevation(text: str) -> bool:
    low = (text or "").lower()
    return "elevation" in low or "access is denied" in low or "administrator" in low


# ── Saved profiles ───────────────────────────────────────────────────────
def parse_profile_xml(xml_text: str) -> Dict[str, Any]:
    root = ET.fromstring(re.sub(r'\sxmlns="[^"]+"', "", xml_text, count=1))
    security = root.find("MSM/security")
    shared = security.find("sharedKey") if security is not None else None
    auth = security.find("authEncryption") if security is not None else None

    def text(node, path, default=""):
        if node is None:
            return default
        found = node.find(path)
        return (found.text or default) if found is not None else default

    return {
        "ssid": text(root, "SSIDConfig/SSID/name") or text(root, "name"),
        "profile": text(root, "name"),
        "hidden": text(root, "SSIDConfig/nonBroadcast", "false").lower() == "true",
        "auto_connect": text(root, "connectionMode", "auto").lower() == "auto",
        "authentication": text(auth, "authentication"),
        "encryption": text(auth, "encryption"),
        "key": text(shared, "keyMaterial") if shared is not None else None,
        "key_protected": text(shared, "protected", "false").lower() == "true",
    }


def export_profiles(name: Optional[str] = None, with_keys: bool = False) -> List[Dict[str, Any]]:
    """Read saved profiles through a private temp folder that is always deleted,
    because `key=clear` briefly writes keys to disk in plain text."""
    folder = tempfile.mkdtemp(prefix="kalki_wifi_")
    try:
        args = ["export", "profile", f"folder={folder}"]
        if name:
            args.append(f"name={name}")
        if with_keys:
            args.append("key=clear")
        _netsh(args, timeout=30)
        profiles = []
        for path in glob.glob(os.path.join(folder, "*.xml")):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
                    profiles.append(parse_profile_xml(handle.read()))
            except (ET.ParseError, OSError):
                continue
        return profiles
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def assess_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Rate a network's security from its authentication and encryption."""
    auth = str(profile.get("authentication") or "").lower()
    enc = str(profile.get("encryption") or "").lower()
    findings: List[str] = []
    fix = ""

    if enc == "wep" or auth == "shared":
        risk, label = "critical", "WEP (broken)"
        findings.append("WEP can be cracked in minutes. Treat this network as having no protection.")
        fix = "Change the router to WPA2 or WPA3, or forget this network."
    elif auth == "owe":
        risk, label = "medium", "Enhanced Open"
        findings.append("Traffic is encrypted, but nothing proves who runs this network.")
        fix = "Use HTTPS or a VPN for anything private."
    elif auth == "open" or (enc == "none" and auth):
        risk, label = "high", "Open (no password)"
        findings.append("No encryption on the Wi-Fi link, so people nearby may see unencrypted traffic.")
        fix = "Turn off auto-connect, and use a VPN on this network."
    elif enc == "tkip" or auth in ("wpa", "wpapsk"):
        risk, label = "high", "WPA / TKIP (outdated)"
        findings.append("WPA and TKIP are outdated and have known weaknesses.")
        fix = "Change the router to WPA2-AES or WPA3."
    elif auth.startswith("wpa3"):
        risk, label = "good", "WPA3"
    elif auth.startswith("wpa2") and enc in ("aes", "gcmp", "gcmp256", "ccmp"):
        risk, label = "ok", "WPA2 (AES)"
    else:
        risk, label = "unknown", profile.get("authentication") or "Unknown"

    if profile.get("auto_connect") and risk in ("critical", "high", "medium"):
        findings.append("Your PC connects to this automatically, so a look-alike network could catch it.")
    if profile.get("hidden"):
        findings.append("Hidden network: your PC keeps calling out its name to find it, which can reveal it.")
    return {"risk": risk, "label": label, "findings": findings, "fix": fix}


def _public_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Everything the UI may see. Never includes the key."""
    return {
        "ssid": profile.get("ssid"),
        "hidden": bool(profile.get("hidden")),
        "auto_connect": bool(profile.get("auto_connect")),
        "authentication": profile.get("authentication"),
        "encryption": profile.get("encryption"),
        **assess_profile(profile),
    }


def rate_password(password: str) -> Dict[str, Any]:
    """Rate a key's strength. The result never contains any of the key."""
    pw = password or ""
    low = pw.lower()
    classes = sum(bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    reasons: List[str] = []
    if len(pw) < 12:
        reasons.append("Shorter than 12 characters, which is practical to guess offline.")
    if any(word in low for word in _WEAK_WORDS):
        reasons.append("Contains a very common word or number pattern.")
    if len(set(pw)) <= 4:
        reasons.append("Uses very few different characters.")
    if reasons:
        strength = "weak"
    elif len(pw) >= 20 or (len(pw) >= 14 and classes >= 3):
        strength = "strong"
    else:
        strength = "fair"
        reasons.append("Fine for most homes. 14+ characters with mixed types would be stronger.")
    return {"strength": strength, "reasons": reasons}


# ── Live connection ──────────────────────────────────────────────────────
def _field_map(output: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for line in (output or "").splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields.setdefault(key.strip().lower(), value.strip())
    return fields


def _percent(value: str) -> Optional[int]:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def _normalize_display(auth: str, cipher: str) -> Tuple[str, str]:
    """Map the display text of `show interfaces/networks` onto profile XML values."""
    a = (auth or "").lower()
    if "wpa3" in a:
        mapped_auth = "WPA3SAE" if ("personal" in a or "sae" in a) else "WPA3"
    elif "wpa2" in a:
        mapped_auth = "WPA2PSK" if "personal" in a else "WPA2"
    elif "wpa" in a:
        mapped_auth = "WPAPSK" if "personal" in a else "WPA"
    elif "owe" in a or "enhanced" in a:
        mapped_auth = "OWE"
    elif "shared" in a:
        mapped_auth = "shared"
    elif "open" in a:
        mapped_auth = "open"
    else:
        mapped_auth = auth or ""
    c = (cipher or "").lower()
    if "ccmp" in c or "gcmp" in c or "aes" in c:
        mapped_cipher = "AES"
    elif "tkip" in c:
        mapped_cipher = "TKIP"
    elif "wep" in c:
        mapped_cipher = "WEP"
    elif "none" in c:
        mapped_cipher = "none"
    else:
        mapped_cipher = cipher or ""
    return mapped_auth, mapped_cipher


def parse_interface(output: str) -> Dict[str, Any]:
    fields = _field_map(output)
    state = fields.get("state", "")
    ssid = fields.get("ssid", "")
    return {
        "adapter": fields.get("name") or fields.get("description") or "",
        "state": state,
        "connected": state.lower() == "connected" or bool(ssid),
        "ssid": ssid,
        "bssid": fields.get("ap bssid") or fields.get("bssid") or "",
        "authentication": fields.get("authentication", ""),
        "cipher": fields.get("cipher", ""),
        "radio": fields.get("radio type", ""),
        "channel": fields.get("channel", ""),
        "signal": _percent(fields.get("signal", "")),
        "speed_mbps": _percent(fields.get("receive rate (mbps)", "")),
    }


def current_connection() -> Dict[str, Any]:
    code, output = _netsh(["show", "interfaces"])
    low = output.lower()
    if _location_blocked(output):
        return {"available": False, "kind": "location_required", "message": LOCATION_HELP}
    if "no wireless interface" in low:
        return {"available": False, "kind": "no_adapter", "message": "This PC has no Wi-Fi adapter."}
    if "wlansvc" in low or "not running" in low:
        return {"available": False, "kind": "service_off", "message": "The Windows Wi-Fi service (WLAN AutoConfig) isn't running."}
    if code != 0:
        return {"available": False, "kind": "error", "message": output.strip()[:200] or "netsh failed."}
    info = parse_interface(output)
    info["available"] = True
    if info["connected"]:
        auth, cipher = _normalize_display(info["authentication"], info["cipher"])
        info.update(assess_profile({"authentication": auth, "encryption": cipher}))
    return info


# ── Nearby networks ──────────────────────────────────────────────────────
def parse_nearby(output: str) -> List[Dict[str, Any]]:
    networks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    bssid: Optional[Dict[str, Any]] = None
    for line in (output or "").splitlines():
        match = re.match(r"^\s*SSID\s+\d+\s*:\s*(.*)$", line)
        if match:
            current = {"ssid": match.group(1).strip(), "authentication": "", "encryption": "", "bssids": []}
            networks.append(current)
            bssid = None
            continue
        if current is None:
            continue
        match = re.match(r"^\s*BSSID\s+\d+\s*:\s*(.*)$", line)
        if match:
            bssid = {"bssid": match.group(1).strip(), "signal": None, "channel": "", "radio": ""}
            current["bssids"].append(bssid)
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip().lower(), value.strip()
        if key == "authentication":
            current["authentication"] = value
        elif key == "encryption":
            current["encryption"] = value
        elif bssid is not None and key == "signal":
            bssid["signal"] = _percent(value)
        elif bssid is not None and key == "channel":
            bssid["channel"] = value
        elif bssid is not None and key == "radio type":
            bssid["radio"] = value
    for network in networks:
        signals = [b["signal"] for b in network["bssids"] if b["signal"] is not None]
        network["best_signal"] = max(signals) if signals else None
        auth, cipher = _normalize_display(network["authentication"], network["encryption"])
        network.update(assess_profile({"authentication": auth, "encryption": cipher}))
    return networks


def find_impostors(nearby: List[Dict[str, Any]], saved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A nearby network using a saved name but weaker security may be a fake access
    point. Several access points with the same name and security are normal."""
    saved_by_ssid = {p.get("ssid"): p for p in saved if p.get("ssid")}
    flagged = []
    for network in nearby:
        known = saved_by_ssid.get(network.get("ssid"))
        if not known:
            continue
        auth, cipher = _normalize_display(network.get("authentication", ""), network.get("encryption", ""))
        seen = assess_profile({"authentication": auth, "encryption": cipher})
        trusted = assess_profile({"authentication": known.get("authentication"), "encryption": known.get("encryption")})
        if seen["risk"] == "unknown" or trusted["risk"] == "unknown":
            continue
        if _RISK_ORDER[seen["risk"]] < _RISK_ORDER[trusted["risk"]]:
            flagged.append({
                "ssid": network["ssid"],
                "saved_security": trusted["label"],
                "seen_security": seen["label"],
                "message": (f"'{network['ssid']}' is saved as {trusted['label']}, but a network with that name is "
                            f"broadcasting {seen['label']}. This could be a fake access point, or the router's "
                            "settings may have changed. Don't connect until you've checked."),
            })
    return flagged


def scan_nearby() -> Dict[str, Any]:
    if not is_supported():
        return _unsupported()
    code, output = _netsh(["show", "networks", "mode=bssid"], timeout=20)
    if _location_blocked(output):
        return {"ok": False, "kind": "location_required", "error": LOCATION_HELP}
    if code != 0:
        return {"ok": False, "kind": "error", "error": output.strip()[:200] or "netsh failed."}
    networks = parse_nearby(output)
    networks.sort(key=lambda n: (_RISK_ORDER.get(n["risk"], 3), -(n["best_signal"] or 0)))
    return {"ok": True, "networks": networks, "impostors": find_impostors(networks, export_profiles())}


# ── Overview and actions ─────────────────────────────────────────────────
def overview() -> Dict[str, Any]:
    if not is_supported():
        return _unsupported()
    profiles = [_public_profile(p) for p in export_profiles()]
    profiles.sort(key=lambda p: (_RISK_ORDER.get(p["risk"], 3), (p["ssid"] or "").lower()))
    counts: Dict[str, int] = {}
    for profile in profiles:
        counts[profile["risk"]] = counts.get(profile["risk"], 0) + 1
    return {"ok": True, "connection": current_connection(), "profiles": profiles, "counts": counts}


def _is_known(ssid: str) -> bool:
    return bool(ssid) and any(p.get("ssid") == ssid or p.get("profile") == ssid for p in export_profiles())


def _unknown_network(ssid: str) -> Dict[str, Any]:
    return {"ok": False, "kind": "unknown", "error": f"'{ssid}' isn't a Wi-Fi network saved on this PC."}


def reveal_password(ssid: str) -> Dict[str, Any]:
    """Return a saved key. The caller must have the user's approval first."""
    if not is_supported():
        return _unsupported()
    ssid = (ssid or "").strip()
    if not ssid:
        return {"ok": False, "kind": "invalid", "error": "Choose a network first."}
    match = next((p for p in export_profiles(name=ssid, with_keys=True) if ssid in (p.get("ssid"), p.get("profile"))), None)
    if not match:
        return _unknown_network(ssid)
    if match.get("key_protected"):
        return {"ok": False, "kind": "needs_admin", "error": ADMIN_HELP}
    if not match.get("key"):
        return {"ok": False, "kind": "no_password", "error": f"'{ssid}' has no saved password. It's open, or it uses a work sign-in."}
    return {"ok": True, "ssid": ssid, "password": match["key"]}


def audit_passwords() -> Dict[str, Any]:
    """Rate every saved key without returning any of them."""
    if not is_supported():
        return _unsupported()
    results = []
    needs_admin = False
    for profile in export_profiles(with_keys=True):
        if profile.get("key_protected"):
            needs_admin = True
            results.append({"ssid": profile.get("ssid"), "strength": "unknown", "reasons": ["Needs administrator rights to check."]})
        elif profile.get("key"):
            results.append({"ssid": profile.get("ssid"), **rate_password(profile["key"])})
    order = {"weak": 0, "fair": 1, "unknown": 2, "strong": 3}
    results.sort(key=lambda r: order.get(r["strength"], 2))
    return {"ok": True, "results": results, "needs_admin": needs_admin}


def _run_change(args: List[str], success: str) -> Dict[str, Any]:
    code, output = _netsh(args)
    if code == 0:
        return {"ok": True, "message": success}
    if _needs_elevation(output):
        return {"ok": False, "kind": "needs_admin", "error": ADMIN_HELP}
    return {"ok": False, "kind": "error", "error": output.strip()[:200] or "Windows refused the change."}


def forget_network(ssid: str) -> Dict[str, Any]:
    if not is_supported():
        return _unsupported()
    ssid = (ssid or "").strip()
    if not _is_known(ssid):
        return _unknown_network(ssid)
    return _run_change(["delete", "profile", f"name={ssid}"], f"Forgot '{ssid}'.")


def set_auto_connect(ssid: str, enabled: bool) -> Dict[str, Any]:
    if not is_supported():
        return _unsupported()
    ssid = (ssid or "").strip()
    if not _is_known(ssid):
        return _unknown_network(ssid)
    mode = "auto" if enabled else "manual"
    state = "on" if enabled else "off"
    return _run_change(["set", "profileparameter", f"name={ssid}", f"connectionmode={mode}"],
                       f"Auto-connect is {state} for '{ssid}'.")


def spoken_summary() -> str:
    """Plain-language check-up for voice and chat. Contains no keys."""
    data = overview()
    if not data.get("ok"):
        return data.get("error", "I couldn't check Wi-Fi.")
    parts = []
    connection = data["connection"]
    if connection.get("connected"):
        parts.append(f"You're connected to {connection.get('ssid') or 'a network'}, secured with {connection.get('label', 'unknown security')}.")
    elif connection.get("message"):
        parts.append(connection["message"])
    risky = [p for p in data["profiles"] if p["risk"] in ("critical", "high", "medium")]
    if risky:
        names = ", ".join(p["ssid"] for p in risky[:5])
        parts.append(f"{len(risky)} of your {len(data['profiles'])} saved networks need attention: {names}.")
    else:
        parts.append(f"None of your {len(data['profiles'])} saved networks have a security problem.")
    return " ".join(parts)
