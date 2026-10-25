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
MINING_PORTS = {3333, 4444, 5555, 7777, 8888, 9999, 14444, 14433, 45700}

# Cryptocurrency address regexes for clipboard protection
CRYPTO_PATTERNS = {
    "Bitcoin": re.compile(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "Ethereum": re.compile(r"\b(0x[a-fA-F0-9]{40})\b"),
    "Monero": re.compile(r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"),
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
        path = _get_shield_settings_path()
        defaults = {
            "realtime_shield": True,
            "download_watcher": True,
            "process_monitor": True,
            "clipboard_guard": True,
            "phishing_shield": True,
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    defaults.update(saved)
            except Exception:
                pass
        return defaults


def update_shield_settings(updates: Dict[str, bool]) -> Dict[str, bool]:
    with _lock:
        current = get_shield_settings()
        current.update(updates)
        path = _get_shield_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
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


def get_windows_defender_status() -> Dict[str, Any]:
    """Query native Windows Defender health via PowerShell."""
    if os.name != "nt":
        return {"available": False, "reason": "Non-Windows platform"}
    try:
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureAge, QuickScanAge, ComputerState | ConvertTo-Json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            return {
                "available": True,
                "antivirus_enabled": bool(data.get("AntivirusEnabled")),
                "realtime_enabled": bool(data.get("RealTimeProtectionEnabled")),
                "signature_age_days": data.get("AntivirusSignatureAge", 0),
                "quick_scan_age_days": data.get("QuickScanAge", 0),
            }
    except Exception as e:
        return {"available": False, "error": str(e)}
    return {"available": False, "reason": "No response"}


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


def scan_file(file_path: str) -> Dict[str, Any]:
    """
    Perform deep static heuristic & signature analysis on a file.
    Runs Defender CLI if available on Windows, supplemented with Python heuristics.
    """
    if not os.path.exists(file_path):
        return {"ok": False, "clean": True, "error": "File does not exist", "path": file_path}

    try:
        file_size = os.path.getsize(file_path)
    except OSError as e:
        return {"ok": False, "clean": True, "error": str(e), "path": file_path}

    filename = os.path.basename(file_path)
    base_name, ext = os.path.splitext(filename)
    lower_ext = ext.lower()

    findings: List[str] = []
    threat_level = "Clean"
    threat_name = ""

    # 1. Double extension check (e.g. invoice.pdf.exe)
    double_ext_match = re.search(r"\.(pdf|docx?|xlsx?|pptx?|txt|jpg|png|mp3|zip)\.(exe|scr|vbs|bat|cmd|ps1|hta)$", filename, re.IGNORECASE)
    if double_ext_match:
        findings.append(f"Deceptive double extension detected: '.{double_ext_match.group(1)}.{double_ext_match.group(2)}'")
        threat_level = "Critical"
        threat_name = "Trojan.DoubleExtension.Dropper"

    # 2. Compute SHA-256 and MD5 hashes
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            # Read first chunk for quick inspection
            header_bytes = f.read(65536)
            sha256_hash.update(header_bytes)
            md5_hash.update(header_bytes)
            while chunk := f.read(131072):
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
    except Exception as e:
        err_msg = str(e)
        if "virus" in err_msg.lower() or "225" in err_msg or "operation did not complete successfully" in err_msg.lower() or "invalid argument" in err_msg.lower():
            return {
                "ok": True,
                "clean": False,
                "threat_level": "Critical",
                "threat_name": "Win32.Malware.BlockedByOS",
                "findings": ["File access was immediately blocked by Windows Defender / Antivirus protection."],
                "path": file_path,
                "filename": filename,
                "size_bytes": file_size,
                "sha256": "blocked_by_os_shield",
                "md5": "blocked_by_os_shield",
                "timestamp": time.time(),
            }
        return {"ok": False, "clean": True, "error": f"Failed reading file: {e}", "path": file_path}

    sha256_hex = sha256_hash.hexdigest().lower()
    md5_hex = md5_hash.hexdigest().lower()

    # 3. Known signature & EICAR test file check
    if sha256_hex == EICAR_SHA256 or EICAR_SUBSTRING in header_bytes:
        findings.append("Standard EICAR Antivirus Test Signature detected")
        threat_level = "High"
        threat_name = "Test.Virus.EICAR.Standard"

    # 4. Pattern matching for scripts and macros
    if lower_ext in {".ps1", ".bat", ".cmd", ".vbs", ".hta", ".js", ".wsf", ".docm", ".xlsm"} or lower_ext not in {".png", ".jpg", ".mp4", ".mkv"}:
        for pat, desc in SUSPICIOUS_PATTERNS:
            if pat.search(header_bytes):
                findings.append(f"Suspicious heuristic signature: {desc}")
                if threat_level == "Clean":
                    threat_level = "Medium"
                    threat_name = f"Heur.{desc.split()[0]}"

    # 5. Shannon entropy analysis for executables (packed / ransomware payloads)
    if lower_ext in {".exe", ".dll", ".scr"} and file_size > 1024:
        entropy = _calculate_entropy(header_bytes)
        if entropy > 7.45:
            findings.append(f"Extremely high byte entropy ({entropy}/8.0) indicating packed/encrypted payload")
            if threat_level == "Clean":
                threat_level = "Medium"
                threat_name = "Suspicious.HighEntropy.Packer"

    # 6. Windows Defender native scan fallback/confirmation
    defender_path = _find_mpcmdrun()
    defender_output = ""
    if defender_path:
        try:
            res = subprocess.run(
                [defender_path, "-Scan", "-ScanType", "3", "-File", file_path, "-DisableRemediation"],
                capture_output=True, text=True, timeout=20
            )
            defender_output = res.stdout
            if "Threat detected" in defender_output or "found threats" in defender_output.lower():
                threat_level = "Critical"
                findings.append("Windows Defender flagged this file as malicious")
                threat_name = threat_name or "Win32.Malware.Generic"
        except Exception:
            pass

    is_clean = (threat_level == "Clean")

    result = {
        "ok": True,
        "clean": is_clean,
        "threat_level": threat_level,
        "threat_name": threat_name or ("None" if is_clean else "Suspicious.File"),
        "findings": findings,
        "path": file_path,
        "filename": filename,
        "size_bytes": file_size,
        "sha256": sha256_hex,
        "md5": md5_hex,
        "timestamp": time.time(),
    }

    if not is_clean:
        oversight.record_alert("antivirus", f"Threat detected in {filename}: {threat_name} ({threat_level})", "critical")

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
                            if not res.get("clean"):
                                threats_found.append(res)
                            if scanned_files >= 250:
                                break
                        except Exception:
                            pass
                if scanned_files >= 250:
                    break
        except Exception:
            pass

    # 4. Process scan
    proc_res = scan_processes()
    for p_threat in proc_res.get("suspicious", []):
        threats_found.append({
            "clean": False,
            "threat_level": "High",
            "threat_name": p_threat.get("reason", "Suspicious.Process"),
            "findings": [f"PID {p_threat.get('pid')}: {p_threat.get('name')} at {p_threat.get('exe')}"],
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


def quarantine_file(file_path: str, threat_name: str = "Generic.Malware") -> Dict[str, Any]:
    """Safely move a flagged file to the quarantine vault with restricted permissions."""
    if not os.path.exists(file_path):
        return {"ok": False, "error": "File does not exist"}

    qdir = _get_quarantine_dir()
    file_id = f"q_{int(time.time())}_{secrets_token(6)}"
    filename = os.path.basename(file_path)
    quarantine_path = os.path.join(qdir, f"{file_id}.kalki_quarantined")

    try:
        shutil.move(file_path, quarantine_path)
        # Restrict permissions
        if os.name == "nt":
            subprocess.run(["icacls", quarantine_path, "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', 'Everyone')}:(R)"], capture_output=True)
        else:
            os.chmod(quarantine_path, 0o400)

        entry = {
            "id": file_id,
            "original_path": file_path,
            "filename": filename,
            "quarantine_path": quarantine_path,
            "threat_name": threat_name,
            "timestamp": time.time(),
        }

        _add_quarantine_entry(entry)
        oversight.record_alert("antivirus", f"Quarantined threat: {filename} ({threat_name})", "info")
        return {"ok": True, "entry": entry}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def secrets_token(length: int = 6) -> str:
    import secrets
    return secrets.token_hex(length)


def _add_quarantine_entry(entry: Dict[str, Any]) -> None:
    with _lock:
        path = os.path.join(_get_data_dir(), "quarantine_index.json")
        entries = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                pass
        entries.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)


def get_quarantined_files() -> List[Dict[str, Any]]:
    with _lock:
        path = os.path.join(_get_data_dir(), "quarantine_index.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
            # Verify file still on disk
            valid = [e for e in entries if os.path.exists(e.get("quarantine_path", ""))]
            return valid
        except Exception:
            return []


def resolve_quarantine(threat_id: str, action: str) -> Dict[str, Any]:
    """Delete permanently or restore a quarantined file."""
    with _lock:
        path = os.path.join(_get_data_dir(), "quarantine_index.json")
        if not os.path.exists(path):
            return {"ok": False, "error": "No quarantine records found"}
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        target = next((e for e in entries if e.get("id") == threat_id), None)
        if not target:
            return {"ok": False, "error": "Threat ID not found"}

        qpath = target.get("quarantine_path")
        orig = target.get("original_path")

        if action == "delete":
            try:
                if os.path.exists(qpath):
                    os.unlink(qpath)
                entries = [e for e in entries if e.get("id") != threat_id]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=2)
                return {"ok": True, "action": "deleted"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        elif action == "restore":
            try:
                if os.path.exists(qpath):
                    os.makedirs(os.path.dirname(orig), exist_ok=True)
                    shutil.move(qpath, orig)
                entries = [e for e in entries if e.get("id") != threat_id]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=2)
                return {"ok": True, "action": "restored", "path": orig}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        return {"ok": False, "error": "Unknown action (must be 'delete' or 'restore')"}


def _record_scan_event(scan_result: Dict[str, Any]) -> None:
    with _lock:
        path = _get_threat_log_path()
        logs = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                pass
        logs.append(scan_result)
        logs = logs[-30:]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass


def get_antivirus_status() -> Dict[str, Any]:
    """Consolidated endpoint status report for UI and background monitors."""
    defender = get_windows_defender_status()
    shields = get_shield_settings()
    quarantined = get_quarantined_files()

    last_scan = None
    log_path = _get_threat_log_path()
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                if history:
                    last_scan = history[-1]
        except Exception:
            pass

    return {
        "ok": True,
        "shield_active": shields.get("realtime_shield", True),
        "shields": shields,
        "defender": defender,
        "quarantined_count": len(quarantined),
        "quarantined_items": quarantined,
        "last_scan": last_scan,
        "engine_version": "1.4.0-ShieldCore",
        "system_protected": bool(shields.get("realtime_shield", True) and (defender.get("antivirus_enabled", True) if defender.get("available") else True)),
    }
