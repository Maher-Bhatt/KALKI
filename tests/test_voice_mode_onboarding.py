"""Voice mode's server side (speech to text, text to speech) and the in-app onboarding."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import base64
import io
import os
import sys
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import server  # noqa: E402
import voice_turn  # noqa: E402
import routes_setup  # noqa: E402
import settings_schema  # noqa: E402


def wav_bytes(seconds=0.2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * int(16000 * seconds))
    return buf.getvalue()


class Transcribe(unittest.TestCase):
    def test_bad_input_is_refused(self):
        self.assertEqual(voice_turn.transcribe_route({"audio": "%%%"})[1], 400)
        self.assertEqual(voice_turn.transcribe_route({"audio": base64.b64encode(b"not a wav").decode()})[1], 400)
        self.assertEqual(voice_turn.transcribe_route({})[1], 400)

    def test_groq_first_then_the_next_engine(self):
        wav = wav_bytes()
        with mock.patch.object(server.config, "GROQ_API_KEY", "gsk_x", create=True), \
                mock.patch.object(server.config, "OPENAI_API_KEY", "", create=True), \
                mock.patch.object(voice_turn, "_whisper", return_value="hello there") as whisper:
            r = voice_turn.transcribe(wav)
        self.assertEqual((r["text"], r["engine"]), ("hello there", "groq-whisper"))
        self.assertIn("groq.com", whisper.call_args[0][0])
        with mock.patch.object(server.config, "GROQ_API_KEY", "gsk_x", create=True), \
                mock.patch.object(server.config, "OPENAI_API_KEY", "", create=True), \
                mock.patch.object(voice_turn, "_whisper", side_effect=OSError("down")), \
                mock.patch.object(voice_turn, "_google", return_value="fallback words"):
            r = voice_turn.transcribe(wav)
        self.assertEqual((r["text"], r["engine"]), ("fallback words", "google"))

    def test_all_engines_failing_says_so(self):
        with mock.patch.object(server.config, "GROQ_API_KEY", "", create=True), \
                mock.patch.object(server.config, "OPENAI_API_KEY", "", create=True), \
                mock.patch.object(voice_turn, "_google", side_effect=ImportError("no")):
            r = voice_turn.transcribe(wav_bytes())
        self.assertFalse(r["ok"])
        self.assertIn("google: not installed", r["error"])

    def test_multipart_has_the_file_and_model(self):
        body, ctype = voice_turn._multipart({"model": "m"}, "speech.wav", b"RIFFdata", "audio/wav")
        self.assertIn("multipart/form-data; boundary=", ctype)
        self.assertIn(b'name="model"\r\n\r\nm', body)
        self.assertIn(b'filename="speech.wav"', body)


class Speak(unittest.TestCase):
    def test_returns_audio_and_cleans_up(self):
        path = os.path.join(os.environ.get("TEMP", "."), "vt_test.mp3")
        with open(path, "wb") as f:
            f.write(b"ID3fake")
        with mock.patch.object(voice_turn, "_build_tts_file", lambda text: (path, "edge")):
            r = voice_turn.speech_audio("hello")
        self.assertEqual(base64.b64decode(r["audio"]), b"ID3fake")
        self.assertFalse(os.path.exists(path))

    def test_failure_lets_the_app_use_its_own_voice(self):
        with mock.patch.object(voice_turn, "_build_tts_file", side_effect=RuntimeError("No audio was received.")):
            self.assertFalse(voice_turn.speech_audio("hello")["ok"])
        self.assertEqual(voice_turn.speak_route({})[1], 400)


class ChatInVoiceMode(unittest.TestCase):
    def test_voice_mode_asks_for_short_spoken_replies(self):
        source = (ROOT / "app" / "server.py").read_text(encoding="utf-8")
        self.assertIn('if body.get("voiceMode"):', source)
        self.assertIn("voice_turn.VOICE_STYLE", source)
        page = (ROOT / "app" / "ui" / "features" / "voice.js").read_text(encoding="utf-8")
        self.assertIn("voiceMode: true", page)
        self.assertIn("s.interrupt()", page)  # barge-in


class Onboarding(unittest.TestCase):
    def setUp(self):
        path = routes_setup._marker_path()
        if os.path.exists(path):
            os.remove(path)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

    def test_marker_round_trip(self):
        self.assertFalse(routes_setup.setup_state({})[0]["complete"])
        routes_setup.setup_complete({})
        self.assertTrue(routes_setup.setup_state({})[0]["complete"])

    def test_telegram_can_be_saved(self):
        self.assertEqual(settings_schema.validate("TELEGRAM_USER_ID", "123456789"), "123456789")
        with self.assertRaises(settings_schema.SettingError):
            settings_schema.validate("TELEGRAM_USER_ID", "@me")
        self.assertEqual(settings_schema.validate("TELEGRAM_BOT_TOKEN", "123:abc"), "123:abc")

    def test_app_no_longer_blocks_on_the_old_wizard(self):
        source = (ROOT / "app" / "main_app.py").read_text(encoding="utf-8")
        self.assertIn('KALKI_CLASSIC_WIZARD', source)
        self.assertNotIn("Setup was cancelled or incomplete. Exiting KALKI.", source)


if __name__ == "__main__":
    unittest.main()
