"""Hands-free "Hey KALKI": the matcher and the listener's two-stage decision.

The transcripts below are what Google's speech recognition really wrote for recordings
of "Hey Kalki ..." in five voices (US, Indian and British English), and for everyday
sentences that must never wake KALKI."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import wake_detect  # noqa: E402

HEARD_FOR_HEY_KALKI = {
    # Accepted straight away.
    "hey Kalki open Notepad": ("wake", "open Notepad", False),
    "Hey KALKI.": ("wake", "", False),
    "Ok KALKI, play some music.": ("wake", "play some music", False),
    "KALKI, what's the time?": ("wake", "what's the time", False),
    "hey cookie open Notepad": ("maybe", "open Notepad", False),
    "ok cookie play some music": ("maybe", "play some music", False),
    "ykal ki open Notepad": ("wake", "open Notepad", False),
    "Hai cal ki brief me": ("wake", "brief me", False),
    # Only with Whisper's confirmation.
    "high quality open Notepad": ("maybe", "open Notepad", True),
    "Khaki what's the time": ("maybe", "what's the time", True),
    "Kyunki what's the time": ("maybe", "what's the time", True),
}

EVERYDAY = [
    "Hey Kelly, how are you?", "I love playing hockey", "Can you call the key maker?",
    "Call me tomorrow morning", "Hey Siri, set a timer", "Hello Calvin, nice to meet you",
    "the cat is sitting on the table", "aaj mausam kaisa hai", "this is high quality work",
    "I ate a cookie", "I told my friend about KALKI yesterday and he laughed at the idea",
]


class Matcher(unittest.TestCase):
    def test_real_google_transcripts_of_hey_kalki(self):
        for heard, expected in HEARD_FOR_HEY_KALKI.items():
            self.assertEqual(wake_detect.classify(heard), expected, heard)

    def test_everyday_speech_never_wakes_kalki_on_its_own(self):
        for heard in EVERYDAY:
            level, _, confirm = wake_detect.classify(heard)
            self.assertTrue(level == "" or confirm, heard)


class ListenerDecision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import listener
        cls.l = listener

    def test_clear_wake_alone_needs_no_cloud(self):
        with mock.patch.object(self.l, "transcribe_with_kalki") as t:
            self.assertEqual(self.l.decide("Hey KALKI", object()), "")
        t.assert_not_called()

    def test_whisper_gives_the_exact_command(self):
        with mock.patch.object(self.l, "transcribe_with_kalki", return_value=("Hey KALKI, open WhatsApp.", "groq-whisper")):
            self.assertEqual(self.l.decide("hey cookie open what's up", object()), "open WhatsApp")

    def test_whisper_rejects_a_doubtful_match(self):
        with mock.patch.object(self.l, "transcribe_with_kalki", return_value=("This is high quality work.", "groq-whisper")):
            self.assertIs(self.l.decide("high quality work", object()), self.l.NOT_FOR_KALKI)

    def test_doubtful_match_without_whisper_is_ignored(self):
        with mock.patch.object(self.l, "transcribe_with_kalki", return_value=(None, None)):
            self.assertIs(self.l.decide("Khaki what's the time", object()), self.l.NOT_FOR_KALKI)
            self.assertEqual(self.l.decide("hey cookie open notepad", object()), "open notepad")

    def test_not_addressed_is_ignored(self):
        with mock.patch.object(self.l, "transcribe_with_kalki") as t:
            self.assertIs(self.l.decide("I love playing hockey", object()), self.l.NOT_FOR_KALKI)
        t.assert_not_called()

    def test_mode_follows_the_setting_live(self):
        with mock.patch.object(self.l, "LAST_STATUS", {"listenMode": "push"}):
            self.assertEqual(self.l.current_mode(), "push")
        with mock.patch.object(self.l, "LAST_STATUS", {"listenMode": "always"}):
            self.assertEqual(self.l.current_mode(), "always")

    def test_old_everyday_false_triggers_are_gone(self):
        self.assertFalse(self.l.contains_wake("I love playing hockey"))
        self.assertFalse(self.l.contains_wake("can you call the key maker"))
        self.assertTrue(self.l.contains_wake("hey kalki open spotify"))
        self.assertEqual(self.l.extract_inline("Hey Kalki, open Spotify"), "open Spotify")


if __name__ == "__main__":
    unittest.main()
