"""Notes: search, tags, edit, delete with Undo, and Markdown export."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402,F401  sets up the store
import db  # noqa: E402
import notes  # noqa: E402
import routes_productivity as rp  # noqa: E402


class NotesTest(unittest.TestCase):
    def setUp(self):
        self._clear()
        self.addCleanup(self._clear)

    def _clear(self):
        with db.connect() as conn:
            conn.execute("DELETE FROM notes")


class Search(NotesTest):
    def test_text_any_case_and_tags(self):
        a = notes.add_note("Buy MILK #shopping")
        b = notes.add_note("call the bank #admin")
        self.assertEqual([n["id"] for n in notes.search("milk")], [a])
        self.assertEqual([n["id"] for n in notes.search("", "admin")], [b])
        self.assertEqual([n["id"] for n in notes.search("", "#Shopping")], [a])
        self.assertEqual(len(notes.search("")), 2)

    def test_wildcards_are_literal(self):
        notes.add_note("100% done")
        notes.add_note("1000 done")
        notes.add_note("snake_case")
        notes.add_note("snakeXcase")
        self.assertEqual([n["text"] for n in notes.search("0%")], ["100% done"])
        self.assertEqual([n["text"] for n in notes.search("e_c")], ["snake_case"])

    def test_tag_counts(self):
        notes.add_note("a #work")
        notes.add_note("b #work #ideas")
        self.assertEqual(notes.all_tags(), [{"tag": "work", "count": 2}, {"tag": "ideas", "count": 1}])


class EditDeleteUndo(NotesTest):
    def test_edit_updates_text_and_tags(self):
        nid = notes.add_note("draft #old")
        note = notes.update_note(nid, "final #new")
        self.assertEqual((note["text"], note["tags"]), ("final #new", ["new"]))
        with self.assertRaises(ValueError):
            notes.update_note(nid, "   ")
        self.assertIsNone(notes.update_note(999999, "x"))

    def test_delete_then_undo_restores_it_exactly(self):
        nid = notes.add_note("keep me #safe")
        before = notes.get_note(nid)
        deleted = notes.delete_note(nid)
        self.assertEqual(deleted, before)
        self.assertIsNone(notes.get_note(nid))
        self.assertEqual(notes.restore_note(deleted), before)
        self.assertIsNone(notes.delete_note(123456))


class Export(NotesTest):
    def test_markdown_grouped_by_day(self):
        with db.connect() as conn:
            conn.execute("INSERT INTO notes (text, tags, ts, date) VALUES ('older', '[]', '2026-11-12T09:05:00', '2026-11-12')")
            conn.execute("INSERT INTO notes (text, tags, ts, date) VALUES ('line one\nline two', '[]', '2026-11-13T18:30:00', '2026-11-13')")
        md = notes.export_markdown()
        self.assertEqual(md, "# KALKI notes\n\n## 2026-11-12\n\n- 09:05  older\n## 2026-11-13\n\n- 18:30  line one\n  line two\n")


class Routes(NotesTest):
    def test_update_delete_restore_tags_export(self):
        nid = rp.add_note({"text": "plan trip #travel"})[0]["id"]
        self.assertEqual(rp.update_note({"id": nid, "text": "plan the trip #travel"})[1], 200)
        self.assertEqual(rp.update_note({"id": "abc", "text": "x"})[1], 400)
        self.assertEqual(rp.update_note({"id": nid, "text": ""})[1], 400)
        self.assertEqual(rp.update_note({"id": 999999, "text": "x"})[1], 404)
        self.assertEqual(rp.note_tags({})[0]["tags"], [{"tag": "travel", "count": 1}])
        payload, _ = rp.export_notes({"tag": "travel"})
        self.assertEqual(payload["count"], 1)
        self.assertIn("plan the trip", payload["markdown"])
        payload, status = rp.delete_note({"id": nid})
        self.assertEqual(status, 200)
        self.assertEqual(rp.delete_note({"id": nid})[1], 404)
        self.assertEqual(rp.restore_note({"note": payload["deleted"]})[1], 200)
        self.assertEqual(rp.restore_note({"note": {"id": 1}})[1], 400)
        self.assertEqual(rp.search_notes({"q": "trip"})[0]["notes"][0]["id"], nid)

    def test_voice_search_still_works(self):
        notes.add_note("dentist on monday")
        self.assertIn("dentist", server.handle_local("search notes for dentist")[1])


class Screens(unittest.TestCase):
    def test_every_notes_endpoint_the_ui_calls_exists(self):
        source = (ROOT / "app" / "ui" / "api" / "endpoints.js").read_text(encoding="utf-8")
        called = set(re.findall(r"'(/api/notes/[a-z]+)'", source))
        self.assertEqual(called - set(rp.POST_ROUTES), set())
        self.assertGreaterEqual(len(called), 8)

    def test_today_box_no_longer_promises_search(self):
        page = (ROOT / "app" / "ui" / "features" / "today.js").read_text(encoding="utf-8")
        self.assertNotIn("or search notes", page)
        self.assertIn("openNotesDialog", page)


if __name__ == "__main__":
    unittest.main()
