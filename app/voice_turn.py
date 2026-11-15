"""Voice mode's two server jobs: turn speech into text, and text into audio the app plays.

The app records you, notices when you stop, and sends a short WAV here. The words go to
the same chat as typing (with a "keep it short, this is spoken" note), and the reply comes
back here to become audio. Because the app plays it, it can stop the moment you talk.

Speech to text, in order of preference:
  1. Groq Whisper (whisper-large-v3-turbo), when a Groq key is set: fast, good with
     Hindi, English and Hinglish.
  2. OpenAI Whisper, when an OpenAI key is set.
  3. Google's free speech recognition (the same one the background listener uses).
"""

import base64
import io
import json
import os
import tempfile
import urllib.error
import urllib.request
import uuid
import wave
from typing import Any, Callable, Dict, Optional, Tuple

import config

Result = Tuple[Dict[str, Any], int]
MAX_AUDIO_BYTES = 12 * 1024 * 1024
VOICE_STYLE = ("This is a spoken conversation in KALKI's voice mode. Reply the way a person talks: "
               "usually one to three short sentences, no lists, no markdown, no code blocks unless asked. "
               "Ask a short follow-up only when it really helps.")

_build_tts_file: Optional[Callable[[str], Tuple[str, str]]] = None
_log: Callable[[str], None] = lambda m: None


def configure(build_tts_file: Callable[[str], Tuple[str, str]], log: Callable[[str], None]) -> None:
    global _build_tts_file, _log
    _build_tts_file, _log = build_tts_file, log


def _key(name: str) -> str:
    value = str(getattr(config, name, "") or "").strip()
    return "" if not value or value.upper().startswith(("PASTE_", "YOUR_")) else value


def _multipart(fields: Dict[str, str], filename: str, data: bytes, mime: str) -> Tuple[bytes, str]:
    boundary = "kalki" + uuid.uuid4().hex
    out = io.BytesIO()
    for name, value in fields.items():
        out.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    out.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
              f"Content-Type: {mime}\r\n\r\n".encode())
    out.write(data)
    out.write(f"\r\n--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


def _whisper(url: str, key: str, model: str, wav: bytes) -> str:
    fields = {"model": model, "response_format": "json", "temperature": "0"}
    body, ctype = _multipart(fields, "speech.wav", wav, "audio/wav")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": ctype,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KALKI"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return str(json.loads(r.read().decode("utf-8")).get("text", "")).strip()


def _google(wav: bytes) -> str:
    import speech_recognition as sr  # optional: also used by the background listener
    with wave.open(io.BytesIO(wav)) as w:
        audio = sr.AudioData(w.readframes(w.getnframes()), w.getframerate(), w.getsampwidth())
    try:
        return sr.Recognizer().recognize_google(audio, language=getattr(config, "STT_LANGUAGE", "en-IN") or "en-IN")
    except sr.UnknownValueError:
        return ""


def transcribe(wav: bytes) -> Dict[str, Any]:
    """Text for a short WAV recording, from the first engine that works."""
    tried = []
    engines = []
    if _key("GROQ_API_KEY"):
        engines.append(("groq-whisper", lambda: _whisper("https://api.groq.com/openai/v1/audio/transcriptions",
                                                         _key("GROQ_API_KEY"), "whisper-large-v3-turbo", wav)))
    if _key("OPENAI_API_KEY"):
        engines.append(("openai-whisper", lambda: _whisper("https://api.openai.com/v1/audio/transcriptions",
                                                           _key("OPENAI_API_KEY"), "whisper-1", wav)))
    engines.append(("google", lambda: _google(wav)))
    for name, run in engines:
        try:
            return {"ok": True, "text": run(), "engine": name}
        except ImportError:
            tried.append(f"{name}: not installed")
        except urllib.error.HTTPError as e:
            tried.append(f"{name}: HTTP {e.code}")
        except Exception as e:  # try the next engine
            tried.append(f"{name}: {e}")
    _log("voice transcription failed: " + "; ".join(tried))
    return {"ok": False, "error": "KALKI couldn't turn that into text (" + "; ".join(tried) + ")."}


def speech_audio(text: str) -> Dict[str, Any]:
    """MP3 of KALKI's voice saying `text`, for the app to play."""
    if not _build_tts_file:
        return {"ok": False, "error": "Speech isn't set up."}
    path = None
    try:
        path, provider = _build_tts_file(text)
        with open(path, "rb") as f:
            data = f.read()
        return {"ok": True, "audio": base64.b64encode(data).decode("ascii"), "mime": "audio/mpeg", "provider": provider}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


# ── Routes ────────────────────────────────────────────────────────────────

def transcribe_route(body: Dict[str, Any]) -> Result:
    try:
        wav = base64.b64decode(str(body.get("audio") or ""), validate=True)
    except (ValueError, TypeError):
        return {"ok": False, "error": "audio must be base64 WAV"}, 400
    if not wav:
        return {"ok": False, "error": "no audio"}, 400
    if len(wav) > MAX_AUDIO_BYTES:
        return {"ok": False, "error": "That recording is too long."}, 413
    if wav[:4] != b"RIFF":
        return {"ok": False, "error": "audio must be WAV"}, 400
    return transcribe(wav), 200


def speak_route(body: Dict[str, Any]) -> Result:
    text = str(body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text required"}, 400
    return speech_audio(text[:1500]), 200


POST_ROUTES = {"/api/voice/transcribe": transcribe_route, "/api/voice/speak": speak_route}
