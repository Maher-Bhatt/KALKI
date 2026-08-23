"""KALKI isolated verification sandbox.

This is the release-gate test runner for KALKI.  It starts the real HTTP
handler on localhost with a temporary APPDATA/data directory, so it can test
the app without touching a user's settings, memories, vault, tasks, or backup
files.  It deliberately never runs OS-control, credentialed, or third-party
automation routes.

Run from the app directory:
    python verification_sandbox.py

Optional integrations (Google, Spotify, mail, Telegram, cloud sync, AI
providers, microphone, and destructive system controls) require real accounts,
hardware, or explicit user confirmation.  They are inventoried in the report
rather than being invoked from an automated sandbox.
"""

from __future__ import annotations

import argparse
import http.client
import importlib
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable


APP_DIR = Path(__file__).resolve().parent


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""


class VerificationSandbox:
    """Runs deterministic checks against an isolated real KALKI server."""

    SAFE_GET = {
        "/", "/manifest.json", "/service-worker.js", "/api/health",
        "/api/status", "/api/models", "/api/settings/get", "/api/metrics",
        "/api/github/status", "/api/focus",
        "/api/dashboard", "/api/memories", "/api/memory/list",
    }
    SAFE_POST = {
        "/api/listener_state", "/api/settings/save", "/api/tasks/list",
        "/api/reminders/list", "/api/notes/list", "/api/memory/list",
    }
    EXTERNAL_OR_GUARDED = {
        "AI/provider calls", "Google, Spotify, Gmail, Telegram, and cloud-sync OAuth",
        "microphone, TTS playback, screenshots, clipboard, and installed-app control",
        "web/cyber scans, port scans, downloads, and third-party network calls",
        "system power, volume, recycle-bin, startup, and file-changing actions",
        "backup restore, factory reset, and user-provided document processing",
    }

    def __init__(self) -> None:
        self.results: list[CheckResult] = []
        self.server: Any = None
        self.thread: threading.Thread | None = None
        self.port = 0
        self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.api_token = ""

    def record(self, name: str, check: Callable[[], str]) -> None:
        try:
            self.results.append(CheckResult(name, "PASS", check()))
        except Exception as exc:
            self.results.append(CheckResult(name, "FAIL", f"{exc}\n{traceback.format_exc(limit=2)}"))

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None,
                 headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        payload = json.dumps(body or {}).encode("utf-8") if method == "POST" else None
        request_headers = dict(headers or {})
        if self.api_token:
            request_headers.setdefault("X-KALKI-Token", self.api_token)
        if payload is not None:
            request_headers.setdefault("Content-Type", "application/json")
            request_headers["Content-Length"] = str(len(payload))
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        try:
            connection.request(method, path, body=payload, headers=request_headers)
            response = connection.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), data
        finally:
            connection.close()

    @staticmethod
    def _json(data: bytes) -> dict[str, Any]:
        return json.loads(data.decode("utf-8"))

    def _start_server(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="kalki-verification-")
        root = Path(self.temp_dir.name)
        os.environ["KALKI_SANDBOX"] = "1"
        os.environ["KALKI_SANDBOX_DATA_DIR"] = str(root / "data")
        os.environ["APPDATA"] = str(root / "appdata")
        sys.path.insert(0, str(APP_DIR))

        # Import after environment setup so config/vault/data modules resolve
        # entirely inside the temporary sandbox.
        config = importlib.import_module("config")
        server_module = importlib.import_module("server")
        self.server = server_module.ThreadingHTTPServer(("127.0.0.1", 0), server_module.Handler)
        self.api_token = server_module.API_TOKEN
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                status, _, data = self._request("GET", "/api/health")
                if status == 200 and self._json(data).get("ok"):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("sandbox server did not start")

    def _stop_server(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=3)
        if self.temp_dir:
            self.temp_dir.cleanup()
        for key in ("KALKI_SANDBOX", "KALKI_SANDBOX_DATA_DIR"):
            os.environ.pop(key, None)

    def _check_static_sources(self) -> str:
        excluded_dirs = {"dist", "build", ".build_packages", ".build-venv", "__pycache__"}
        source_files = [
            p for p in APP_DIR.rglob("*.py")
            if not any(part in excluded_dirs for part in p.parts)
        ]
        for path in source_files:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        return f"compiled {len(source_files)} Python source files"

    def _check_tool_contracts(self) -> str:
        tools = importlib.import_module("tools")
        schemas = tools.TOOLS_SCHEMA
        if not schemas:
            raise AssertionError("tool schema is empty")
        names = set()
        for item in schemas:
            function = item.get("function", {})
            if item.get("type") != "function" or not function.get("name") or not function.get("parameters"):
                raise AssertionError(f"invalid tool schema: {item}")
            if function["name"] in names:
                raise AssertionError(f"duplicate tool name: {function['name']}")
            names.add(function["name"])
        return f"validated {len(names)} AI tool contracts"

    def _check_local_utilities(self) -> str:
        cybertools = importlib.import_module("cybertools")
        if cybertools.hash_text("test1234", "sha256") != "937e8d5fbb48bd4949536cd65b8d35c426b80d2f830c5c308e2cdec422ae2244":
            raise AssertionError("SHA-256 output mismatch")
        if cybertools.decode(cybertools.encode("KALKI", "base64"), "base64") != "KALKI":
            raise AssertionError("base64 round trip failed")
        if len(cybertools.random_password(24)) != 24:
            raise AssertionError("password length mismatch")
        return "verified local hashing, codec, and password utilities"

    def _check_route_inventory(self) -> str:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")
        routes = sorted(set(re.findall(r'path\s*==\s*["\'](/api/[^"\']+)', source)))
        covered = self.SAFE_GET | self.SAFE_POST
        unclassified = [route for route in routes if route not in covered]
        return f"inventoried {len(routes)} API routes ({len(covered & set(routes))} automated; {len(unclassified)} guarded/external)"

    def _check_authentication(self) -> str:
        status, _, body = self._request_without_auth("GET", "/api/status")
        if status != 401:
            raise AssertionError(f"expected 401 for unauthenticated status request, got {status}: {body[:200]!r}")
        return "unauthenticated privileged GET rejected with 401"

    def _request_without_auth(self, method: str, path: str, body: dict[str, Any] | None = None):
        payload = json.dumps(body or {}).encode("utf-8") if method == "POST" else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def _check_safe_routes(self) -> str:
        checks: dict[str, set[str] | None] = {
            "/api/health": {"ok", "ts"},
            "/api/status": {"uptimeSec", "cpu", "ram"},
            "/api/models": {"models"},
            "/api/settings/get": {"ok", "settings", "secretStatus"},
            "/api/metrics": {"ok"},
            "/api/dashboard": None,
            "/api/github/status": {"ok", "configured", "count"},
            "/api/focus": {"ok", "active", "remainingSec"},
            "/api/memories": None,
            "/api/memory/list": None,
        }
        for path, required in checks.items():
            status, _, raw = self._request("GET", path)
            if status != 200:
                raise AssertionError(f"{path} returned HTTP {status}")
            if required:
                missing = required - set(self._json(raw))
                if missing:
                    raise AssertionError(f"{path} missing {sorted(missing)}")
        return f"exercised {len(checks)} safe API reads"

    def _check_static_http_assets(self) -> str:
        for path, content_type in (("/", "text/html"), ("/manifest.json", "application/manifest+json"), ("/service-worker.js", "application/javascript")):
            status, headers, raw = self._request("GET", path)
            if status != 200 or content_type not in headers.get("Content-Type", "") or not raw:
                raise AssertionError(f"{path} asset contract failed")
        return "served UI shell, web manifest, and service worker"

    def _check_safe_post_routes(self) -> str:
        status, _, raw = self._request("POST", "/api/listener_state", {"muted": True})
        if status != 200 or not self._json(raw).get("ok"):
            raise AssertionError("listener state route failed")

        status, _, raw = self._request("POST", "/api/settings/save", {"updates": {"OWNER_NAME": "Sandbox User", "OWNER_TITLE": "Tester"}})
        if status != 200 or not self._json(raw).get("ok"):
            raise AssertionError("settings save route failed")
        status, _, raw = self._request("GET", "/api/settings/get")
        settings = self._json(raw).get("settings", {})
        if settings.get("OWNER_NAME") != "Sandbox User":
            raise AssertionError("settings did not persist in sandbox")

        for path in ("/api/tasks/list", "/api/reminders/list", "/api/notes/list", "/api/memory/list"):
            status, _, _ = self._request("POST", path, {})
            if status != 200:
                raise AssertionError(f"{path} returned HTTP {status}")
        return "exercised isolated state, settings persistence, and list routes"

    def _check_origin_protection(self) -> str:
        status, _, raw = self._request("POST", "/api/listener_state", {"muted": False}, {"Origin": "https://attacker.example"})
        if status != 403 or self._json(raw).get("ok") is not False:
            raise AssertionError("cross-origin request was not rejected")
        return "rejected untrusted browser origin"

    def run(self) -> dict[str, Any]:
        self.record("Python source compilation", self._check_static_sources)
        try:
            self._start_server()
            self.record("API authentication", self._check_authentication)
            self.record("Tool schema contracts", self._check_tool_contracts)
            self.record("Local utility functions", self._check_local_utilities)
            self.record("API route inventory", self._check_route_inventory)
            self.record("Static HTTP assets", self._check_static_http_assets)
            self.record("Safe API read routes", self._check_safe_routes)
            self.record("Safe API write routes", self._check_safe_post_routes)
            self.record("Local origin protection", self._check_origin_protection)
        except Exception as exc:
            self.results.append(CheckResult("Sandbox startup", "FAIL", f"{exc}\n{traceback.format_exc(limit=3)}"))
        finally:
            self._stop_server()

        return {
            "sandbox": "KALKI isolated verification",
            "passed": sum(result.status == "PASS" for result in self.results),
            "failed": sum(result.status == "FAIL" for result in self.results),
            "results": [asdict(result) for result in self.results],
            "guarded_or_external": sorted(self.EXTERNAL_OR_GUARDED),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KALKI's isolated verification sandbox.")
    parser.add_argument("--report", type=Path, help="Write the JSON report to this path.")
    args = parser.parse_args()

    report = VerificationSandbox().run()
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
