"""
KALKI v1.0.4 PRO — Wake Word Listener
Always-on system mic. Captures wake word, then the follow-up command.
NEVER calls AI itself — POSTs to /api/wake (greeting/Chrome) or /api/chat
(voice command). The browser tab is purely a display.
"""

import os
import re
import sys
import time
import json
import urllib.request
from datetime import datetime

import runtime_security

from runtime_paths import prepare_runtime

_runtime = prepare_runtime()
runtime_security.TOKEN_PATH = os.path.join(_runtime.user_data_dir, "data", "api_token.txt")

BASE_DIR = _runtime.app_root
ENTRY_DIR = _runtime.entry_dir

import config
import settings_schema

settings_schema.repair_config(config)

is_store = os.path.exists(os.path.join(BASE_DIR, "store_build.txt"))
_data_dir = os.path.join(_runtime.user_data_dir, "data") if (is_store or sys.platform != "win32") else os.path.join(BASE_DIR, "data")
LOG_PATH = os.path.join(_data_dir, "listener.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


try:
    import speech_recognition as sr
except Exception as e:
    log(f"speech_recognition import failed: {e}")
    sys.exit(1)


SERVER     = f"http://localhost:{config.PORT}"
STOP_WORDS = ["stop", "stop talking", "shut up", "be quiet", "silence",
              "quiet", "shush", "cancel"]
WAKE_WORDS = [w.lower() for w in config.WAKE_WORDS]

# Common Google STT mishearings of "Kalki".
# NOTE: only Kalki-like tokens that are whole words (matched with \b), so they
# never fire inside ordinary speech. Avoid bare substrings like "cal".
WAKE_FUZZY = [
    "kalki", "kalka", "kalkee", "kalky", "kal ki", "calki", "kalgi", "khalki",
    "hey kalki", "ok kalki", "hi kalki", "hello kalki", "ykal ki", "calkey",
    "kalkie", "calkie", "call key", "colky", "colkey", "calky", "hawkey", "hockey",
    "cal key", "calkee"
]


def _post(endpoint, body=None, timeout=15):
    try:
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"{SERVER}{endpoint}",
            data=data,
            headers={
                "Content-Type": "application/json",
                runtime_security.TOKEN_HEADER: runtime_security.get_api_token(),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        log(f"POST {endpoint} failed: {e}")
        return None


def post_wake(cmd_text=""):
    log(f"WAKE -> '{cmd_text}'")
    _post("/api/wake", {"cmd": cmd_text or ""})


def post_chat_voice(text):
    """Send a voice-captured command. source=voice so UI renders it."""
    log(f"CHAT(voice) -> '{text}'")
    _post(
        "/api/chat",
        {"messages": [{"role": "user", "content": text}], "source": "voice"},
        timeout=45,
    )

def post_clipboard_response(phrase):
    log(f"CLIPBOARD RESPONSE -> '{phrase}'")
    _post("/api/clipboard_response", {"phrase": phrase})


def post_stop():
    log("STOP")
    _post("/api/stop")


LAST_STATUS = {"speaking": False, "listenerPaused": False}
_last_speaking_start = 0

def _status():
    global LAST_STATUS
    try:
        request = urllib.request.Request(
            f"{SERVER}/api/status?client=listener",
            headers={runtime_security.TOKEN_HEADER: runtime_security.get_api_token()},
        )
        with urllib.request.urlopen(request, timeout=2) as r:
            data = json.loads(r.read())
            if isinstance(data, dict):
                LAST_STATUS = data
            return LAST_STATUS
    except Exception:
        return LAST_STATUS


def is_speaking():
    return _status().get("speaking", False)


def is_paused():
    return _status().get("listenerPaused", False)


def get_mute_decision():
    """Single fetch, single decision. Prevents permanent speaking locks."""
    global _last_speaking_start
    st = _status()
    is_speaking = st.get("speaking", False)
    
    # Watchdog: If speaking for > 30 seconds continuously, assume stuck and force false.
    if is_speaking:
        if _last_speaking_start == 0:
            _last_speaking_start = time.time()
        elif time.time() - _last_speaking_start > 30:
            is_speaking = False
    else:
        _last_speaking_start = 0
        
    return bool(st.get("listenerPaused", False) or is_speaking)


def post_mic_state(muted: bool):
    """Tell the server what the listener is actually doing, so the HUD
    reflects ground truth instead of guessing independently."""
    try:
        data = json.dumps({"muted": muted}).encode("utf-8")
        req = urllib.request.Request(
            SERVER + "/api/listener_state", data=data,
            headers={
                "Content-Type": "application/json",
                runtime_security.TOKEN_HEADER: runtime_security.get_api_token(),
            }, method="POST"
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # best-effort - if this fails, the HUD falls back to its old guess


def server_alive():
    try:
        request = urllib.request.Request(
            f"{SERVER}/api/health",
            headers={runtime_security.TOKEN_HEADER: runtime_security.get_api_token()},
        )
        urllib.request.urlopen(request, timeout=2).read()
        return True
    except Exception:
        return False


def wait_for_server():
    for _ in range(60):
        if server_alive():
            return True
        time.sleep(1)
    return server_alive()


def _word_match(needle, haystack):
    """Whole-word match so 'kalki' never fires inside 'atomic'/'custom'."""
    return re.search(r"\b" + re.escape(needle) + r"\b", haystack) is not None


def contains_wake(phrase):
    """Whether the phrase calls KALKI. Uses wake_detect, which knows how speech services
    mishear the name and never fires on everyday words like "hockey"."""
    level, _, confirm = wake_detect.classify(phrase)
    return bool(level) and not confirm


def contains_stop(phrase):
    low = phrase.lower().strip()
    if low in STOP_WORDS:
        return True
    return any(low == s or low.startswith(s + " ") for s in STOP_WORDS)


def extract_inline(phrase):
    """The command after the name, or "" when there isn't one."""
    return wake_detect.classify(phrase)[1]


def listen_once(recognizer, mic, phrase_time_limit=4, timeout=None):
    try:
        with mic as source:
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        lang = getattr(config, "STT_LANGUAGE", "en-US")
        return recognizer.recognize_google(audio, language=lang)
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        log(f"Google STT error: {e}")
        time.sleep(1)
        return None


def wait_until_silent(max_wait=4.0):
    """Block while KALKI is speaking so its own voice doesn't get transcribed."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if not is_speaking():
            time.sleep(0.12)
            return
        time.sleep(0.18)


def pick_input_device():
    """Choose the STT mic. Avoids the Bluetooth headset so it stays in
    high-quality A2DP output mode instead of dropping to muffled HFP/HSP
    every time the wake-word listener opens the mic.

    Order: explicit config.STT_INPUT_DEVICE substring  ->  a built-in/internal
    mic  ->  any non-Bluetooth input  ->  system default (None).
    """
    try:
        names = sr.Microphone.list_microphone_names()
    except Exception as e:
        log(f"could not list mics: {e}")
        return None
    if not names:
        return None

    want = (getattr(config, "STT_INPUT_DEVICE", "") or "").strip().lower()
    avoid_bt = getattr(config, "STT_AVOID_BLUETOOTH", True)

    # Bluetooth / hands-free profiles to avoid (they force muffled HFP).
    BT_HINTS = ("bluetooth", "hands-free", "handsfree", "headset", "airpods",
                "wireless", "hfp", "hsp", "bt audio")
    # Mappers / outputs / loopbacks that follow the system default — skip so we
    # don't accidentally route through the BT headset again.
    SKIP_HINTS = BT_HINTS + ("sound mapper", "primary sound", "stereo mix",
                             "what u hear", "what you hear", "wave speaker",
                             "mirroring", "speaker", "output")
    # Real built-in microphones.
    GOOD_HINTS = ("microphone array", "built-in", "internal", "realtek")

    # 1) explicit choice from config
    if want:
        for i, n in enumerate(names):
            if n and want in n.lower():
                log(f"STT mic (config match): [{i}] {n}")
                return i

    # 2) a physical built-in mic that is NOT bluetooth / not a mapper
    for i, n in enumerate(names):
        low = (n or "").lower()
        if avoid_bt and any(b in low for b in SKIP_HINTS):
            continue
        if any(g in low for g in GOOD_HINTS):
            log(f"STT mic (built-in): [{i}] {n}")
            return i

    # 3) any input that names itself a microphone and isn't bluetooth
    if avoid_bt:
        for i, n in enumerate(names):
            low = (n or "").lower()
            if "mic" in low and not any(b in low for b in SKIP_HINTS):
                log(f"STT mic (non-BT mic): [{i}] {n}")
                return i

    log("STT mic: using system default")
    return None


VOSK_MODEL_PATH = os.path.join(BASE_DIR,
    getattr(config, "VOSK_MODEL_PATH", os.path.join("data", "vosk-model")))


def vosk_available():
    # Vosk's small offline model can't recognize the out-of-vocabulary name
    # "kalki" — it transcribes garbage and the wake word never fires. So Vosk
    # is OPT-IN only (STT_ENGINE="vosk"); "auto"/"google" use reliable cloud STT.
    if (getattr(config, "STT_ENGINE", "google") or "google").lower() != "vosk":
        return False
    try:
        import vosk  # noqa
    except Exception:
        return False
    return os.path.isdir(VOSK_MODEL_PATH)


def run_vosk(dev_index):
    """Offline wake-word loop using Vosk — no network, low CPU, low heat."""
    import json as _json
    import vosk
    import pyaudio

    vosk.SetLogLevel(-1)
    try:
        model = vosk.Model(VOSK_MODEL_PATH)
    except Exception as e:
        log(f"vosk model load failed: {e}; falling back to Google")
        return False

    RATE, CHUNK = 16000, 4000
    pa = pyaudio.PyAudio()

    def open_stream():
        kw = dict(format=pyaudio.paInt16, channels=1, rate=RATE,
                  input=True, frames_per_buffer=CHUNK)
        if dev_index is not None:
            kw["input_device_index"] = dev_index
        return pa.open(**kw)

    def close_vosk_stream():
        nonlocal stream
        if stream is not None:
            try:
                stream.stop_stream()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
            stream = None

    try:
        stream = open_stream()
    except Exception as e:
        log(f"vosk stream open failed: {e}; falling back to Google")
        pa.terminate()
        return False

    rec = vosk.KaldiRecognizer(model, RATE)
    log(f"listening via VOSK (offline). wake words: {WAKE_WORDS}")

    def next_final(timeout):
        """Read until a non-empty final result or timeout. Returns text."""
        end = time.time() + timeout
        while time.time() < end:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                txt = _json.loads(rec.Result()).get("text", "").strip()
                if txt:
                    return txt
        return ""

    paused_logged = 0
    while True:
        try:
            # Release the mic while paused or speaking so other apps can use it.
            if get_mute_decision():
                if stream is not None:
                    try:
                        stream.stop_stream()
                    except Exception:
                        pass
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = None
                if time.time() > paused_logged:
                    log("listener paused — mic released")
                    paused_logged = time.time() + 30
                time.sleep(1.5)
                continue

            if stream is None:
                try:
                    stream = open_stream()
                    rec = vosk.KaldiRecognizer(model, RATE)
                    log("listener resumed — mic re-opened")
                except Exception as e:
                    log(f"failed to reopen stream: {e}")
                    time.sleep(2)
                    continue

            if not stream.is_active():
                try:
                    stream.start_stream()
                except Exception:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = open_stream()
                    rec = vosk.KaldiRecognizer(model, RATE)

            data = stream.read(CHUNK, exception_on_overflow=False)

            # Note: the stream is completely closed above when is_speaking() is true,
            # so we don't need to manually drain the buffer here anymore.

            if not rec.AcceptWaveform(data):
                continue
            phrase = _json.loads(rec.Result()).get("text", "").strip()
            if not phrase:
                continue
            log(f"heard: {phrase}")

            if contains_stop(phrase):
                post_stop(); continue

            # If user clicked Wake / Voice Mode in UI within 8 seconds, phrase is the command directly
            wake_act = (time.time() - LAST_STATUS.get("wakeRequestedAt", 0) < 8.0) or LAST_STATUS.get("wakeRequested")

            if not contains_wake(phrase) and not wake_act:
                continue

            inline = extract_inline(phrase) if contains_wake(phrase) else phrase
            LAST_STATUS["wakeRequested"] = False
            LAST_STATUS["wakeRequestedAt"] = 0
            if inline:
                close_vosk_stream()
                post_chat_voice(inline)
                wait_until_silent(max_wait=12.0)
                continue

            # wake only → greet, then capture the follow-up command
            close_vosk_stream()
            post_wake("")
            wait_until_silent(max_wait=4.0)
            
            # Reopen stream to listen for follow-up command
            try:
                stream = open_stream()
                rec = vosk.KaldiRecognizer(model, RATE)
            except Exception as e:
                log(f"failed to reopen stream for follow-up: {e}")
                continue
                
            follow = next_final(timeout=6)
            close_vosk_stream()
            if not follow:
                log("no follow-up command within window")
                continue
            log(f"follow-up: {follow}")
            if contains_stop(follow):
                post_stop(); continue
            post_chat_voice(follow)
            wait_until_silent(max_wait=12.0)

        except KeyboardInterrupt:
            log("listener stopped by user")
            return True
        except Exception as e:
            log(f"vosk loop error: {e}")
            time.sleep(1)


def _listen_once():
    """Capture a single command after UI button press in push-to-talk mode."""
    if sr is None:
        log("push-to-talk: speech_recognition is not available")
        return
    try:
        log("push-to-talk: opening mic for single command...")
        dev_index = pick_input_device()
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        try:
            mic = sr.Microphone(device_index=dev_index)
        except Exception:
            mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            log("push-to-talk: listening...")
            audio = recognizer.listen(source, timeout=6.0, phrase_time_limit=8.0)
        lang = getattr(config, "STT_LANGUAGE", "en-US")
        try:
            heard = recognizer.recognize_google(audio, language=lang).strip()
        except Exception:
            heard = ""
        phrase = command_text(heard, audio)  # Whisper when a key is set: word for word, Hindi too
        log(f"push-to-talk heard: {phrase}")
        if phrase:
            if contains_stop(phrase):
                post_stop()
            else:
                inline = extract_inline(phrase) if contains_wake(phrase) else phrase
                post_chat_voice(inline)
                wait_until_silent(max_wait=12.0)
    except Exception as e:
        log(f"push-to-talk listen failed: {e}")


# ── Hands-free "Hey KALKI": two stages ────────────────────────────────────
# Stage 1 is Google's free recognizer on every phrase, checked by wake_detect (it knows
# how Google mishears the name). Stage 2 only runs when something sounds like the name:
# the same audio goes to KALKI's own /api/voice/transcribe (Groq or OpenAI Whisper when a
# key is set) to confirm doubtful matches and to get the command word for word.

import base64 as _b64
import wake_detect


def current_mode():
    """The listening mode from KALKI's settings, read live so a change applies at once."""
    st = LAST_STATUS if LAST_STATUS else _status()
    mode = str(st.get("listenMode") or getattr(config, "LISTEN_MODE", "always") or "always").lower()
    return "push" if mode == "push" else "always"


def transcribe_with_kalki(audio, prompt="KALKI"):
    """Accurate text for a phrase, via the server's Whisper. Returns (text, engine) or (None, None)."""
    try:
        wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
    except Exception as e:
        log(f"couldn't prepare audio for transcription: {e}")
        return None, None
    raw = _post("/api/voice/transcribe", {"audio": _b64.b64encode(wav).decode("ascii"), "prompt": prompt}, timeout=20)
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    if not data or not data.get("ok"):
        return None, None
    return str(data.get("text") or "").strip(), data.get("engine")


NOT_FOR_KALKI = object()


def decide(text, audio):
    """What to do with one heard phrase: NOT_FOR_KALKI, "" (wake only) or the command."""
    level, command, confirm = wake_detect.classify(text)
    if not level:
        return NOT_FOR_KALKI
    if not (confirm or level == "maybe" or command):
        return ""  # a clear "Hey KALKI" on its own: no need to ask Whisper
    better, engine = transcribe_with_kalki(audio, prompt="Hey KALKI.")
    if better is not None and engine and engine != "google":
        w_level, w_command, _ = wake_detect.classify(better)
        if w_level == "wake":
            log(f"confirmed by {engine}: {better}")
            return w_command
        if confirm or level == "maybe":
            log(f"not for KALKI ({engine} heard: {better})")
            return NOT_FOR_KALKI
    if confirm:
        return NOT_FOR_KALKI  # doubtful and nothing accurate to confirm it with
    return command


def command_text(text, audio):
    """The most accurate text for a command phrase: Whisper when available, else what Google heard."""
    better, engine = transcribe_with_kalki(audio)
    if better and engine and engine != "google":
        return better
    return text


def run_push():
    """Push-to-talk: the microphone is off until the mic button is pressed. Returns when
    the setting changes to hands-free."""
    log("push-to-talk mode: the microphone is off until you press the mic button. "
        "Turn on \"Hey KALKI\" in Settings > Voice for hands-free.")
    while True:
        st = _status()
        if current_mode() != "push":
            return
        wake_act = st.get("wakeRequested") or (time.time() - st.get("wakeRequestedAt", 0) < 5.0)
        if wake_act:
            LAST_STATUS["wakeRequested"] = False
            LAST_STATUS["wakeRequestedAt"] = 0
            _listen_once()
        time.sleep(2)


def run_continuous():
    """Hands-free: listen for "Hey KALKI" all the time. Returns when the setting changes to push."""
    log("hands-free mode: listening for \"Hey KALKI\"")
    dev_index = pick_input_device()

    # Offline Vosk, only when chosen (STT_ENGINE=vosk) and its model is installed.
    if vosk_available():
        try:
            if run_vosk(dev_index):
                return
        except Exception as e:
            log(f"vosk engine crashed: {e}; using Google STT")

    if sr is None:
        log("speech_recognition isn't available, so hands-free listening can't start")
        time.sleep(30)
        return
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.7
    try:
        mic = sr.Microphone(device_index=dev_index)
    except Exception as e:
        log(f"mic open failed on device {dev_index}: {e}; falling back to default")
        try:
            mic = sr.Microphone()
        except Exception as e2:
            log(f"default mic open failed: {e2}")
            time.sleep(15)
            return

    with mic as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=1.2)
        except Exception as e:
            log(f"ambient calibration failed: {e}")

    import queue as _queue
    import threading as _threading
    phrases = _queue.Queue()
    _mic_muted = _threading.Event()  # set while KALKI speaks or the listener is paused
    _last_callback_time = [time.time()]

    def _bg_callback(rec, audio):
        _last_callback_time[0] = time.time()
        if _mic_muted.is_set():
            return
        try:
            txt = rec.recognize_google(audio, language=getattr(config, "STT_LANGUAGE", "en-IN"))
        except Exception:
            return
        if _mic_muted.is_set():  # KALKI may have started speaking during the round trip
            return
        if txt:
            phrases.put((txt, audio))

    def _drain():
        try:
            while True:
                phrases.get_nowait()
        except _queue.Empty:
            pass

    try:
        stop_bg = recognizer.listen_in_background(mic, _bg_callback, phrase_time_limit=8)
    except Exception as e:
        log(f"listen_in_background failed: {e}")
        time.sleep(15)
        return
    log(f"listening (hands-free, wake words: {WAKE_WORDS})")

    def _finish():
        try:
            stop_bg(wait_for_stop=False)
        except Exception:
            pass

    last_mode_check = time.time()
    last_heartbeat = 0
    while True:
        try:
            now = time.time()
            if now - last_heartbeat > 60:
                last_heartbeat = now
                log(f"heartbeat OK (last audio {now - _last_callback_time[0]:.0f}s ago, muted={_mic_muted.is_set()})")
            if now - last_mode_check > 3:
                last_mode_check = now
                if current_mode() != "always":
                    log("switching to push-to-talk")
                    _finish()
                    return

            if get_mute_decision():
                if not _mic_muted.is_set():
                    _mic_muted.set()
                    post_mic_state(True)
                    _drain()
                time.sleep(0.3)
                continue
            if _mic_muted.is_set():
                _mic_muted.clear()
                post_mic_state(False)
                _drain()

            try:
                phrase, audio = phrases.get(timeout=1.0)
            except _queue.Empty:
                continue
            log(f"heard: {phrase}")

            if contains_stop(phrase):
                post_stop()
                continue
            st = _status()
            if st.get("clipboardPromptPending"):
                post_clipboard_response(phrase)
                wait_until_silent(max_wait=12.0)
                continue

            # The mic button in the app counts as "Hey KALKI" for the next phrase.
            if (time.time() - st.get("wakeRequestedAt", 0) < 8.0) or st.get("wakeRequested"):
                LAST_STATUS["wakeRequested"] = False
                LAST_STATUS["wakeRequestedAt"] = 0
                post_chat_voice(command_text(phrase, audio))
                wait_until_silent(max_wait=12.0)
                _drain()
                continue

            command = decide(phrase, audio)
            if command is NOT_FOR_KALKI:
                continue
            if command:
                post_chat_voice(command)
                wait_until_silent(max_wait=12.0)
                _drain()
                continue

            # "Hey KALKI" on its own: answer, then take the next phrase as the command.
            post_wake("")
            wait_until_silent(max_wait=4.0)
            _drain()
            log("waiting for the command...")
            try:
                follow, follow_audio = phrases.get(timeout=7.0)
            except _queue.Empty:
                log("no command within 7 seconds")
                continue
            follow = command_text(follow, follow_audio)
            log(f"command: {follow}")
            if contains_stop(follow):
                post_stop()
            else:
                post_chat_voice(follow)
                wait_until_silent(max_wait=12.0)
            _drain()

        except KeyboardInterrupt:
            _finish()
            raise
        except Exception as e:
            log(f"loop error: {e}")
            time.sleep(1)


def main():
    log("listener starting")
    if not wait_for_server():
        log("server never came up; listener exiting")
        return
    _status()
    try:
        while True:
            if current_mode() == "push":
                run_push()
            else:
                run_continuous()
    except KeyboardInterrupt:
        log("listener stopped by user")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL CRASH: {e}")
        import traceback
        log(traceback.format_exc())
