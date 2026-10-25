# KALKI Change History

## 1.4.2 Desktop Companion Pet Always-On-Screen, Real System Control, Marketing Suite & Repository Overhaul

- **Interactive Marketing Web Showcase & Repository Overhaul (marketing/index.html, showcase.html, README.md):
  - Built standalone, zero-dependency cyber-glassmorphism web showcase (marketing/index.html) featuring an ambient particle canvas, Web Audio API sound synthesizer, interactive companion pet playground with 6 selectable cyber species (Gobi, Kittu, Byte, Draco, Nova, Kitsu), interactive ShieldCore radar scanner simulator, dynamic smart model router tester, and multi-platform binary download center.
  - Added root showcase.html with instant redirection for seamless offline double-click launching.
  - Completely redesigned README.md with glowing shields, quick download matrix with verified SHA-256 integrity hashes, system architecture mermaid diagrams, cyber tools reference, and campaign artwork.
- **Desktop Companion Pet Always-On-Screen & Instant App Launch (`app/desktop_pet.py`, `app/ui/pet_overlay.html`):**
  - Resolved PyWebView startup crash by removing invalid 8-character hex color (`#00000000`) and configuring native transparency.
  - Eliminated Windows WebView2 resource lock collision (`0x800700AA: The requested resource is in use`) by creating an isolated `pet_webview_profile` environment.
  - Added new **Chibi Pixel Sprite** (`Gobi`) mascot matching Codex desktop companions with pixel ears, blushing cheeks, and bobbing animations.
  - Clicking the mascot now directly executes `open_main_app()`: restores minimized KALKI window, unminimizes it, brings it to foreground with Win32 `AttachThreadInput` and `SetForegroundWindow`, and dispatches `/api/wake`.
- **Real System Access & Attitude Enforcement (`app/server.py`, `app/ui/features/ask.js`):**
  - Eliminated dummy assistant bluffing where `TOOL CALL: system_control({"action": "lock"})` was rendered as plain text.
  - Added backend System Actions Execution Interceptor in `/api/chat` that detects action tags and tool requests, immediately executing `ctypes.windll.user32.LockWorkStation()` to lock the workstation.
  - In `handle_local()`, commands like `lock`, `lock pc`, `lock screen`, `lock workstation` now execute instantly without fake 30-second confirmation delays.
  - When in Anger Mode, sustained verbal abuse automatically triggers physical screen locking without hesitation.
  - In `ask.js`, raw tool call syntax is replaced with a styled security badge: `🛡️ System Security Action: Workstation Locked`.
- **Apple Music & Dynamic App Launcher (`app/server.py`):**
  - Added native `music:` URI scheme and Windows UWP package launcher (`shell:AppsFolder\AppleInc.AppleMusicWin_nzyj5cx40ttqa!App`), enabling instant opening of Apple Music.
  - Expanded `APP_MAP` with Apple Music, Apple TV, DaVinci Resolve, Valorant, and Brave.
- **Security Right-Side Panel UI/UX Overhaul (`app/ui/features/security.js`):**
  - Removed `.pad` class from `renderSecurityAside()`, eliminating padding squashing and horizontal scrollbars in the 300px sidebar.
  - Resolved `ReferenceError: runLiveScan is not defined` by implementing `runLiveScan('quick')`, `runLiveScan('full')`, and `runLiveScan('memory')`.
  - Upgraded shield switches to native Filament `.tg` controls and streamlined the Defense Telemetry card.
- **Verified 12 Cybersecurity Tools & Wordlist Integration (`app/cybertools.py`, `data/wordlist.txt`):**
  - Bundled `data/wordlist.txt` and integrated an in-memory fallback list into `cybertools.py`, ensuring `crack_hash_dict` succeeds natively without missing wordlist errors.
  - Verified all 12 tools (`surface`, `dns`, `subdomains`, `portscan`, `headers`, `cve`, `identify`, `hash`, `encode`, `decode`, `dorks`, `crack`) with live execution.
- **Dynamic Auto-Model Selection (`app/config.py`, `app/server.py`, `app/ui/lib/format.js`):**
  - Configured `DEFAULT_MODEL = "auto"` across backend and frontend.
  - Enhanced `resolve_auto_model` to automatically classify prompt difficulty: complex reasoning, code, CVE, patents, and research route to Pro models (`gemini-2.5-pro`, `gpt-4o`, `llama-3.3-70b-versatile`); casual chat and system actions route to Flash models (`gemini-2.5-flash`, `gpt-4o-mini`, `llama-3.1-8b-instant`).
  - Added `Auto (Smart)` human-readable label in the composer model picker chip.

## 1.4.1 desktop companion pet persistence, hardware-bound encrypted memory, settings & usage overhaul

- **Desktop Companion Pet Persistence & Synchronization (`app/desktop_pet.py`, `app/ui/pet_overlay.html`, `app/server.py`):**
  - Resolved PyWebView startup crash (`ValueError: Path app/app does not exist`) by ensuring absolute executable resolution prior to working directory shifts.
  - Eliminated hardcoded port `8000` references; updated all endpoints to resolve dynamic origin (`window.location.origin`) or fallback to configured port `8888`.
  - Added native `/api/pet` GET & POST endpoints in `server.py` persisting to `pet_state.json` in user data, keeping species (Kittu, Byte, Draco, Nova, Kitsu), companion name, aura color, and sound preferences in sync across both the main window and floating desktop pet.
  - Upgraded Web Audio synthesizer with user-gesture auto-resume (`ctx.resume()`) so purrs, chimes, and interaction sounds trigger audibly.
  - The desktop pet window remains visible and interactive on screen when KALKI is minimized.
- **Hardware-Bound Encrypted Memory (`app/semantic_memory.py`):**
  - Implemented Windows DPAPI (`win32crypt.CryptProtectData`) hardware-bound encryption at rest with machine-keyed AES-256 Fernet fallback.
  - Semantic memory documents on disk are transparently encrypted with user-locked cryptographic keys, preventing plain-text data exposure.
  - Enhanced `_auto_extract_topic_memory` in `server.py` to extract user preferences, facts, tech stack, and personal details via available AI keys (Groq, OpenAI, Gemini) and an expanded heuristic engine.
- **Settings Provider Keys & Usage Dashboard (`app/ui/features/settings.js`, `app/server.py`):**
  - Fixed `secretRow()` bug where saved API keys displayed "Not set" due to type-checking mismatch on boolean vault statuses.
  - Updated `server.py` on startup to automatically hydrate configuration directly from the encrypted `api_vault`, unlocking stored Groq and Gemini API keys.
  - Built a comprehensive Model Usage & Performance dashboard in Settings displaying total API calls, prompt/completion tokens, local cost estimations, average latency, and per-model activity breakdowns.
  - Fixed "Enhanced visuals" toggle to persist in user preferences and render backdrop-filtered glassmorphism cards.
- **Dynamic Light Theme Support (`app/ui/tokens.css`):**
  - Added complete `html[data-theme="light"]` token palettes (`--void: #f1f5f9`, `--base: #ffffff`, `--text: #0f172a`, etc.) ensuring seamless light and dark mode switching.
- **Fresh Conversation on Startup (`app/ui/main.js`, `app/ui/state/conversations.js`):**
  - Configured application boot to always initialize a fresh, empty conversation with centered suggested action pills rather than automatically pursuing old conversations.
- **Security & Antivirus Command Center (`app/ui/features/security.js`):**
  - Restructured the Security workspace into a full 2-column layout with an active defense telemetry sidebar displaying ShieldCore status, Windows Defender connection, real-time protection toggles, and quick scan triggers.

## 1.4.0 companion pet system, antivirus shield engine, fluid animation overhaul, and installation guide

- **Standalone Codex-Style Desktop Floating Companion Pet (`app/desktop_pet.py`, `app/ui/pet_overlay.html`):**
  - Always-on-top, borderless, transparent floating window placed in the screen corner, draggable anywhere on screen.
  - Fully persistent even when the main KALKI application window is closed or minimized.
  - Active music detection polling Windows SMTC/Apple Music/Spotify to trigger dancing animations and floating musical note particles (`♪`, `♫`).
  - Interactive speech bubble prompt on click ("Hey Maher! What's on your mind?"), accepting questions, speaking answers aloud with Andrew's natural neural voice, and offering a 1-click button to launch the full KALKI app.
  - Web Audio synthesized 8-bit sound effects (purrs, chimes, meows).
- **Proper Antivirus & Cybersecurity Direct Viewer (`app/ui/features/security.js`):**
  - Dedicated **Antivirus & Cyber** rail destination pinned permanently to the main navigation rail (never hidden behind settings).
  - **Live Scan Theater**: Active animated radar sweep, real-time progress bar, and a streaming monospace console displaying actual files examined across user Downloads, AppData Temp, and Windows Startup.
  - **Cybersecurity Tools Directory (Direct Viewer)**: Interactive visual catalog for all 12 security modules (`surface`, `dns`, `subdomains`, `portscan`, `headers`, `cve`, `identify`, `hash`, `encode`, `decode`, `dorks`, `crack`) with category filters (`All`, `Recon & OSINT`, `Vulnerabilities`, `Cryptography`, `Web Defense`, `Offensive CTF`), scope badges, plain-English security guides, presets, and a 1-click "Launch Tool" button.
  - **Interactive Studio**: Scoped execution console with structured results and raw JSON inspection.
- **Intelligence, Web Search & Patent Research Fix (`app/server.py`):**
  - Resolved web search failure on IPv6 NAT64 systems by whitelisting NAT64/DNS64 prefixes (`64:ff9b::/96`) in SSRF guard `_safe_public_url()`.
  - Added modern Chrome User-Agent header in `_http_get()` to bypass search engine anti-bot blocks.
  - Injected live search context directly into `ask_ai_stream()` so that web queries (such as patent research for "Maher patent") fetch real DuckDuckGo results and stream factual, grounded answers.
- **Uncensored Anger & Savage Roast Mode (`app/server.py`):**
  - Real-time profanity and vulgarity detection in chat streaming.
  - When the user uses abusive language or swear words (English or Hinglish: *fuck, shit, idiot, chutiya, bsdk, bhenchod, stfu, useless, moron*), KALKI engages an unrestricted ANGER / SAVAGE ROAST MODE system directive matching energy with sharp wit and zero preachy canned disclaimers.
- **System Control & Automation (Apple Music & Dynamic App Launcher) (`app/server.py`):**
  - Prioritized Apple Music protocol commands (`applemusic:`, `itms:`) in `handle_local()` with web player fallback.
  - Dynamic Windows application launcher (`cmd.exe /c start "" "{clean_app}"`) for opening any installed program on voice or text command.
- **ShieldCore Antivirus & Endpoint Defense Suite (`app/antivirus.py`):**
  - Native Windows Defender integration via PowerShell Get-MpComputerStatus and MpCmdRun.exe CLI reporting real-time protection and definition health.
  - Multi-layer heuristic analyzer detecting double extensions (.pdf.exe), obfuscated PowerShell/cmd droppers (IEX, FromBase64String, DownloadString, Certutil), macro droppers (Auto_Open, baProject), and high Shannon byte entropy (>7.45/8.0).
  - Background process and memory auditor detecting cryptominers (XMRig, minerd, mining ports) and untrusted temp-directory executions.
  - Live clipboard inspection catching crypto-clipper address tampering and dangerous pipe-to-shell patterns (curl | sh).
  - Isolated Quarantine Vault with permission hardening (icacls) isolating flagged binaries with 1-click permanent deletion or safe restoration.
  - High-framerate radar sweep scanner visualization (@keyframes radarSweep, @keyframes radarPulse) and real-time shield toggle matrix in the Security workspace.
- **Comprehensive Installation Guide (INSTALLATION_GUIDE.md):**
  - Created end-to-end installation documentation covering hardware requirements, required runtimes (WebView2, Visual C++, Python), 1-click installer setup (Output\KALKI_Setup_v1.4.0.exe), developer source setup, model providers (Gemini 2.5, Groq, OpenAI, Claude, Ollama), voice configuration, and troubleshooting.
  - Validated Windows 10/11 64-bit production readiness.
- **GPU-Composited Fluid Spring Animation Engine:**
  - Silky message entrances, smooth view transitions, radar sweep scans, and audio visualizer wave bars (@keyframes eqWave).
  - Zero layout thrashing: animations run strictly on composite layers (	ransform: translateZ(0) and opacity).
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
  - Integrated responsive desktop mascot (`app/ui/features/pet.js`) featuring 5 vector cyber species: Kittu (Cat), Byte (Dog), Draco (Dragon), Nova (Drone), and Kitsu (Fox).
  - Lifecycle reactivity: alert on typing, working during streaming, happy dance on done, jamming to music, and floating sleep `z Z Z` particles after 45s idle.
  - Interactive petting, treat feeding (fish, bone, battery, candy), laser ball fetch, persistent level/XP progression (Lvl 1-99), and mood telemetry.
  - Zero external assets: 100% SVG, CSS keyframe animations, and Web Audio API synthesized sound effects.
  - Settings customization dialog (species, custom name, aura color, sound toggle) accessible from chat header, Settings tab, and Command Palette.
- **Conversational UI & Neural Read Aloud Overhaul:**
  - Distinct user message bubbles (`.umsg`) with right-aligned gradient surfaces, timestamps, and hover action bars (copy, edit & resend).
  - Native neural Read Aloud speaker button on every assistant turn calling `/api/tts/test` with active pulsing animation and instant stop toggle.
  - Inline title renaming, 1-click Markdown export (`.md`) formatted with timestamps, and full chat clearing with confirmation dialog.
  - Context turn meter chip showing active turns vs. window limits.
- **Fluid Spring Animation Engine:**
  - Added `@keyframes msgIn` and `@keyframes viewFadeIn` for silky message and view transitions.
  - Micro-interactions on buttons, suggestion pills, and cards with tactile spring scaling (`transform: scale(0.95)`).
- **Human Neural Voice Default:** Default voice configured to en-US-AndrewMultilingualNeural for expressive human cadence.
- **Edge TTS SSL Fallback:** Added resilient fallback to an unverified SSL connector (aiohttp.TCPConnector(ssl=CERT_NONE)) upon SSLCertVerificationError to eliminate 24-second freezes behind antivirus/proxies and prevent fallback to robotic SAPI speech.
- **Settings API Unwrapping & BOM Protection:**
  - Enhanced /api/settings/save to accept unwrapped direct keys from api.save().
  - Migrated configuration JSON loading across server.py, config.py, and kalki_setup_wizard.py to utf-8-sig to eliminate Unexpected UTF-8 BOM decoding errors.
  - Added retry resilience against Windows file locks in _atomic_write_json.
- **UI/UX & Responsive Layout Polish:**
  - Centered all desktop workspace views (.pad max-width 980px) and composer/chat stream (.msgs > div, .comp max-width 820px).
  - Fixed button text squishing and vertical overflow in Settings aside by adding white-space: nowrap; and flexbox alignment.
  - Widened voice identity dropdown to 24rem to prevent long model name truncation.
- **Media Engine & Cover Art:**
  - Multi-source music playback fallback (Windows SMTC -> YouTube Music -> Apple Music).
  - High-res iTunes cover art converted directly to Base64 in Python for dependable display in WebView2.
- **Tasks:** Added plural/singular handling for "clear all tasks" voice commands and UI actions.

## 1.4.0 build and verification fixes

- **New Jarvis HUD:** A transparent overlay HUD displaying voice status, activity log, approvals queue, and notifications.
- **Activity Log & Approvals Queue:** Added logging for reversible actions and an approvals queue for sensitive commands.
- **Morning Briefing:** A new AI-generated morning briefing covering weather, calendar, and news.
- **Skills Management:** Added ability to toggle individual skills on/off via UI and API.
- **Cyber Tools Fixes:** Fixed and stabilized cyber tools functionality.
- **Cleanup:** Removed obsolete patch scripts and fixed duplicate imports in server.py.

- Fixed: the Oversight "watch a site", "remove site" and "check site" routes crashed with HTTP 500 (undefined variable `data`; the request body is `body`). Watching a website from the UI now works.
- Fixed: release files disagreed on the version. The MSIX manifest and Inno Setup script said 2.0.0 while the app is 1.4.0; `release.ps1` now reads the version from `app/version.py` so artifact names and the manifest cannot drift.
- Added: `tests/feature_check.py` boots the real server with an isolated profile and checks authentication, tasks, notes, reminders, memory, settings, oversight, cyber tools, graceful behaviour without credentials, backup and the vault (Windows only).
- Added: `tests/version_check.py` fails the build if version strings drift.
- Added: `.github/workflows/windows.yml` builds the EXE, portable ZIP and MSIX on `windows-2022`, runs every check first, uploads the artifacts and attaches them to tagged releases.

## v1.4.0 — Oversight, Presence & Background Notifications

**Release date:** Unreleased

This release adds comprehensive background monitoring and deepens the system integration without touching the core routing or frontend architecture established in v2.0.0.

- **System Oversight panel.** Added a new 'Oversight' destination to the navigation rail, surfacing live machine telemetry, watched websites, threshold configurations, and a 50-item rolling alert history.
- **Background API reliability.** The backend now implements a robust 1-step fallback for AI requests. If the primary provider fails, KALKI transparently tries the next configured provider (e.g. Gemini or Ollama) before surfacing an error to the user, ensuring uninterrupted service. Added a 'Test connection' button in Settings to verify API keys.
- **Native OS Notifications.** Background loops (alerts, watchdogs, reminders) now generate native Windows toast notifications using `plyer` when KALKI is running hidden in the background, in addition to spoken alerts.
- **Hidden state optimization.** The frontend status loop now correctly detects when the window is hidden (`document.hidden`) and throttles polling to 30s while maintaining background notification capability.


## v2.0.0 — Full frontend rebuild: Filament

**Release date:** September 19, 2026

This release replaces the entire user interface. `app/index.html` — previously a single 2,529-line file holding the whole dashboard — is now a 41-line shell that loads a 27-module, no-build-step application from `app/ui/`. The backend, voice pipeline, memory system, and every existing API route are unchanged: this is a frontend and packaging release, not a rewrite of KALKI's capabilities.

**Why:** an audit of the previous interface found that 56 of the server's 83 API endpoints — tasks, reminders, notes, calendar, mail, Spotify, WhatsApp, GitHub, workflows, the credential vault, code generation, screen vision, and the cybersecurity toolkit — had no interface at all. The rebuild's first job was exposing that work, not restyling what already existed.

- **New product architecture.** Five destinations — Ask, Today, Memory, Workbench, Settings — replace the fixed three-column HUD. A command palette (`Ctrl/Cmd+K`) reaches every action, conversation, and setting in one keystroke, built on native `<dialog>` so focus management needs no hand-written trap.
- **New visual identity: Filament.** Cold graphite surfaces, a single warm-platinum presence mark that lives in the navigation rail rather than at screen center. The mark only ever animates opacity and scale — never width, height, or a filter — because the packaged app runs WebView2 with GPU compositing disabled, and that is also the cheapest thing a software renderer can draw. Retires the cream-and-terracotta theme.
- **Security workspace is now gated.** The thirteen `/api/cyber/*` routes, previously unreachable, are exposed as a real workspace — hidden by default, surfaced only when a Shodan key is configured or a person turns it on in Settings → Advanced.
- **Conversation history moves to the frontend.** The backend has no conversation database (`history.json` is a flat, 10-exchange rolling window with no IDs). The new frontend owns threads — title, pin, search, timestamps — in IndexedDB, and states the real context window on the composer ("6 of 10 turns in context") instead of hiding the limit.
- **Voice states are now honest.** Because `listener.py` runs as a separate process and the frontend only observes it through polling, the interface shows only the states it can verify — ready, attending, thinking, speaking, interrupted — and does not fabricate a "listening" indicator the backend cannot confirm.
- **New static-asset route.** Added `/ui/*` to `server.py` with an explicit content-type allowlist and a realpath prefix check against directory traversal, since the previous `/assets/*` route served every file as `image/png` or `application/octet-stream`, which a browser refuses for `<script type="module">`.
- **Service worker rewritten.** The previous cache-first policy for non-API assets meant a shipped frontend file was cached forever and could never be updated. The API and the HTML shell are now network-only; `/ui/*` is network-first; everything else is stale-while-revalidate.
- **`/api/status` no longer re-parses the memory file on every poll.** `memCount` and hardware stats are now cached for 5 seconds; the endpoint was being hit roughly 2,400 times an hour under the previous fixed 1.5-second timer. Polling itself is now adaptive — 2s while a reply is streaming, 10s idle, fully suspended while the window is hidden — and a new `GET /api/history` lets the frontend reconcile voice turns recorded while the window was closed.
- **No development signing certificate ships in this repository.** The committed `.pfx` from prior releases has been removed; local development signing now resolves `KALKI_DEV_CERT_PATH` and `KALKI_DEV_CERT_PASSWORD` from the environment, and an MSIX built with neither set is left unsigned, which is what Microsoft Partner Center expects on submission.
- Updated the Windows installer, MSIX staging, GitHub-release staging, and Linux packager to ship `app/ui/` — the previous packaging scripts copied only `index.html`, which would have produced a blank window.
- Updated the Windows package identity to `2.0.0.0` and synchronized the version string across `version.py`, `config.example.py`, the installer, the file version resource, and the Linux packager.

The v2.0.0 Store identity is `2.0.0.0`. Local package validation must pass before distribution, while production signing and certification remain Microsoft Partner Center responsibilities.

## v1.3.5 — Legal, setup, and release synchronization

**Release date:** August 26, 2026

This maintenance release synchronizes the user-facing documentation and setup assets with the current desktop runtime. It includes the expanded Terms and Conditions, clean UTF-8 release history, v1.3.5 dashboard and package metadata, and refreshed release documentation. The package continues to use the native Windows frame, conservative WebView2 rendering, delayed optional integrations, a CSS-only center, and installer process shutdown before file replacement.

The v1.3.5 Store identity is `1.3.5.0`. Local package validation must pass before distribution, while production signing and certification remain Microsoft Partner Center responsibilities.

## v1.3.4 — Windows WebView stability and release hardening

**Release date:** August 26, 2026

This release hardens the Windows desktop shell after reports of the packaged application becoming unresponsive shortly after first paint.

- Replaced the custom frameless PyWebView shell with a native Windows window frame and standard message handling.
- Disabled WebView2 GPU compositing for the packaged desktop path to reduce graphics-driver-specific post-paint hangs.
- Delayed optional system-tray initialization and microphone-listener startup so they cannot compete with the first WebView paint.
- Removed remote Google Fonts loading from the dashboard so the local interface does not depend on a network font request.
- Removed duplicate 4K eye-background compositing and kept the center presence treatment CSS-based with no active canvas redraw loop.
- Preserved the KALKI eye artwork, lightweight Indian-futurist presence core, Theme Lab, connected dashboard controls, and guarded local actions.
- Updated the Windows package identity to `1.3.4.0` and passed the Store validation gate with 16 checks, 0 warnings, and 0 errors.
- Updated the Terms and Conditions to describe local-first storage, optional third-party services, microphone and background behavior, guarded system actions, human review, compatibility limits, updates, and Microsoft Store distribution.

## v1.3.3 — Conservative center and WebView performance

- Replaced the heavy center animation with a CSS-only eye-based presence core.
- Removed active continuous canvas rendering and reduced unnecessary browser work.
- Added in-flight status-poll protection and a bounded local status timeout.
- Updated the Store package identity to `1.3.3.0`.

## v1.3.2 — Launcher startup hotfix

- Restored the desktop launcher import required before the first window is created.
- Updated the dashboard and package identity to `1.3.2.0`.
- Retained installer process-shutdown handling for locked KALKI helper files.

## v1.3.1 — Theme Lab and installer replacement safety

- Added persisted Indian-inspired theme presets, custom color controls, motion and glow preferences, quick theme cycling, and center focus actions.
- Added server-side validation and bounded persistence for theme values.
- Hardened installer shutdown behavior so running KALKI helper processes are stopped before file replacement.
- Updated the Store package identity to `1.3.1.0`.

## v1.2.7 — Multi-mode sound engine and core fixes

- Configured `en-GB-RyanNeural` as the default Edge TTS voice across system configuration and user settings.
- Added mode-adaptive speech profiles for supported workflows.
- Enforced the Windows selector event-loop policy for stable background audio behavior.
- Rebuilt the standalone helper executables and generated a validated Microsoft Store package.

## Release policy

Every release package must be validated independently before distribution. Local Store validation confirms package structure, manifest identity, required assets, entry-point files, and package-size limits; it does not replace Microsoft Partner Center signing, certification, or publication. See [`TERMS.md`](TERMS.md) for the terms applicable to the current release and [`README.md`](README.md) for installation and platform guidance.
