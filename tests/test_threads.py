"""Conversations stored on the server, shared by the app, voice and Telegram."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import db  # noqa: E402
import routes_threads  # noqa: E402
import threads  # noqa: E402

NOW = 1_800_000_000_000
HOUR = 3_600_000


def message(msg_id, role="user", content="hello", **extra):
    return {"id": msg_id, "role": role, "content": content, "ts": NOW, **extra}


def thread(thread_id="t1", messages=(), **fields):
    return {"id": thread_id, "title": "Title", "createdAt": NOW, "updatedAt": NOW,
            "pinned": False, "archived": False, "model": "", "messages": list(messages), **fields}


class ThreadCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_threads_")
        previous = db.current_path()
        db.configure(os.path.join(self.dir, "kalki.db"))
        db.open_store(self.dir)
        threads.set_active(None)
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(db.configure, previous)
        self.addCleanup(threads.set_active, None)

    def get(self, thread_id="t1"):
        return next((t for t in threads.list_all() if t["id"] == thread_id), None)


class Save(ThreadCase):
    def test_round_trip_keeps_every_field(self):
        threads.save(thread(messages=[message("m1", attachments=[{"name": "a.pdf", "size": 3}], failed=True)],
                            pinned=True, model="gemini", title="Trip"))
        saved = self.get()
        self.assertEqual((saved["title"], saved["pinned"], saved["model"]), ("Trip", True, "gemini"))
        self.assertEqual(saved["messages"][0]["attachments"], [{"name": "a.pdf", "size": 3}])
        self.assertIs(saved["messages"][0]["failed"], True)

    def test_order_is_kept_and_updates_stay_in_place(self):
        threads.save(thread(messages=[message("m1"), message("m2", "assistant", "")]))
        threads.save(thread(messages=[message("m2", "assistant", "finished", done=True)]))
        saved = self.get()["messages"]
        self.assertEqual([m["id"] for m in saved], ["m1", "m2"])
        self.assertEqual(saved[1]["content"], "finished")
        self.assertIs(saved[1]["done"], True)

    def test_a_stale_save_never_removes_messages(self):
        """Regression guard: a window that hasn't seen a voice reply can't erase it."""
        threads.save(thread(messages=[message("m1")]))
        threads.append_exchange("voice question", "voice answer", "voice", thread_id="t1", now=NOW)
        threads.save(thread(messages=[message("m1", content="edited")]))
        self.assertEqual(len(self.get()["messages"]), 3)

    def test_newest_first_with_pinned_on_top(self):
        threads.save(thread("old", updatedAt=NOW))
        threads.save(thread("new", updatedAt=NOW + 5))
        threads.save(thread("pin", updatedAt=NOW - 5, pinned=True))
        self.assertEqual([t["id"] for t in threads.list_all()], ["pin", "new", "old"])

    def test_bad_input_is_rejected(self):
        for bad in (thread("bad id!"), thread(""), {"title": "no id"}, thread(messages="nope"),
                    thread(messages=[{"role": "user", "content": "no id"}]),
                    thread(messages=[message("m1", role="system")]),
                    thread(messages=[message("m1", content=5)])):
            with self.assertRaises(ValueError, msg=bad):
                threads.save(bad)
        self.assertEqual(threads.list_all(), [])

    def test_sql_text_is_just_text(self):
        threads.save(thread(messages=[message("m1", content="'); DROP TABLE threads; --")]))
        self.assertIn("DROP", self.get()["messages"][0]["content"])


class Remove(ThreadCase):
    def test_truncate_removes_from_that_message_on(self):
        threads.save(thread(messages=[message("m1"), message("m2"), message("m3")]))
        threads.save(thread("other", messages=[message("m2")]))
        self.assertTrue(threads.truncate("t1", "m2"))
        self.assertEqual([m["id"] for m in self.get()["messages"]], ["m1"])
        self.assertEqual(len(self.get("other")["messages"]), 1)

    def test_truncate_of_unknown_message_changes_nothing(self):
        threads.save(thread(messages=[message("m1")]))
        self.assertFalse(threads.truncate("t1", "nope"))
        self.assertEqual(len(self.get()["messages"]), 1)

    def test_delete_removes_its_messages(self):
        threads.save(thread(messages=[message("m1")]))
        self.assertTrue(threads.delete("t1"))
        self.assertIsNone(self.get())
        threads.save(thread(messages=[]))
        self.assertEqual(self.get()["messages"], [])

    def test_clear_keeps_pinned(self):
        threads.save(thread("a"))
        threads.save(thread("b", pinned=True))
        threads.clear_unpinned()
        self.assertEqual([t["id"] for t in threads.list_all()], ["b"])


class SharedThread(ThreadCase):
    def test_voice_joins_the_thread_open_in_the_app(self):
        threads.save(thread(messages=[message("m1")]))
        threads.set_active("t1")
        self.assertEqual(threads.append_exchange("q", "a", "voice", now=NOW + 1000), "t1")
        saved = self.get()["messages"]
        self.assertEqual([m["content"] for m in saved[1:]], ["q", "a"])
        self.assertEqual(saved[1]["origin"], "voice")
        self.assertEqual(self.get()["updatedAt"], NOW + 1000)

    def test_with_nothing_open_it_uses_the_latest_recent_thread(self):
        threads.save(thread("old", updatedAt=NOW - HOUR))
        threads.save(thread("recent", updatedAt=NOW))
        self.assertEqual(threads.append_exchange("q", "a", "telegram", now=NOW + 1000), "recent")

    def test_after_a_long_gap_it_starts_a_new_thread(self):
        threads.save(thread(updatedAt=NOW))
        new_id = threads.append_exchange("what is the plan", "a", "voice", now=NOW + 7 * HOUR)
        self.assertNotEqual(new_id, "t1")
        self.assertEqual(self.get(new_id)["title"], "what is the plan")

    def test_a_deleted_active_thread_is_not_recreated(self):
        threads.save(thread())
        threads.set_active("t1")
        threads.delete("t1")
        self.assertNotEqual(threads.append_exchange("q", "a", "voice", now=NOW), "t1")

    def test_repeated_identical_exchanges_are_all_kept(self):
        threads.save(thread())
        for _ in range(2):
            threads.append_exchange("same", "same", "voice", thread_id="t1", now=NOW)
        self.assertEqual(len(self.get()["messages"]), 4)

    def test_recent_context_is_clean_and_limited(self):
        threads.save(thread(messages=[
            message("m1", content="first"), message("m2", "assistant", "broken", failed=True),
            message("m3", "assistant", ""), message("m4", content="second"), message("m5", "assistant", "third")]))
        threads.set_active("t1")
        self.assertEqual(threads.recent_context(limit=2, now=NOW), [
            {"role": "user", "content": "second"}, {"role": "assistant", "content": "third"}])

    def test_recent_context_is_empty_after_a_long_gap(self):
        threads.save(thread(messages=[message("m1")]))
        self.assertEqual(threads.recent_context(now=NOW + 7 * HOUR), [])


class Routes(ThreadCase):
    def test_flow(self):
        routes = routes_threads.POST_ROUTES
        self.assertEqual(routes["/api/threads/save"]({"thread": thread(messages=[message("m1"), message("m2")])})[1], 200)
        self.assertEqual(len(routes["/api/threads/list"]({})[0]["threads"]), 1)
        self.assertTrue(routes["/api/threads/truncate"]({"id": "t1", "messageId": "m2"})[0]["ok"])
        self.assertTrue(routes["/api/threads/delete"]({"id": "t1"})[0]["ok"])
        self.assertEqual(routes["/api/threads/clear"]({})[1], 200)

    def test_bad_input_is_a_400(self):
        self.assertEqual(routes_threads.POST_ROUTES["/api/threads/save"]({"thread": "nope"})[1], 400)
        self.assertEqual(routes_threads.POST_ROUTES["/api/threads/save"]({"thread": thread("bad id!")})[1], 400)


if __name__ == "__main__":
    unittest.main()
