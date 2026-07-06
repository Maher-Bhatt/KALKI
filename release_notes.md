# 🚀 KALKI v1.0.20 — Native Claude Integration & Settings Modal Polish

**Release Date:** July 6, 2026  
**Build:** Production  

---

## 🔥 v1.0.20 Patch Notes

- **Native Claude / Anthropic Support:** Implemented native Anthropic Claude completions and token streaming endpoints (`ask_anthropic` and `ask_anthropic_stream`) with direct SSE yielding, fully supporting models like `claude-3-5-sonnet-20241022` and `claude-3-5-haiku-20241022`.
- **Wired Redesigned Settings Controls:** Connected all JS components in the 12-tab configurations board, allowing the user to map distinct models for Chat, Vision, Coding, and Voice roles, verify telemetry/alert flags, trigger one-click local backups, restore ZIP containers, and add/delete semantic memories.
- **Safe Input Parsing & Guards:** Wrapped type conversions (like vision retention days integer castings) and window focus restorations (`SetForegroundWindow`) in try/except blocks to eliminate crash vectors.
- **Version Clean Bump:** Bumped version to `v1.0.20` across the server configuration, ISS installer definitions, PyInstaller metadata builders, and web user interfaces.

---

# 🚀 KALKI v1.0.17 — Ultimate Intelligence, Security & HUD Upgrade

**Release Date:** July 6, 2026  
**Build:** Production  

---

## 🔥 v1.0.17 Patch Notes

- **Real-Time Token Streaming (SSE):** Rewrote the chat completion pipe to stream tokens directly into the chat interface via Server-Sent Events (SSE), achieving sub-second time-to-first-token.
- **Secure API Key Vault:** Integrated hardware-bound Windows DPAPI and native keyring storage so API secrets are encrypted and persistent across updates.
- **Advanced Model Manager:** Added support for Groq, Gemini, OpenAI, Anthropic, and local model backends (Ollama/LM Studio) with automatic health checks.
- **Semantic Memory CRUD:** Added a fully interactive memory manager in the settings panel to inspect, store, or delete long-term facts.
- **Binary Document Parsing:** Drag-and-drop now parses PDFs, DOCX, XLSX, PPTX, and ZIP archives directly in the background using server-side extraction logic.
- **One-Click Backup & Restore:** Safeguard configurations, memories, and productivity history into secure encrypted ZIP files.
- **Interactive Plexus Screensaver:** Integrated a GPU-accelerated Plexus particle screen saver overlay triggered on idle or manually via the topbar.
- **Support Donation Link:** Added a premium sponsorship/support button next to Settings.
- **Start Menu Launch Restoration:** Restored app mutex mapping so duplicate shortcuts locate and foreground the native hidden window.

---

# 🚀 KALKI v1.0.16 — Fresh Install Bootstrapping Fix

## 🔥 v1.0.16 Patch Notes

- **Fresh Install Crash (`ModuleNotFoundError`):** Fixed a major issue where fresh installations of the packaged app would crash instantly on boot. The installer now packages and deploys `config.example.py` correctly, allowing the app to successfully bootstrap `config.py` on its first launch.
- **Start Menu Pathing:** Fully hardened the `sys.path` and working directory anchors to resolve execution failures when launched from shortcuts.

---

# 🚀 KALKI v1.0.15 — Start Menu Launch Fix

**Release Date:** July 6, 2026  
**Build:** Production  

---

## 🔥 v1.0.15 Patch Notes

- **Start Menu Pathing Error (`ModuleNotFoundError`):** Fixed a critical pathing bug where launching KALKI from a shortcut (like the Start Menu or Desktop) would fail to find `config.py` and immediately crash. The application now properly sets its working directory and `sys.path` to its installation folder on boot, regardless of how it was launched.

---

# 🚀 KALKI v1.0.14 — Massive UX Overhaul & Deep Productivity Tracking

**Release Date:** July 6, 2026  
**Build:** Production  

---

## 🔥 v1.0.14 Patch Notes

- **Platinum Aesthetic Overhaul:** Entire UI shifted from high-contrast neons to a much sleeker, premium "Platinum & Bronze" aesthetic (`#9aa3ad`, `#a9835c`).
- **Granular App-Level Productivity:** `productivity.py` no longer relies on window titles. It now tracks the actual underlying `.exe` processes (e.g. `chrome.exe`, `cursor.exe`, `discord.exe`). The dashboard now graphs exact time spent per application within each overarching category.
- **Dynamic Morning Briefings:** KALKI now fetches real-time weather via `wttr.in` and injects it into your morning greeting. It also intelligently changes its greeting tone based on how heavy your calendar and inbox loads are.
- **Voice & Personality GUI Configuration:** The Setup Wizard (`KALKI_Setup_Wizard.exe`) now includes a dedicated "Voice & Personality" tab letting you change TTS Voices, Listen Mode, and Personality Spice without manually editing config files.

---

# 🚀 KALKI v1.0.13 — Hotfix for UnboundLocalError & AI Hang

**Release Date:** July 5, 2026  
**Build:** Production  

---

## 🔥 v1.0.13 Patch Notes

- **UnboundLocalError Fix:** Resolved a critical python scoping crash in `server.py` that occurred when requesting email summaries or morning briefings, causing the AI brain to hang indefinitely.
- **Auto-Update Stability:** Improved validation for OTA updates and remote registry values.

---

# 🚀 KALKI v1.0.12 — Chrome Startup Auto-Launch Patch

**Release Date:** July 5, 2026  
**Build:** Production  

---

## 🔥 v1.0.12 Patch Notes

- **Chrome Startup Patch:** Removed the aggressive browser auto-launch mechanism during morning startup checks. KALKI now runs silently in the background tray and only opens a browser window when specifically summoned or requested.

---

# 🚀 KALKI v1.0.11 — Startup Hotfix & Config Bootstrap

**Release Date:** July 5, 2026  
**Build:** Production  

---

## 🔥 v1.0.11 Patch Notes

- **Startup Hang Fix:** Fixed a fatal `SyntaxError` that caused the application to freeze on the boot splash screen by inserting a missing `</script>` tag in the dashboard HTML.
- **Config Bootstrap:** Fresh installations no longer crash instantly due to a missing configuration file. The app now properly auto-copies the template `config.example.py` during initialization.
- **Setup Wizard Pathing:** The Setup Wizard now correctly patches the active Python configuration variables instead of just writing to a disconnected JSON file.
- **Legacy Cleanup:** Removed obsolete `.bat` files and duplicate config files from the repository root, ensuring a cleaner packaged application environment.

---

# 🚀 KALKI v1.0.10 — UX Fixes & Stability

## 🔥 v1.0.10 Patch Notes

- **Duplicate Instance Guard (U4):** Added strong mutex locking to prevent multiple independent instances from launching on startup, which caused double-triggering of microphones and port conflicts.
- **Dashboard Layout Fix (U1):** Fixed a CSS syntax regression that caused system metrics to render incorrectly on a single line.
- **Wake Focus Restoration (U2):** Fixed a missing config fallback that prevented the desktop window from jumping to the foreground when summoned by voice. Added proactive config drift alerts on startup.
- **Clipboard Interactive Prompt (U3):** Broadened clipboard monitoring to detect code snippets and properly integrated the response listener. KALKI will now wait up to 10 seconds for a conversational "yes/no" before analyzing copied text.

---

# 🚀 KALKI v1.0.9 — Setup Loop Hotfix

## 🔥 v1.0.9 Patch Notes

- **Setup Loop Fix:** Fixed a regression where the setup wizard wrote the `setup_complete.marker` to the installation directory (`data/`) while the main application checked for it in the user's roaming AppData directory (`%APPDATA%/KALKI/`). Both now correctly use `%APPDATA%/KALKI/`.

---

# 🚀 KALKI v1.0.8 — Remediation & Stability Update

**Release Date:** July 5, 2026  
**Build:** Production  
**Installer:** `KALKI_Setup_Wizard.exe` / `KALKI_Setup.exe`

---

## 🔥 v1.0.8 Patch Notes

- **Cloud Sync Security:** Rewrote cloud sync encryption using a portable, passphrase-based PBKDF2 + Fernet AES mechanism instead of DPAPI. Users must provide their `CLOUD_SYNC_PASSPHRASE` to restore or sync.
- **Robust Updater UI:** Re-wired OTA downloads to stream progress chunks to the UI via `STATE_UPDATE_PROGRESS` and display a clear percentage inside the memory readout.
- **Boot Interceptors:** Added a Safe Mode boot interceptor to cleanly display and clear `data/crash.log` without entering a crash loop. Added a "KALKI is Updating" splash screen when `updating.lock` exists.
- **Setup Wizard Fixes:** The first-run state is now controlled by a dedicated `setup_complete.marker` rather than the fragile presence of a config file. Re-added missing Spotify, Calendar, and Telegram OAuth screens directly into the setup wizard flow.
- **Dependency & Cleanup:** Purged corrupt root requirements files and ensured `wmi`, `customtkinter`, and `cryptography` are bundled.
- **Dead Code Purge:** Cleaned out redundant header bloat and duplicate stub functions (`scan_computer`, `sync_to_cloud`) from the server core.
- **Spotify Hotfix:** Properly wired the frontend "Reconnect" button to the `/api/setup/tool` handler for robust token refresh.

---

# 🚀 KALKI v1.0.7 — Setup & Intelligence Overhaul

**Release Date:** July 4, 2026  
**Build:** Production  
**Installer:** `KALKI_Setup.exe`

---

## 🔥 v1.0.7 Patch Notes

- **Installer Hotfix:** Resolved the `Access is Denied` update error by enabling native `CloseApplications=force` inside the Inno Setup script to gracefully close KALKI during OTA updates.
- **Background Mic Fix:** Completely rewrote the mic lifecycle with heartbeat monitoring, automatic crash recovery, and dead-thread detection. The mic now stays alive reliably.
- **Setup Wizard Redesign:** Added YouTube tutorial link, Spotify/Google credential fields, step-by-step help guides, and all API key inputs.
- **Settings Page Overhaul:** Added missing fields (Location, Email, GitHub, Shodan), Spotify/Google setup guides with direct links, and fixed redirect URI mismatches.
- **Morning Briefing:** Greetings now include real calendar events and unread email counts from `gcal.startup_summary()`.
- **YouTube Tutorial:** Embedded setup video link in both the wizard and web settings.
- **Config Persistence:** All API keys safely stored in `%APPDATA%/KALKI/` — never lost on update.

---

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
