"""Reminders: repeats, snooze, missed reminders, time words and honest errors."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import commands_productivity  # noqa: E402
import notify  # noqa: E402
import routes_productivity  # noqa: E402
import tasks  # noqa: E402

FRIDAY_8PM = datetime(2026, 11, 13, 20, 0)


class FrozenNow(datetime):
    @classmethod
    def now(cls, tz=None):
        return FRIDAY_8PM


class TimeWords(unittest.TestCase):
    def parse(self, text):
        with mock.patch.object(tasks, "datetime", FrozenNow):
            return tasks.parse_when(text)[0]

    def test_tomorrow_is_respected(self):
        # "Tomorrow at 9pm" said at 8pm used to mean today at 9pm.
        self.assertEqual(self.parse("call mom tomorrow at 9pm"), datetime(2026, 11, 14, 21, 0))

    def test_weekdays_and_day_only(self):
        self.assertEqual(self.parse("on monday at 10am"), datetime(2026, 11, 16, 10, 0))
        self.assertEqual(self.parse("friday"), datetime(2026, 11, 20, 9, 0))
        self.assertEqual(self.parse("day after tomorrow"), datetime(2026, 11, 15, 9, 0))

    def test_word_durations(self):
        self.assertEqual(self.parse("in an hour"), FRIDAY_8PM + timedelta(hours=1))
        self.assertEqual(self.parse("in half an hour"), FRIDAY_8PM + timedelta(minutes=30))

    def test_no_time_means_no_time(self):
        self.assertIsNone(self.parse("buy milk"))


class Repeats(unittest.TestCase):
    def test_repeat_words(self):
        cases = {
            "stretch every day at 3pm": "daily", "stand up every weekday at 10am": "weekdays",
            "backup weekly": "weekly", "call mom every sunday at 6pm": "weekly",
            "read the daily report at 9am": "", "visit the everyday store": "",
        }
        for text, repeat in cases.items():
            self.assertEqual(tasks.parse_repeat(text)[0], repeat, text)

    def test_next_occurrence_skips_weekends_and_missed_days(self):
        friday_9am = datetime(2026, 11, 13, 9, 0)
        self.assertEqual(tasks.next_occurrence(friday_9am, "weekdays", FRIDAY_8PM), datetime(2026, 11, 16, 9, 0))
        self.assertEqual(tasks.next_occurrence(friday_9am - timedelta(days=10), "daily", FRIDAY_8PM),
                         datetime(2026, 11, 14, 9, 0))
        self.assertEqual(tasks.next_occurrence(friday_9am, "weekly", FRIDAY_8PM), datetime(2026, 11, 20, 9, 0))


class Store(unittest.TestCase):
    def setUp(self):
        for r in tasks.list_reminders(include_fired=True):
            tasks.delete_reminder(r["id"])
        self.addCleanup(lambda: [tasks.delete_reminder(r["id"]) for r in tasks.list_reminders(include_fired=True)])

    def test_a_time_it_cannot_read_is_an_error_not_a_guess(self):
        with self.assertRaises(ValueError):
            tasks.add_reminder("water plants", "sometime soonish")
        self.assertEqual(tasks.list_reminders(), [])

    def test_one_off_fires_once_and_says_how_late(self):
        rid = tasks.add_reminder("one off", datetime.now() - timedelta(minutes=30))
        fired = tasks.pop_due_reminders()
        self.assertEqual([r["id"] for r in fired], [rid])
        self.assertGreaterEqual(fired[0]["late_minutes"], 29)
        self.assertEqual(tasks.pop_due_reminders(), [])

    def test_repeating_moves_to_its_next_time(self):
        rid = tasks.add_reminder("daily one", datetime.now() - timedelta(days=3, minutes=1), repeat="daily")
        fired = tasks.pop_due_reminders()
        self.assertEqual(len(fired), 1)
        [still] = [r for r in tasks.list_reminders() if r["id"] == rid]
        self.assertGreater(datetime.fromisoformat(still["due"]), datetime.now())
        self.assertEqual(still["repeat"], "daily")

    def test_snooze_brings_back_the_last_one(self):
        tasks.add_reminder("stretch", datetime.now() - timedelta(minutes=1))
        tasks.pop_due_reminders()
        snoozed = tasks.snooze_reminder(None, 15)
        self.assertEqual(snoozed["text"], "stretch")
        [pending] = tasks.list_reminders()
        self.assertAlmostEqual((datetime.fromisoformat(pending["due"]) - datetime.now()).total_seconds(), 900, delta=5)

    def test_snoozing_a_repeat_keeps_its_schedule(self):
        rid = tasks.add_reminder("pills", datetime.now() - timedelta(minutes=1), repeat="daily")
        tasks.pop_due_reminders()
        snoozed = tasks.snooze_reminder(None, 10)
        self.assertNotEqual(snoozed["id"], rid)
        self.assertEqual(len(tasks.list_reminders()), 2)


class CommandsAndRoutes(Store):
    def say(self, text):
        return commands_productivity.reminders_command(text.lower(), text)

    def test_repeating_reminder_by_voice(self):
        reply = self.say("remind me every weekday at 10am to stand up")
        self.assertIn("every weekday", reply)
        [r] = tasks.list_reminders()
        self.assertEqual((r["text"], r["repeat"]), ("stand up", "weekdays"))

    def test_snooze_and_cancel_by_voice(self):
        tasks.add_reminder("stretch", datetime.now() - timedelta(minutes=1))
        tasks.pop_due_reminders()
        self.assertIn("Snoozed for 5 minutes", self.say("snooze 5 minutes"))
        self.assertEqual(self.say("cancel reminder stretch"), "Reminder deleted.")
        self.assertEqual(self.say("snooze"), "There's no reminder to snooze.")

    def test_add_route_refuses_a_time_it_cannot_read(self):
        payload, status = routes_productivity.add_reminder({"text": "x", "due": "whenever"})
        self.assertEqual(status, 400)
        self.assertIn("couldn't tell when", payload["error"])

    def test_add_route_understands_repeats_in_the_time(self):
        payload, status = routes_productivity.add_reminder({"text": "stretch", "due": "every day at 3pm"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["reminder"]["repeat"], "daily")
        self.assertIn("every day", payload["when"])

    def test_ai_tool_reports_the_real_time_or_the_problem(self):
        bad = server._run_tool_call("add_reminder", {"text": "x", "due": "whenever"})
        self.assertTrue(bad.startswith("Error:"), bad)
        good = server._run_tool_call("add_reminder", {"text": "call", "due": "in 20 minutes"})
        self.assertTrue(good.startswith("Reminder set for"), good)


class Notifications(unittest.TestCase):
    def test_a_failed_notification_says_so(self):
        with mock.patch.dict(sys.modules, {"plyer": None}):
            self.assertFalse(notify.notify_desktop("Reminder", "x"))


if __name__ == "__main__":
    unittest.main()
