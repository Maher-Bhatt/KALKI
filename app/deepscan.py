"""
KALKI Deep Scan Module
======================

DevTools-level website analysis for the Jarvis system.
Loads the page in a real (headless) Chromium via Playwright, so it sees what
"Inspect" sees: the rendered DOM after JS, EVERY loaded resource (all scripts
incl. cross-origin, CSS, JSON/XHR), cookies, and localStorage/sessionStorage.

Then it hunts vulnerabilities across all of it and saves the "inside files".

Authorized, non-destructive: it loads and reads, it does not attack.
Builds on webscan.py for the finding format + secret patterns.
"""

import os
import re
import json
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import webscan
import sys

BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))

if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(BASE_DIR, "browsers")

SCANS_DIR = "data/scans"


def available() -> bool:
    """
    Check if the Playwright library is installed and available.
    
    Returns:
        bool: True if Playwright is available, False otherwise.
    """
    try:
        import playwright  # noqa
        from playwright.sync_api import sync_playwright  # noqa
        return True
    except ImportError:
        return False


def _host(url: str) -> str:
    """Extract the hostname from a URL."""
    return urllib.parse.urlparse(url).netloc or "site"


def _slug(url: str) -> str:
    """Create a safe filename slug from a URL."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", _host(url))


# ── Analysis Helpers (reuse webscan finding format) ──────────

def _storage_findings(raw_json: str, where: str) -> List[Dict[str, str]]:
    """Scan browser storage (local/session) for sensitive data."""
    out = []
    try:
        data = json.loads(raw_json) if raw_json else {}
    except Exception:
        return out
        
    pat = re.compile(r"(token|jwt|secret|api[_-]?key|password|auth|bearer|session)", re.I)
    
    items = data.items() if isinstance(data, dict) else []
    for k, v in items:
        sval = str(v)
        if pat.search(str(k)) or sval.startswith("eyJ") or pat.search(sval[:40]):
            out.append(webscan._finding(
                "HIGH", f"Sensitive data in {where}",
                f"Key '{k}' = {sval[:60]}",
                "Don't keep tokens/secrets in browser storage — XSS can steal them."
            ))
        if len(out) >= 6:
            break
    return out


def _cookie_findings(cookies: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Analyze cookies for missing security flags."""
    out = []
    for c in cookies or []:
        name = c.get("name", "?")
        if not c.get("secure", False):
            out.append(webscan._finding(
                "MEDIUM", f"Cookie '{name}' missing Secure",
                "Cookie can be sent over plain HTTP.",
                "Set the Secure flag."
            ))
        if not c.get("httpOnly", False):
            out.append(webscan._finding(
                "MEDIUM", f"Cookie '{name}' missing HttpOnly",
                "Cookie readable by JavaScript (XSS theft).",
                "Set HttpOnly on session cookies."
            ))
        if not c.get("sameSite") or c.get("sameSite") == "None":
            out.append(webscan._finding(
                "LOW", f"Cookie '{name}' weak SameSite",
                f"SameSite={c.get('sameSite')}.",
                "Use SameSite=Lax or Strict."
            ))
        if len(out) >= 12:
            break
    return out


def _header_findings(headers: Dict[str, str], scheme: str) -> List[Dict[str, str]]:
    """Analyze HTTP response headers for missing security configurations."""
    out = []
    h = {k.lower(): v for k, v in (headers or {}).items()}
    checks = {
        "strict-transport-security": (
            "HIGH", "Missing HSTS header",
            "No HSTS — connection can be downgraded.",
            "Add Strict-Transport-Security: max-age=31536000; includeSubDomains"
        ),
        "content-security-policy": (
            "MEDIUM", "Missing Content-Security-Policy",
            "No CSP — bigger XSS blast radius.", "Define a restrictive CSP."
        ),
        "x-frame-options": (
            "MEDIUM", "Missing X-Frame-Options",
            "Clickjacking risk.", "Add X-Frame-Options: DENY or CSP frame-ancestors."
        ),
        "x-content-type-options": (
            "LOW", "Missing X-Content-Type-Options",
            "MIME sniffing not disabled.", "Add X-Content-Type-Options: nosniff"
        ),
    }
    
    for key, f in checks.items():
        if key == "strict-transport-security" and scheme != "https":
            continue
        if key not in h:
            out.append(webscan._finding(*f))
            
    server = h.get("server", "")
    if server and re.search(r"\d", server):
        out.append(webscan._finding(
            "LOW", "Server version disclosed",
            f"Server: {server}", "Suppress version banners."
        ))
        
    if h.get("access-control-allow-origin") == "*" and h.get("access-control-allow-credentials", "").lower() == "true":
        out.append(webscan._finding(
            "HIGH", "Insecure CORS",
            "ACAO * with credentials allowed.",
            "Never combine wildcard origin with credentials."
        ))
    return out


def deep_scan(url: str, timeout_ms: int = 25000) -> Dict[str, Any]:
    """
    Perform a deep DevTools-level scan on a given URL.
    
    Args:
        url (str): The URL to scan.
        timeout_ms (int): The maximum timeout for the scan in milliseconds.
        
    Returns:
        Dict[str, Any]: Scan results including findings and saved file paths.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    from playwright.sync_api import sync_playwright

    host = _host(url)
    findings, resources, console_msgs = [], [], []
    main_headers, final_url = {}, url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--no-sandbox"])
        ctx = browser.new_context(ignore_https_errors=True, user_agent="KALKI-DeepScan/1.0 (authorized testing)")
        page = ctx.new_page()
        captured = []
        page.on("response", lambda r: captured.append(r))
        page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text}"[:300]))

        main_resp = None
        for wait in ("networkidle", "domcontentloaded"):
            try:
                main_resp = page.goto(url, wait_until=wait, timeout=timeout_ms)
                break
            except Exception:
                continue
                
        if main_resp is None:
            browser.close()
            return {"target": url, "host": host, "error": "page would not load", "findings": []}

        main_headers = main_resp.headers
        final_url = page.url
        try:
            page.wait_for_timeout(1500)   # catch late XHRs
        except Exception:
            pass

        html = page.content()
        try:
            local_storage = page.evaluate("() => JSON.stringify(window.localStorage)")
        except Exception:
            local_storage = "{}"
        try:
            session_storage = page.evaluate("() => JSON.stringify(window.sessionStorage)")
        except Exception:
            session_storage = "{}"
        cookies = ctx.cookies()

        for resp in captured:
            try:
                ct = (resp.headers.get("content-type", "") or "").lower()
                ru = resp.url
                if (any(k in ct for k in ("javascript", "json", "css", "html", "text", "xml"))
                        or ru.split("?")[0].endswith((".js", ".json", ".css", ".map"))):
                    body = resp.text()
                    if body:
                        resources.append((ru, ct, resp.status, body))
            except Exception:
                continue
        browser.close()

    scheme = urllib.parse.urlparse(final_url).scheme or "https"

    # Secrets across EVERY loaded file + the rendered DOM
    for ru, ct, st, body in resources:
        nm = ru.split("/")[-1].split("?")[0] or ru
        findings += webscan.scan_secrets(body, f"file {nm}")
    findings += webscan.scan_secrets(html, "rendered DOM")
    
    # Browser-storage secrets
    findings += _storage_findings(local_storage, "localStorage")
    findings += _storage_findings(session_storage, "sessionStorage")
    
    # Cookies, headers
    findings += _cookie_findings(cookies)
    findings += _header_findings(main_headers, scheme)
    
    # Mixed content actually loaded
    if scheme == "https":
        http_res = [r for r in resources if r[0].startswith("http://")]
        if http_res:
            findings.append(webscan._finding(
                "MEDIUM", "Mixed content loaded",
                f"{len(http_res)} resource(s) fetched over HTTP on an HTTPS page.",
                "Serve every asset over HTTPS."
            ))
            
    # Third-party script inventory
    tp = sorted({urllib.parse.urlparse(r[0]).netloc for r in resources
                 if "javascript" in r[1].lower() and urllib.parse.urlparse(r[0]).netloc not in ("", host)})
    if tp:
        findings.append(webscan._finding(
            "INFO", "Third-party scripts",
            f"{len(tp)} external script host(s): {', '.join(tp[:10])}",
            "Each can read the whole page — vet every one."
        ))
        
    # Forms / injection surface from the RENDERED dom
    try:
        fsrc, _ = webscan.analyze_source(f"{scheme}://{host}", html)
        findings += [f for f in fsrc if f["title"].split()[0] in ("Form", "Password", "Input")]
    except Exception:
        pass
        
    # Console security warnings
    sec = [m for m in console_msgs if re.search(r"csp|mixed content|cors|blocked|insecure|refused", m, re.I)]
    if sec:
        findings.append(webscan._finding(
            "INFO", "Console security warnings",
            "; ".join(sec[:4]), "Review the browser console messages."
        ))

    files_dir = _save_files(host, final_url, html, resources, local_storage, session_storage, cookies, console_msgs)

    # Dedupe + sort
    seen, uniq = set(), []
    for f in findings:
        k = (f["severity"], f["title"], f["detail"][:60])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    uniq.sort(key=lambda f: webscan.SEV_ORDER.get(f["severity"], 9))
    counts = {}
    for f in uniq:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    report = _write_report(host, final_url, uniq, counts, files_dir, len(resources))
    return {
        "target": final_url, "host": host, "findings": uniq, "counts": counts,
        "report_path": report, "files_dir": files_dir, "resource_count": len(resources)
    }


def _save_files(host: str, url: str, html: str, resources: List[Tuple[str, str, int, str]], ls: str, ss: str, cookies: List[Dict[str, Any]], console_msgs: List[str]) -> Optional[str]:
    """Save captured resources, DOM, and storage to disk for offline analysis."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = os.path.join(SCANS_DIR, f"{_slug(url)}_{ts}_inspect")
    try:
        os.makedirs(os.path.join(d, "files"), exist_ok=True)
        with open(os.path.join(d, "rendered_dom.html"), "w", encoding="utf-8") as f:
            f.write(html or "")
            
        # Save each loaded file
        for i, (ru, ct, st, body) in enumerate(resources):
            base = re.sub(r"[^a-zA-Z0-9._-]", "_", ru.split("/")[-1].split("?")[0]) or f"res{i}"
            fn = f"{i:03d}_{base}"[:80]
            try:
                with open(os.path.join(d, "files", fn), "w", encoding="utf-8") as f:
                    f.write(f"/* {ru}  (HTTP {st}, {ct}) */\n\n" + body)
            except Exception:
                pass
                
        with open(os.path.join(d, "storage.json"), "w", encoding="utf-8") as f:
            json.dump({"localStorage": ls, "sessionStorage": ss, "cookies": cookies}, f, indent=2, default=str)
            
        with open(os.path.join(d, "console.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(console_msgs))
            
        return d
    except Exception:
        return None


def _write_report(host: str, url: str, findings: List[Dict[str, str]], counts: Dict[str, int], files_dir: Optional[str], res_count: int) -> str:
    """Generate a text report summarizing the deep scan findings."""
    os.makedirs(SCANS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCANS_DIR, f"{_slug(url)}_{ts}_deepscan.txt")
    
    lines = [
        "=" * 66,
        "KALKI DEEP SCAN (DevTools-level) REPORT",
        f"Target : {url}",
        f"Time   : {datetime.now().isoformat(timespec='seconds')}",
        f"Files  : {res_count} loaded resources captured -> {files_dir}",
        "Note   : Authorized, non-destructive. Loaded + read, not attacked.",
        "=" * 66
    ]
    
    summary = ", ".join(f"{counts[s]} {s}" for s in sorted(counts, key=lambda k: webscan.SEV_ORDER.get(k, 9))) or "no issues found"
    lines.append(f"SUMMARY: {summary}")
    lines.append("")
    if not findings:
        lines.append("No issues detected by the checks performed.")
        
    for i, f in enumerate(findings, 1):
        lines.append(f"[{i}] {f['severity']}  —  {f['title']}")
        lines.append(f"     What : {f['detail']}")
        if f.get("fix"):
            lines.append(f"     Fix  : {f['fix']}")
        lines.append("")
        
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def summarize(result: Dict[str, Any], title: str = "Sir") -> str:
    """
    Format a conversational summary of the deep scan results.
    
    Args:
        result (Dict[str, Any]): The result dictionary from deep_scan.
        title (str): The title to use when addressing the user.
        
    Returns:
        str: A formatted summary string.
    """
    if result.get("error"):
        return f"I couldn't load {result.get('host', 'that site')}, {title}. {result['error']}"
        
    findings = result.get("findings", [])
    counts = result.get("counts", {})
    rc = result.get("resource_count", 0)
    
    if not findings:
        return (f"Deep scan complete, {title}. I inspected {rc} loaded files on "
                f"{result['host']} and flagged nothing. Full report saved.")
                
    parts = [f"{counts[s]} {s.lower()}" for s in sorted(counts, key=lambda k: webscan.SEV_ORDER.get(k, 9))]
    top = findings[0]
    
    return (f"Deep scan complete, {title}. Inspected {rc} loaded files on "
            f"{result['host']}. Found {', '.join(parts)}. Top issue: {top['title']}. "
            f"Full report and all the source files are saved.")
