"""Small talk, help, PC stats and mail quick commands."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import commands_chat as cc  # noqa: E402

MADE_UP = ("Neural", "100%", "Sovereign", "crack hashes", "Fuck you", "I'm your creation", "You did")


class SmallTalk(unittest.TestCase):
    def say(self, text, **kw):
        return cc.smalltalk_command(text, **kw)

    def test_replies_make_no_claims_nothing_measured(self):
        for text in ("hi", "how are you", "help", "commands", "thanks", "who are you", "who made you",
                     "i love you", "i messed up", "good night"):
            for _ in range(8):
                reply = self.say(text)
                for phrase in MADE_UP:
                    self.assertNotIn(phrase, reply, f"{text}: {reply}")

    def test_greeting_follows_the_time_and_title(self):
        with mock.patch.object(cc.config, "OWNER_TITLE", "boss", create=True):
            self.assertTrue(self.say("hello", hour=9).startswith("Good morning, boss."))
        with mock.patch.object(cc.config, "OWNER_TITLE", "", create=True):
            self.assertTrue(self.say("hello", hour=20).startswith("Good evening."))

    def test_admitting_a_mistake_gets_help_not_abuse(self):
        reply = self.say("ugh i messed up the build")
        self.assertTrue(any(w in reply for w in ("error", "wrong", "changed")))

    def test_help_lists_real_tools_and_routines(self):
        reply = self.say("what can you do", tools=["search_web", "add_reminder"], modes=["Study mode"])
        self.assertIn("search web", reply)
        self.assertIn("Study mode", reply)

    def test_ordinary_text_is_left_alone(self):
        self.assertIsNone(self.say("help me write an email to my landlord"))


class PcAndMail(unittest.TestCase):
    def test_files_come_from_the_workspace(self):
        folder = tempfile.mkdtemp()
        open(os.path.join(folder, "plan.txt"), "w").close()
        reply = cc.pc_command("list files", folder)
        self.assertIn("plan.txt", reply)
        self.assertIn("1 items", reply)

    def test_stats_are_measured(self):
        reply = cc.pc_command("system stats", tempfile.mkdtemp())
        self.assertIn("CPU:", reply)
        self.assertNotIn("Sovereign", reply)

    def test_mail_commands(self):
        mail = mock.Mock()
        mail.summary_for_speech.return_value = "2 new"
        self.assertEqual(cc.mail_command("check my mail", mail), "2 new")
        mail.summary_for_speech.assert_called_with(only_important=False, limit=5)
        cc.mail_command("any important mail", mail)
        mail.summary_for_speech.assert_called_with(only_important=True, limit=8)
        self.assertIsNone(cc.mail_command("write a mail to bob", mail))


class StillRoutedByHandleLocal(unittest.TestCase):
    def test_handle_local_uses_them(self):
        self.assertTrue(server.handle_local("thanks")[0])
        handled, reply = server.handle_local("list files")
        self.assertTrue(handled)
        self.assertIn("workspace", reply)
        with mock.patch.object(server, "fetch_online_joke", return_value="a joke"):
            self.assertEqual(server.handle_local("tell me a joke"), (True, "a joke"))


if __name__ == "__main__":
    unittest.main()
