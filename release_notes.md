# 🚀 KALKI v1.2.1 — Major Bugfixes and UX Improvements

## 🔥 v1.2.1 Patch Notes

- **Settings API & OAuth Links:** Fixed the Settings menu API keys and Spotify/Google OAuth linking that had broken redirect ports.
- **Mic Mute Loop Glitch Fixed:** Added a watchdog to release the `speaking` lock so KALKI no longer mutes the microphone indefinitely if a request hangs.
- **Rate Limits & Weather:** Switched the default model from 70B to `llama3-8b-8192` to avoid Groq rate limits, and integrated Open-Meteo with exact IP geolocation for accurate weather.
- **Screen Time Dashboard:** Fully implemented 7-day and 30-day Screen Time dashboards in the Telemetry tab.
- **UX Polish:** Improved Settings UI readability with larger fonts, added Support/Review buttons, and simplified the Setup Wizard instructions.

Installer SHA-256:
[PENDING]
