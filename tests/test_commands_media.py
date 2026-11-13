"""Music, WhatsApp and YouTube download quick commands."""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP))

import server  # noqa: E402
import commands_media as cm  # noqa: E402
import media_mod  # noqa: E402


def deps(linked=False, playing="Nothing playing"):
    spotify = mock.Mock()
    spotify.is_configured.return_value = linked
    for name in ("pause", "play", "retry", "next_track", "prev_track", "now_playing", "shuffle_on", "set_volume", "play_lofi"):
        getattr(spotify, name).return_value = f"spotify {name}"
    media = mock.Mock(spec=["pause", "play", "next_track", "prev_track", "now_playing", "now_playing_json"])
    media.pause.return_value = "Paused."
    media.play.return_value = "Played."
    media.next_track.return_value = "Skipped to next track."
    media.prev_track.return_value = "Skipped to previous track."
    media.now_playing.return_value = playing
    media.now_playing_json.return_value = {"title": playing}
    return {"spotify": spotify, "media": media, "open_url": mock.Mock(), "set_volume": mock.Mock(return_value=True),
            "open_apple_music": mock.Mock()}


class Music(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(cm.config, "OWNER_TITLE", "", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_media_function_used_exists(self):
        source = (APP / "commands_media.py").read_text(encoding="utf-8")
        for name in set(re.findall(r"media\.(\w+)", source)):
            self.assertTrue(hasattr(media_mod, name), f"media_mod.{name} doesn't exist")

    def test_without_spotify_controls_reach_windows(self):
        d = deps()
        self.assertEqual(cm.music_command("pause", d), (True, "Paused."))
        self.assertEqual(cm.music_command("next", d), (True, "Skipped to next track."))
        self.assertEqual(cm.music_command("previous song", d), (True, "Skipped to previous track."))
        d["media"].pause.assert_called_once()

    def test_a_failure_is_reported_not_hidden(self):
        d = deps()
        d["media"].pause.side_effect = OSError("no media session")
        handled, reply = cm.music_command("pause", d)
        self.assertIn("couldn't pause", reply)

    def test_with_spotify_it_uses_spotify(self):
        d = deps(linked=True)
        self.assertEqual(cm.music_command("play lo-fi", d), (True, "spotify play_lofi"))
        self.assertEqual(cm.music_command("play daft punk", d)[1], "spotify play")
        d["spotify"].play.assert_called_with("daft punk")

    def test_opening_a_page_is_not_called_playing(self):
        d = deps()
        reply = cm.music_command("play daft punk", d)[1]
        self.assertIn("Opened a YouTube search", reply)
        self.assertIn("music.youtube.com", cm.music_command("resume", d)[1] + str(d["open_url"].call_args))

    def test_resume_plays_what_was_paused(self):
        d = deps(playing="Song A")
        self.assertEqual(cm.music_command("resume", d), (True, "Played."))
        d["open_url"].assert_not_called()

    def test_shuffle_without_spotify_says_so(self):
        self.assertIn("needs Spotify", cm.music_command("shuffle", deps())[1])

    def test_volume_without_spotify_gives_a_reply(self):
        d = deps()
        self.assertEqual(cm.music_command("music volume 60", d), (True, "Volume set to 60%."))
        d["set_volume"].return_value = False
        self.assertEqual(cm.music_command("music volume 60", d), (True, "I couldn't change the volume."))

    def test_retry_is_not_music(self):
        for text in ("retry", "try again", "again", "retry that"):
            self.assertIsNone(cm.music_command(text, deps()), text)

    def test_apple_music_only_when_asked(self):
        d = deps()
        self.assertIsNone(cm.music_command("how much is apple music a month", d))
        self.assertEqual(cm.music_command("open apple music", d)[0], True)
        d["open_apple_music"].assert_called_once()


class WhatsAppAndDownloads(unittest.TestCase):
    def test_whatsapp_waits_for_approval_with_the_exact_message(self):
        queued = {}
        result = cm.whatsapp_command("send whatsapp to mom saying see you at 5", "send whatsapp to Mom saying See you at 5",
                                     mock.Mock(), lambda text, fn: queued.setdefault("text", text) and (True, "waiting"))
        self.assertEqual(result, (True, "waiting"))
        self.assertIn("See you at 5", queued["text"])

    def test_contacts(self):
        wa = mock.Mock()
        wa.list_contacts.return_value = {"mom": "+91"}
        self.assertEqual(cm.whatsapp_command("my contacts", "my contacts", wa, None), (True, "1 contacts: mom"))

    def test_download_says_where_it_saved(self):
        yt = mock.Mock()
        yt.download.return_value = {"ok": True, "path": "C:/Downloads/song.mp3"}
        reply = cm.youtube_command("download song from https://youtu.be/x", "download song from https://youtu.be/x", yt, lambda s: None)
        self.assertIn("C:/Downloads/song.mp3", reply[1])
        yt.download.assert_called_with("https://youtu.be/x", audio_only=True)


class Routing(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(cm.config, "OWNER_TITLE", "", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_handle_local_routes_music(self):
        with mock.patch.object(server.spotify_mod, "is_configured", return_value=False), \
                mock.patch.object(server.media_mod, "pause", return_value="Paused."):
            self.assertEqual(server.handle_local("pause"), (True, "Paused."))


if __name__ == "__main__":
    unittest.main()
