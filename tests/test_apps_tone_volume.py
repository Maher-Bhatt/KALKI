"""Opening installed apps (Store apps too), insults in Hindi and Hinglish, Savage mode,
and KALKI turning its own Windows mixer volume back up."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import app_launcher  # noqa: E402
import mood  # noqa: E402

APPS = {
    "spotify": ("Spotify", "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"),
    "apple music": ("Apple Music", "AppleInc.AppleMusicWin_nzyj5cx40ttqa!App"),
    "visual studio code": ("Visual Studio Code", "Microsoft.VisualStudioCode"),
    "google chrome": ("Google Chrome", "Chrome"),
    "google meet": ("Google Meet", "meet"),
    "uninstall spotify": ("Uninstall Spotify", "x"),
}


class Launcher(unittest.TestCase):
    def test_finds_by_spoken_name(self):
        cases = {"spotify": "Spotify", "the spotify app": "Spotify", "apple music": "Apple Music",
                 "vs code": "Visual Studio Code", "chrome": "Google Chrome", "nothing like this": None}
        for spoken, expected in cases.items():
            found = app_launcher.find(spoken, APPS)
            self.assertEqual(found[0] if found else None, expected, spoken)

    def test_launch_uses_the_start_menu_id_without_a_shell(self):
        with mock.patch.object(app_launcher, "find", return_value=APPS["spotify"]), \
                mock.patch.object(app_launcher.subprocess, "Popen") as popen:
            self.assertEqual(app_launcher.launch("spotify"), "Spotify")
        self.assertEqual(popen.call_args[0][0], ["explorer.exe", "shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"])

    def test_open_spotify_reaches_the_launcher_but_websites_dont(self):
        with mock.patch.object(app_launcher, "launch", return_value="Spotify") as launch:
            self.assertEqual(server.handle_local("open spotify"), (True, "Opening Spotify."))
        launch.assert_called_once_with("spotify")
        with mock.patch.object(app_launcher, "launch") as launch, mock.patch.object(server.webbrowser, "open"):
            server.handle_local("open youtube")
        launch.assert_not_called()


class Insults(unittest.TestCase):
    def test_hindi_and_hinglish(self):
        for text in ("tu chutiya hai", "behenchod kaam kar", "bhosdiwale", "तू चूतिया है", "मादरचोद", "abe lodu"):
            self.assertTrue(mood.is_abusive(text), text)

    def test_everyday_hindi_isnt_abuse(self):
        for text in ("kutte ki tarah kaam kar raha hu", "aaj mausam kaisa hai", "मुझे गाना सुनाओ", "kam se kam"):
            self.assertFalse(mood.is_abusive(text), text)


class Tone(unittest.TestCase):
    def test_always_mirrors_the_language(self):
        with mock.patch.object(server.config, "ROAST_MODE", False, create=True):
            block = server._tone_block()
        self.assertIn("same language and script", block)
        self.assertNotIn("Savage mode", block)

    def test_savage_mode(self):
        with mock.patch.object(server.config, "ROAST_MODE", True, create=True):
            block = server._tone_block()
        self.assertIn("Savage mode is ON", block)
        self.assertIn("Never use slurs", block)


class OwnVolume(unittest.TestCase):
    def session(self, pid, muted, level):
        vol = mock.Mock()
        vol.GetMute.return_value = muted
        vol.GetMasterVolume.return_value = level
        return mock.Mock(Process=mock.Mock(pid=pid), SimpleAudioVolume=vol)

    def test_turns_only_its_own_volume_up(self):
        mine = self.session(os.getpid(), True, 0.0)
        other = self.session(os.getpid() + 1, True, 0.0)
        with mock.patch.object(server, "PYCAW_OK", True), \
                mock.patch.object(server, "AudioUtilities", mock.Mock(GetAllSessions=lambda: [other, mine]), create=True), \
                mock.patch.object(server.config, "TTS_FIX_APP_VOLUME", True, create=True):
            self.assertEqual(server._ensure_own_volume_audible(), "unmuted and set to 100%")
        mine.SimpleAudioVolume.SetMasterVolume.assert_called_once_with(1.0, None)
        other.SimpleAudioVolume.SetMasterVolume.assert_not_called()

    def test_leaves_a_normal_volume_alone_and_respects_the_setting(self):
        mine = self.session(os.getpid(), False, 0.6)
        with mock.patch.object(server, "PYCAW_OK", True), \
                mock.patch.object(server, "AudioUtilities", mock.Mock(GetAllSessions=lambda: [mine]), create=True):
            self.assertEqual(server._ensure_own_volume_audible(), "")
            with mock.patch.object(server.config, "TTS_FIX_APP_VOLUME", False, create=True):
                mine.SimpleAudioVolume.GetMasterVolume.return_value = 0.0
                self.assertEqual(server._ensure_own_volume_audible(), "")
        mine.SimpleAudioVolume.SetMasterVolume.assert_not_called()


if __name__ == "__main__":
    unittest.main()
