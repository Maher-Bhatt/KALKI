"""KALKI Antivirus & Endpoint Shield Engine.

Provides multi-layer security:
1. Native Windows Defender CLI and PowerShell integration for deep definition scans.
2. Built-in heuristic static analyzer (double extensions, PowerShell obfuscation,
   macro droppers, entropy analysis, and EICAR / signature checks).
3. Process & Memory Threat Monitor (miner detection, anomalous parentage, temp execution).
4. Phishing URL & Link Reputation Inspector.
5. Clipboard Hijack & Crypto-Clipper Protector.
6. Isolated Quarantine Vault with secure file permissions.
"""

import os
import sys
import time
import math
import glob
import json
import shutil
import hashlib
import re
import threading
import subprocess
from typing import Dict, Any, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

import oversight
import safe_json

_lock = threading.RLock()

# EICAR standard antivirus test signature
EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
EICAR_SUBSTRING = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

# High-risk executable extensions
DANGEROUS_EXTENSIONS = {
    ".exe", ".scr", ".vbs", ".vbe", ".bat", ".cmd", ".ps1", ".hta", ".wsf",
    ".js", ".jse", ".jar", ".pif", ".cpl", ".iso", ".img", ".lnk"
}

# Suspicious script patterns
SUSPICIOUS_PATTERNS = [
    (re.compile(rb"(?i)frombase64string"), "Base64 Obfuscated Payload"),
    (re.compile(rb"(?i)invoke-expression|iex\s+"), "PowerShell Dynamic Execution (IEX)"),
    (re.compile(rb"(?i)downloadstring|downloadfile"), "Remote Script Downloader"),
    (re.compile(rb"(?i)bypass\s+-noprofile|-w\s+hidden|-windowstyle\s+hidden"), "Hidden Execution Policy Bypass"),
    (re.compile(rb"(?i)wscript\.shell|shell\.application"), "Windows Script Host Shell Execution"),
    (re.compile(rb"(?i)certutil\s+-urlcache"), "Certutil File Fetcher"),
    (re.compile(rb"(?i)regsvr32\s+/s\s+/u\s+/i:"), "Squiblydoo AppLocker Bypass"),
    (re.compile(rb"(?i)virtualalloc|writeprocessmemory|createremotethread"), "Process Injection API References"),
    (re.compile(rb"(?i)vbaProject\.bin|Auto_Open|Document_Open"), "Suspicious Embedded Office Macro"),
]

# Mining pool keywords and ports
MINING_KEYWORDS = ["xmrig", "minerd", "stratum+tcp", "stratum+ssl", "nicehash", "nanopool", "supportxmr", "moneroocean"]
# 8888 is deliberately absent: it's KALKI's own default port.
MINING_PORTS = {3333, 4444, 5555, 7777, 9999, 14444, 14433, 45700}

# Cryptocurrency address regexes for clipboard protection
CRYPTO_PATTERNS = {
    "Bitcoin": re.compile(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "Ethereum": re.compile(r"\b(0x[a-fA-F0-9]{40})\b"),
    "Monero": re.compile(r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"),
}


# Each key is a monitor in shield_monitors.py. The link guard reads the active
# browser address, so it stays off until the user turns it on.
DEFAULT_SHIELDS = {
    "download_watcher": True,
    "process_monitor": True,
    "clipboard_guard": True,
    "phishing_shield": False,
}


def _get_data_dir() -> str:
    from runtime_paths import prepare_runtime
    return prepare_runtime().user_data_dir


def _get_quarantine_dir() -> str:
    qdir = os.path.join(_get_data_dir(), "quarantine")
    os.makedirs(qdir, exist_ok=True)
    return qdir


def _get_threat_log_path() -> str:
    return os.path.join(_get_data_dir(), "threat_log.json")


def _get_shield_settings_path() -> str:
    return os.path.join(_get_data_dir(), "shield_settings.json")


def get_shield_settings() -> Dict[str, bool]:
    with _lock:
        settings = dict(DEFAULT_SHIELDS)
        try:
            saved = safe_json.read_json(_get_shield_settings_path(), {})
            settings.update({k: bool(v) for k, v in saved.items() if k in DEFAULT_SHIELDS})
        except OSError as e:
            oversight.record_alert("antivirus", f"Couldn't read monitor settings, so defaults are in use: {e}", "warning")
        return settings


def update_shield_settings(updates: Dict[str, bool]) -> Dict[str, bool]:
    with _lock:
        current = get_shield_settings()
        current.update({k: bool(v) for k, v in (updates or {}).items() if k in DEFAULT_SHIELDS})
        try:
            safe_json.write_json(_get_shield_settings_path(), current)
        except OSError as e:
            oversight.record_alert("antivirus", f"Failed saving shield settings: {e}", "warning")
        return current


def _find_mpcmdrun() -> Optional[str]:
    """Locate Windows Defender CLI executable."""
    if os.name != "nt":
        return None
    candidates = [
        r"C:\Program Files\Windows Defender\MpCmdRun.exe",
        r"C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe",
    ]
    for pattern in candidates:
        matches = sorted(glob.glob(pattern), reverse=True)
        for m in matches:
            if os.path.isfile(m):
                return m
    return None


def _age(value: Any) -> Optional[int]:
    """Defender reports ages in days; 4294967295 (or -1) means "never"."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return None if n < 0 or n >= 65535 else n


def get_windows_defender_status() -> Dict[str, Any]:
    """Windows Defender's real state, from Get-MpComputerStatus. Nothing is assumed:
    a value Windows doesn't report stays None and the screen says "unknown"."""
    if os.name != "nt":
        return {"available": False, "reason": "Windows Defender is only on Windows."}
    fields = ("AMServiceEnabled", "AntivirusEnabled", "RealTimeProtectionEnabled", "IsTamperProtected",
              "AntivirusSignatureAge", "AntivirusSignatureLastUpdated", "QuickScanAge", "FullScanAge",
              "QuickScanEndTime", "AMProductVersion")
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
           "Get-MpComputerStatus | Select-Object " + ", ".join(fields)
           + " | ConvertTo-Json -Compress -Depth 2"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "Windows Defender didn't answer in time."}
    except OSError as e:
        return {"available": False, "reason": f"Couldn't ask Windows Defender ({e.strerror or e})."}
    if res.returncode != 0 or not res.stdout.strip():
        detail = (res.stderr or "").strip().splitlines()
        reason = "Windows Defender isn't running. Another antivirus may have replaced it."
        if detail and "0x800106ba" in detail[0].lower():
            reason = "Windows Defender's service isn't running. Another antivirus may have replaced it."
        return {"available": False, "reason": reason}
    try:
        data = json.loads(res.stdout)
    except ValueError:
        return {"available": False, "reason": "Windows Defender's answer couldn't be read."}

    def when(value: Any) -> Optional[str]:
        # PowerShell 5 serialises dates as "/Date(1731577200000)/".
        m = re.search(r"(\d{10,})", str(value or ""))
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(m.group(1)) / 1000)) if m else None

    return {
        "available": True,
        "service_enabled": bool(data.get("AMServiceEnabled")),
        "antivirus_enabled": bool(data.get("AntivirusEnabled")),
        "realtime_enabled": bool(data.get("RealTimeProtectionEnabled")),
        "tamper_protected": data.get("IsTamperProtected"),
        "signature_age_days": _age(data.get("AntivirusSignatureAge")),
        "signatures_updated": when(data.get("AntivirusSignatureLastUpdated")),
        "quick_scan_age_days": _age(data.get("QuickScanAge")),
        "full_scan_age_days": _age(data.get("FullScanAge")),
        "last_quick_scan": when(data.get("QuickScanEndTime")),
        "version": data.get("AMProductVersion") or "",
    }


def _calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy to detect packed, encrypted, or compressed payloads."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    occurrences = [0] * 256
    for byte in data:
        occurrences[byte] += 1
    for count in occurrences:
        if count == 0:
            continue
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 2)


def _defender_threat_name(output: str) -> str:
    """The threat name Defender printed, if any (e.g. "Virus:DOS/EICAR_Test_File"). Only used for
    display: whether something was detected comes from the exit code."""
    m = re.search(r"Threat\s*:\s*(\S[^\r\n]*)", output or "")
    return m.group(1).strip() if m else ""


def defender_scan(file_path: str, timeout: int = 120) -> Dict[str, Any]:
    """Ask Windows Defender about one file. MpCmdRun's documented exit codes: 0 means no
    threat, 2 means a threat was found, anything else means the scan didn't complete."""
    path = _find_mpcmdrun()
    if not path:
        return {"checked": False, "detected": False, "error": "Windows Defender isn't available on this PC."}
    try:
        res = subprocess.run([path, "-Scan", "-ScanType", "3", "-File", file_path, "-DisableRemediation"],
                             capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"checked": False, "detected": False, "error": "Windows Defender took too long to check this file."}
    except (OSError, subprocess.SubprocessError) as e:
        return {"checked": False, "detected": False, "error": f"Windows Defender couldn't be started ({type(e).__name__})."}
    if res.returncode == 0:
        return {"checked": True, "detected": False}
    if res.returncode == 2:
        return {"checked": True, "detected": True, "name": _defender_threat_name(res.stdout)}
    return {"checked": False, "detected": False, "error": f"Windows Defender couldn't check this file (exit code {res.returncode})."}


# File types where script-style patterns mean something. In programs and documents
# they match ordinary content (nearly every .exe mentions VirtualAlloc).
SCRIPT_EXTENSIONS = {".ps1", ".psm1", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".hta", ".wsf", ".wsh", ".sct"}
MACRO_EXTENSIONS = {".docm", ".xlsm", ".pptm", ".dotm", ".xltm"}
PATTERN_BYTES = 4 * 1024 * 1024
# Windows refuses to open a file Defender has blocked with these errors.
BLOCKED_BY_DEFENDER = {225, 226}  # ERROR_VIRUS_INFECTED, ERROR_VIRUS_DELETED


def _blocked_by_defender(path: str, error: OSError) -> bool:
    """Whether Windows refused the file because Defender reported it infected. Python's open()
    turns that into a plain "Invalid argument", so ask Windows for the real error."""
    if getattr(error, "winerror", None) in BLOCKED_BY_DEFENDER:
        return True
    if os.name != "nt" or error.errno != 22:
        return False
    try:
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateFileW.restype = ctypes.c_void_p
        handle = k32.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)  # GENERIC_READ, OPEN_EXISTING
        if handle not in (None, ctypes.c_void_p(-1).value):
            k32.CloseHandle(ctypes.c_void_p(handle))
            return False
        return ctypes.get_last_error() in BLOCKED_BY_DEFENDER
    except (AttributeError, OSError):
        return False


def scan_file(file_path: str) -> Dict[str, Any]:
    """Check one file with Windows Defender, plus a few plain checks of KALKI's own.

    verdict is one of:
      "threat"     Windows Defender detected it (or Windows blocked it as infected)
      "suspicious" KALKI's checks found something worth a look; Defender didn't flag it
      "clean"      Defender checked it and found nothing, and KALKI's checks agree
      "unchecked"  KALKI's checks found nothing but Defender couldn't check it, so this isn't a clean result
    KALKI never makes up a malware name: findings say what was seen and why it matters.
    """
    base = {"path": file_path, "filename": os.path.basename(file_path), "timestamp": time.time()}
    if not os.path.isfile(file_path):
        return {"ok": False, "clean": False, "verdict": "unchecked", "scan_status": "not_scanned",
                "error": "That file doesn't exist.", **base}
    try:
        file_size = os.path.getsize(file_path)
    except OSError as e:
        return {"ok": False, "clean": False, "verdict": "unchecked", "scan_status": "not_scanned",
                "error": f"Couldn't read the file: {e.strerror or e}", **base}

    lower_ext = os.path.splitext(base["filename"])[1].lower()
    findings: List[str] = []
    notes: List[str] = []

    sha256_hash, md5_hash, head = hashlib.sha256(), hashlib.md5(), b""
    try:
        with open(file_path, "rb") as f:
            head = f.read(PATTERN_BYTES)
            sha256_hash.update(head)
            md5_hash.update(head)
            while chunk := f.read(1024 * 1024):
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
    except OSError as e:
        if _blocked_by_defender(file_path, e):
            result = {"ok": True, "clean": False, "verdict": "threat", "scan_status": "scanned", "defender_checked": True,
                      "threat_level": "Critical", "threat_name": "Blocked by Windows Defender",
                      "findings": ["Windows refused to open this file because Windows Defender reported it as infected."],
                      "notes": [], "size_bytes": file_size, "sha256": "", "md5": "", **base}
            oversight.record_alert("antivirus", f"Windows Defender blocked {base['filename']}.", "critical")
            return result
        return {"ok": False, "clean": False, "verdict": "unchecked", "scan_status": "not_scanned",
                "error": f"Couldn't scan this file: {e.strerror or e}. It may be open in another program.",
                "size_bytes": file_size, **base}

    sha256_hex, md5_hex = sha256_hash.hexdigest(), md5_hash.hexdigest()

    # KALKI's own checks: plain reasons, never a malware name.
    double_ext = re.search(r"\.(pdf|docx?|xlsx?|pptx?|txt|jpe?g|png|mp[34]|zip)\.(exe|scr|com|pif|vbs|bat|cmd|ps1|hta|js)$",
                           base["filename"], re.IGNORECASE)
    if double_ext:
        findings.append(f"Suspicious because it ends in .{double_ext.group(1)}.{double_ext.group(2)}: it looks like a "
                        f"{double_ext.group(1).upper()} but runs as a program.")
    if sha256_hex == EICAR_SHA256 or EICAR_SUBSTRING in head[:1024]:
        findings.append("This is the EICAR test file, a harmless file every antivirus treats as a threat for testing.")
    if lower_ext in SCRIPT_EXTENSIONS or lower_ext in MACRO_EXTENSIONS:
        for pat, desc in SUSPICIOUS_PATTERNS:
            if pat.search(head):
                findings.append(f"Suspicious because the script contains: {desc}.")
    if lower_ext in {".exe", ".dll", ".scr"} and file_size > 1024:
        entropy = _calculate_entropy(head[:65536])
        if entropy > 7.45:
            # Installers and compressed programs look like this too, so it's a note, not a finding.
            notes.append(f"Its content is packed or compressed (entropy {entropy}/8). Common for installers; "
                         "also used to hide malware.")
    if file_size > PATTERN_BYTES and (lower_ext in SCRIPT_EXTENSIONS or lower_ext in MACRO_EXTENSIONS):
        notes.append(f"Only the first {PATTERN_BYTES // (1024 * 1024)} MB was checked by KALKI's own checks.")

    defender = defender_scan(file_path)
    if defender["detected"]:
        verdict, level = "threat", "Critical"
        name = f"Windows Defender: {defender['name']}" if defender.get("name") else "Windows Defender detected a threat"
        findings.insert(0, "Windows Defender detected a threat in this file.")
    elif findings:
        verdict, level = "suspicious", "Medium"
        name = "Looks suspicious"
    elif defender["checked"]:
        verdict, level, name = "clean", "Clean", "Nothing found"
    else:
        verdict, level, name = "unchecked", "Unknown", "Not fully checked"

    result = {
        "ok": True, "clean": verdict == "clean", "verdict": verdict, "scan_status": "scanned",
        "defender_checked": defender["checked"], **({} if defender["checked"] else {"defender_error": defender["error"]}),
        "threat_level": level, "threat_name": name, "findings": findings, "notes": notes,
        "size_bytes": file_size, "sha256": sha256_hex, "md5": md5_hex, **base,
    }
    if verdict in ("threat", "suspicious"):
        oversight.record_alert("antivirus", f"{base['filename']}: {name}.", "critical" if verdict == "threat" else "warning")
    return result


def scan_quick() -> Dict[str, Any]:
    """
    Scans common persistence and drop vectors:
    - User Downloads folder
    - AppData Local Temp
    - Windows Startup folder
    - Running processes
    """
    t0 = time.time()
    targets = []
    
    # 1. Downloads folder
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(downloads):
        targets.append(downloads)

    # 2. Local Temp
    temp = os.environ.get("TEMP", os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp"))
    if os.path.exists(temp):
        targets.append(temp)

    # 3. Windows Startup folder
    startup = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    if os.path.exists(startup):
        targets.append(startup)

    scanned_files = 0
    unreadable_files = 0
    defender_unchecked = 0
    skipped_folders = 0
    threats_found: List[Dict[str, Any]] = []

    for folder in targets:
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    # Focus on executable/script files for rapid quick scan
                    if ext in DANGEROUS_EXTENSIONS or ".pdf." in f.lower():
                        full_p = os.path.join(root, f)
                        try:
                            scanned_files += 1
                            res = scan_file(full_p)
                            if res.get("scan_status") == "not_scanned":
                                unreadable_files += 1
                            else:
                                if not res.get("defender_checked"):
                                    defender_unchecked += 1
                                if res.get("verdict") in ("threat", "suspicious"):
                                    threats_found.append(res)
                            if scanned_files >= 250:
                                break
                        except Exception:
                            unreadable_files += 1
                if scanned_files >= 250:
                    break
        except OSError:
            skipped_folders += 1

    # 4. Process scan
    proc_res = scan_processes()
    for p_threat in proc_res.get("suspicious", []):
        threats_found.append({
            "clean": False,
            "threat_level": "High",
            "verdict": "suspicious",
            "threat_name": "Suspicious process",
            "findings": [f"Suspicious because: {p_threat.get('reason', 'it behaves unusually')}.",
                         f"PID {p_threat.get('pid')}: {p_threat.get('name')} at {p_threat.get('exe')}"],
            "path": p_threat.get("exe", "memory"),
            "filename": p_threat.get("name", "process"),
        })

    duration_ms = round((time.time() - t0) * 1000)

    # Trigger background native Defender Quick Scan if available
    defender_path = _find_mpcmdrun()
    if defender_path:
        threading.Thread(
            target=lambda: subprocess.run([defender_path, "-Scan", "-ScanType", "1"], capture_output=True, timeout=90),
            daemon=True
        ).start()

    summary = {
        "ok": True,
        "scanned_files": scanned_files,
        "unreadable_files": unreadable_files,
        "defender_unchecked": defender_unchecked,
        "skipped_folders": skipped_folders,
        "limit_reached": scanned_files >= 250,
        "threats_count": len(threats_found),
        "threats": threats_found,
        "duration_ms": duration_ms,
        "timestamp": time.time(),
        "clean": len(threats_found) == 0,
    }

    _record_scan_event(summary)
    return summary


def scan_processes() -> Dict[str, Any]:
    """Inspect active running processes for cryptominers, script droppers, and temp-directory executions."""
    if not psutil:
        return {"ok": False, "error": "psutil library unavailable"}

    suspicious = []
    scanned = 0

    temp_dirs = [
        os.environ.get("TEMP", "").lower(),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp").lower(),
    ]

    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "cpu_percent"]):
        try:
            scanned += 1
            info = p.info
            name = (info.get("name") or "").lower()
            exe = (info.get("exe") or "").lower()
            cmdline = " ".join(info.get("cmdline") or []).lower()

            # Check 1: Process running from Temp directory
            if exe and any(td in exe for td in temp_dirs if td):
                if not name.startswith("python") and not name.startswith("code") and not name.startswith("pywebview"):
                    suspicious.append({
                        "pid": info["pid"],
                        "name": info.get("name"),
                        "exe": info.get("exe"),
                        "reason": "Process running directly from Temp folder",
                        "severity": "Medium"
                    })

            # Check 2: Known miner signatures
            for kw in MINING_KEYWORDS:
                if kw in name or kw in cmdline:
                    suspicious.append({
                        "pid": info["pid"],
                        "name": info.get("name"),
                        "exe": info.get("exe"),
                        "reason": f"Cryptominer keyword signature match: '{kw}'",
                        "severity": "Critical"
                    })
                    break

            # Check 3: Hidden PowerShell or command prompt executions
            if ("powershell" in name or "cmd" in name) and any(f in cmdline for f in ["-enc ", "downloadstring", "frombase64string", "windowstyle hidden"]):
                suspicious.append({
                    "pid": info["pid"],
                    "name": info.get("name"),
                    "exe": info.get("exe"),
                    "reason": "Obfuscated / hidden shell execution with remote download arguments",
                    "severity": "High"
                })

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "ok": True,
        "scanned_processes": scanned,
        "suspicious_count": len(suspicious),
        "suspicious": suspicious,
        "clean": len(suspicious) == 0,
    }


def scan_url(url: str) -> Dict[str, Any]:
    """Inspect URLs for phishing, spoofed TLDs, and malicious redirect patterns."""
    if not url:
        return {"ok": False, "error": "Empty URL"}

    threats = []
    lower = url.lower().strip()

    # IP hostname instead of domain
    ip_match = re.search(r"^https?://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", lower)
    if ip_match:
        ip = ip_match.group(1)
        if not ip.startswith("127.") and not ip.startswith("192.168.") and not ip.startswith("10."):
            threats.append(f"Raw IP hostname ({ip}) instead of registered domain name")

    # Data URI exploit
    if lower.startswith("data:text/html") or lower.startswith("javascript:"):
        threats.append("Executable Data URI / Javascript protocol in link")

    # Typosquatting heuristics
    typos = ["paypa1", "g00gle", "micros0ft", "app1e", "amzn-security", "netf1ix", "secure-login-"]
    for t in typos:
        if t in lower:
            threats.append(f"Typosquatting brand impersonation match: '{t}'")

    # Suspicious file downloads
    if any(lower.endswith(ext) for ext in [".exe", ".scr", ".vbs", ".bat", ".ps1"]):
        threats.append("Direct link to an executable file download")

    is_clean = len(threats) == 0
    return {
        "ok": True,
        "url": url,
        "clean": is_clean,
        "threat_level": "Clean" if is_clean else ("High" if len(threats) > 1 else "Medium"),
        "findings": threats,
    }


def inspect_clipboard(text: str) -> Dict[str, Any]:
    """Check clipboard text for malicious shell commands or crypto-clipper replacements."""
    if not text or len(text) > 100000:
        return {"clean": True}

    findings = []
    # 1. Dangerous curl | sh or powershell | iex patterns
    pipe_match = re.search(r"(curl|wget|iwr)\s+[^\n|]+\|\s*(sh|bash|powershell|iex)", text, re.IGNORECASE)
    if pipe_match:
        findings.append(f"Dangerous pipe-to-shell command pattern: '{pipe_match.group(0)[:40]}...'")

    # 2. Crypto addresses found
    crypto_matches = {}
    for coin, pattern in CRYPTO_PATTERNS.items():
        found = pattern.findall(text)
        if found:
            crypto_matches[coin] = found

    is_clean = len(findings) == 0
    return {
        "clean": is_clean,
        "findings": findings,
        "crypto_detected": crypto_matches,
    }


QUARANTINE_MAGIC = b"KALKIQ1\0"
QUARANTINE_MAX_BYTES = 512 * 1024 * 1024


def _quarantine_key() -> bytes:
    """A 256-bit key for quarantined files, kept encrypted with Windows DPAPI (secure_store)."""
    import base64
    import secure_store
    path = os.path.join(_get_quarantine_dir(), "quarantine.key")
    with _lock:
        try:
            with open(path, "r", encoding="ascii") as f:
                return base64.b64decode(secure_store.unprotect(f.read().strip()))
        except FileNotFoundError:
            pass
        key = os.urandom(32)
        with open(path, "w", encoding="ascii") as f:
            f.write(secure_store.protect(base64.b64encode(key).decode("ascii")))
        return key


def _encrypt_into(src: str, dest: str) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    with open(src, "rb") as f:
        data = f.read()
    nonce = os.urandom(12)
    with open(dest, "wb") as f:
        f.write(QUARANTINE_MAGIC + nonce + AESGCM(_quarantine_key()).encrypt(nonce, data, QUARANTINE_MAGIC))


def _decrypt_into(src: str, dest: str) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    with open(src, "rb") as f:
        blob = f.read()
    nonce, body = blob[len(QUARANTINE_MAGIC):len(QUARANTINE_MAGIC) + 12], blob[len(QUARANTINE_MAGIC) + 12:]
    data = AESGCM(_quarantine_key()).decrypt(nonce, body, QUARANTINE_MAGIC)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)


def quarantine_file(file_path: str, threat_name: str = "Flagged in a check-up") -> Dict[str, Any]:
    """Move a flagged file into quarantine, encrypted (AES-256-GCM, key protected by Windows
    DPAPI), so it can't run or be opened by accident. Restore brings back the exact original."""
    if not os.path.isfile(file_path):
        return {"ok": False, "error": "File does not exist"}
    try:
        size = os.path.getsize(file_path)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    if size > QUARANTINE_MAX_BYTES:
        return {"ok": False, "error": "This file is too large to quarantine (over 512 MB). Delete it or let Windows Defender handle it."}

    qdir = _get_quarantine_dir()
    file_id = f"q_{int(time.time())}_{secrets_token(6)}"
    filename = os.path.basename(file_path)
    quarantine_path = os.path.join(qdir, f"{file_id}.kalki_quarantined")
    try:
        _encrypt_into(file_path, quarantine_path)
        try:
            os.remove(file_path)
        except OSError as e:
            os.remove(quarantine_path)
            return {"ok": False, "error": f"Couldn't remove the original file ({e.strerror or e}). It may be in use."}
        entry = {
            "id": file_id, "original_path": file_path, "filename": filename,
            "quarantine_path": quarantine_path, "threat_name": threat_name,
            "timestamp": time.time(), "encrypted": True, "size_bytes": size,
        }
        _add_quarantine_entry(entry)
        oversight.record_alert("antivirus", f"Quarantined {filename} ({threat_name}). It's encrypted and can be restored.", "info")
        return {"ok": True, "entry": entry}
    except Exception as e:
        if os.path.exists(quarantine_path) and os.path.exists(file_path):
            try:
                os.remove(quarantine_path)
            except OSError:
                pass
        return {"ok": False, "error": str(e)}


def secrets_token(length: int = 6) -> str:
    import secrets
    return secrets.token_hex(length)


def _add_quarantine_entry(entry: Dict[str, Any]) -> None:
    with _lock:
        path = os.path.join(_get_data_dir(), "quarantine_index.json")
        entries = safe_json.read_json(path, [])
        entries.append(entry)
        safe_json.write_json(path, entries)


def get_quarantined_files() -> List[Dict[str, Any]]:
    with _lock:
        try:
            entries = safe_json.read_json(os.path.join(_get_data_dir(), "quarantine_index.json"), [])
        except OSError:
            return []
        # Only list files that are still on disk.
        return [e for e in entries if os.path.exists(e.get("quarantine_path", ""))]


def resolve_quarantine(threat_id: str, action: str) -> Dict[str, Any]:
    """Delete permanently or restore a quarantined file."""
    with _lock:
        path = os.path.join(_get_data_dir(), "quarantine_index.json")
        if not os.path.exists(path):
            return {"ok": False, "error": "No quarantine records found"}
        try:
            entries = safe_json.read_json(path, [])
        except OSError as e:
            return {"ok": False, "error": str(e)}

        target = next((e for e in entries if e.get("id") == threat_id), None)
        if not target:
            return {"ok": False, "error": "Threat ID not found"}

        qpath = target.get("quarantine_path")
        orig = target.get("original_path")

        if action == "delete":
            try:
                if os.path.exists(qpath):
                    try:
                        os.unlink(qpath)
                    except PermissionError:
                        # Files quarantined by older versions were made read-only for this user.
                        if os.name == "nt":
                            subprocess.run(["icacls", qpath, "/grant", f"{os.environ.get('USERNAME', '')}:F"],
                                           capture_output=True, timeout=15)
                        os.unlink(qpath)
                entries = [e for e in entries if e.get("id") != threat_id]
                safe_json.write_json(path, entries)
                return {"ok": True, "action": "deleted"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        elif action == "restore":
            try:
                if os.path.exists(qpath):
                    if os.path.exists(orig):
                        return {"ok": False, "error": "A file already exists at the original location. Move it first."}
                    os.makedirs(os.path.dirname(orig), exist_ok=True)
                    if target.get("encrypted"):
                        _decrypt_into(qpath, orig)
                        os.remove(qpath)
                    else:  # quarantined before encryption existed
                        shutil.move(qpath, orig)
                entries = [e for e in entries if e.get("id") != threat_id]
                safe_json.write_json(path, entries)
                return {"ok": True, "action": "restored", "path": orig}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        return {"ok": False, "error": "Unknown action (must be 'delete' or 'restore')"}


def _record_scan_event(scan_result: Dict[str, Any]) -> None:
    with _lock:
        path = _get_threat_log_path()
        try:
            logs = safe_json.read_json(path, [])
            logs.append(scan_result)
            safe_json.write_json(path, logs[-30:])
        except OSError as e:
            oversight.record_alert("antivirus", f"Couldn't save scan history: {e}", "warning")


def get_antivirus_status() -> Dict[str, Any]:
    """Consolidated endpoint status report for UI and background monitors."""
    defender = get_windows_defender_status()
    shields = get_shield_settings()
    quarantined = get_quarantined_files()

    try:
        history = safe_json.read_json(_get_threat_log_path(), [])
    except OSError:
        history = []
    last_scan = history[-1] if history else None

    try:
        import shield_monitors
        monitors = shield_monitors.status()
    except Exception:
        monitors = {}
    # Real-time protection is Windows Defender's job. KALKI reports it, and never
    # says "protected" unless Defender itself confirms it.
    system_protected = bool(defender.get("available") and defender.get("antivirus_enabled")
                            and defender.get("realtime_enabled"))
    return {
        "ok": True,
        "shields": shields,
        "monitors": monitors,
        "defender": defender,
        "quarantined_count": len(quarantined),
        "quarantined_items": quarantined,
        "last_scan": last_scan,
        "engine_version": defender.get("version") or "",
        "system_protected": system_protected,
    }
