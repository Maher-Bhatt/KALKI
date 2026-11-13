"""KALKI's mood: clear insults change its tone, and sustained abuse locks the PC.

Matching is strict, because a false trigger can end in a locked PC."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import mood  # noqa: E402
import server  # noqa: E402


class Matching(unittest.TestCase):
    def test_everyday_messages_never_count(self):
        for text in ("compose a post for linkedin", "find a McDonald's near me", "take out the trash",
                     "this code sucks, help me fix it", "that was a dumb mistake of mine", "is the BC ferry running",
                     "show my position", "skills I need", "this is useless without a key", "crap, I forgot",
                     "shitake mushrooms recipe", "scunthorpe weather", "the Dickens novel", "assess the risk"):
            self.assertFalse(mood.is_abusive(text), text)

    def test_clear_insults_count(self):
        for text in ("you idiot", "you're a moron", "fuck you", "shut up bitch", "chutiya hai tu", "IDIOTS"):
            self.assertTrue(mood.is_abusive(text), text)


class Streak(unittest.TestCase):
    def test_tone_then_warning_then_lock(self):
        state = {}
        results = [mood.update(state, "you idiot") for _ in range(mood.LOCK_THRESHOLD)]
        self.assertEqual(results[0], "roast")
        self.assertEqual(results[mood.WARN_THRESHOLD - 1], "warn")
        self.assertEqual(results[-1], "lock")
        self.assertEqual(state["mood_aggressive_streak"], 0)

    def test_kind_messages_calm_it_down(self):
        state = {}
        for _ in range(3):
            mood.update(state, "you idiot")
        for _ in range(3):
            mood.update(state, "thanks, that helped")
        self.assertFalse(state["mood_aggressive"])
        self.assertIsNone(mood.update(state, "what time is it"))


class LockingThePc(unittest.TestCase):
    def setUp(self):
        self.saved = {k: server.STATE.get(k) for k in ("mood_aggressive", "mood_aggressive_streak")}
        self.addCleanup(server.STATE.update, self.saved)
        server.STATE.update(mood_aggressive=False, mood_aggressive_streak=0)

    def abuse(self, times):
        return [server._apply_mood("you idiot") for _ in range(times)]

    def test_it_locks_after_sustained_abuse(self):
        with mock.patch.object(server, "_lock_pc_soon") as lock, mock.patch.object(server.sys, "platform", "win32"), \
                mock.patch.object(server.config, "MOOD_LOCK_ENABLED", True, create=True):
            prompts = self.abuse(mood.LOCK_THRESHOLD)
        lock.assert_called_once()
        self.assertIn("locking their PC", prompts[-1])
        self.assertIn("WILL lock their PC", prompts[mood.WARN_THRESHOLD - 1])

    def test_the_setting_turns_the_lock_off(self):
        with mock.patch.object(server, "_lock_pc_soon") as lock, mock.patch.object(server.sys, "platform", "win32"), \
                mock.patch.object(server.config, "MOOD_LOCK_ENABLED", False, create=True):
            self.abuse(mood.LOCK_THRESHOLD)
        lock.assert_not_called()

    def test_everyday_words_never_lock(self):
        with mock.patch.object(server, "_lock_pc_soon") as lock, mock.patch.object(server.sys, "platform", "win32"):
            for _ in range(30):
                self.assertEqual(server._apply_mood("take out the trash and post the mc results"), "")
        lock.assert_not_called()

    def test_both_chat_paths_use_the_same_check(self):
        source = Path(server.__file__).read_text(encoding="utf-8")
        self.assertEqual(source.count("sys_prompt += _apply_mood(last_user)"), 2)
        self.assertNotIn("vulgar_keywords", source)


if __name__ == "__main__":
    unittest.main()
