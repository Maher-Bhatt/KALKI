"""Focus sessions: stored, survive restarts, finish on their own, keep a history."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import db  # noqa: E402
import focus  # noqa: E402

T0 = 1_800_000_000.0  # a fixed "now"


class FocusTest(unittest.TestCase):
    def setUp(self):
        with db.connect() as conn:
            conn.execute("DELETE FROM focus_sessions")
        self.addCleanup(self._clear)
        self.changes = []
        focus.configure(self.changes.append)
        self.addCleanup(focus.configure, server._focus_changed)

    def _clear(self):
        with db.connect() as conn:
            conn.execute("DELETE FROM focus_sessions")


class Lifecycle(FocusTest):
    def test_start_status_and_stop(self):
        focus.start(25, "essay", now=T0)
        st = focus.status(T0 + 60)
        self.assertTrue(st["active"])
        self.assertEqual((st["remainingSec"], st["label"]), (24 * 60, "essay"))
        ended = focus.stop(T0 + 600)
        self.assertEqual(ended["focusedMinutes"], 10.0)
        self.assertFalse(ended["completed"])
        self.assertFalse(focus.status(T0 + 601)["active"])
        self.assertEqual(self.changes, [True, False])

    def test_survives_a_restart(self):
        # Nothing is held in memory: a fresh read of the store finds the running session.
        focus.start(50, now=T0)
        self.assertEqual(focus.active(T0 + 1200)["minutes"], 50)

    def test_runs_out_on_its_own_and_is_announced_once(self):
        focus.start(25, now=T0)
        self.assertFalse(focus.is_active(T0 + 25 * 60))
        [done] = focus.pop_finished(T0 + 25 * 60 + 5)
        self.assertTrue(done["completed"])
        self.assertFalse(done["late"])
        self.assertEqual(done["focusedMinutes"], 25.0)
        self.assertEqual(focus.pop_finished(T0 + 25 * 60 + 40), [])
        self.assertEqual(self.changes[-1], False)

    def test_one_that_ended_while_closed_is_late(self):
        focus.start(25, now=T0)
        [done] = focus.pop_finished(T0 + 3 * 3600)
        self.assertTrue(done["late"])
        self.assertEqual(done["endedAt"], T0 + 25 * 60)

    def test_stopped_sessions_are_never_announced(self):
        focus.start(25, now=T0)
        focus.stop(T0 + 60)
        self.assertEqual(focus.pop_finished(T0 + 3600), [])

    def test_starting_again_keeps_the_first_in_history(self):
        focus.start(25, "one", now=T0)
        focus.start(15, "two", now=T0 + 300)
        h = focus.history(1, now=T0 + 400)
        self.assertEqual([s["label"] for s in h["sessions"]], ["one"])
        self.assertEqual(focus.active(T0 + 400)["label"], "two")

    def test_length_limits(self):
        for bad in (0, 241, "soon", None):
            with self.assertRaises(ValueError):
                focus.start(bad, now=T0)
        self.assertIsNone(focus.active(T0))

    def test_history_totals(self):
        focus.start(25, now=T0)
        focus.pop_finished(T0 + 1600)
        focus.start(30, now=T0 + 2000)
        focus.stop(T0 + 2000 + 600)
        h = focus.history(7, now=T0 + 3000)
        self.assertEqual((h["completed"], h["stopped"], h["periodMinutes"]), (1, 1, 35))


class Commands(FocusTest):
    def test_lengths_and_labels(self):
        cases = {
            "start a focus session": (25, ""), "focus for 50 minutes": (50, ""),
            "start a 45 minute focus session": (45, ""), "focus on the essay for 30 minutes": (30, "the essay"),
            "focus for an hour": (60, ""), "focus for half an hour": (30, ""), "begin focus": (25, ""),
            "set a 2 hour focus timer": (120, ""),
        }
        for text, (minutes, label) in cases.items():
            reply = focus.command(text)
            self.assertIn("started", reply, text)
            cur = focus.active()
            self.assertEqual((cur["minutes"], cur["label"]), (minutes, label), text)

    def test_not_focus_commands(self):
        for text in ("focus", "focus mode", "help me focus on studying", "what is focus", "the focus of this essay"):
            self.assertIsNone(focus.command(text), text)

    def test_stop_status_and_stats(self):
        self.assertEqual(focus.command("stop focus session"), "No focus session is running.")
        focus.command("focus for 20 minutes")
        self.assertIn("left in your focus session", focus.command("how much time is left"))
        self.assertIn("stopped after", focus.command("stop focus session"))
        self.assertIn("today across 1 session", focus.command("how much did i focus today"))

    def test_too_long_says_why(self):
        self.assertIn("1 to 240 minutes", focus.command("focus for 500 minutes"))


class Wiring(FocusTest):
    def test_the_today_buttons_reach_the_server(self):
        page = (ROOT / "app" / "ui" / "features" / "today.js").read_text(encoding="utf-8")
        self.assertIn("system.focusStart(", page)
        self.assertIn("system.focusStop()", page)
        self.assertNotIn("system.command('stop focus session')", page)

    def test_routes(self):
        payload, status = focus.POST_ROUTES["/api/focus/start"]({"minutes": 30, "label": "x"})
        self.assertEqual((status, payload["active"], payload["minutes"]), (200, True, 30))
        self.assertEqual(focus.POST_ROUTES["/api/focus/start"]({"minutes": 999})[1], 400)
        payload, _ = focus.GET_ROUTES["/api/focus"]({})
        self.assertTrue(payload["active"])
        payload, _ = focus.POST_ROUTES["/api/focus/stop"]({})
        self.assertFalse(payload["active"])
        self.assertIsNotNone(payload["stopped"])

    def test_handle_local_uses_focus(self):
        with mock.patch.object(server, "speak"):
            handled, reply = server.handle_local("focus for 15 minutes")
        self.assertTrue(handled)
        self.assertIn("15 minutes", reply)

    def test_notifications_held_back_only_while_running(self):
        focus.configure(server._focus_changed)
        self.addCleanup(server.STATE.update, {"workflow": server.STATE.get("workflow")})
        with mock.patch.object(server, "is_urgent", return_value=False), mock.patch.object(server, "log"):
            focus.start(25)
            self.assertFalse(server.speak("New mail", is_notification=True))
            self.assertEqual(server.STATE.get("workflow"), "focus")
            focus.stop()
            self.assertNotEqual(server.STATE.get("workflow"), "focus")
            self.assertFalse(server._focus_active())

    def test_a_finished_session_is_spoken_and_alerted(self):
        focus.start(1, now=time.time() - 120)
        with mock.patch.object(server, "speak") as speak, mock.patch("oversight.record_alert") as alert, \
                mock.patch("notify.notify_desktop", return_value=True):
            server._announce_finished_focus()
        self.assertIn("Focus session done", speak.call_args[0][0])
        alert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
