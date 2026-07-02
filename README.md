<div align="center">
  <img src="screenshots/kalki-hud.png" alt="KALKI HUD" width="100%">

  <h1><img src="assets/kalki_logo.png" width="48" style="vertical-align: middle;"> KALKI</h1>

  <h2>A Windows-native, voice-first AI assistant inspired by J.A.R.V.I.S.</h2>

  <p>
    <img src="https://img.shields.io/badge/release-v1.0.0_PRO-6c757d?style=flat-square" alt="release">
    <img src="https://img.shields.io/badge/platform-Windows_10%2B-8a8276?style=flat-square" alt="platform">
    <img src="https://img.shields.io/badge/brain-Groq_%2B_LLaMA-c4a065?style=flat-square" alt="tech">
  </p>

  <h3><a href="https://github.com/Maher-Bhatt/KALKI/releases">Download the latest EXE</a></h3>
</div>

---

## What is KALKI?

KALKI is an autonomous personal assistant built from scratch in Python and a single HTML file. Wakes on **"Hey KALKI"**, speaks in a neural voice, and manages your life through a sleek sci-fi HUD. The HUD is **state-reactive** — the interface retunes as KALKI idles, listens, thinks, and speaks.

## Features

- **Voice-first, always-on:** Say "Hey KALKI" from anywhere, even with browser tab closed. Cloud STT with optional offline Vosk engine.
- **Smart model routing:** Fast 8B for casual turns, LLaMA-3.3-70B for code/cyber. Offline fallback to local Ollama.
- **Cybersecurity Toolkit:** Web vulnerability scanner, Shodan OSINT, CVE intel, Subdomain enumeration, Port scan.
- **Proactive Alerts:** KALKI interrupts you when urgent email arrives, GitHub has new notifications, or battery is low.
- **Integrated Control:** Lock PC, mute audio, empty recycle bin, open VS Code by voice.
- **Clipboard AI Coding:** Copy broken code, say *"Fix the code in my clipboard"* — KALKI fixes and pastes it back.
- **Personal Assistant:** Google Calendar events, Gmail reader, Tasks, Reminders, Password vault.
- **No build step:** Pure Python + one HTML file. Clone and run.

## Install

1. Download `KALKI_Setup.exe` from the [Releases](https://github.com/Maher-Bhatt/KALKI/releases) page.
2. Open it and follow the Setup Wizard to install.
3. Windows 10/11 required. A free Groq API key is required for the cloud AI brain.

## Showcase

*(Please upload new screenshots to the screenshots/ folder to display them here)*

<br>

<div align="center">
  <img src="screenshots/hud_tactical.png" width="48%" alt="Tactical Ops">
  <img src="screenshots/hud_models.png" width="48%" alt="Neural Models">
</div>

<br>

<div align="center">
  <img src="screenshots/settings_general.png" width="48%" alt="General Settings">
  <img src="screenshots/settings_integrations.png" width="48%" alt="Integrations">
</div>

## Tech stack

| Layer | Tech |
|---|---|
| UI / HUD | Vanilla JS + Canvas2D, single `index.html`, no build step |
| Server | Python 3.11 stdlib (`http.server` + `ThreadingMixIn`) - no Flask |
| LLM | Groq API (`llama-3.3-70b-versatile` / `llama-4-scout` vision) |
| TTS | Microsoft edge-tts + pygame mixer (non-blocking) |
| STT | SpeechRecognition + PyAudio + Google STT |
| Integrations | google-api-python-client, imaplib, spotipy, pywhatkit |
| System | psutil, pycaw, pillow, comtypes, ctypes, win32crypt (DPAPI) |
| OSINT | Shodan API, crt.sh, NVD API, hackertarget.com, GitHub REST API v3 |
