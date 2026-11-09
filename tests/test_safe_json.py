"""Small JSON files: a bad read must never lead to overwriting good data."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import antivirus  # noqa: E402
import oversight  # noqa: E402
import runtime_security  # noqa: E402
import safe_json  # noqa: E402
import workflows  # noqa: E402


class TempCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_json_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def path(self, name):
        return os.path.join(self.dir, name)

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8") as f:
            f.write(text)
        return self.path(name)

    def kept_aside(self):
        return [n for n in os.listdir(self.dir) if ".corrupt." in n]


class SafeJson(TempCase):
    def test_missing_file_gives_the_default(self):
        self.assertEqual(safe_json.read_json(self.path("x.json"), []), [])

    def test_good_file_is_read(self):
        self.assertEqual(safe_json.read_json(self.write("x.json", "[1]"), []), [1])

    def test_corrupt_file_is_kept_aside(self):
        path = self.write("x.json", "{broken")
        self.assertEqual(safe_json.read_json(path, []), [])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(len(self.kept_aside()), 1)

    def test_wrong_shape_counts_as_corrupt(self):
        path = self.write("x.json", "{}")
        self.assertEqual(safe_json.read_json(path, []), [])
        self.assertEqual(len(self.kept_aside()), 1)

    def test_locked_file_raises_so_nothing_overwrites_it(self):
        path = self.write("x.json", "[1]")
        with mock.patch("builtins.open", side_effect=PermissionError("locked")):
            with self.assertRaises(OSError):
                safe_json.read_json(path, [])
        self.assertTrue(os.path.exists(path))

    def test_failed_write_keeps_the_old_file(self):
        path = self.write("x.json", "[1]")
        with mock.patch.object(safe_json.os, "replace", side_effect=PermissionError("locked")):
            with self.assertRaises(OSError):
                safe_json.write_json(path, [2])
        self.assertEqual(safe_json.read_json(path, []), [1])
        self.assertEqual([n for n in os.listdir(self.dir) if n.endswith(".tmp")], [])


class Alerts(TempCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(oversight, "get_data_dir", return_value=self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_alert_round_trip(self):
        oversight.record_alert("test", "hello", "info")
        self.assertEqual(oversight.recent_alerts()[0]["message"], "hello")

    def test_corrupt_alert_file_is_kept(self):
        self.write("oversight_alerts.json", "{broken")
        oversight.record_alert("test", "after", "info")
        self.assertEqual(len(self.kept_aside()), 1)
        self.assertEqual(oversight.recent_alerts()[0]["message"], "after")

    def test_failed_alert_write_is_not_silent(self):
        with mock.patch.object(safe_json, "write_json", side_effect=OSError("disk full")), \
                mock.patch("sys.stderr.write") as err:
            oversight.record_alert("test", "lost alert", "critical")
        self.assertIn("lost alert", "".join(str(c.args[0]) for c in err.call_args_list))


class Quarantine(TempCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(antivirus, "_get_data_dir", return_value=self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_corrupt_index_is_kept_and_new_entries_still_save(self):
        """Regression: a corrupt index was overwritten, losing the restore records."""
        self.write("quarantine_index.json", "{broken")
        antivirus._add_quarantine_entry({"id": "new", "quarantine_path": self.path("q")})
        self.assertEqual(len(self.kept_aside()), 1)
        self.assertEqual(json.load(open(self.path("quarantine_index.json"), encoding="utf-8"))[0]["id"], "new")

    def test_quarantine_then_restore(self):
        target = self.write("risky.exe", "x")
        result = antivirus.quarantine_file(target, "Test")
        self.assertTrue(result["ok"])
        self.assertFalse(os.path.exists(target))
        items = antivirus.get_quarantined_files()
        self.assertEqual(len(items), 1)
        self.assertTrue(antivirus.resolve_quarantine(items[0]["id"], "restore")["ok"])
        self.assertTrue(os.path.exists(target))

    def test_shield_settings_survive_corruption(self):
        self.write("shield_settings.json", "{broken")
        self.assertEqual(antivirus.get_shield_settings(), antivirus.DEFAULT_SHIELDS)
        self.assertEqual(len(self.kept_aside()), 1)
        self.assertFalse(antivirus.update_shield_settings({"process_monitor": False})["process_monitor"])
        self.assertFalse(antivirus.get_shield_settings()["process_monitor"])


class DefenderHonesty(TempCase):
    def _scan(self, **run):
        target = self.write("file.txt", "hello")
        with mock.patch.object(antivirus, "_find_mpcmdrun", return_value="MpCmdRun.exe"), \
                mock.patch.object(antivirus.subprocess, "run", **run):
            return antivirus.scan_file(target)

    def test_clean_defender_result_is_marked_checked(self):
        result = self._scan(return_value=subprocess.CompletedProcess([], 0, stdout="found no threats"))
        self.assertTrue(result["clean"])
        self.assertTrue(result["defender_checked"])

    def test_defender_failure_is_reported(self):
        """Regression: if Defender failed to run, the file still looked fully checked."""
        result = self._scan(side_effect=subprocess.TimeoutExpired("x", 60))
        self.assertFalse(result["defender_checked"])
        self.assertIn("defender_error", result)

    def test_defender_detection_is_flagged(self):
        result = self._scan(return_value=subprocess.CompletedProcess([], 2, stdout="found 1 threats"))
        self.assertFalse(result["clean"])
        self.assertTrue(result["defender_checked"])

    def test_no_defender_is_reported(self):
        target = self.write("file.txt", "hello")
        with mock.patch.object(antivirus, "_find_mpcmdrun", return_value=None):
            self.assertFalse(antivirus.scan_file(target)["defender_checked"])


class Routines(TempCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(workflows, "CUSTOM_ROUTINES_PATH", self.path("custom_routines.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(workflows.MODES.pop, "my routine", None)
        self.addCleanup(workflows.MODE_ALIASES.pop, "my routine", None)

    def test_saved_routine_survives_reload(self):
        workflows.add_custom_routine("My Routine", [["open_url", "https://example.com"]])
        workflows.MODES.pop("my routine")
        workflows.load_custom_routines()
        self.assertIn("my routine", workflows.MODES)

    def test_corrupt_file_is_kept_not_overwritten(self):
        """Regression: saving after a bad read destroyed every other routine."""
        self.write("custom_routines.json", "{broken")
        workflows.add_custom_routine("My Routine", [["open_url", "https://example.com"]])
        self.assertEqual(len(self.kept_aside()), 1)

    def test_locked_file_refuses_to_save(self):
        self.write("custom_routines.json", '{"old": {"actions": []}}')
        with mock.patch("builtins.open", side_effect=PermissionError("locked")):
            with self.assertRaises(OSError):
                workflows.add_custom_routine("My Routine", [])


class TokenFile(TempCase):
    def test_lock_failure_is_reported(self):
        path = self.write("token.txt", "x")
        with mock.patch.object(runtime_security.os, "name", "nt"), \
                mock.patch.dict(os.environ, {"USERNAME": "someone"}), \
                mock.patch.object(runtime_security.subprocess, "run",
                                  return_value=subprocess.CompletedProcess([], 5)):
            self.assertFalse(runtime_security._restrict_file(path))

    def test_lock_success_is_reported(self):
        path = self.write("token.txt", "x")
        with mock.patch.object(runtime_security.os, "name", "nt"), \
                mock.patch.dict(os.environ, {"USERNAME": "someone"}), \
                mock.patch.object(runtime_security.subprocess, "run",
                                  return_value=subprocess.CompletedProcess([], 0)):
            self.assertTrue(runtime_security._restrict_file(path))


if __name__ == "__main__":
    unittest.main()
