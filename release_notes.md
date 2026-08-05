# 🚀 KALKI v1.2.6 — Robust Speech Synthesis & Microsoft Store Ready

## 🔥 v1.2.6 Patch Notes

- **Offline Speech Fallback:** Rewrote the TTS fallback engine. KALKI now automatically fails over to the built-in Windows SpeechSynthesizer if the cloud Edge TTS or Groq neural voices are unavailable. You will never be left with a silent UI.
- **WebView Local Speech:** Switched the voice path to use the desktop WebView’s local speech engine for chat and voice-command replies, preventing the system from waiting indefinitely on unreliable server-side text-to-speech.
- **Microsoft Store MSIX Packaging:** Configured and validated a complete flat MSIX package for Microsoft Store deployment containing all FullTrust capabilities and isolated Python runtimes.
- **Independent Services:** Fixed PyInstaller flattening overwriting DLLs and Python modules by moving helper programs into named service directories for the MSIX.
- **Version Bump:** Clean bumped version to `1.2.6` across `AppxManifest.xml`, Python `build_msix.py`, ISS installer definitions, and HTML UI.

Installer SHA-256 (`KALKI_Setup_v1.2.6.exe`):
D2E585B357000D19093F0D439EE0FAA4D1FB13E2ECD1199F694AF54DD82C6DA6

MSIX SHA-256 (`KALKI.msix`):
F37CF234D22E70F4DD43D0DF6F9F1B6F20325846A4645F44C377894EC9EC2D8F
