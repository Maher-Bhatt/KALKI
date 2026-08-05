# 🚀 KALKI v1.2.7 — Multi-Mode Sound Engine & Bug Fixes

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
