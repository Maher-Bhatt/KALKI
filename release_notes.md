# 🚀 KALKI v1.0.6 — Intelligence & Automation Update

**Release Date:** July 3, 2026  
**Build:** Production  
**Installer:** `KALKI_Setup.exe`

---

## 🔥 v1.0.6 Patch Notes

- **Live Web Browsing:** KALKI can now actively fetch and read the contents of any URL you send it to solve problems using live context.
- **CTF Mode Overhaul:** CTF mode now triggers an unrestricted "Hacker Mindset" prompt, making KALKI aggressively use its tools to solve challenges instead of just opening tabs.
- **Functional Gaming Mode:** Gaming mode automatically kills background hogs (Chrome, VS Code) and opens Windows Quiet Moments settings.
- **Proactive Morning Briefing:** On first wake before 12 PM, KALKI briefs you and asks for your day's priorities, automatically generating Tasks and Reminders.
- **Attitude Enforcement:** Be nice. Excessive rudeness prompts KALKI to roast you and physically lock your Windows screen via `system_control`.
- **Persistent Setup:** `user_config.json` is now stored securely in `%APPDATA%`, preventing data wipe during background app updates.
- **Zero Mic Dropping:** Fixed a regression where background listening rapidly toggled during TTS response, causing dropped words and failed confirmations.

---

## 🚀 KALKI v1.0.5 — Microphone Hardware Toggle Patch

**Release Date:** July 3, 2026  
**Build:** Production  
**Installer:** `KALKI_Setup.exe`

---

## 🔥 v1.0.5 Patch Notes

- **Microphone Auto-Toggle Fix:** KALKI now automatically and cleanly releases the OS microphone hardware whenever it starts speaking (TTS), turning the microphone icon completely off. The HUD microphone button visually syncs with this behavior. 
- **Auto-Updater Fix:** Bumped internal version tracking to ensure seamless future over-the-air (OTA) updates.

---

## 🚀 v1.0.4 — Mood Engine & Stability Update

### 🎭 Mood Swing Engine (Persistent)
- KALKI now detects your mood from your language and **matches your energy exactly**
- Use aggressive or vulgar language → KALKI mirrors your tone, roasts back harder, uses strong language freely
- **Persistent moods**: Aggressive mode stays active for **5+ exchanges** — no more random de-escalation after one message
- KALKI will **never** say "let's keep things respectful" or "I don't want to fight" while you're bantering
- Automatically cools down after 5 clean exchanges

### 👋 Dynamic Greeting System
- Every boot generates a **unique, multi-line greeting** assembled from randomized pools
- Time-of-day aware: different pools for morning, afternoon, evening, and night
- Personalized with owner name and title
- Contextual sign-offs that vary each session
- Two greetings almost never sound the same

### 🖥️ Dynamic Hardware Detection
- System specs (CPU model, GPU name, RAM size) are **auto-detected at runtime**
- No more hardcoded "RTX 5060 / 32GB RAM" — every user sees their actual hardware
- Works across all supported NVIDIA, AMD, and Intel GPUs

### ☁️ Firebase Cloud Sync
- Configuration and session data sync to Firebase Realtime Database
- Cross-device persistence and cloud backup capability
- Secured with Firebase Admin SDK service account authentication

### 🐛 Sentry Error Monitoring
- Production-grade crash reporting and performance monitoring
- Every unhandled exception captured with full stack traces and system context
- Automatic breadcrumb collection for debugging

### 📐 Core Architecture Refactor
- New `core/` Python package isolating global state management
- `core/state.py` — Centralized state machine
- `core/telemetry.py` — System metrics collection
- `core/cloud_sync.py` — Firebase sync engine
- `core/updater.py` — Auto-update checker

---

## 🛠️ Improvements

- **Base prompt personality**: Changed from "strictly professional" to "adaptable to user's mood" — enables natural mood matching
- **Abuse restriction softened**: KALKI can now match aggressive banter energy instead of being forced to stay calm
- **Greeting diversity**: 8+ opener variants, 5+ sign-offs, weather-aware, day-aware
- **Adaptive Display Engine 2.0**: Constraint-based layout with dynamic REM scaling for any resolution
- **Zero Echo Audio Pipeline**: Aggressive pyaudio buffer flushing eliminates voice feedback loops
- **Developer Diagnostics**: `Ctrl+Shift+D` reveals real-time FPS, Memory, DPR, UI Scale, Audio Latency
- **Professional Windows Build**: Executables carry proper KALKI Technologies publisher metadata

---

## 📦 Installation

1. Download `KALKI_Setup.exe` from this release
2. Run the installer — it handles everything automatically
3. Get a free API key from [Groq Console](https://console.groq.com)
4. Launch KALKI and say **"Hi KALKI"**

---

## 💻 System Requirements

| Component | Cloud Mode (Min) | Local Mode (Recommended) |
|:---|:---|:---|
| **OS** | Windows 10/11 64-bit | Windows 10/11 64-bit |
| **CPU** | Intel i3 / Ryzen 3 | Intel i5 / Ryzen 5+ |
| **RAM** | 4 GB | 16 GB+ |
| **GPU** | Not required | RTX 3060+ / RX 6600+ (8GB VRAM) |
| **Storage** | 2 GB SSD | 15 GB+ NVMe SSD |

---

**Full Changelog:** [v1.0.3...v1.0.4](https://github.com/Maher-Bhatt/KALKI/compare/v1.0.3...v1.0.4)
