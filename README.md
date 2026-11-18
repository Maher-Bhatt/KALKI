<div align="center">

# KALKI

**A personal AI assistant that lives on your Windows PC, and talks back.**

It plans your day, plays your music, opens your apps, remembers what matters and keeps your PC safe, and it always asks before anything important.

[![Release](https://img.shields.io/github/v/release/Maher-Bhatt/KALKI?style=flat-square&label=release&color=2a2520)](https://github.com/Maher-Bhatt/KALKI/releases/latest)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-2a2520?style=flat-square)](https://github.com/Maher-Bhatt/KALKI/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-2a2520?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2a2520?style=flat-square)](LICENSE)

[**Download**](https://github.com/Maher-Bhatt/KALKI/releases/latest) · [Website](https://kalki-marketing.vercel.app/) · [Docs](https://kalki-marketing.vercel.app/docs.html) · [Privacy](PRIVACY.md) · [Changelog](CHANGES.md)

</div>

---

## What KALKI does

| | |
|---|---|
| **Talk naturally** | A real voice conversation: it notices when you stop, answers out loud, and stops the moment you interrupt. English, Hindi and Hinglish. |
| **Your day, briefed** | The first time your PC starts each day, KALKI reads your calendar, reminders, tasks and the weather for where you are. |
| **Music and apps** | "Play some music" uses Spotify, Apple Music or YouTube Music. "Open WhatsApp" opens any installed app, Microsoft Store apps included. |
| **Tasks, reminders, notes** | Repeating reminders with snooze, focus sessions that survive a restart, searchable tagged notes with Markdown export. |
| **Remembers you** | Facts and preferences you share are kept encrypted on your PC and used to fit answers to you. |
| **Security check-up** | Works with Windows Defender: real status, file checks judged by Defender's own exit codes, plain reasons when something looks suspicious, and encrypted quarantine. |
| **A desktop companion** | A see-through pixel-art pet that floats over your windows and shows when KALKI is working or needs you. |
| **Deep research with sources** | Say *"research rooftop solar in India"*: KALKI plans several searches, reads the best pages from different sites and your own notes, and writes an answer where every claim cites its source, with the links listed underneath. |
| **Skills** | Teach KALKI how you like certain jobs done (trip plans, emails, study help). Skills use the open Agent Skills format (a `SKILL.md`), so you can add them from GitHub; three come built in. KALKI shows you the whole skill and anything risky before installing, never runs a skill's scripts, and a skill can never skip an approval. |
| **Learns from you** | Thumbs up or down on any reply. KALKI turns your ratings into short lessons it follows from then on, which you can read, edit or delete. A built-in benchmark tests every AI you've set up on everyday KALKI tasks, and Auto uses the results to pick the best one. |
| **Savage mode** | Optional. Blunt, witty and free to swear; insults get roasted back in your language. |

## Get started

1. **Download** the installer from the [latest release](https://github.com/Maher-Bhatt/KALKI/releases/latest) and run it.
2. **Open KALKI.** A three-minute setup guide walks you through your name, an AI service (each key has numbered steps, a link to the right page and a real test), voice, and optional apps: Google Calendar, Gmail, Spotify, Telegram and GitHub.
3. **Talk to it.** Say "Hey KALKI", or open voice mode and try *"brief me"*, *"play some music"* or *"remind me to stretch in 30 minutes"*.

You need one AI service for questions and chat. **Google Gemini** and **Groq** have free tiers; **OpenAI** and **Anthropic** are paid; **Ollama** runs fully offline on your PC. Tasks, notes, reminders, focus, music and app control work without any of them.

## Privacy and safety

- **Your data stays on your PC**, in `%APPDATA%\KALKI`. Memories and keys are encrypted with Windows' own protection (DPAPI).
- **Your questions go only to the AI service you choose**, or nowhere if you use Ollama.
- **Anything consequential waits for your approval**: sending messages, deleting things, running commands. Reading untrusted web content blocks automatic actions for that request.
- **Location and screen time are off until you turn them on.** Location comes from Windows (GPS or Wi-Fi), never your IP address, and isn't saved. Screen time stores app names and minutes only, never window titles.
- **Skills and lessons can't loosen KALKI's rules.** A skill is only ever used as written instructions (its scripts are never run), skills that try to override KALKI are refused, and lessons about approvals, secrets or safety are thrown away.
- **Research reads web pages as evidence only.** Page text is quoted to the AI with an instruction never to follow anything written inside it, and only public addresses are opened.
- **KALKI isn't an antivirus.** It works with Windows Defender and says plainly when something couldn't be checked.

Read the full [privacy notice](PRIVACY.md).

## How it's built

```
KALKI.exe (main_app.py)         Desktop window: pywebview on WebView2, auto-start
 └─ KALKI_Server (server.py)    Local API on 127.0.0.1:8888, token-protected
     ├─ ui/                     The app: plain ES modules, no build step
     ├─ db.py                   SQLite store with versioned migrations
     ├─ vault.py, secure_store  DPAPI-encrypted secrets
     ├─ tool_policy, approvals  Risk levels and the approval queue for AI actions
     ├─ voice_turn.py           Voice mode: Whisper speech-to-text, Edge neural voice
     ├─ research.py             Deep research: plan, search, read, cite
     ├─ skills.py               Installable Agent Skills (instructions only, reviewed before install)
     ├─ learning.py             Feedback → lessons, benchmarks, smarter Auto routing
     ├─ briefing, focus, tasks, notes, core/productivity   Your day
     └─ antivirus, shield_monitors, cybertools, wifi_security   Security
 ├─ KALKI_Listener (listener.py) Background "Hey KALKI" wake word
 └─ KALKI_Pet (desktop_pet.py)   Layered, click-through desktop companion
```

Route modules (`routes_*.py`, `focus.py`, `briefing.py`) take a request body and return `(payload, status)`, with no dependence on the web server, so they're easy to test and ready for a move to FastAPI. The plan for that move, and everything else in progress, is in the [master plan](docs/KALKI_MASTER_PLAN.md).

## Develop

```powershell
git clone https://github.com/Maher-Bhatt/KALKI.git
cd KALKI\app
python -m pip install -r requirements.txt
python main_app.py
```

Run the tests from the repository folder (552 tests; each runs on a throwaway profile, never your real data):

```powershell
python -m pytest tests
```

Build the Windows installer (needs [Inno Setup](https://jrsoftware.org/isinfo.php)):

```powershell
python app\build_tools\build_installer.py
```

Linux and macOS run from source with Windows-only features (Defender, app launching, location) switched off; see the [install guide](INSTALLATION_GUIDE.md).

## Documentation

- [Website docs](https://kalki-marketing.vercel.app/docs.html): setup, voice, things to say, keys, apps, troubleshooting
- [Install guide](INSTALLATION_GUIDE.md)
- [Master plan and progress](docs/KALKI_MASTER_PLAN.md)
- [Changelog](CHANGES.md)
- [Privacy](PRIVACY.md) · [Terms](TERMS.md)

## Responsible use

The security tools are for your own devices and for systems you're authorised to test. KALKI doesn't build attack payloads.

## License

[MIT](LICENSE) © KALKI contributors.
