<div align="center">
  <img src="screenshots/poster_banner.png" alt="KALKI AI Assistant" width="100%">

  <h1><img src="assets/kalki_logo.png" width="48" style="vertical-align: middle;"> KALKI — Tactical AI Desktop Assistant</h1>

  <strong>A fully voice-controlled, autonomous AI assistant for Windows.</strong><br>
  <em>Inspired by J.A.R.V.I.S. • Powered by Groq LLaMA • Engineered for power users & developers.</em>

  <p>
    <img src="https://img.shields.io/badge/release-v1.0.4-00c8ff?style=for-the-badge&logo=github" alt="release">
    <img src="https://img.shields.io/badge/platform-Windows_10%2B-0078d4?style=for-the-badge&logo=windows" alt="platform">
    <img src="https://img.shields.io/badge/brain-Groq_LLaMA_3.3-ff6b35?style=for-the-badge&logo=meta" alt="brain">
    <img src="https://img.shields.io/badge/engine-Python_3.11+-3776AB?style=for-the-badge&logo=python" alt="python">
    <img src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge" alt="license">
    <img src="https://img.shields.io/badge/monitoring-Sentry-362d59?style=for-the-badge&logo=sentry" alt="sentry">
    <img src="https://img.shields.io/badge/cloud-Firebase-FFCA28?style=for-the-badge&logo=firebase" alt="firebase">
  </p>

  <h3><a href="https://github.com/Maher-Bhatt/KALKI/releases">⬇️ Download KALKI_Setup.exe (Latest Release)</a></h3>
</div>

---

## 📢 What's New in v1.0.4 — Mood Engine & Stability Update

> KALKI v1.0.4 introduces the **Mood Swing Engine**, enhanced greeting personalization, dynamic hardware detection, Firebase cloud sync, Sentry error monitoring, and dozens of stability improvements.

### 🔥 Highlights

| Feature | Description |
|:---|:---|
| **🎭 Mood Swing Engine** | KALKI now adapts its personality to your energy. Use aggressive language and KALKI matches your vibe — roasts back harder, uses strong language, and stays in character for **5+ exchanges** without randomly de-escalating. |
| **👋 Dynamic Greeting System** | Every boot generates a unique, multi-line greeting from randomized pools — time-of-day aware (morning/afternoon/evening/night), with personalized owner addressing and contextual sign-offs. No two greetings are ever the same. |
| **🖥️ Dynamic Hardware Detection** | System specs (CPU, GPU, RAM) are now auto-detected at runtime using the actual user's hardware — no more hardcoded values. Every user sees *their own* system info. |
| **☁️ Firebase Cloud Sync** | Configuration, memory, and session data sync to Firebase Realtime Database for cross-device persistence and cloud backup. |
| **🐛 Sentry Error Monitoring** | Production-grade crash reporting and performance monitoring via Sentry. Every unhandled exception is captured with full stack traces and system context. |
| **📐 Core Architecture Refactor** | Global state, telemetry, cloud sync, and auto-updater extracted into a clean `core/` Python package — laying the foundation for plugin architecture in v1.1.0. |
| **🎨 Adaptive Display Engine 2.0** | Completely constraint-based layout with dynamic REM scaling. The HUD adapts flawlessly to 1080p, 1440p, 4K, and ultra-wide displays. |
| **🔇 Zero Echo Audio Pipeline** | Aggressive `pyaudio` buffer flushing during TTS output eliminates feedback loops entirely — KALKI will never transcribe its own voice again. |
| **📊 Developer Diagnostics** | Press `Ctrl+Shift+D` to reveal a hidden telemetry overlay: real-time FPS, Memory, DevicePixelRatio, UI Scale, and Audio Latency. |

---

## 🌌 What is KALKI?

**KALKI** is an autonomous, voice-first personal AI assistant built entirely from scratch using **pure Python** and an embedded **Vanilla JS Heads-Up Display (HUD)**. It is not a chatbot — it is a fully integrated desktop command center.

KALKI lives on your machine, wakes on the command **"Hi KALKI"**, and manages your system, tasks, emails, calendar, music, cybersecurity workflows, and more — entirely via voice.

### Why KALKI?

- 🚫 **No Electron.** No bloated frameworks. Pure HTML5 Canvas2D + vanilla JS = blazing fast HUD.
- 🧠 **Not just a wrapper.** KALKI has its own cognitive routing engine, memory system, mood detection, and tool orchestration.
- 🔒 **Your data stays local.** All credentials stored via Windows DPAPI encryption. Cloud sync is optional.
- ⚡ **Sub-second responses.** Groq's LPU inference delivers LLaMA-70B responses in under 500ms.

---

## ✨ Complete Feature Set

### 🎙️ Voice-First, Always-On
| Feature | Details |
|:---|:---|
| **Wake Word** | Say **"Hi KALKI"** from anywhere — no clicks, no keyboard |
| **Smart Audio Pipeline** | Advanced signal processing prevents feedback loops |
| **Offline Fallback** | Optional VOSK wake-word detection for zero-latency, privacy-first mode |
| **Continuous Listening** | Background daemon captures speech and routes it to the AI brain |

### 🧠 Multi-Model Cognitive Router
| Model | Use Case |
|:---|:---|
| `LLaMA-3.1-8B` | Fast casual conversations, quick commands |
| `LLaMA-3.3-70B-Versatile` | Deep reasoning, complex coding, debugging |
| `LLaMA-4-Scout` | Vision tasks (screenshot analysis, image understanding) |
| **Ollama (Local)** | Full offline autonomy — run entirely on your GPU |

### 🎭 Personality & Mood Engine
| Feature | Details |
|:---|:---|
| **Mood Detection** | Automatically detects aggressive, vulgar, playful, or calm language |
| **Persistent Moods** | Aggressive mode stays active for 5+ exchanges — no random de-escalation |
| **Roast-Back Engine** | If you roast KALKI, it fires back harder. Authorized to use strong language when you do |
| **Adaptive Tone** | Professional by default, adjusts to match your energy exactly |
| **Dynamic Greetings** | Randomized, time-aware greetings — never the same message twice |

### 🛡️ Tactical Cybersecurity Toolkit
| Tool | Capability |
|:---|:---|
| **Deep Webscan** | Voice-trigger a headless Chromium audit for security headers, SSL, cookies |
| **Shodan OSINT** | Pull real-time IP intelligence, open ports, and service banners |
| **CVE Intel** | Live NVD vulnerability tracking with severity ratings |
| **Port Scanner** | Integrated port mapping with service detection |
| **Source Viewer** | Download and analyze page source code on command |

### 💻 Developer Tools
| Feature | Details |
|:---|:---|
| **Clipboard AI Coding** | Copy broken code → say "Fix the code in my clipboard" → optimized code pasted back |
| **Code Generation** | Generate Python scripts, web pages, and utilities via voice |
| **Sandbox Execution** | Run generated scripts safely in an isolated environment |
| **GitHub Integration** | Manage repositories, create gists, check commit history |

### 🤖 System & Life Integration
| Integration | What It Does |
|:---|:---|
| **PC Control** | Lock screen, adjust volume, clear recycle bin, open apps via voice |
| **Google Calendar** | View, create, and manage events via voice |
| **Gmail** | Read inbox summaries, search emails, get notification alerts |
| **Spotify** | Play, pause, skip tracks, and control your music hands-free |
| **WhatsApp** | Send messages and interact with contacts via browser automation |
| **Reminders & Tasks** | Set, list, and manage reminders with voice — synced to memory |
| **Notes & Vault** | Encrypted password vault (DPAPI) and persistent note-taking |

### 🎨 Premium HUD Interface
| Feature | Details |
|:---|:---|
| **Sci-Fi Design** | Canvas2D-rendered waveforms, particle effects, glowing elements |
| **Adaptive Scaling** | Fluid REM-based layout — 1080p to 4K, any DPI |
| **Dark Mode** | Premium dark theme with accent colors and glassmorphism |
| **Real-Time Telemetry** | CPU, RAM, GPU, network stats displayed in the HUD |
| **Diagnostics Overlay** | `Ctrl+Shift+D` reveals FPS, memory, DPR, scale metrics |

---

## 🚀 Installation

KALKI requires **zero manual build steps**.

1. **Download** → Go to [Releases](https://github.com/Maher-Bhatt/KALKI/releases) and grab `KALKI_Setup.exe`
2. **Install** → Run the setup wizard. It installs the core engine, Chromium DeepScan browser, and all offline assets automatically
3. **Configure** → Get a free API key from [Groq Console](https://console.groq.com) and enter it in KALKI's settings panel
4. **Launch** → Say **"Hi KALKI"** and your assistant is online

> **Optional Integrations:** Google Calendar/Gmail (OAuth2), Spotify (API key), Shodan (API key), Firebase (service account JSON)

---

## 💻 System Requirements

### ☁️ Cloud Mode (Recommended)
| Component | Minimum |
|:---|:---|
| **OS** | Windows 10/11 (64-bit) |
| **CPU** | Intel Core i3 / AMD Ryzen 3 |
| **RAM** | 4 GB DDR4 |
| **Storage** | 2 GB SSD |
| **Network** | Broadband internet |
| **Peripherals** | Microphone + Speakers |

### 🖥️ Local Offline Mode (via Ollama)
*Run the full LLaMA model locally without any cloud API.*

| Component | Recommended |
|:---|:---|
| **CPU** | Intel Core i5 / AMD Ryzen 5+ |
| **RAM** | 16 GB+ |
| **GPU** | NVIDIA RTX 3060+ / AMD RX 6600+ (8GB+ VRAM) |
| **Storage** | 15 GB+ NVMe SSD |

---

## 📐 Architecture

KALKI separates its **Brain** from its **Body** — the interface never freezes while the AI is thinking.

```
┌─────────────────────────────────────────────────────┐
│                    KALKI System                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│   ┌─────────────┐     ┌──────────────────────┐      │
│   │  Listener    │────▶│   Server Core        │      │
│   │  (Speech)    │     │   (server.py)        │      │
│   │              │     │                      │      │
│   │  VOSK/Google │     │  ┌────────────────┐  │      │
│   │  STT Engine  │     │  │ Cognitive      │  │      │
│   └─────────────┘     │  │ Router         │  │      │
│                        │  │ (Multi-Model)  │  │      │
│   ┌─────────────┐     │  └────────────────┘  │      │
│   │  HUD        │◀───▶│                      │      │
│   │  (index.html)│     │  ┌────────────────┐  │      │
│   │              │     │  │ Tool Engine    │  │      │
│   │  Canvas2D +  │     │  │ (20+ modules) │  │      │
│   │  Vanilla JS  │     │  └────────────────┘  │      │
│   └─────────────┘     └──────────────────────┘      │
│                                                      │
│   ┌─────────────────────────────────────────┐       │
│   │            core/ Package                 │       │
│   │  state.py │ telemetry.py │ cloud_sync   │       │
│   │  updater.py │ __init__.py               │       │
│   └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

| Component | Technology | Role |
|:---|:---|:---|
| **HUD Frontend** | Vanilla JS + HTML5 Canvas2D | Real-time waveforms, telemetry, chat UI |
| **Server Core** | Python `http.server` + Threading | AI routing, API orchestration, state management |
| **Listener Daemon** | VOSK / Google STT + PyAudio | Background speech capture and transcription |
| **Core Package** | Python package (`core/`) | Global state, telemetry, Firebase sync, auto-updater |
| **Cognitive Engine** | Groq API / Ollama | LLaMA model inference and response generation |
| **Audio Engine** | `edge-tts` + `pygame` mixer | Text-to-speech with zero-echo pipeline |

---

## 📸 Visual Showcase

<div align="center">
  <img src="screenshots/poster_features.png" width="48%" alt="Feature Overview">
  <img src="screenshots/poster_logo.png" width="48%" alt="KALKI Logo">
</div>
<br>

<div align="center">
  <img src="screenshots/kalki-hud.png" width="98%" alt="KALKI HUD — Main Interface">
</div>
<br>

<div align="center">
  <img src="screenshots/hud_tactical.png" width="48%" alt="Tactical Cybersecurity Ops">
  <img src="screenshots/hud_models.png" width="48%" alt="Neural Model Selection">
</div>
<br>

<div align="center">
  <img src="screenshots/settings_general.png" width="48%" alt="Settings — General">
  <img src="screenshots/settings_integrations.png" width="48%" alt="Settings — Integrations">
</div>

---

## 🛠️ Technology Stack

| Layer | Technology |
|:---|:---|
| **HUD / Frontend** | Vanilla JavaScript + HTML5 Canvas2D |
| **Backend Core** | Pure Python 3.11+ (`http.server` + `ThreadingMixIn`) |
| **Core Package** | `core/` — state management, telemetry, cloud sync, auto-updater |
| **Cognitive Engine** | Groq API (`llama-3.3-70b`, `llama-3.1-8b`, `llama-4-scout`) |
| **Audio Pipeline** | Microsoft `edge-tts` + `pygame` mixer + Google STT |
| **Cloud Services** | Firebase Realtime DB, Sentry Error Monitoring |
| **Integrations** | `google-api-python-client`, `imaplib`, `spotipy`, Playwright |
| **System Layer** | `psutil`, `pycaw`, `pillow`, Windows DPAPI (`win32crypt`) |
| **Cyber Recon** | Playwright headless Chromium, Shodan API, `crt.sh`, NVD |
| **Build System** | PyInstaller + Inno Setup 6 |

---

## 📂 Project Structure

```
KALKI/
├── server.py              # Main backend server — AI routing, tools, API
├── listener.py            # Background speech recognition daemon
├── main_app.py            # Desktop window host (pywebview)
├── index.html             # HUD frontend — Canvas2D + Vanilla JS
├── launcher.py            # Process launcher and orchestrator
├── kalki_setup_wizard.py  # First-run configuration wizard
│
├── core/                  # Core Python package
│   ├── __init__.py
│   ├── state.py           # Global state management
│   ├── telemetry.py       # System telemetry collection
│   ├── cloud_sync.py      # Firebase Realtime DB sync
│   └── updater.py         # Auto-update checker
│
├── cybertools.py          # Cybersecurity toolkit (CVE, ports, recon)
├── webscan.py             # Web vulnerability scanner
├── deepscan.py            # Headless Chromium deep inspector
├── shodan_mod.py          # Shodan OSINT integration
├── vision.py              # Screenshot & image analysis (LLaMA Vision)
├── coder.py               # AI code generation & sandbox execution
├── clipboard_mod.py       # Clipboard AI (fix/optimize pasted code)
│
├── gcal.py                # Google Calendar integration
├── mail.py                # Gmail IMAP integration
├── spotify_mod.py         # Spotify playback control
├── whatsapp_mod.py        # WhatsApp browser automation
├── github_mod.py          # GitHub repository management
│
├── notes.py               # Persistent notes system
├── tasks.py               # Task & reminder management
├── vault.py               # DPAPI-encrypted password vault
├── semantic_memory.py     # Long-term conversational memory
├── tools.py               # System tools (volume, lock, apps)
├── workflows.py           # Multi-step workflow automation
│
├── runtime_log.py         # Structured logging framework
├── runtime_security.py    # Security hardening & input validation
├── browser_url.py         # Browser URL utilities
├── watchdog.py            # Process health monitoring
│
├── config.example.py      # Template config (copy to config.py)
├── requirements.txt       # Python dependencies
├── assets/                # Icons, logos, and branding
├── screenshots/           # README visual assets
├── build_tools/           # PyInstaller specs + Inno Setup scripts
└── LICENSE                # MIT License
```

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. **Fork** this repository
2. **Clone** your fork locally
3. Copy `config.example.py` → `config.py` and fill in your API keys
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python launcher.py`
6. Submit a **Pull Request** with your changes

---

## 📜 License

KALKI is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details.

---

## 🙏 Acknowledgements

- [Groq](https://groq.com) — Unprecedented LLaMA inference speeds via their LPU engine
- [edge-tts](https://github.com/rany2/edge-tts) — High-quality Microsoft Edge text-to-speech
- [Firebase](https://firebase.google.com) — Realtime Database for cloud state sync
- [Sentry](https://sentry.io) — Production-grade error monitoring
- [Playwright](https://playwright.dev) — Headless browser automation for DeepScan

---

<div align="center">
  <strong>Built with 🔥 by <a href="https://github.com/Maher-Bhatt">Maher Bhatt</a></strong><br>
  <em>"Sometimes you gotta run before you can walk." — Tony Stark</em>
</div>
