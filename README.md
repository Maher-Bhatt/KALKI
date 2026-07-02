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

## System Requirements

KALKI dynamically scales depending on whether you rely on Cloud AI (Groq API) or Local Offline LLMs (Ollama).

### Minimum Requirements (Cloud AI Mode)
- **OS:** Windows 10 or Windows 11 (64-bit)
- **CPU:** Intel Core i3 / AMD Ryzen 3 or equivalent
- **RAM:** 4 GB system memory
- **Storage:** 2 GB available space (SSD highly recommended)
- **Audio:** Working Microphone (essential for voice control) and Speakers
- **Network:** High-speed internet connection (required for Groq LLM, Edge TTS, Google STT)

### Recommended Requirements (Local Offline Mode)
*Required if you intend to run LLaMA 8B locally via Ollama instead of the Cloud API.*
- **OS:** Windows 10 / 11 (64-bit)
- **CPU:** Intel Core i5 / AMD Ryzen 5 or better
- **RAM:** 16 GB system memory 
- **GPU:** NVIDIA RTX 2060 / AMD RX 6600 or better (VRAM 6GB+ for hardware acceleration)
- **Storage:** 15 GB+ available space on an NVMe SSD

## Core Subsystems & Architecture

KALKI is modularly designed, entirely decoupling its "Brain" from its visual "Body" to ensure real-time responsiveness and zero UI blocking.

1. **The HUD Interface (`index.html`)**
   A completely standalone, zero-build-step frontend built in Vanilla JS and Canvas2D. The interface continuously polls the backend for state changes, updating telemetry, logs, audio waveforms, and tactical controls visually.

2. **The Server Core (`main.py`)**
   A lightweight, multi-threaded HTTP server using Python's standard library. It handles incoming requests from the HUD, processes voice input asynchronously in background threads, and routes execution to the appropriate integration.

3. **Cognitive Routing**
   KALKI intelligently routes tasks based on difficulty. Casual chatter and system commands are sent to a blazing-fast `LLaMA-3.1-8B` model for instant responses. Complex coding questions, clipboard AI fixing, and deep cybersecurity scans are dynamically routed to the heavy `LLaMA-3.3-70B` or `LLaMA-4-SCOUT` vision models.

4. **Cyber Reconnaissance Engine**
   Built-in capabilities for deep network reconnaissance. KALKI can scan a domain for missing security headers, execute Shodan IP queries, enumerate subdomains using `crt.sh`, and pull critical CVE intelligence from NVD—all requested via natural voice commands.

## Install

1. Download `KALKI_Setup.exe` from the [Releases](https://github.com/Maher-Bhatt/KALKI/releases) page.
2. Open it and follow the Setup Wizard to install.
3. Windows 10/11 required. A free Groq API key is required for the cloud AI brain.

## Showcase

<div align="center">
  <img src="screenshots/kalki-hud.png" width="98%" alt="Main HUD">
</div>

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
