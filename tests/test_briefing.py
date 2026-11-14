"""The daily briefing: chosen sections, each on its own, honest about what failed."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import sys
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import briefing  # noqa: E402
import settings_schema  # noqa: E402
import routes_settings  # noqa: E402
import tasks  # noqa: E402


def fine():
    return {"text": "All good.", "items": [1]}


def broken():
    raise RuntimeError("server said no")


def not_set_up():
    raise briefing.Unavailable("Connect it first.")


def slow():
    time.sleep(3)
    return {"text": "late"}


class Building(unittest.TestCase):
    def test_one_failure_never_breaks_the_rest(self):
        result = briefing.build(["calendar", "tasks", "mail"],
                                builders={"calendar": broken, "tasks": fine, "mail": not_set_up})
        status = {s["id"]: s["status"] for s in result["sections"]}
        self.assertEqual(status, {"calendar": "failed", "tasks": "ok", "mail": "unavailable"})
        self.assertIn("server said no", result["sections"][0]["text"])
        self.assertIn("All good.", result["text"])
        self.assertIn("couldn't get calendar", result["text"])

    def test_a_slow_source_is_cut_off_at_the_deadline(self):
        started = time.monotonic()
        result = briefing.build(["sites", "tasks"], builders={"sites": slow, "tasks": fine}, deadline=0.3)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual([s["status"] for s in result["sections"]], ["timeout", "ok"])

    def test_sections_follow_the_briefing_order_and_unknown_ids_are_dropped(self):
        self.assertEqual(briefing.chosen_sections(["weather", "nonsense", "calendar"]), ["calendar", "weather"])
        self.assertEqual(briefing.chosen_sections(None), list(briefing.DEFAULT_SECTIONS))
        self.assertEqual(briefing.chosen_sections([]), [])

    def test_nothing_chosen_says_how_to_fix_it(self):
        self.assertIn("Settings", briefing.spoken([]))

    def test_greeting_uses_the_title_only_when_set(self):
        self.assertEqual(briefing.greeting(datetime(2026, 1, 1, 8), ""), "Good morning.")
        self.assertEqual(briefing.greeting(datetime(2026, 1, 1, 19), "boss"), "Good evening, boss.")


class Sections(unittest.TestCase):
    def setUp(self):
        for r in tasks.list_reminders(include_fired=True):
            tasks.delete_reminder(r["id"])
        self.addCleanup(lambda: [tasks.delete_reminder(r["id"]) for r in tasks.list_reminders(include_fired=True)])

    def test_reminders_today_and_later(self):
        tasks.add_reminder("call the bank", datetime.now() + timedelta(minutes=5))
        tasks.add_reminder("renew passport", datetime.now() + timedelta(days=3))
        result = briefing.reminders_section()
        self.assertIn("call the bank", result["text"])
        self.assertNotIn("passport", result["text"])
        tomorrow = briefing.reminders_section(date.today() - timedelta(days=1))
        self.assertTrue(tomorrow["empty"])
        self.assertIn("2 reminders coming up later", tomorrow["text"])

    def test_calendar_not_connected_is_unavailable_not_failed(self):
        with mock.patch("gcal.is_configured", return_value=False):
            with self.assertRaises(briefing.Unavailable):
                briefing.calendar_section()

    def test_calendar_error_is_a_failure(self):
        with mock.patch("gcal.is_configured", return_value=True), \
                mock.patch("gcal.today_events", return_value={"error": "token expired"}):
            with self.assertRaisesRegex(RuntimeError, "token expired"):
                briefing.calendar_section()

    def test_calendar_events_are_listed(self):
        events = [{"summary": "Standup", "start": {"dateTime": "2026-11-14T09:30:00+05:30"}},
                  {"summary": "Holiday", "start": {"date": "2026-11-14"}}]
        with mock.patch("gcal.is_configured", return_value=True), mock.patch("gcal.today_events", return_value=events):
            result = briefing.calendar_section()
        self.assertEqual(result["text"], "2 events today: 9:30 AM Standup; All day Holiday.")

    def test_unwatched_sites_are_unavailable(self):
        with mock.patch("watchdog.list_sites", return_value=[]):
            with self.assertRaises(briefing.Unavailable):
                briefing.sites_section()

    def test_weather_needs_a_location(self):
        with mock.patch.object(server.config, "LATITUDE", None, create=True):
            with self.assertRaises(briefing.Unavailable):
                briefing.weather_section()

    def test_weather_codes_read_as_words(self):
        self.assertEqual(briefing.describe_weather(0), "Clear")
        self.assertEqual(briefing.describe_weather(63), "Rain")
        self.assertEqual(briefing.describe_weather(None), "Weather")


class Wiring(unittest.TestCase):
    def test_route_is_a_get_and_always_answers(self):
        with mock.patch.object(briefing, "BUILDERS", {"tasks": fine, "calendar": broken}), \
                mock.patch.object(server.config, "BRIEFING_SECTIONS", ["calendar", "tasks"], create=True):
            payload, status = briefing.GET_ROUTES["/api/briefing/get"]({})
        self.assertEqual(status, 200)
        self.assertEqual([s["status"] for s in payload["briefing"]["sections"]], ["failed", "ok"])

    def test_brief_me_reads_the_briefing_not_the_security_brief(self):
        with mock.patch.object(briefing, "current", return_value={"text": "Good morning. No open tasks."}), \
                mock.patch.object(server, "speak"), mock.patch.object(server, "build_security_brief") as security:
            for phrase in ("brief me", "morning brief", "read my briefing", "daily briefing"):
                self.assertEqual(server.handle_local(phrase), (True, "Good morning. No open tasks."), phrase)
        security.assert_not_called()

    def test_ai_tool_uses_the_same_briefing(self):
        fake = {"text": "x", "sections": [{"title": "Tasks", "status": "empty", "text": "No open tasks."}]}
        with mock.patch.object(briefing, "current", return_value=fake):
            self.assertEqual(server._run_tool_call("get_daily_briefing", {}), "Tasks (empty): No open tasks.")

    def test_setting_accepts_known_sections_only(self):
        spec = settings_schema.SCHEMA["BRIEFING_SECTIONS"]
        self.assertEqual(spec.check(["weather", "calendar"]), ["calendar", "weather"])
        with self.assertRaises(settings_schema.SettingError):
            spec.check(["calendar", "horoscope"])
        self.assertIn("BRIEFING_SECTIONS", routes_settings.get_settings({})[0]["settings"])

    def test_today_does_not_wait_for_the_briefing(self):
        page = (ROOT / "app" / "ui" / "features" / "today.js").read_text(encoding="utf-8")
        start = page.index("export async function loadToday")
        block = page[start:page.index("export async function loadBriefing")]
        self.assertNotIn("system.briefing()", block)


if __name__ == "__main__":
    unittest.main()
