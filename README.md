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

  <h3><a href="https://github.com/Maher-Bhatt/KALKI/releases/latest">⬇️ Download KALKI_Setup.exe (Latest Release)</a></h3>
</div>

---

## 📢 What's New in v1.0.4 — Mood Engine & Stability Update

> KALKI v1.0.4 introduces the **Mood Swing Engine**, enhanced greeting personalization, dynamic hardware detection, Firebase cloud sync, Sentry error monitoring, and dozens of stability improvements.

<details>
<summary><strong>🔥 Click to expand full changelog</strong></summary>

| Feature | Description |
|:---|:---|
| **🎭 Mood Swing Engine** | KALKI adapts its personality to your energy. Use aggressive language and KALKI matches your vibe — roasts back harder, uses strong language, and stays in character for **5+ exchanges** without de-escalating. |
| **👋 Dynamic Greetings** | Every boot generates a unique, multi-line greeting from randomized pools — time-of-day aware with personalized addressing. No two greetings are ever the same. |
| **🖥️ Hardware Detection** | System specs (CPU, GPU, RAM) auto-detected at runtime — every user sees *their own* hardware. |
| **☁️ Firebase Cloud Sync** | Config and session data sync to Firebase Realtime Database for cloud backup. |
| **🐛 Sentry Monitoring** | Production-grade crash reporting with full stack traces and system context. |
| **📐 Core Refactor** | Global state, telemetry, cloud sync, and auto-updater extracted into a clean `core/` package. |
| **🎨 Adaptive Display 2.0** | Constraint-based REM scaling — flawless on 1080p, 1440p, 4K, and ultra-wide. |
| **🔇 Zero Echo Audio** | Aggressive buffer flushing eliminates voice feedback loops entirely. |
| **📊 Dev Diagnostics** | `Ctrl+Shift+D` reveals real-time FPS, Memory, DPR, UI Scale, Audio Latency. |

</details>

---

## 🌌 What is KALKI?

**KALKI** is an autonomous, voice-first personal AI assistant built entirely from scratch using **pure Python** and an embedded **Vanilla JS Heads-Up Display (HUD)**. It is not a chatbot — it is a fully integrated desktop command center.

KALKI lives on your machine, wakes on the command **"Hi KALKI"**, and manages your system, tasks, emails, calendar, music, cybersecurity workflows, and more — entirely via voice.

<div align="center">
  <table>
    <tr>
      <td>🚫 <strong>No Electron.</strong> Pure Canvas2D + JS = blazing fast</td>
      <td>🧠 <strong>Not a wrapper.</strong> Own cognitive router & memory</td>
    </tr>
    <tr>
      <td>🔒 <strong>Data stays local.</strong> Windows DPAPI encryption</td>
      <td>⚡ <strong>Sub-second.</strong> Groq LPU delivers 70B in <500ms</td>
    </tr>
  </table>
</div>

---

## ✨ Feature Overview

<details>
<summary><strong>🎙️ Voice-First, Always-On</strong></summary>

| Feature | Details |
|:---|:---|
| **Wake Word** | Say **"Hi KALKI"** from anywhere — no clicks, no keyboard |
| **Smart Audio Pipeline** | Advanced signal processing prevents feedback loops |
| **Offline Fallback** | Optional VOSK wake-word detection for zero-latency, privacy-first mode |
| **Continuous Listening** | Background daemon captures speech and routes it to the AI brain |

</details>

<details>
<summary><strong>🧠 Multi-Model Cognitive Router</strong></summary>

| Model | Use Case |
|:---|:---|
| `LLaMA-3.1-8B` | Fast casual conversations, quick commands |
| `LLaMA-3.3-70B-Versatile` | Deep reasoning, complex coding, debugging |
| `LLaMA-4-Scout` | Vision tasks (screenshot analysis, image understanding) |
| **Ollama (Local)** | Full offline autonomy — run entirely on your GPU |

</details>

<details>
<summary><strong>🎭 Personality & Mood Engine</strong></summary>

| Feature | Details |
|:---|:---|
| **Mood Detection** | Automatically detects aggressive, playful, or calm language |
| **Persistent Moods** | Aggressive mode stays active for 5+ exchanges — no random de-escalation |
| **Roast-Back Engine** | If you roast KALKI, it fires back harder |
| **Adaptive Tone** | Professional by default, adjusts to match your energy exactly |
| **Dynamic Greetings** | Randomized, time-aware greetings — never the same message twice |

</details>

<details>
<summary><strong>🛡️ Tactical Cybersecurity Toolkit</strong></summary>

| Tool | Capability |
|:---|:---|
| **Deep Webscan** | Voice-trigger a headless Chromium audit for security headers, SSL, cookies |
| **Shodan OSINT** | Real-time IP intelligence, open ports, and service banners |
| **CVE Intel** | Live NVD vulnerability tracking with severity ratings |
| **Port Scanner** | Integrated port mapping with service detection |
| **Source Viewer** | Download and analyze page source code on command |

</details>

<details>
<summary><strong>💻 Developer Tools</strong></summary>

| Feature | Details |
|:---|:---|
| **Clipboard AI Coding** | Copy broken code → say "Fix the code in my clipboard" → fixed code pasted back |
| **Code Generation** | Generate Python scripts, web pages, and utilities via voice |
| **Sandbox Execution** | Run generated scripts safely in an isolated environment |
| **GitHub Integration** | Manage repositories, create gists, check commit history |

</details>

<details>
<summary><strong>🤖 System & Life Integration</strong></summary>

| Integration | What It Does |
|:---|:---|
| **PC Control** | Lock screen, adjust volume, clear recycle bin, open apps via voice |
| **Google Calendar** | View, create, and manage events via voice |
| **Gmail** | Read inbox summaries, search emails, get notification alerts |
| **Spotify** | Play, pause, skip tracks, and control music hands-free |
| **WhatsApp** | Send messages via browser automation |
| **Reminders & Tasks** | Set, list, and manage reminders — synced to memory |
| **Notes & Vault** | DPAPI-encrypted password vault and persistent note-taking |

</details>

<details>
<summary><strong>🎨 Premium HUD Interface</strong></summary>

| Feature | Details |
|:---|:---|
| **Sci-Fi Design** | Canvas2D-rendered waveforms, particles, glowing elements |
| **Adaptive Scaling** | Fluid REM-based layout — 1080p to 4K, any DPI |
| **Dark Mode** | Premium dark theme with glassmorphism |
| **Real-Time Telemetry** | CPU, RAM, GPU, network stats displayed live |
| **Diagnostics Overlay** | `Ctrl+Shift+D` reveals FPS, memory, DPR, scale metrics |

</details>

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

## 🚀 Installation

KALKI requires **zero manual build steps**.

| Step | Action |
|:---|:---|
| **1. Download** | Grab [`KALKI_Setup.exe`](https://github.com/Maher-Bhatt/KALKI/releases/latest) from Releases |
| **2. Install** | Run the setup wizard — it handles everything automatically |
| **3. Configure** | Get a free API key from [Groq Console](https://console.groq.com) |
| **4. Launch** | Say **"Hi KALKI"** and your assistant is online |

> **Optional Integrations:** Google Calendar/Gmail (OAuth2), Spotify (API key), Shodan (API key), Firebase (service account JSON)

---

## 💻 System Requirements

| Component | ☁️ Cloud Mode (Min) | 🖥️ Local Offline Mode |
|:---|:---|:---|
| **OS** | Windows 10/11 (64-bit) | Windows 10/11 (64-bit) |
| **CPU** | Intel i3 / Ryzen 3 | Intel i5 / Ryzen 5+ |
| **RAM** | 4 GB DDR4 | 16 GB+ |
| **GPU** | Not required | RTX 3060+ / RX 6600+ (8GB VRAM) |
| **Storage** | 2 GB SSD | 15 GB+ NVMe SSD |
| **Network** | Broadband internet | Not required |

---

## 📐 Architecture

KALKI separates its **Brain** (Python backend) from its **Body** (JS HUD) — the interface never freezes while the AI is computing.

```
┌──────────────────────────────────────────────────────┐
│                   KALKI Architecture                  │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────┐      ┌───────────────────────┐      │
│  │  Listener    │─────▶│    Server Core         │      │
│  │  (Speech)    │      │    (server.py)         │      │
│  │  VOSK/Google │      │                       │      │
│  └─────────────┘      │  ┌─────────────────┐  │      │
│                        │  │ Cognitive Router │  │      │
│  ┌─────────────┐      │  │ (Multi-Model AI) │  │      │
│  │  HUD        │◀────▶│  └─────────────────┘  │      │
│  │  (Canvas2D)  │      │  ┌─────────────────┐  │      │
│  │  Vanilla JS  │      │  │ Tool Engine     │  │      │
│  └─────────────┘      │  │ (20+ modules)   │  │      │
│                        │  └─────────────────┘  │      │
│  ┌────────────────────────────────────────────┐      │
│  │  core/ — state │ telemetry │ cloud_sync    │      │
│  └────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | Vanilla JavaScript + HTML5 Canvas2D |
| **Backend** | Pure Python 3.11+ (`http.server` + Threading) |
| **AI Engine** | Groq API (`llama-3.3-70b`, `llama-4-scout`) / Ollama |
| **Audio** | Microsoft `edge-tts` + `pygame` + Google STT |
| **Cloud** | Firebase Realtime DB, Sentry Error Monitoring |
| **Integrations** | Google APIs, `imaplib`, `spotipy`, Playwright |
| **Security** | `psutil`, `pycaw`, Windows DPAPI (`win32crypt`) |
| **Cyber Recon** | Playwright Chromium, Shodan API, `crt.sh`, NVD |
| **Build** | PyInstaller + Inno Setup 6 |

---

## 📂 Repository Structure

```
KALKI/
├── 📄 README.md              # You are here
├── 📄 LICENSE                 # MIT License
├── 📄 release_notes.md       # v1.0.4 changelog
│
├── 📁 app/                   # ← All source code lives here
│   ├── server.py             # Main backend — AI routing, tools, API
│   ├── listener.py           # Background speech recognition daemon
│   ├── main_app.py           # Desktop window host (pywebview)
│   ├── index.html            # HUD frontend — Canvas2D + Vanilla JS
│   ├── launcher.py           # Process orchestrator
│   ├── config.example.py     # Template config file
│   ├── requirements.txt      # Python dependencies
│   │
│   ├── core/                 # Core Python package
│   │   ├── state.py          # Global state management
│   │   ├── telemetry.py      # System metrics collection
│   │   ├── cloud_sync.py     # Firebase sync engine
│   │   └── updater.py        # Auto-update checker
│   │
│   ├── cybertools.py         # CVE, ports, recon toolkit
│   ├── webscan.py            # Web vulnerability scanner
│   ├── deepscan.py           # Headless Chromium inspector
│   ├── vision.py             # Screenshot & image analysis
│   ├── coder.py              # AI code generation & sandbox
│   │
│   ├── gcal.py               # Google Calendar
│   ├── mail.py               # Gmail IMAP
│   ├── spotify_mod.py        # Spotify control
│   ├── whatsapp_mod.py       # WhatsApp automation
│   └── ...                   # 30+ modules total
│
├── 📁 assets/                # Icons, logos, branding
└── 📁 screenshots/           # README visual assets
```

---

## 🤝 Contributing

1. **Fork** this repository
2. **Clone** your fork locally
3. Copy `app/config.example.py` → `app/config.py` and fill in your API keys
4. Install dependencies: `pip install -r app/requirements.txt`
5. Run: `python app/launcher.py`
6. Submit a **Pull Request**

---

## 📜 License

KALKI is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details.

---

## 🙏 Acknowledgements

- [Groq](https://groq.com) — Unprecedented LLaMA inference via LPU
- [edge-tts](https://github.com/rany2/edge-tts) — High-quality Microsoft TTS
- [Firebase](https://firebase.google.com) — Realtime Database sync
- [Sentry](https://sentry.io) — Production error monitoring
- [Playwright](https://playwright.dev) — Headless browser automation

---

<div align="center">
  <strong>Built with 🔥 by <a href="https://github.com/Maher-Bhatt">Maher Bhatt</a></strong><br>
  <em>"Sometimes you gotta run before you can walk." — Tony Stark</em>
</div>
