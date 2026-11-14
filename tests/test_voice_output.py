"""KALKI keeps talking: it follows Windows' current speaker or headset, retries the natural
voice once, and uses the Windows voice instead of going silent (unless that's turned off)."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402


class InlineThread:
    """Run speak()'s background work right away so the test can check the result."""

    def __init__(self, target=None, daemon=None, **kw):
        self.target = target

    def start(self):
        self.target()


class Output(unittest.TestCase):
    def setUp(self):
        self.addCleanup(server.STATE.pop, "tts_output_id", None)

    def test_reopens_when_the_default_device_changes(self):
        mixer = mock.Mock()
        mixer.get_init.return_value = True
        with mock.patch.object(server, "pygame", mock.Mock(mixer=mixer)), \
                mock.patch.object(server, "_tts_output_device", return_value=None), \
                mock.patch.object(server, "_init_tts_mixer") as init, \
                mock.patch.object(server, "_default_output_id", side_effect=["speakers", "speakers", "headset"]):
            server.STATE["tts_output_id"] = "speakers"
            server._ensure_tts_output()
            server._ensure_tts_output()
            init.assert_not_called()
            server._ensure_tts_output()
            init.assert_called_once()
        self.assertEqual(server.STATE["tts_output_id"], "headset")

    def test_opens_when_not_open(self):
        mixer = mock.Mock()
        mixer.get_init.return_value = False
        with mock.patch.object(server, "pygame", mock.Mock(mixer=mixer)), \
                mock.patch.object(server, "_tts_output_device", return_value=None), \
                mock.patch.object(server, "_init_tts_mixer") as init, \
                mock.patch.object(server, "_default_output_id", return_value=None):
            server._ensure_tts_output()
        init.assert_called_once()


class Fallback(unittest.TestCase):
    def speak_with(self, build, fallback_setting=True):
        with mock.patch.object(server.threading, "Thread", InlineThread), \
                mock.patch.object(server, "_build_tts_file", side_effect=build), \
                mock.patch.object(server, "_speak_with_windows_sapi") as sapi, \
                mock.patch.object(server.time, "sleep"), \
                mock.patch.object(server.config, "TTS_WINDOWS_FALLBACK", fallback_setting, create=True), \
                mock.patch.object(server.config, "TTS_VOICE", "en-US-AndrewMultilingualNeural", create=True):
            getattr(server, "_original_speak", server.speak)("hello there")
        return sapi

    def test_natural_voice_failing_uses_the_windows_voice(self):
        sapi = self.speak_with(RuntimeError("No audio was received."))
        sapi.assert_called_once()
        self.assertEqual(server.STATE["last_tts_provider"], "windows-sapi")

    def test_turning_the_fallback_off_keeps_it_silent(self):
        sapi = self.speak_with(RuntimeError("No audio was received."), fallback_setting=False)
        sapi.assert_not_called()

    def test_one_dropped_request_is_retried(self):
        calls = []

        def flaky(text):
            calls.append(text)
            if len(calls) == 1:
                raise RuntimeError("No audio was received.")
            raise RuntimeError("stop here")  # the retry happened; playback isn't under test

        self.speak_with(flaky)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
