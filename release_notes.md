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
