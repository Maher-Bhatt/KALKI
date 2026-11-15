# KALKI Privacy Notice

**Version:** 2.1.0
**Last updated:** November 15, 2026

KALKI is designed as a local-first desktop assistant for Windows and Linux. This Privacy Notice explains what may be stored on the device, what may leave the device when optional features are enabled, and the controls available to the person using KALKI.

## Local data

KALKI may store ordinary runtime data in the platform user-data directory. Depending on the features you use, this may include configuration, conversation history, memories, notes, tasks, reminders, productivity and screen-time summaries, logs, backups, temporary files, and local service state. The application uses a per-installation API token to protect privileged localhost routes. Runtime data and credentials should be treated as private device data.

KALKI does not require a cloud account for its basic local interface, typed interaction, local settings, or guarded local workflows. The application cannot guarantee that data will survive an operating-system failure, disk failure, accidental deletion, malware, or a failed update. Maintain independent backups of important information.

## Optional providers and integrations

When you configure an external provider or integration, the information required for that feature may be sent to the selected provider. Examples include AI prompts and selected files, speech-recognition audio, text-to-speech text, calendar or mail requests, media commands, GitHub or Shodan requests, weather or location requests, and explicitly enabled telemetry or error-reporting data.

Each provider controls its own processing, retention, security, and privacy terms. Review the provider’s current privacy notice before enabling it. KALKI does not control or guarantee third-party processing.

## Microphone and voice

Voice recognition and wake-word features require operating-system microphone permission and may use a configured recognition provider. The optional background listener may capture audio while enabled. Speech synthesis may send reply text to the configured speech provider unless a local fallback is selected. The microphone can be disabled through KALKI controls and operating-system permissions.

In voice mode, KALKI records only while you speak, and sends that short recording to the speech-to-text service available: Groq or OpenAI Whisper when you've added their key, otherwise Google's speech recognition. The recording isn't saved; the transcript is saved with your conversations. The reply text is sent to the speech provider to create the voice, unless the Windows voice is used.

Do not enable microphone or background listening in places where recording or processing would be unlawful or where appropriate notice and consent have not been provided.

## Screen, clipboard, and files

KALKI can offer actions that read a selected screen region, selected file, or clipboard content when you explicitly request the action. These features are not intended to collect data continuously. Review the target and content before approving an action, and avoid sending confidential material to an external provider unless you are authorized to do so.

## Location, weather, and diagnostics

Using this PC's location is off until you turn it on. When it's on, KALKI asks Windows for the position (Windows uses GPS or nearby Wi-Fi), never your IP address. The coordinates stay in memory, are refreshed every 30 minutes, and are sent only to Open-Meteo for the weather and to OpenStreetMap to name your city. An older IP-based lookup exists only behind a separate setting that is off by default.

Screen time is off until you turn it on. It stores app names and minutes per day only, never window titles, keeps them for the period you choose, and can be viewed in full and deleted from Settings. The local interface may also display device health information such as CPU, memory, disk, battery, and application uptime.

## Security controls

KALKI binds its ordinary API to the local machine and protects privileged routes with an installation-specific token. Do not forward the local port, expose the token, publish runtime logs, or place vault files and credentials in public repositories. Generated host code execution is disabled by default, and high-impact local actions may require confirmation.

## Your choices

You can decline optional integrations, remove provider credentials from the secure vault, disable microphone and background listener features, clear local memories and history through supported controls, remove local runtime data, and disable optional telemetry where that feature is available. Removing runtime data may permanently delete local history, preferences, logs, backups, and screen-time records.

## Children and sensitive information

KALKI is not designed to collect information from children. Do not use KALKI to process another person’s sensitive information without a lawful basis and appropriate authorization. Do not enter passwords, private keys, authentication tokens, health records, financial records, or confidential business information into prompts or diagnostic logs unless the selected processing path is authorized and appropriate.

## Changes

This notice may change when KALKI’s capabilities, providers, storage behavior, or distribution methods change. The version and date above identify the notice shipped with the current release. The related [`TERMS.md`](TERMS.md) document describes responsible use, limitations, third-party services, updates, and liability terms.
