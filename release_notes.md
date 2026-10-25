# KALKI v1.4.0 — Human Neural Voice, Companion Pet System, Antivirus Shield & Animation Overhaul

## ✦ v1.4.2 Desktop Companion Pet Always-On-Screen, Real System Control, Marketing Suite & Repository Overhaul

This release solidifies production readiness with an always-on-screen desktop companion pet, real Win32 workstation security controls, an overhaul of the Security rail aside, dynamic smart model routing, and a world-class marketing showcase:

- **🌐 Interactive Cyber-Glassmorphism Marketing Showcase (`marketing/index.html`, `showcase.html`, `README.md`):**
  - Standalone, zero-dependency marketing landing page with ambient particle canvas, Web Audio sound effects synthesizer, live interactive companion pet simulator with 6 species, ShieldCore radar sweep simulator, dynamic smart model router tester, and multi-platform download matrix.
  - Added root `showcase.html` with instant redirection for seamless offline double-click launching.
  - Complete redesign of `README.md` with glowing badges, download tables with verified SHA-256 integrity hashes, system architecture diagrams, and cybersecurity tools reference.
- **🐱 Standalone Codex-Style Desktop Floating Companion Pet (`app/desktop_pet.py`, `app/ui/pet_overlay.html`):**
  - Fixed PyWebView initialization by removing invalid 8-character hex code (`#00000000`) and configuring native window transparency.
  - Resolved Edge WebView2 concurrent profile lock collision (`0x800700AA`) by routing pet data to an isolated profile `%APPDATA%\KALKI\pet_webview_profile`.
  - Added new **Chibi Pixel Sprite** (`Gobi`) mascot matching Codex desktop companions with horns, blushing cheeks, and bobbing animations.
  - Pinned on screen even when KALKI main window is minimized or closed.
  - Mascot click executes `open_main_app()`: restores minimized KALKI window, unminimizes it, brings it to foreground using Win32 `AttachThreadInput` + `SetForegroundWindow`, and dispatches `/api/wake`.
- **⚡ Real System Execution & Attitude Enforcement (`app/server.py`, `app/ui/features/ask.js`):**
  - Eliminated dummy assistant bluffing where tool calls were output as plain text.
  - Added backend System Actions Execution Interceptor in `/api/chat` that directly calls `ctypes.windll.user32.LockWorkStation()` on lock commands.
  - In `handle_local()`, commands like `lock`, `lock pc`, `lock screen`, `lock workstation` execute immediately without 30-second confirmation delays.
  - Sustained verbal abuse streaks automatically trigger physical workstation screen locking via Attitude Enforcement Protocol.
- **🎵 Apple Music & Dynamic App Launcher (`app/server.py`):**
  - Added native `music:` registered URI scheme and Windows UWP package launcher (`shell:AppsFolder\AppleInc.AppleMusicWin_nzyj5cx40ttqa!App`), enabling instant opening of Apple Music.
  - Expanded `APP_MAP` with Apple Music, Apple TV, DaVinci Resolve, Valorant, and Brave.
- **🛡️ Security Sidebar UI/UX Overhaul & 12 Verified Tools (`app/ui/features/security.js`, `app/cybertools.py`):**
  - Removed nested `.pad` class from `renderSecurityAside()`, eliminating padding squashing and horizontal scrollbars in the 300px sidebar.
  - Resolved `ReferenceError: runLiveScan is not defined` by implementing `runLiveScan('quick')`, `runLiveScan('full')`, and `runLiveScan('memory')`.
  - Upgraded shield switches to native Filament `.tg` controls and streamlined the Defense Telemetry card.
  - Verified all 12 cybersecurity tools (`surface`, `dns`, `subdomains`, `portscan`, `headers`, `cve`, `identify`, `hash`, `encode`, `decode`, `dorks`, `crack`) with live execution.
  - Bundled `data/wordlist.txt` with top common passwords and added an in-memory fallback list to `cybertools.py`.
- **🧠 Dynamic Auto-Model Selection (`app/config.py`, `app/server.py`, `app/ui/lib/format.js`):**
  - Configured `DEFAULT_MODEL = "auto"` across backend and frontend (`Auto (Smart)` in composer chip).
  - Enhanced `resolve_auto_model` to automatically classify prompt difficulty into Flash vs Pro tiers.

## ✦ v1.4.0 Interactive Companion Mascot, Antivirus Shield Core & Animation Engine

This release introduces an interactive AI Companion Pet system (inspired by Codex mascots), builds the complete ShieldCore Antivirus & Endpoint Defense suite with native Windows Defender integration, delivers fluid 60/120fps GPU-composited spring animations, overhauls conversational message UI and audio playback, and publishes the comprehensive Installation & Deployment Guide (INSTALLATION_GUIDE.md):

- **🐱 Standalone Codex-Style Desktop Floating Companion Pet (`app/desktop_pet.py`, `app/ui/pet_overlay.html`):**
  - Always-on-top, borderless, transparent floating window placed in the screen corner, draggable anywhere on screen.
  - Fully persistent even when the main KALKI application window is closed or minimized.
  - Active music detection polling Windows SMTC/Apple Music/Spotify to trigger dancing animations and floating musical note particles (`♪`, `♫`).
  - Interactive speech bubble prompt on click ("Hey Maher! What's on your mind?"), accepting questions, speaking answers aloud with Andrew's natural neural voice, and offering a 1-click button to launch the full KALKI app.
  - Web Audio synthesized 8-bit sound effects (purrs, chimes, meows).
- **🛡️ Proper Antivirus & Cybersecurity Direct Viewer (`app/ui/features/security.js`):**
  - Dedicated **Antivirus & Cyber** rail destination pinned permanently to the main navigation rail (never hidden behind settings).
  - **Live Scan Theater**: Active animated radar sweep, real-time progress bar, and a streaming monospace console displaying actual files examined across user Downloads, AppData Temp, and Windows Startup.
  - **Cybersecurity Tools Directory (Direct Viewer)**: Interactive visual catalog for all 12 security modules (`surface`, `dns`, `subdomains`, `portscan`, `headers`, `cve`, `identify`, `hash`, `encode`, `decode`, `dorks`, `crack`) with category filters (`All`, `Recon & OSINT`, `Vulnerabilities`, `Cryptography`, `Web Defense`, `Offensive CTF`), scope badges, plain-English security guides, presets, and a 1-click "Launch Tool" button.
  - **Interactive Studio**: Scoped execution console with structured results and raw JSON inspection.
- **🧠 Intelligence, Web Search & Patent Research Fix (`app/server.py`):**
  - Resolved web search failure on IPv6 NAT64 systems by whitelisting NAT64/DNS64 prefixes (`64:ff9b::/96`) in SSRF guard `_safe_public_url()`.
  - Added modern Chrome User-Agent header in `_http_get()` to bypass search engine anti-bot blocks.
  - Injected live search context directly into `ask_ai_stream()` so that web queries (such as patent research for "Maher patent") fetch real DuckDuckGo results and stream factual, grounded answers.
- **⚡ Uncensored Anger & Savage Roast Mode (`app/server.py`):**
  - Real-time profanity and vulgarity detection in chat streaming.
  - When the user uses abusive language or swear words (English or Hinglish: *fuck, shit, idiot, chutiya, bsdk, bhenchod, stfu, useless, moron*), KALKI engages an unrestricted ANGER / SAVAGE ROAST MODE system directive matching energy with sharp wit and zero preachy canned disclaimers.
- **🎵 System Control & Automation (Apple Music & Dynamic App Launcher) (`app/server.py`):**
  - Prioritized Apple Music protocol commands (`applemusic:`, `itms:`) in `handle_local()` with web player fallback.
  - Dynamic Windows application launcher (`cmd.exe /c start "" "{clean_app}"`) for opening any installed program on voice or text command.
- **🛡️ ShieldCore Antivirus & Native Endpoint Defense Engine (`app/antivirus.py`):**
  - **Windows Defender Native Bridge**: Directly interfaces with Windows Defender via PowerShell Get-MpComputerStatus and MpCmdRun.exe CLI, reporting real-time protection status, definition age, and quick scan telemetry.
  - **Multi-Engine Heuristic Analysis**: Static code and file scanner detecting deceptive double extensions (.pdf.exe), obfuscated PowerShell/batch droppers (IEX, FromBase64String, DownloadString, Certutil), macro droppers (Auto_Open, baProject), and high Shannon byte entropy (>7.45/8.0).
  - **Running Process & Cryptominer Audit**: Actively scans background processes and memory for known mining signatures (XMRig, minerd, mining pool ports) and rogue executables running directly from user Temp folders.
  - **Clipboard Hijack & Phishing Protection**: Live clipboard inspection catching crypto-clipper address tampering and dangerous pipe-to-shell patterns (curl | sh). Outbound link checker flagging typosquatting, raw IP servers, and payload downloads.
  - **Isolated Quarantine Vault**: Automatic permission hardening (icacls) isolating flagged binaries in quarantine/ with 1-click permanent elimination or safe restoration.
  - **High-Framerate Radar Sweep UI**: 60/120fps GPU-composited radar scanner visualization (@keyframes radarSweep, @keyframes radarPulse) and live shield toggle matrix in the Security workspace.
- **📚 Comprehensive Installation Guide (INSTALLATION_GUIDE.md):**
  - Complete, production-grade installation guide covering hardware specifications, required runtimes (WebView2, Visual C++, Python), 1-click installer setup (Output\KALKI_Setup_v1.4.0.exe), developer source setup, model provider configuration (Gemini 2.5, Groq, OpenAI, Claude, Ollama), voice settings, and troubleshooting.
  - Validated Windows 10/11 64-bit production readiness.
- **🎨 Fluid GPU-Composited Spring Animation Engine:**
  - Zero layout thrashing: All high-framerate animations (
adarSweep, msgIn, iewFadeIn, eqWave, petBreathe, cardSlideIn) animate exclusively on composite layers (	ransform: translateZ(0) and opacity).
  - Tactile spring micro-interactions on buttons, suggestion pills, and cards (	ransform: scale(0.95)).
- **Natural Neural Human Voice Guarantee & No Robotic SAPI Switch:**
  - Fixed root cause where long multi-paragraph responses exceeded Edge-TTS timeout, causing the server to fall back to the robotic Windows SAPI voice (Microsoft David).
  - Raised Edge-TTS timeout to 30 seconds and pre-configured direct SSL context (`aiohttp.TCPConnector(ssl=ssl_ctx)`) on the primary call.
  - Implemented `extract_conversational_lead` for chat responses: AI replies automatically speak the natural opening conversational sentences (<220 chars) in ~0.6s with Andrew's natural neural voice, avoiding long blocking speech synthesis while streaming full markdown and code blocks in the UI.
  - Completely disabled fallback to robotic Windows SAPI unless explicitly configured in settings.
- **Sub-200ms TTFT Response Speed & Provider Circuit Breaker:**
  - Resolved 3-5 second initial token delay caused by expired/403 Groq API keys being queried on every request.
  - Added intelligent provider circuit breaker in `core/model_manager.py` and `server.py` that immediately flags failed/unauthorized providers (401/403) and bypasses them for 10 minutes without latency penalty.
  - Prioritized Google Gemini 2.5 Flash / Gemini 2.5 Pro as default high-speed neural models whenever `GEMINI_API_KEY` is present.
- **Fixed Disappearing Input Text & Persistent Forms:**
  - Fixed issue where background status polling (every 2s) re-mounted input elements, wiping typed text in Today (tasks, notes) and Memory (quick add).
  - Component forms and input textareas are now persistent DOM elements, completely preserving typed text, focus, and cursor position across background metric refreshes.
- **Conversation Deletion & Route Synchronization:**
  - Fixed conversation deletion to properly update client IndexedDB, sidebar history, active thread view, and URL hash (`#/ask`).
  - Clearing messages or deleting threads immediately transitions to the clean welcome stage with suggested action pills.
- **Refined Layout ("The Pads and All the Things"):**
  - Modernized `.pad` in `app.css` with generous breathing room (`padding: 26px 36px 48px; max-width: 1040px; margin: 0 auto;`).
  - Polished cards (`.card`), fields (`.field`), buttons (`.btn`), and badges with smooth elevation, subtle border glow, and spring micro-interactions matching Linear and Raycast design standards.
  - Fixed Settings sidebar card squishing by replacing `.pad` with direct flex fragment containers in aside.
- **Interactive AI Desk Companion (Pet System):**
  - Built-in responsive desktop mascot docked right inside the Ask workspace.
  - **5 Vector Species:** Kittu (Cyber Cat), Byte (Robo Pup), Draco (Cyber Dragon), Nova (Floating Drone Bot), and Kitsu (Twin-tailed Cyber Fox).
  - **Event-Driven Reactive States:** Automatically reacts to chat lifecycle — alert when user types in composer, working/calculating during streaming, happy dance on answer completion, head-bob jamming when music is playing, and gentle sleep mode (`z Z Z`) when idle for >45 seconds.
  - **Mini-gameplay & Progression:** Interactive petting (hearts + purr chime), snack feeding (treat menu with fish 🐟, bone 🍖, battery 🔋, candy 🍬), laser ball fetch 🎾 across the chat floor, persistent XP leveling (Lvl 1-99), and mood telemetry.
  - **Web Audio Sound Effects:** Zero external audio files; generates cute synthesized 8-bit chimes, purrs, and level-up arpeggios via Web Audio API.
  - **Full Customization:** Choose species, personalized pet name, aura/eye glow color (Filament Gold, Cyber Cyan, Neon Purple, Matrix Green, Sunset Amber, Sakura Pink), and toggle sounds or visibility from Chat header, Settings, or Command Palette (`Ctrl/Cmd+K`).
- **Conversational UI & Neural Audio Playback:**
  - **Sleek User Message Bubbles (`.umsg`):** Right-aligned gradient surface with rounded corners, timestamps, and hover action bars (copy, edit & resend).
  - **Direct Neural Read Aloud (TTS):** Native speaker button on every assistant response calling `/api/tts/test` with KALKI's neural voice (`en-US-AndrewMultilingualNeural`) with active pulsing animation and instant stop toggle.
  - **Thread Management:** Inline title renaming, 1-click Markdown export (`.md`) formatted with timestamps and role badges, and clear thread messages with confirmation dialog.
  - **Live Context Turn Meter:** Real-time indicator displaying active context turns against the rolling window limit.
- **Fluid Spring Animation Engine:**
  - Silky message entrances (`@keyframes msgIn`), smooth view transitions (`@keyframes viewFadeIn`), and organic streaming cursor shimmer.
  - Micro-interactions on buttons, suggestion pills, and cards with tactile spring scaling (`transform: scale(0.95)`).
- **Human Neural Voice by Default (`en-US-AndrewMultilingualNeural`):** Configured Andrew Multilingual Neural as the default assistant voice across `config.py`, server defaults, and setup wizard. Delivers an expressive, natural human cadence.
- **SSL Fallback for Zero-Freeze Speech Synthesis:** Edge TTS now includes transparent SSL context fallback (`ssl.CERT_NONE` via `aiohttp.TCPConnector`) if the initial connection fails with `SSLCertVerificationError`. This prevents the previous 24-second freeze/hang when running behind corporate proxies or SSL-intercepting antivirus software, completely eliminating unwanted fallbacks to robotic Windows SAPI voices.
- **Robust Settings Save & Synchronisation:**
  - Fixed `/api/settings/save` to accept direct top-level keys sent by the frontend `api.save()` without requiring a nested `"updates"` object wrapper.
  - Resolved `Unexpected UTF-8 BOM (decode using utf-8-sig)` crashes by switching all JSON configuration loading to `encoding="utf-8-sig"`.
  - Added a 5-attempt retry loop with exponential backoff on `_atomic_write_json` to eliminate transient Windows file lock errors (`PermissionError [WinError 5]`).
- **UI/UX & Layout Enhancements:**
  - **Centered Desktop Views:** Enforced `max-width: 980px; margin: 0 auto;` on `.pad` across Today, Memory, Workbench, and Settings, and centered chat messages (`.msgs > div`) and the composer (`.comp`) with `max-width: 820px`, eliminating excessive empty margins on wide monitors.
  - **Settings Aside Layout:** Resolved button squishing and text wrapping on the "Create backup" and "Restore" buttons by adding `white-space: nowrap;` and flexbox alignment.
  - **Voice Select Dropdown:** Widened select dropdown to `24rem` to eliminate text truncation of long neural voice names. Made Rate and Pitch input boxes compact (`8rem`).
- **Multi-Source Music & Media Integration:**
  - Intelligent fallback playback engine: Checks active Windows System Media Transport Controls (SMTC), searches and launches YouTube Music or standard YouTube queries, and supports Apple Music.
  - High-resolution iTunes album art fetching in Python converted directly to Base64 data URLs for 100% reliable cover rendering in WebView2.
- **Task Management:**
  - Added universal matching for both singular and plural commands (`clear all task`, `clear all tasks`, `clear tasks`, `delete all task`) directly calling `taskmod.clear_all_tasks()`.

---

# KALKI v2.0.0 — Filament: a rebuilt frontend

## v2.0.0 Frontend Rebuild

KALKI's interface has been rebuilt from a single 2,529-line HTML file into a 27-module, no-build-step application under `app/ui/`, following the Filament design language: cold graphite surfaces, one warm-platinum presence mark that lives in the navigation rail rather than at screen center, and a command palette (`Ctrl/Cmd+K`) as a core interaction system rather than an afterthought.

The backend is unchanged in substance. Three additive routes were added to `server.py` — a `/ui/*` static route with a content-type allowlist and a directory-traversal guard, `GET /api/history` for reconciling voice turns recorded while the window was closed, and 5-second caching on the memory count and hardware stats that `/api/status` was previously recomputing on every poll (roughly 2,400 times an hour under the old fixed timer). No existing route changed behavior, and no route was removed.

The most significant change is exposure: an audit of the previous interface found 56 of the server's 83 API endpoints had never been given a UI — tasks, reminders, notes, calendar, mail, Spotify, WhatsApp, GitHub, workflows, the credential vault, code generation, screen vision, and thirteen cybersecurity routes. All of them now have one. The cybersecurity workspace is gated behind a configured key or an explicit Settings toggle rather than shown to every user by default.

The service worker's caching policy is also fixed: the previous cache-first rule for non-API assets meant a shipped frontend file could never be updated once installed. The shell and API traffic are now network-only; application code is network-first; other assets are stale-while-revalidate.

The Windows installer, MSIX staging, GitHub-release staging, and Linux packager now all ship `app/ui/`; previously only `index.html` was copied. No development signing certificate ships in this repository — local signing resolves `KALKI_DEV_CERT_PATH` and `KALKI_DEV_CERT_PASSWORD` from the environment, and an MSIX built without them is left unsigned, which is what Microsoft Partner Center expects on submission.

## 📦 Binaries

Built by the release pipeline (`microsoft_store/release.ps1`); this repository does not commit binaries. SHA-256 checksums are written alongside each generated artifact.

**KALKI_Setup_v2.0.0.exe** (Standalone Installer)
**KALKI_v2.0.0.msix** (Microsoft Store Package, unsigned pending Partner Center)

---

# 🚀 KALKI v1.3.0 — Stability, Consistent Voice, and Professional Desktop UX

## ✦ v1.3.0 Stability and Professional UX Release

KALKI 1.3.0 prioritizes a responsive desktop shell and a consistent assistant identity. Service startup no longer blocks the first UI paint while waiting for the local server or listener, the desktop close callback no longer re-enters the PyWebView message loop, and the launcher now verifies its runtime imports before packaging.

The voice path is now deliberately consistent: Edge neural TTS uses `en-GB-RyanNeural` with neutral rate, pitch, and volume in every mode and notification. Mode profiles no longer change the assistant’s voice identity. The dashboard uses the supplied KALKI eye background as its visual presence layer, removes the heavy center orb animation, adds lightweight bounded waveform rendering, supports full-screen and minimize controls, and adds an explicit close control for the frameless window.

The release pipeline produces a GitHub-ready portable ZIP and a Microsoft Store-ready MSIX, validates the manifest and assets, and writes SHA-256 checksums. The MSIX is unsigned for Store submission unless `-SignDevelopment` is explicitly used with a local development certificate.

## 🔥 v1.2.7 Patch Notes

- **Default Free Voice Engine:** Configured `en-GB-RyanNeural` (Microsoft Edge TTS British male voice) as the default voice across system configuration and user settings — 100% free with zero API key requirement.
- **Multi-Mode Sound & Voice Profiles:** Integrated mode-adaptive speech modulation in `app/workflows.py` (`MODE_AUDIO_PROFILES`) and `app/server.py` (`_build_edge_tts_file`). Voice rate, pitch, volume, and style dynamically shift per active mode (`gaming`, `ctf`, `dev`, `focus`, `study`, `morning`, `shutdown`).
- **Core Stability (Hotfix):** Resolved a critical UI freeze ("Not Responding") caused by an `asyncio` `ProactorEventLoop` deadlock on Windows background threads during speech synthesis termination. Enforced `WindowsSelectorEventLoopPolicy` for stable background audio.
- **Store Build Pipeline & MSIX Rebuild:** Recompiled standalone `.exe` binaries (`KALKI.exe`, `KALKI_Server.exe`, `KALKI_Listener.exe`, `KALKI_Setup_Wizard.exe`) and generated the validated Microsoft Store `.msix` package (`KALKI.msix`, 631.37 MB, 16/16 checks passed).
- **Version Bump:** Clean bumped version to `1.2.7` across `AppxManifest.xml`, Python `build_msix.py`, ISS installer definitions, and HTML UI.

## 📦 Binaries

**KALKI_Setup_v1.2.7.exe** (Standalone Installer)
- SHA-256: `E59B4117C259616B99C9142F8424904873A96CC20524362A2141244307FF0CED`

**KALKI_v1.2.7.msix** (Microsoft Store Package)
- SHA-256: `4BF6174A8E5C076E018DDC96FF247EB9F96E816223099E3867FDF0F764F0E735`
