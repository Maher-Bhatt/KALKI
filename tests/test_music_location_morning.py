"""Apple Music when Spotify isn't set up, this PC's location from Windows (never the IP
address), and the spoken briefing the first time the PC starts or wakes each day."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import briefing  # noqa: E402
import commands_media as cm  # noqa: E402
from core import location_provider as lp  # noqa: E402


def deps(app):
    spotify = mock.Mock()
    spotify.is_configured.return_value = app == "spotify"
    spotify.play.return_value = "spotify play"
    media = mock.Mock(spec=["pause", "play", "next_track", "prev_track", "now_playing", "now_playing_json"])
    media.now_playing_json.return_value = {"title": "Nothing playing"}
    return {"spotify": spotify, "media": media, "open_url": mock.Mock(), "set_volume": mock.Mock(),
            "open_apple_music": mock.Mock(), "music_app": lambda: app,
            "apple_music": mock.Mock(side_effect=lambda q: f"apple:{q}")}


class Music(unittest.TestCase):
    def test_without_spotify_apple_music_plays(self):
        d = deps("apple_music")
        for text in ("play some music", "play music", "play a song", "resume"):
            self.assertEqual(cm.music_command(text, d), (True, "apple:None"), text)
        self.assertEqual(cm.music_command("play arijit singh", d), (True, "apple:arijit singh"))
        d["open_url"].assert_not_called()

    def test_spotify_still_wins_when_connected(self):
        d = deps("spotify")
        self.assertEqual(cm.music_command("play some music", d), (True, "spotify play"))
        d["apple_music"].assert_not_called()

    def test_choosing_the_app(self):
        with mock.patch.object(server.spotify_mod, "is_configured", return_value=False), \
                mock.patch.object(server, "apple_music_installed", return_value=True):
            for choice, expected in (("auto", "apple_music"), ("youtube", "youtube"), ("spotify", "apple_music")):
                with mock.patch.object(server.config, "MUSIC_APP", choice, create=True):
                    self.assertEqual(server.music_app(), expected, choice)
        with mock.patch.object(server.spotify_mod, "is_configured", return_value=False), \
                mock.patch.object(server, "apple_music_installed", return_value=False), \
                mock.patch.object(server.config, "MUSIC_APP", "auto", create=True):
            self.assertEqual(server.music_app(), "youtube")

    def test_apple_music_reply_is_honest(self):
        with mock.patch.object(server.media_mod, "play_app", side_effect=[None, None, True]), \
                mock.patch.object(server, "_open_apple_music") as opened, mock.patch.object(server.time, "sleep"):
            self.assertEqual(server._apple_music(), "Opened Apple Music and started playing.")
        opened.assert_called_once()
        with mock.patch.object(server.media_mod, "play_app", return_value=None), \
                mock.patch.object(server, "_open_apple_music"), mock.patch.object(server.time, "sleep"), \
                mock.patch.object(server.time, "time", side_effect=[0, 0, 30, 30]):
            self.assertIn("press play there", server._apple_music())
        with mock.patch.object(server, "apple_music_installed", return_value=False), \
                mock.patch.object(server.webbrowser, "open") as browser:
            self.assertIn("Pick a result", server._apple_music("kesariya"))
        self.assertIn("music.apple.com/search?term=kesariya", browser.call_args[0][0])
        with mock.patch.object(server, "apple_music_installed", return_value=True), \
                mock.patch.object(server.os, "startfile", create=True) as start, \
                mock.patch.object(server.webbrowser, "open") as browser:
            server._apple_music("kesariya")
        self.assertTrue(start.call_args[0][0].startswith("musics://music.apple.com/search?term=kesariya"))
        browser.assert_not_called()

    def test_ai_tool_no_longer_claims_spotify(self):
        with mock.patch.object(server, "music_app", return_value="apple_music"), \
                mock.patch.object(server, "_apple_music", return_value="Playing Apple Music."):
            self.assertEqual(server._run_tool_call("play_music", {"query": ""}), "Playing Apple Music.")

    def test_play_some_music_reaches_the_music_command(self):
        with mock.patch.object(server, "music_app", return_value="apple_music"), \
                mock.patch.object(server, "_apple_music", return_value="Playing Apple Music.") as apple:
            self.assertEqual(server.handle_local("play some music"), (True, "Playing Apple Music."))
        apple.assert_called_once_with(None)


class Location(unittest.TestCase):
    def test_reads_windows_answers(self):
        ok = lp.parse("OK:19.0761,72.8775,107,WiFi")
        self.assertEqual((ok["latitude"], ok["accuracy_m"], ok["source"]), (19.0761, 107, "WiFi"))
        self.assertIn("Privacy & security > Location", lp.parse("ACCESS:Denied")["reason"])
        self.assertFalse(lp.parse("TIMEOUT")["ok"])
        self.assertFalse(lp.parse("")["ok"])

    def test_off_means_no_lookup_at_all(self):
        with mock.patch.object(server.config, "USE_DEVICE_LOCATION", False, create=True), \
                mock.patch.object(lp.subprocess, "run", side_effect=AssertionError("asked Windows")), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertFalse(lp.refresh()["ok"])

    def test_on_sets_the_weather_coordinates_and_never_uses_ip(self):
        out = subprocess.CompletedProcess([], 0, stdout="OK:12.5,77.5,50,WiFi\n")
        with mock.patch.object(server.config, "USE_DEVICE_LOCATION", True, create=True), \
                mock.patch.object(server.config, "LATITUDE", None, create=True), \
                mock.patch.object(server.config, "LONGITUDE", None, create=True), \
                mock.patch.object(lp.os, "name", "nt"), \
                mock.patch.object(lp.subprocess, "run", return_value=out), \
                mock.patch.object(lp, "place_name", return_value=None):
            lp._last.clear()
            fix = lp.refresh(force=True)
            self.assertTrue(fix["ok"])
            self.assertEqual((server.config.LATITUDE, server.config.LONGITUDE), (12.5, 77.5))
        source = (ROOT / "app" / "core" / "location_provider.py").read_text(encoding="utf-8")
        self.assertNotIn("ipapi", source)
        self.assertNotIn("ipinfo", source)


class MorningBriefing(unittest.TestCase):
    def setUp(self):
        self.state = {}
        p1 = mock.patch.object(briefing, "due_today",
                               side_effect=lambda now=None, state=None: self.state.get("day") != briefing._day(now or datetime.now()))
        p2 = mock.patch.object(briefing, "mark_spoken",
                               side_effect=lambda now=None: self.state.update(day=briefing._day(now or datetime.now())))
        p3 = mock.patch.object(briefing, "morning_text", return_value="Good morning. No open tasks.")
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)

    def test_speaks_once_a_day_when_you_are_there(self):
        said = []
        now = lambda: datetime(2026, 11, 15, 8, 30)
        self.assertTrue(briefing.run_day_start(said.append, lambda: True, lambda: 5, now=now))
        self.assertFalse(briefing.run_day_start(said.append, lambda: True, lambda: 5, now=now))
        self.assertEqual(said, ["Good morning. No open tasks."])

    def test_waits_for_you_then_gives_up(self):
        said, sleeps = [], []
        self.assertFalse(briefing.run_day_start(said.append, lambda: True, lambda: 10_000,
                                                sleep=sleeps.append, now=lambda: datetime(2026, 11, 15, 8)))
        self.assertEqual(said, [])
        self.assertEqual(sum(sleeps), briefing.WAIT_FOR_YOU_SECONDS)

    def test_off_means_silent(self):
        said = []
        self.assertFalse(briefing.run_day_start(said.append, lambda: False, lambda: 0))
        self.assertEqual(said, [])

    def test_late_night_still_counts_as_yesterday(self):
        self.assertEqual(briefing._day(datetime(2026, 11, 15, 2, 0)), "2026-11-14")
        self.assertEqual(briefing._day(datetime(2026, 11, 15, 6, 0)), "2026-11-15")

    def test_weather_is_in_the_default_briefing(self):
        self.assertIn("weather", briefing.DEFAULT_SECTIONS)


class Settings(unittest.TestCase):
    def test_screens_and_settings(self):
        import routes_settings
        import settings_schema
        sent = routes_settings.get_settings({})[0]["settings"]
        for key in ("MUSIC_APP", "USE_DEVICE_LOCATION", "BRIEFING_ON_START", "AUTO_START"):
            self.assertIn(key, sent)
            self.assertIn(key, settings_schema.SCHEMA)
        startup = (ROOT / "app" / "main_app.py").read_text(encoding="utf-8")
        self.assertNotIn('if getattr(config, "AUTO_START", True) and not is_store', startup)


if __name__ == "__main__":
    unittest.main()
