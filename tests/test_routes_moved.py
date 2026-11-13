"""Activity, settings, calendar and setup routes, moved out of server.py, and the guard that
keeps every test away from the real profile."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import activity  # noqa: E402
import routes_calendar  # noqa: E402
import routes_settings  # noqa: E402
import routes_setup  # noqa: E402


class TestsUseAThrowawayProfile(unittest.TestCase):
    def test_kalki_data_is_in_a_temporary_folder(self):
        temp = os.path.realpath(tempfile.gettempdir())
        for path in (server.DATA_DIR, server.USER_CONFIG_PATH):
            self.assertTrue(os.path.realpath(path).startswith(temp), path)


class ActivityUndo(unittest.TestCase):
    def test_two_undos_at_once_run_it_only_once(self):
        calls = []
        gate = threading.Event()

        def slow_undo():
            calls.append(1)
            gate.wait(1)

        act_id = activity.record("undo me twice", "test", reversible=True, undo_fn=slow_undo)
        results = []
        threads = [threading.Thread(target=lambda: results.append(activity.undo_route({"id": act_id})[1])) for _ in range(2)]
        for t in threads:
            t.start()
        gate.set()
        for t in threads:
            t.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(sorted(results), [200, 400])

    def test_a_failed_undo_can_be_tried_again(self):
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("busy")

        act_id = activity.record("flaky", "test", reversible=True, undo_fn=flaky)
        self.assertEqual(activity.undo_route({"id": act_id})[1], 500)
        self.assertEqual(activity.undo_route({"id": act_id})[1], 200)


class SettingsExport(unittest.TestCase):
    def test_export_never_includes_a_secret(self):
        path = server.USER_CONFIG_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        before = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        self.addCleanup(lambda: (open(path, "w", encoding="utf-8").write(before) if before is not None
                                 else os.path.exists(path) and os.remove(path)))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"OWNER_NAME": "Test", "GROQ_API_KEY": "gsk_real_looking_secret", "GITHUB_TOKEN": "ghp_secret"}, f)
        exported = json.loads(routes_settings.export_text())
        self.assertEqual(exported, {"OWNER_NAME": "Test"})

    def test_set_secrets_come_back_empty(self):
        self.assertEqual(routes_settings.public_value("GROQ_API_KEY", "gsk_live_value"), "")
        self.assertEqual(routes_settings.public_value("OWNER_NAME", "Maher"), "Maher")

    def test_settings_screen_gets_names_and_status_it_expects(self):
        payload, status = routes_settings.get_settings({})
        self.assertEqual(status, 200)
        self.assertIn("OWNER_NAME", payload["settings"])
        self.assertIn("GROQ_API_KEY", payload["secretStatus"])

    def test_every_setting_the_screen_shows_is_sent(self):
        import re
        screen = (ROOT / "app" / "ui" / "features" / "settings.js").read_text(encoding="utf-8")
        used = set(re.findall(r"toggleRow\([^)]*?'([A-Z_]{3,})'", screen))
        used |= set(re.findall(r"textRow\([^)]*?'([A-Z_]{3,})'", screen))
        used |= set(re.findall(r"values\.([A-Z_]{3,})", screen))
        sent = set(routes_settings.get_settings({})[0]["settings"])
        self.assertEqual(sorted(used - sent - routes_settings.SECRET_SETTING_KEYS), [])

    def test_first_run_reads_those_names(self):
        page = (ROOT / "app" / "ui" / "features" / "firstrun.js").read_text(encoding="utf-8")
        self.assertIn("r.data.settings", page)
        self.assertIn("r.data.secretStatus", page)


class CalendarAndSetup(unittest.TestCase):
    def test_upcoming_count_is_kept_sensible(self):
        with mock.patch.object(routes_calendar.gcal, "upcoming_events", return_value=[]) as upcoming, \
                mock.patch.object(routes_calendar.gcal, "events_summary", return_value=""):
            routes_calendar.upcoming({"n": 100000})
            upcoming.assert_called_with(50)
        self.assertEqual(routes_calendar.upcoming({"n": "many"})[1], 400)

    def test_events_are_formatted_and_junk_skipped(self):
        events = routes_calendar.format_events([{"summary": "Standup", "start": {"dateTime": "2026-11-13T09:00"}}, "junk"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Standup")

    def test_unknown_setup_tool_is_refused(self):
        self.assertEqual(routes_setup.setup_tool({"tool": "nope"})[1], 400)

    def test_ai_test_reports_failure_plainly(self):
        routes_setup.configure(lambda m: (_ for _ in ()).throw(RuntimeError("no key")), routes_setup.nullcontext, print)
        payload, _ = routes_setup.test_ai({})
        self.assertEqual(payload, {"ok": False, "error": "no key"})


if __name__ == "__main__":
    unittest.main()
