"""Data store tests: migrations, safe import from JSON, tasks, reminders, notes, logs."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import db  # noqa: E402
import notes  # noqa: E402
import runtime_log  # noqa: E402
import tasks  # noqa: E402


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_store_")
        self._previous = db.current_path()
        db.configure(os.path.join(self.dir, "kalki.db"))

    def tearDown(self):
        db.configure(self._previous)
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_json(self, name, data):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f)
        return path


class Migrations(StoreCase):
    def test_new_store_reaches_latest_version(self):
        db.open_store(self.dir)
        with db.connect() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)

    def test_reopening_is_harmless(self):
        db.open_store(self.dir)
        tasks.add_task("keep me")
        db.open_store(self.dir)
        self.assertEqual([t["text"] for t in tasks.list_tasks()], ["keep me"])

    def test_upgrade_backs_up_first(self):
        path = db.current_path()
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE old_data (x)")
        conn.execute("PRAGMA user_version = 0")
        conn.commit()
        conn.close()
        db.open_store(self.dir)
        backups = [n for n in os.listdir(self.dir) if n.startswith("kalki.db.v0")]
        self.assertEqual(len(backups), 1)

    def test_newer_store_is_refused_not_damaged(self):
        path = db.current_path()
        conn = sqlite3.connect(path)
        conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 5}")
        conn.commit()
        conn.close()
        with self.assertRaises(db.StoreError):
            db.open_store(self.dir)

    def test_failed_migration_rolls_back(self):
        original = list(db.MIGRATIONS)
        db.MIGRATIONS.append((db.SCHEMA_VERSION + 1, "CREATE TABLE half_done (x); THIS IS NOT SQL;"))
        try:
            with self.assertRaises(sqlite3.Error):
                db.migrate()
        finally:
            db.MIGRATIONS[:] = original
        with db.connect() as conn:
            # The good migrations stay applied. Only the broken one is undone.
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master")]
        self.assertNotIn("half_done", names)


class LegacyImport(StoreCase):
    TASKS = [{"id": 7, "text": "old task", "added": "2026-01-01T10:00:00", "done": False},
             {"id": 9, "text": "done task", "added": "2026-01-01T10:00:00", "done": True,
              "completed": "2026-01-02T10:00:00"}]

    def test_imports_keep_ids_and_fields(self):
        self.write_json("tasks.json", self.TASKS)
        report = db.open_store(self.dir)
        self.assertEqual(report["imported"]["tasks"], 2)
        rows = tasks.list_tasks(include_done=True)
        self.assertEqual([t["id"] for t in rows], [7, 9])
        self.assertTrue(rows[1]["done"])
        self.assertEqual(rows[1]["completed"], "2026-01-02T10:00:00")
        self.assertEqual(tasks.add_task("new"), 10)

    def test_original_file_is_left_untouched(self):
        path = self.write_json("tasks.json", self.TASKS)
        before = open(path, "rb").read()
        db.open_store(self.dir)
        self.assertEqual(open(path, "rb").read(), before)

    def test_import_runs_only_once(self):
        self.write_json("tasks.json", self.TASKS)
        db.open_store(self.dir)
        tasks.delete_task(7)
        db.open_store(self.dir)
        self.assertEqual([t["id"] for t in tasks.list_tasks(include_done=True)], [9])

    def test_corrupt_file_is_reported_kept_and_retried(self):
        path = self.write_json("notes.json", "{not json")
        report = db.open_store(self.dir)
        self.assertIn("notes", report["failed"])
        self.assertTrue(os.path.exists(path))
        self.assertEqual(notes.list_recent(), [])
        self.write_json("notes.json", [{"id": 1, "text": "fixed", "tags": [],
                                        "ts": "2026-01-01T10:00:00", "date": "2026-01-01"}])
        db.open_store(self.dir)
        self.assertEqual(notes.list_recent()[0]["text"], "fixed")

    def test_bad_rows_are_skipped_and_counted(self):
        self.write_json("reminders.json", [
            {"id": 1, "text": "good", "due": "2099-01-01T10:00:00", "fired": False},
            {"id": 2, "due": "2099-01-01T10:00:00"}, "nonsense"])
        report = db.open_store(self.dir)
        self.assertEqual(report["imported"]["reminders"], 1)
        self.assertEqual(report["skipped"]["reminders"], 2)


class Tasks(StoreCase):
    def setUp(self):
        super().setUp()
        db.open_store(self.dir)

    def test_id_never_matches_text(self):
        """Regression: deleting task 1 also deleted every task with '1' in its text."""
        first = tasks.add_task("first")
        other = tasks.add_task("Call at 1pm")
        third = tasks.add_task("Q1 report")
        self.assertTrue(tasks.delete_task(first))
        self.assertEqual([t["id"] for t in tasks.list_tasks()], [other, third])
        self.assertEqual(tasks.complete_task(first), None)

    def test_ambiguous_text_changes_nothing(self):
        tasks.add_task("buy milk")
        tasks.add_task("buy eggs")
        self.assertFalse(tasks.delete_task("buy"))
        self.assertEqual(len(tasks.list_tasks()), 2)

    def test_exact_text_beats_partial(self):
        tasks.add_task("buy")
        tasks.add_task("buy eggs")
        self.assertTrue(tasks.delete_task("buy"))
        self.assertEqual([t["text"] for t in tasks.list_tasks()], ["buy eggs"])

    def test_complete_by_text_and_shape(self):
        tid = tasks.add_task("  file taxes ")
        done = tasks.complete_task("taxes")
        self.assertEqual(done["id"], tid)
        self.assertEqual(done["text"], "file taxes")
        self.assertIs(done["done"], True)
        self.assertEqual(tasks.list_tasks(), [])
        self.assertIsNone(tasks.complete_task("taxes"))

    def test_clear_helpers(self):
        a = tasks.add_task("a")
        tasks.add_task("b")
        tasks.complete_task(a)
        self.assertEqual(tasks.clear_completed(), 1)
        self.assertTrue(tasks.clear_all_tasks())
        self.assertEqual(tasks.list_tasks(include_done=True), [])

    def test_ids_are_never_reused(self):
        a = tasks.add_task("a")
        tasks.delete_task(a)
        self.assertGreater(tasks.add_task("b"), a)


class Reminders(StoreCase):
    def setUp(self):
        super().setUp()
        db.open_store(self.dir)

    def test_due_reminder_fires_once(self):
        past = datetime.now() - timedelta(minutes=1)
        rid = tasks.add_reminder("now", past)
        tasks.add_reminder("later", datetime.now() + timedelta(days=1))
        self.assertEqual([r["id"] for r in tasks.pop_due_reminders()], [rid])
        self.assertEqual(tasks.pop_due_reminders(), [])
        self.assertEqual([r["text"] for r in tasks.list_reminders()], ["later"])
        self.assertEqual(len(tasks.list_reminders(include_fired=True)), 2)

    def test_natural_language_due(self):
        tasks.add_reminder("x", "in 2 hours")
        due = datetime.fromisoformat(tasks.list_reminders()[0]["due"])
        self.assertGreater(due, datetime.now() + timedelta(minutes=110))

    def test_delete_by_id_only_touches_that_id(self):
        a = tasks.add_reminder("first", "in 2 hours")
        b = tasks.add_reminder("Call 1pm", "in 2 hours")
        self.assertTrue(tasks.delete_reminder(a))
        self.assertEqual([r["id"] for r in tasks.list_reminders()], [b])

    def test_survives_reopen(self):
        tasks.add_reminder("persist", "in 2 hours")
        db.configure(db.current_path())
        db.open_store(self.dir)
        self.assertEqual(tasks.list_reminders()[0]["text"], "persist")


class Notes(StoreCase):
    def setUp(self):
        super().setUp()
        db.open_store(self.dir)

    def test_add_extracts_tags_and_lists_newest_first(self):
        notes.add_note("first #Work")
        second = notes.add_note("second")
        recent = notes.list_recent()
        self.assertEqual(recent[0]["id"], second)
        self.assertEqual(recent[1]["tags"], ["work"])

    def test_empty_note_rejected(self):
        self.assertIsNone(notes.add_note("   "))

    def test_search_text_and_tags_with_special_characters(self):
        notes.add_note("Try Ollama #ai")
        notes.add_note("100% done_ok")
        self.assertEqual(len(notes.search("ollama")), 1)
        self.assertEqual(len(notes.search("ai")), 1)
        self.assertEqual(len(notes.search("100%")), 1)
        self.assertEqual(len(notes.search("done_")), 1)
        self.assertEqual(notes.search("%"), notes.search("100%"))

    def test_delete_by_id_only_touches_that_id(self):
        a = notes.add_note("first")
        b = notes.add_note("meeting at 1pm")
        self.assertTrue(notes.delete_note(a))
        self.assertEqual([n["id"] for n in notes.list_recent()], [b])

    def test_date_helpers(self):
        notes.add_note("today")
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(len(notes.notes_on(today)), 1)
        self.assertEqual(len(notes.notes_this_week()), 1)
        self.assertEqual(notes.notes_yesterday(), [])


class BackupRestore(StoreCase):
    def setUp(self):
        super().setUp()
        db.open_store(self.dir)

    def test_copy_then_restore_brings_data_back(self):
        tasks.add_task("in the backup")
        copy = os.path.join(self.dir, "copy.db")
        db.backup_to(copy)
        tasks.clear_all_tasks()
        tasks.add_task("after the backup")
        db.restore_from(copy)
        self.assertEqual([t["text"] for t in tasks.list_tasks()], ["in the backup"])

    def test_restore_keeps_a_safety_copy(self):
        tasks.add_task("before restore")
        copy = os.path.join(self.dir, "copy.db")
        db.backup_to(copy)
        db.restore_from(copy)
        self.assertTrue([n for n in os.listdir(self.dir) if n.startswith("kalki.db.before-restore")])

    def test_bad_file_is_rejected_and_data_kept(self):
        tasks.add_task("safe")
        bad = self.write_json("bad.db", "this is not a database")
        with self.assertRaises(db.StoreError):
            db.restore_from(bad)
        self.assertEqual([t["text"] for t in tasks.list_tasks()], ["safe"])


class LogScrubbing(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_log_")
        self.path = os.path.join(self.dir, "x.log")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def test_known_secret_shapes_are_removed(self):
        samples = ["gsk_" + "a" * 30, "sk-" + "b" * 30, "ghp_" + "c" * 30, "AIza" + "d" * 30,
                   "Authorization: Bearer abcdefghijklmnop", "password=hunter2secret", "api_key=abc123def456"]
        for sample in samples:
            runtime_log.append_log(self.path, f"failed with {sample} here")
        text = self.read()
        for secret in ("aaaaaaaa", "bbbbbbbb", "cccccccc", "dddddddd", "abcdefghijklmnop", "hunter2secret", "abc123def456"):
            self.assertNotIn(secret, text)
        self.assertIn("[REDACTED]", text)

    def test_registered_secret_is_removed(self):
        runtime_log.register_secret("my-local-session-token-value")
        runtime_log.append_log(self.path, "token my-local-session-token-value used")
        self.assertNotIn("my-local-session-token-value", self.read())

    def test_short_values_cannot_be_registered(self):
        runtime_log.register_secret("a")
        runtime_log.append_log(self.path, "a normal sentence")
        self.assertIn("a normal sentence", self.read())

    def test_structured_event_is_one_json_line(self):
        runtime_log.log_event(self.path, "error", "scan_failed", path="/api/x", detail="sk-" + "e" * 30)
        line = self.read().strip()
        record = json.loads(line[line.index("{"):])
        self.assertEqual(record["level"], "error")
        self.assertEqual(record["event"], "scan_failed")
        self.assertEqual(record["path"], "/api/x")
        self.assertNotIn("eeeeeeee", line)


if __name__ == "__main__":
    unittest.main()
