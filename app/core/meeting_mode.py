import os
import threading
import wave
import json
import urllib.request
import speech_recognition as sr
from datetime import datetime

import config
import tasks as taskmod

_recording = False
_thread = None

AUDIO_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "meeting.wav")

def _record_loop():
    global _recording
    r = sr.Recognizer()
    
    # We will record in chunks and append to a raw bytes buffer
    audio_data = b""
    sample_rate = 16000
    sample_width = 2
    
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        print("[MEETING] Recording started...")
        while _recording:
            try:
                # Listen in short chunks so we can check _recording flag
                chunk = r.listen(source, timeout=1, phrase_time_limit=5)
                audio_data += chunk.get_raw_data()
                sample_rate = chunk.sample_rate
                sample_width = chunk.sample_width
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                print(f"[MEETING] Recording error: {e}")
                break
                
    print("[MEETING] Recording stopped. Processing...")
    
    if not audio_data:
        print("[MEETING] No audio captured.")
        return
        
    # Save to WAV
    os.makedirs(os.path.dirname(AUDIO_PATH), exist_ok=True)
    with wave.open(AUDIO_PATH, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
        
    _transcribe_and_summarize()

def _transcribe_and_summarize():
    if not getattr(config, "GROQ_API_KEY", ""):
        print("[MEETING] Missing Groq API Key.")
        return
        
    print("[MEETING] Uploading to Groq Whisper...")
    try:
        import requests
        
        with open(AUDIO_PATH, "rb") as f:
            files = {"file": ("meeting.wav", f, "audio/wav")}
            data = {"model": "whisper-large-v3"}
            headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
            
            res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", files=files, data=data, headers=headers)
            if res.status_code != 200:
                print(f"[MEETING] Whisper Error: {res.text}")
                return
                
            transcript = res.json().get("text", "")
            
        if not transcript.strip():
            print("[MEETING] Transcript empty.")
            return
            
        print("[MEETING] Generating Action Items...")
        prompt = f"Extract a concise bulleted list of Action Items and key decisions from this meeting transcript:\n\n{transcript}"
        
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.GROQ_API_KEY}"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            ans = json.loads(response.read().decode("utf-8"))
            action_items = ans["choices"][0]["message"]["content"]
            
        # Add the action items to tasks so the user sees them
        task_text = f"Meeting Action Items ({datetime.now().strftime('%Y-%m-%d %H:%M')}):\n{action_items}"
        taskmod.add_task(task_text)
        print("[MEETING] Action Items saved to tasks.")
        
    except Exception as e:
        print(f"[MEETING] Transcription failed: {e}")

def start_meeting():
    global _recording, _thread
    if _recording: return False
    _recording = True
    _thread = threading.Thread(target=_record_loop, daemon=True)
    _thread.start()
    return True

def stop_meeting():
    global _recording
    if not _recording: return False
    _recording = False
    return True
