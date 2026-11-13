"""Calendar, microphone and "who am I" commands, and backup and restore."""

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import commands_assistant as ca  # noqa: E402
import routes_backup  # noqa: E402


class CalendarCommands(unittest.TestCase):
    def setUp(self):
        for name, value in (("is_configured", True), ("today_summary", "TODAY"), ("tomorrow_events", []),
                            ("upcoming_events", []), ("events_summary", "EVENTS")):
            patcher = mock.patch.object(ca.gcal, name, return_value=value) if name != "events_summary" else \
                mock.patch.object(ca.gcal, name, side_effect=lambda *a, **k: "EVENTS")
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_questions_read_the_calendar(self):
        self.assertEqual(ca.calendar_command("what's on my calendar"), "TODAY")
        self.assertEqual(ca.calendar_command("what's my schedule tomorrow"), "EVENTS")
        self.assertEqual(ca.calendar_command("upcoming events"), "EVENTS")

    def test_requests_to_add_something_go_to_the_ai(self):
        for text in ("schedule a meeting with my boss tomorrow", "add a dentist appointment to my calendar tomorrow",
                     "book a call on my calendar", "please schedule lunch tomorrow", "cancel my schedule for today"):
            self.assertIsNone(ca.calendar_command(text), text)

    def test_not_linked_says_so_with_the_chosen_title(self):
        with mock.patch.object(ca.gcal, "is_configured", return_value=False), \
                mock.patch.object(ca.config, "OWNER_TITLE", "boss", create=True):
            self.assertEqual(ca.calendar_command("what's on my calendar"),
                             "Your calendar isn't linked yet. Link Google in Settings, boss.")
        with mock.patch.object(ca.gcal, "is_configured", return_value=False), \
                mock.patch.object(ca.config, "OWNER_TITLE", "", create=True):
            self.assertNotIn("Sir", ca.calendar_command("what's on my calendar"))


class OtherCommands(unittest.TestCase):
    def test_listener_pause_and_resume(self):
        state = {}
        self.assertIn("paused", ca.listener_command("pause mic", state))
        self.assertTrue(state["listener_paused"])
        ca.listener_command("listen again", state)
        self.assertFalse(state["listener_paused"])
        self.assertIsNone(ca.listener_command("pause the music", state))

    def test_who_am_i_says_only_what_it_knows(self):
        with mock.patch.multiple(ca.config, create=True, OWNER_NAME="Maher", OWNER_CITY="Pune",
                                 OWNER_STATE="", OWNER_COUNTRY="India"):
            reply = ca.owner_command("who am i", lambda: [1, 2])
        self.assertEqual(reply, "You are Maher, based in Pune, India. I have 2 memories on file.")
        for invented in ("Bhatt", "gaming", "cybersecurity"):
            self.assertNotIn(invented, reply)

    def test_who_am_i_without_a_name(self):
        with mock.patch.multiple(ca.config, create=True, OWNER_NAME="YourName", OWNER_CITY="YourCity",
                                 OWNER_STATE="", OWNER_COUNTRY=""):
            self.assertIn("don't know your name", ca.owner_command("what is my name", lambda: []))

    def test_handle_local_still_routes_them(self):
        with mock.patch.object(ca.gcal, "is_configured", return_value=False):
            handled, reply = server.handle_local("what's on my calendar")
        self.assertTrue(handled)
        self.assertIn("isn't linked", reply)


class BackupAndRestore(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="kalki_backup_")
        self.profile = root
        self.data = os.path.join(root, "data")
        os.makedirs(self.data)
        routes_backup.configure(self.profile, self.data)
        self.addCleanup(routes_backup.configure, os.path.dirname(server.DATA_DIR), server.DATA_DIR)

    def write(self, folder, name, data):
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_backup_goes_in_kalkis_own_folder(self):
        self.write(self.profile, "user_config.json", {"OWNER_NAME": "A"})
        payload, status = routes_backup.create({})
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["file"].startswith(os.path.join(self.profile, "backups")))
        with zipfile.ZipFile(payload["file"]) as archive:
            self.assertIn("kalki.db", archive.namelist())
            self.assertIn("user_config.json", archive.namelist())

    def test_restore_keeps_a_copy_of_each_file_it_replaces(self):
        self.write(self.profile, "user_config.json", {"OWNER_NAME": "current"})
        archive_path = os.path.join(self.profile, "old.zip")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("user_config.json", json.dumps({"OWNER_NAME": "from backup"}))
        with mock.patch.object(routes_backup.semantic_memory.memory, "reload"):
            self.assertEqual(routes_backup.restore({"path": archive_path})[1], 200)
        with open(os.path.join(self.profile, "user_config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["OWNER_NAME"], "from backup")
        copies = [n for n in os.listdir(self.profile) if n.startswith("user_config.json.before-restore.")]
        self.assertEqual(len(copies), 1)
        with open(os.path.join(self.profile, copies[0]), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["OWNER_NAME"], "current")

    def test_unknown_and_oversized_files_are_skipped(self):
        archive_path = os.path.join(self.profile, "odd.zip")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../../evil.py", "print('x')")
            archive.writestr("user_config.json", "x" * (routes_backup.MAX_FILE_BYTES + 1))
        with mock.patch.object(routes_backup.semantic_memory.memory, "reload"):
            routes_backup.restore({"path": archive_path})
        self.assertFalse(os.path.exists(os.path.join(self.profile, "user_config.json")))
        self.assertFalse(any(n.endswith(".py") for n in os.listdir(self.profile)))

    def test_not_a_backup_is_refused_plainly(self):
        path = os.path.join(self.profile, "nope.zip")
        with open(path, "w") as f:
            f.write("not a zip")
        payload, status = routes_backup.restore({"path": path})
        self.assertEqual(status, 400)
        self.assertIn("isn't a KALKI backup", payload["error"])


if __name__ == "__main__":
    unittest.main()
