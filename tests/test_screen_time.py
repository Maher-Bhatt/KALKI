"""Screen time: opt-in, idle and sleep don't count, exclusions, pause, retention, delete."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import settings_schema  # noqa: E402
import routes_screen_time as rst  # noqa: E402
from core import productivity as p  # noqa: E402

TODAY = date(2026, 11, 14)


class ScreenTimeTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.file = os.path.join(folder, "productivity.json")
        patches = [
            mock.patch.object(p, "DATA_FILE", self.file),
            mock.patch.object(server.config, "SCREEN_TIME_ENABLED", True, create=True),
            mock.patch.object(server.config, "SCREEN_TIME_EXCLUDED", [], create=True),
            mock.patch.object(server.config, "SCREEN_TIME_RETENTION_DAYS", 30, create=True),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        p._pending.clear()
        p.resume()
        self.addCleanup(p._pending.clear)
        self.addCleanup(p.resume)

    def stored(self):
        p.flush(force=True, today=TODAY)
        return json.load(open(self.file, encoding="utf-8")) if os.path.exists(self.file) else {}


class Counting(ScreenTimeTest):
    def test_counts_by_app_and_category(self):
        p.record("code.exe", "main.py - secret project", 5, today=TODAY)
        p.record("code.exe", "main.py - secret project", 5, today=TODAY)
        day = self.stored()[TODAY.isoformat()]
        self.assertEqual(day["categories"], {"Coding": 10})
        self.assertEqual(day["category_apps"], {"Coding": {"code.exe": 10}})

    def test_window_titles_are_never_stored(self):
        p.record(None, "Bank statement March.pdf", 5, today=TODAY)
        p.record("weird.exe", "Diary - private", 5, today=TODAY)
        text = json.dumps(self.stored())
        self.assertNotIn("Bank", text)
        self.assertNotIn("Diary", text)
        self.assertIn("Unknown app", text)

    def test_idle_sleep_off_and_paused_dont_count(self):
        self.assertEqual(p.record("code.exe", "x", 5, idle_seconds=300, today=TODAY)[1], "idle")
        self.assertEqual(p.record("code.exe", "x", 3600, today=TODAY)[1], "gap")
        p.pause(60)
        self.assertEqual(p.record("code.exe", "x", 5, today=TODAY)[1], "paused")
        p.resume()
        with mock.patch.object(server.config, "SCREEN_TIME_ENABLED", False):
            self.assertEqual(p.record("code.exe", "x", 5, today=TODAY)[1], "off")
        self.assertEqual(self.stored(), {})

    def test_excluded_apps_dont_count(self):
        with mock.patch.object(server.config, "SCREEN_TIME_EXCLUDED", ["discord.exe"]):
            self.assertEqual(p.record("Discord.exe", "x", 5, today=TODAY)[1], "excluded")

    def test_existing_installs_keep_tracking_until_turned_off(self):
        with mock.patch.object(server.config, "SCREEN_TIME_ENABLED", None):
            self.assertFalse(p.is_enabled())  # nothing recorded yet: off
            json.dump({"2026-11-01": {"Coding": 60}}, open(self.file, "w"))
            self.assertTrue(p.is_enabled())
            p.clear()  # deleting the data doesn't turn it off
            self.assertTrue(p.is_enabled())


class Storage(ScreenTimeTest):
    def test_old_days_are_pruned(self):
        old = (TODAY - timedelta(days=40)).isoformat()
        json.dump({old: {"categories": {"Coding": 60}, "category_apps": {}}}, open(self.file, "w"))
        p.record("code.exe", "x", 5, today=TODAY)
        self.assertEqual(list(self.stored()), [TODAY.isoformat()])

    def test_old_flat_days_are_upgraded_when_written(self):
        json.dump({TODAY.isoformat(): {"Coding": 60}}, open(self.file, "w"))
        p.record("code.exe", "x", 5, today=TODAY)
        self.assertEqual(self.stored()[TODAY.isoformat()]["categories"]["Coding"], 65)

    def test_week_clear_and_forget(self):
        p.record("code.exe", "x", 10, today=TODAY)
        p.record("chrome.exe", "x", 5, today=TODAY - timedelta(days=1))
        self.stored()
        w = p.week(today=TODAY)
        self.assertEqual([d["total"] for d in w["days"]][-2:], [5, 10])
        self.assertEqual(w["topApps"][0], {"app": "code.exe", "category": "Coding", "seconds": 10})
        self.assertEqual(p.forget_app("Code"), 10)
        self.assertNotIn("Coding", self.stored().get(TODAY.isoformat(), {}).get("categories", {}))
        self.assertEqual(p.clear((TODAY - timedelta(days=1)).isoformat()), 1)
        p.record("code.exe", "x", 5, today=TODAY)
        self.stored()
        self.assertGreaterEqual(p.clear(), 1)
        self.assertEqual(self.stored(), {})


class Routes(ScreenTimeTest):
    def test_routes(self):
        self.assertEqual(rst.overview({})[1], 200)
        self.assertEqual(rst.pause({"minutes": "lots"})[1], 400)
        self.assertTrue(rst.pause({"minutes": 30})[0]["status"]["pausedUntil"])
        self.assertFalse(rst.resume({})[0]["status"]["pausedUntil"])
        self.assertEqual(rst.clear({"date": "yesterday"})[1], 400)
        self.assertEqual(rst.forget({})[1], 400)
        self.assertEqual(rst.raw({})[0]["file"], self.file)

    def test_settings_are_validated(self):
        self.assertEqual(settings_schema.SCHEMA["SCREEN_TIME_EXCLUDED"].check(["Discord.exe", "discord.exe"]), ["discord.exe"])
        with self.assertRaises(settings_schema.SettingError):
            settings_schema.SCHEMA["SCREEN_TIME_RETENTION_DAYS"].check(0)
        self.assertFalse(settings_schema.SCHEMA["SCREEN_TIME_ENABLED"].default)

    def test_the_screen_has_a_section(self):
        page = (ROOT / "app" / "ui" / "features" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("['screentime', 'Screen time']", page)
        self.assertIn("screenTime.clear()", page)


if __name__ == "__main__":
    unittest.main()
