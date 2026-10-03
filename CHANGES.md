# KALKI Change History

## 2.1.0 build and verification fixes

- **New Jarvis HUD:** A transparent overlay HUD displaying voice status, activity log, approvals queue, and notifications.
- **Activity Log & Approvals Queue:** Added logging for reversible actions and an approvals queue for sensitive commands.
- **Morning Briefing:** A new AI-generated morning briefing covering weather, calendar, and news.
- **Skills Management:** Added ability to toggle individual skills on/off via UI and API.
- **Cyber Tools Fixes:** Fixed and stabilized cyber tools functionality.
- **Cleanup:** Removed obsolete patch scripts and fixed duplicate imports in server.py.

- Fixed: the Oversight "watch a site", "remove site" and "check site" routes crashed with HTTP 500 (undefined variable `data`; the request body is `body`). Watching a website from the UI now works.
- Fixed: release files disagreed on the version. The MSIX manifest and Inno Setup script said 2.0.0 while the app is 2.1.0; `release.ps1` now reads the version from `app/version.py` so artifact names and the manifest cannot drift.
- Added: `tests/feature_check.py` boots the real server with an isolated profile and checks authentication, tasks, notes, reminders, memory, settings, oversight, cyber tools, graceful behaviour without credentials, backup and the vault (Windows only).
- Added: `tests/version_check.py` fails the build if version strings drift.
- Added: `.github/workflows/windows.yml` builds the EXE, portable ZIP and MSIX on `windows-2022`, runs every check first, uploads the artifacts and attaches them to tagged releases.

## v2.1.0 — Oversight, Presence & Background Notifications

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
