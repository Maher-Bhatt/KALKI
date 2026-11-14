# KALKI Master Plan

**Date:** 9 November 2026 · **Baseline:** v1.5.0 (`ba018d3`) plus uncommitted edits · **Status:** plan only, no app code changed

**The goal:** turn KALKI from an impressive demo into software people can trust every day.

**Main finding:** KALKI has about 40 features. A few are solid, many work only partly, and some only look real. The biggest risk isn't missing features. It's screens that claim things the code doesn't do.

## Progress

**Phase 0: code done, not yet committed or released (9 November 2026).** The scorecard below shows the ratings from before this work.

| Area | Status |
|---|---|
| Chat, status, approvals and `/pet` crashes | Fixed |
| Auth exemption, `Host` and `Origin` checks; Telegram and pet use the token | Fixed |
| Chat text reaching a shell; `shell=True` with dynamic strings | Fixed. The Terminal tab's own commands still use a shell when host execution is on, until feature 21 |
| Location opt-in, updater consent, exact release URL check | Fixed. The HTTPS location provider (`ipapi.co`) hasn't been called live |
| Scan honesty and hardcoded UI status | Fixed |
| Streaming connections left open after each reply | Fixed |
| Wi-Fi (feature 45) | Built: saved-network ratings, live connection, nearby scan, look-alike warning, password view and strength check behind a Windows prompt, auto-connect and forget |
| Shield toggles (feature 30, part) | Now real monitors in `app/shield_monitors.py`. They warn after the fact; Defender stays the real-time protection |
| CI | Ruff F821/F823 on Windows and Linux; `tests/test_phase0.py` on Windows. Not yet run on GitHub |

**Next for security, ahead of the original roadmap order:**
- Find out why `headers` failed certificate checks, `cve` timed out, and `subdomains` got a 502.
- Add a way to supply a wordlist for `crack`.
- Test a real Defender detection with the harmless EICAR file. It raises a real Defender alert, so it needs your OK.
- Features 31–34: cancel and progress, scan consent, and safer process killing.

**Phase 2: done on `feat/phase-2-design`, waiting for review.** Built directly on a branch for review, rather than as a separate prototype (§5.7).

| Item | Status |
|---|---|
| Look (13 Nov 2026) | Rebuilt from your reference images: warm paper light theme (now the default) and a warm ink dark theme, serif greetings, a KALKI mountain mark and ink-wash mountains on Ask. Full-height sidebar with the model, this PC and your profile at the bottom; top bar with back and forward, search, model, status and an Activity bell that counts approvals. Ask's empty screen is a home page with quick actions and Today at a glance. Voice mode is a full screen that only shows real states |
| Design tokens | Type, spacing, corners, elevation and motion. Segoe UI Variable adopted, as the font named before was never loaded. A test fails if a screen uses a token that doesn't exist |
| Blur | Dropped, with its setting. It was slow with GPU compositing off |
| Shell | Labelled sidebar that collapses (Ask, Today, Memory, Workbench, Security, Settings), and turns into icons below 1000px. Activity is the bell in the top bar. The top bar has only search and one status menu. Automate waits until automations are discussed |
| Ask | Tool cards that say what KALKI did ("Searched the web", "Send an email: waiting for your approval"); only safe details are shown. Approvals appear in the conversation. Real reply times instead of a made-up "1.1 s". A failed AI call says so instead of showing an empty reply |
| Approvals | One shared card and one shared list for every screen, so they can't drift apart |
| Today | Ordered by urgency, one "Connect your accounts" row. The invented clipboard suggestion and briefing time are gone |
| Library | One search box across memories, notes and conversations. KALKI has no document or meeting-transcript store yet, so those aren't searched |
| Security | One honest result at the top ("Windows Defender is on · Definitions updated today · Nothing to review"), with loading and error states. Plain names for every check. Duplicate buttons removed |
| Settings | Search across every section |
| First run | Three steps inside the app: name, AI service with a real test and Ollama detection, and what KALKI will and won't do. Ends with a real first answer when the AI test passed. Existing installs skip it |
| Pets (feature 42) | Six original pixel characters shared by the app, the desktop and the website. The desktop pet has its own layered window: real transparency and click-through, tested over a bright window. Live status, approvals and dragging tested against a running KALKI. Status is read every 1.5 s, not pushed |
| Accessibility | Every screen audited in dark and light: text contrast passes WCAG AA, every control is at least 24px, has a name and works from the keyboard. Switches are real switches. Rechecked at 900px, 1360px and 4K with no sideways scrolling |
| Not done | Screenshot tests in CI (no browser on the runners yet), watching real people use first run, and 125%/150% Windows scaling checked by eye. The voice demo screen with made-up states was removed rather than fixed |

**Phase 1: in progress on `feat/phase-1-foundations`, not yet committed.**

| Item | Status |
|---|---|
| F2 pytest, Ruff config, dev requirements, dependency lock file | Done. The lock was made on Python 3.13, while CI uses 3.12, so the first CI run must confirm it |
| F4 SQLite store with versioned migrations | Tasks, reminders, notes, chat history, memories and activity moved, with a one-time import that leaves the JSON files untouched. Memories stay encrypted row by row. Settings still to move |
| F7 logging | Started: secret scrubbing and structured error records with tracebacks. Removing broad `except` handlers still to do |
| Backups | Tasks, reminders and notes now included; restore validates first and keeps a safety copy |
| Bugs fixed along the way | Deleting item 1 also deleted items with "1" in their text. UI restore requests were rejected. Host check rejected servers on other ports. A failed memory decrypt overwrote all memories with nothing. "remember ..." called a missing function and hid the error. Vault save failures were silent |
| F5 one vault and typed settings | Encryption is now one module (`secure_store.py`) used by both vaults, with base64 and machine-derived keys removed for new data. Secrets move out of plain-text settings. The two vault files stay separate because they hold different things. Settings are validated by `settings_schema.py`: bad values fall back to defaults, a corrupt file is kept aside, and weakening safety settings needs a Windows prompt |
| F7 exceptions | Bare `except:` removed and blocked by Ruff. Handlers hiding data or security failures fixed through `safe_json.py`. The rest of the silent `except: pass` handlers were triaged as mostly best-effort cleanup, and a test stops the number rising |
| F3, 13 Nov 2026 | On `feat/phase-1-backend` (built on Phase 2): approvals moved to `approvals.py` and the pet routes to `routes_pet.py`. GET requests now check route modules first, like POST. `server.py` is down to 7,433 lines. Fixed on the way: toggling the desktop pet could start a second copy; pet settings were stored unchecked and written unsafely; a failed save still said it worked |
| F3, second step | Activity (with its store) moved to `activity.py`; settings, calendar and first-run setup routes moved to `routes_settings.py`, `routes_calendar.py` and `routes_setup.py`. `server.py` is down to 6,929 lines. Fixed on the way: exported settings could include API keys from older settings files; two Undo clicks at once could undo twice; a failed Undo couldn't be retried; the first-run check read the wrong field names; Google's sign-in file wasn't written safely; "Test" buttons said "Valid" when they only checked setup |
| Test isolation (incident) | From 9 to 13 Nov, the full test run used the real KALKI profile on this PC, because the first test file to import the server didn't set a throwaway one. Tests changed real settings and data: test notes, memories and activity were added, a restore test replaced the real database (with a safety copy kept each time), and the database's copy of tasks was cleared. Fixed with `tests/conftest.py` and a test that fails if data isn't in a temporary folder. Cleaned up on 13 Nov with the owner's OK, after a verified backup: test notes, tasks, memories, activity, a test conversation and test files removed, the original task restored from `tasks.json`. The settings file had been fully overwritten by tests on 9 Nov, so it was reset to empty and KALKI uses `config.py` |
| F3, third step | Backup and restore moved to `routes_backup.py`. They now use KALKI's own profile folder instead of rebuilding `%APPDATA%` paths (wrong on Linux and portable installs), restore keeps a copy of every file it replaces and swaps each file in whole, and a file that isn't a backup gets a plain message. `server.py` is down to 6,789 lines |
| Phase 3, 13 Nov 2026 | Abuse lock made real again with strict whole-word matching (`mood.py`) shared by both chat paths, with a setting to turn it off. Calendar, microphone and "who am I" commands moved to `commands_assistant.py`: requests like "schedule a meeting tomorrow" now reach the AI instead of reading the calendar, "who am I" no longer adds a made-up surname and interests, and replies use your chosen title instead of a hardcoded "Sir" |
| Phase 3, matcher | PC stats, processes, files, small talk, help and mail moved to `commands_chat.py`. Replies no longer claim a "Sovereign Engine", "neural engine" or "100%"; "I messed up" gets help instead of abuse; "who made you" no longer says "you did" to everyone; help lists only real tools and routines; "list files" shows your workspace, not KALKI's program folder; "mute" says it toggles. Two duplicate blocks that could never run were removed. `server.py` is down to 6,627 lines |
| Phase 3, music | Music, WhatsApp and YouTube download moved to `commands_media.py`. Without Spotify, pause, resume and previous never worked: they called functions that don't exist, and the error was hidden behind a success message. They now use the real ones and report failures. Opening a search page is no longer called "playing", shuffle says it needs Spotify, "retry" and "try again" no longer start music, Apple Music opens only when asked, and "music volume 60" without Spotify no longer breaks. `server.py` is down to 6,486 lines |
| Phase 3, desktop | Clipboard, site watching, note capture and PC control moved to `commands_desktop.py`. "Fix my code" never worked: it called a function that doesn't exist; it now asks the AI. "Save my work" no longer becomes a note, "watch the news." no longer adds a site, a failed recycle-bin empty is reported, VS Code opens without a shell, and clipboard captures show what was saved. `server.py` is down to 6,367 lines |
| Phase 3, private | Password vault and screen reading moved to `commands_private.py`. "Save password X for Y" stored the password in lowercase, so it was wrong; passwords now keep their capitals. Copied and generated passwords leave the clipboard after a minute. A password not in the vault no longer blocks other commands. The screen is only captured when you clearly ask: phrases like "help me with this essay" or "look at this code" used to send a picture of your screen to the AI service. `server.py` is down to 6,268 lines |
| Phase 4, reminders (feature 8) | Repeats (every day, every weekday, every week or a named weekday), snooze ("snooze 15 minutes"), delete by voice and from Today, and missed reminders said as missed instead of lost. "Tomorrow", weekdays, "in an hour" and "in half an hour" are understood; before, "tomorrow at 9pm" at 8pm meant today. A time KALKI can't read is now an error, not a silent "in one hour". The AI tool reports the real time it set. Notifications report when they can't be shown. Database migration 4 adds the repeat columns |
| Phase 4, daily briefing (feature 12) | Rebuilt in `briefing.py`. You choose its sections in Settings → Briefing (calendar, reminders, tasks, mail, watched sites, screen time, weather). Each runs on its own with an 8-second limit and says whether it worked, had nothing, isn't set up, failed or was too slow, so one failure no longer empties the whole briefing. It's a plain GET now and no longer switched off by default. Today loads it separately, so a slow source doesn't hold up the page; "Hide until tomorrow" is remembered. "Brief me" and "morning brief" read it aloud instead of the security brief or the local plan. The AI tool uses the same briefing instead of web-searching "weather today". Weather uses Open-Meteo with only your saved coordinates; news is left out until there's a real source |
| Phase 4, focus sessions (feature 10) | Rebuilt in `focus.py`, stored in SQLite (migration 5), so a session carries on after KALKI restarts, and one whose time ran out while KALKI was closed counts as done and is noted in alerts instead of announced late. Two bugs fixed: the End button sent "stop focus session", which the command matcher didn't know, so the session kept running while the screen said it had ended; and a finished session left KALKI in focus mode, holding back notifications indefinitely. Now: lengths from 1 to 240 minutes by voice or the Today card ("focus on the essay for 45 minutes", "focus for an hour"), an optional label, "end early", a spoken and desktop "done" notice, and history with today's and this week's totals. The card says what a session really does: it holds back non-urgent spoken alerts, and doesn't block apps or sites |
| Phase 4, notes (feature 9) | Notes got a full screen from Today ("All notes"): live search, #tag filters with counts, edit, delete with Undo, and export to Markdown, all or just the current search or tag. Each note on Today can be edited or deleted. The Today box said "Capture a thought or search notes" but only ever saved, and its "this week" count was really the number shown; both fixed. Search now runs in SQLite and treats `%` and `_` as plain characters. New routes: update, restore, tags, export |
| Voice in the installed app (14 Nov 2026) | Reported: after installing, KALKI didn't speak. Two causes. The audio output was opened once and kept, so when KALKI started with Windows before the speakers or a Bluetooth headset were ready, or the default device changed, speech played into nothing with no error; it now follows Windows' current default device and reopens when it changes. And when the natural voice failed ("No audio was received", logged since 13 Nov), KALKI stayed silent by design; it now retries once and then uses the Windows voice, with a switch to turn that off (Settings → Voice). Minimum edge-tts raised to 7.0. Checked on this PC: the natural voice plays, and the Windows voice takes over when the natural one fails. Also fixed: reply buttons Copy and Read/Stop overlapped (a 30px icon square), a "0.0 s" duration on instant replies, a cut-off notes placeholder, and briefing sections that aren't set up now have a one-click fix ("Use this PC's location", "Connect Google Calendar") |
| Music, location, morning briefing (14 Nov 2026) | **Music:** a "Plays music with" setting (Automatic, Spotify, Apple Music, YouTube Music). On Automatic, without Spotify connected, "play some music" opens Apple Music and presses play on its own player; "play <song>" opens an Apple Music search inside the app. Apple Music only joins Windows' media controls once something is loaded, so on a fresh start with nothing queued it says to press play there. The AI's play_music tool used to say "Playing music on Spotify" without Spotify; it now goes the same way. **Location:** "Use this PC's location" gets the position from Windows (GPS or Wi-Fi), never the IP address; the old Windows call never worked (PowerShell 5 can't await it) and failed silently. It refreshes every 30 minutes, isn't saved, and the screen shows the accuracy and source. Checked on this PC: Wi-Fi, about 107 m, real weather. **Morning briefing:** the first time KALKI starts or the PC wakes each day (after 4 am), once you're at the keyboard, it reads the briefing aloud, weather included by default; it replaces the startup greeting that day. A "Start KALKI when I sign in to Windows" switch was added; turning it off never removed KALKI from startup before, now it does. KALKI's language model is still Groq or local Ollama; no model was trained |
| Phase 4, security check-up (feature 30) | Windows Defender now decides, by its documented exit codes (0 nothing found, 2 threat, anything else "couldn't check"), not by matching words in its output. Each file gets one of four verdicts: threat, suspicious, clean, or not fully checked. A file is only "clean" if Defender checked it. Invented malware names are gone (`Trojan.DoubleExtension.Dropper`, `Win32.Malware.Generic` and others): findings say "Suspicious because…", and a Defender detection shows Defender's own name. A file another program has open is "couldn't scan", not malware; a file Windows blocks as infected (error 225, which Python reports as "Invalid argument") is a threat. Script patterns only run on scripts and macro documents, since nearly every program mentions VirtualAlloc; packed programs get a note instead of a verdict; patterns read 4 MB instead of 64 KB. Defender status adds tamper protection, last quick and full scan, signature date and version, and says "unknown" instead of 0 days. The screen says "KALKI isn't an antivirus. It works with Windows Defender" and names which part of Defender is off. Checked on this PC: the EICAR test file is detected through Defender, a locked file shows "couldn't scan", and a harmless file is clean. Still to do: startup items review, optional YARA and VirusTotal, measuring false alarms on a clean PC |
| Phase 4, screen time (feature 11) | New Settings → Screen time: an on/off switch (off for new installs; installs that were already tracking stay on), pause for 1 or 4 hours, a week view with per-day delete, top apps with Exclude (which also deletes that app's stored time), a retention limit (7, 30, 90 or 365 days, default 30), "See what is stored" showing the whole file, and Delete all. The tracker no longer counts time while you're away (2 minutes without input) or while the PC sleeps, never stores window titles (unknown apps used to be saved under their title, which can name documents), and writes every 30 seconds instead of every 5. Deleting data doesn't change whether tracking is on. Checked in a browser. Also added a `.grow` style that the Today focus card, notes and screen time rows needed |
| UI, typing interrupted (14 Nov 2026) | Reported: the app "refreshed" while typing, so you had to click the field again. Cause: every status poll re-rendered the whole screen, every 10 seconds (2 while busy) and whenever the window got focus, which replaced the field you were typing in. Polls now re-render only when something shown changes (uptime, CPU and countdowns are ignored), and every re-render keeps the focused field's text, cursor and focus. Checked in a browser |
| Test isolation, second fix | Tests run through `python -m unittest` or directly didn't load `conftest.py`, so the first file to load the server could still reach the real profile. Every test file now imports `tests/_isolation.py` first, and a test enforces it. Checked with pytest, unittest and a direct run |
| F7, 13 Nov 2026 | Handlers that hid real failures now log them or catch only what they expect: web lookups, the backup-model fallback, memory extraction, the briefing and usage tracking. Silent `except: pass` count 165 → 149, enforced by a test |
| F3 FastAPI move | Started without FastAPI: tasks, reminders, notes and memory moved to `routes_productivity.py` and `routes_memory.py`, written to work with any framework. The move itself should wait until CI is green |
| Real-account testing to confirm ratings | Not started: needs your accounts and hardware |

**Phase 3: in progress on `feat/phase-3-core-assistant`.** `g4f` removed. F6 approval system built for AI tools (`tool_policy.py`): every tool has a risk level, consequential actions always wait and show exact content, and untrusted content blocks later automatic actions in that request. `[TASK:]`, `[REMIND:]` and `TOOL CALL:` text in replies goes through the same gate, and approvals can be answered from any screen. Quick commands: `command_intent.py` now sends conversational sentences to the AI before the 1,648-line matcher sees them, with a two-way phrase test. Replacing the matcher has started: tasks, reminders and notes moved to `commands_productivity.py`, in their old positions so command order is unchanged. Chat threads moved to SQLite (`threads.py`), shared by the app, voice and Telegram, with older browser chats moved across on load. Message text is stored unencrypted, as before; encrypting it is still open.

**Accepted for now:** untrusted content only counts within one request, so a later message can still act on what an earlier one read. Consequential actions wait for approval anyway, so this only affects reversible ones.

**Parked for later (9 Nov 2026):** Windows CI failed once at "Automated tests" with code that also passed, so one test is flaky. Re-run usually clears it. Suspected cause, unconfirmed: background threads from the server tests overlapping tests that swap the data store path.

## How to read the ratings

| Rating | Meaning |
|---|---|
| 🟢 **Real** | Does the job. Needs polish and tests. |
| 🟡 **Partial** | The core works, but important parts are missing or fragile. |
| 🟠 **Toy** | Works in a demo, or relies on a fragile shortcut. Won't hold up in daily use. |
| 🔴 **False or broken** | Fails, or the screen claims something the code doesn't do. |

Ratings come from reading the code, a test run on a throwaway copy, and a review of the live UI. **I didn't test with real Google, Spotify, mail, Telegram or microphone setups, or the packaged installers.** Those ratings are from code only and need confirming in Phase 1. All ratings assume the Phase 0 crash fix, because today chat and status fail for everyone.

---

## 1. The rule for "not a toy"

A feature only ships when it passes all 8 of these. If it can't pass, we rename it to what it really does, or cut it.

1. **Truthful.** The UI only claims what the code does. No hardcoded status or fake numbers.
2. **Works end to end.** Tested from the real UI with a real account or device.
3. **Fails clearly.** Each failure says what happened and what to do next. No silent `except: pass`.
4. **All states designed.** Loading, empty, not connected, error, offline and success.
5. **Safe.** Risky actions need approval, and secrets live in the vault.
6. **Survives restarts.** Data is saved atomically, and a crash or reboot doesn't lose it.
7. **Tested.** Automated tests cover it, and CI blocks the release if they fail.
8. **Honest about privacy.** The user can see what leaves the PC and where it goes.

---

## 2. Decisions I need from you

My recommendation comes first in each. The plan below assumes these.

| # | Decision | Recommendation | Why |
|---|---|---|---|
| 1 | What is KALKI? | **A personal AI assistant for your PC, with security check-ups as a side feature** | It's currently an assistant, an antivirus and a hacking toolkit. One clear product is easier to make excellent. |
| 2 | Keep the "Antivirus" name? | **No. Call it "Security Check-up", with Windows Defender as the engine** | It has no real-time protection today. See §7. |
| 3 | Keep `g4f` free AI? | **Remove it** | It's unofficial, and prompts go through providers you can't verify. That contradicts "local-first". |
| 4 | Which platforms for v2? | **Windows first. Linux and macOS labelled experimental** | Much of the code is Windows-only, and there's no macOS CI. |
| 5 | Rewrite or fix? | **Fix in steps. No full rewrite** | Your feature logic has value, and rewrites stall. |
| 6 | How to handle the security toolkit? | **Decided by you (9 Nov): keep the security features and make each one really work, with guardrails.** Wi-Fi comes first | Security moves up to right after Phase 0. The one exception is below. See §10. |

**Your instruction (9 Nov):** keep all cybersecurity features, Wi-Fi included, and make them genuinely workable. The plan now does that. The guardrails below are about *safety and honesty*, not about removing anything:
- **Your own machine** (reading saved Wi-Fi keys, scanning your own files, listing your processes): real and full, with a Windows approval prompt every time something reveals a credential.
- **Another host** (port scan, web scan, subdomains, attack surface): real, after a one-time "I'm authorized to test this target" confirmation per domain, which is standard for security tools.
- **Reverse-shell payloads:** the one exception. The uncommitted edits disabled this route, and it stays disabled. This plan doesn't rebuild it.
- **Packaging caveat:** real security tooling can trip antivirus or Microsoft Store review. I still need to confirm Store policy before a Store release; a direct signed download avoids that.

---

## 3. Scorecard: every feature

| # | Feature | Now | Biggest problem | Plan |
|---|---|---|---|---|
| **Assistant core** | | | | |
| 1 | AI chat | 🔴 | Returns 500 today; only keeps 20 messages | Fix, then rebuild threads |
| 2 | Models and providers | 🟡 | Hardcoded model lists; hidden `g4f` | Provider layer |
| 3 | Memory | 🟡 | Two stores; "semantic" needs a cloud key | Local search in SQLite |
| 4 | Voice | 🟠 | Wake word uses cloud speech recognition | Local wake word |
| 5 | Quick commands | 🔴 | "run ..." in a chat message goes to the shell | Replace with a registry |
| 6 | AI tools, approvals, activity | 🟡 | Email sends with no approval | One approval system |
| **Daily** | | | | |
| 7 | Tasks | 🟢 | Basic: no due dates or projects | Extend |
| 8 | Reminders | 🟡 | No repeat or snooze; notification library not installed | Real reminders |
| 9 | Notes | 🟡 | Search and delete missing from the UI | Finish |
| 10 | Focus sessions | 🟡 | Only a timer | Connect to automations |
| 11 | Screen time | 🟢 | Tracking is real; privacy controls needed | Add controls |
| 12 | Daily briefing | 🔴 | UI calls with the wrong method and gets 404 | Fix and rebuild |
| **Integrations** | | | | |
| 13 | Google Calendar | 🟡 | Today works; week view and event creation are incomplete | Finish |
| 14 | Mail | 🟠 | Reads headers only; keyword "importance" | Rebuild |
| 15 | Music and media | 🟡 | Spotify limits; `winrt` missing from requirements | System media first |
| 16 | WhatsApp | 🟠 | Drives WhatsApp Web through browser automation | Honest draft flow |
| 17 | Telegram | 🟠 | Only works through the auth hole | Secure rebuild |
| 18 | GitHub | 🟡 | Backend fine; no screen | Add screen |
| 19 | YouTube download | 🟡 | No progress or queue; no UI | Decide, then finish |
| **Workbench** | | | | |
| 20 | Workflows | 🔴 | Cards promise steps the code doesn't have | Rebuild as Automations |
| 21 | Terminal | 🟠 | One-shot commands with a 30s limit | Real terminal |
| 22 | Workspace and editor | 🟠 | A plain textarea | Real editor |
| 23 | Code studio | 🔴 | "Sandbox ready" is hardcoded; it isn't a sandbox | Honest isolation |
| 24 | Screen and image vision | 🟡 | Groq-only; OCR needs a separate install | Multi-provider |
| 25 | Documents | 🟡 | Text only, no scans, no large files | Local knowledge |
| 26 | Skills catalog | 🔴 | Same 404; hardcoded list | Fix |
| 27 | Plugins | 🟠 | Runs any `.py`, with no permissions | Pause |
| 28 | Meeting mode | 🔴 | No UI; its summary model was shut down in 2025 | Rebuild |
| 29 | Vision Recall | 🟠 | Screen OCR into memory; high privacy risk | Pause |
| **Security** | | | | |
| 30 | Antivirus "Shield" | 🔴 | Toggles do nothing; says Protected regardless | Security Check-up |
| 31 | Cyber tools | 🟡 | Useful; long jobs can't be cancelled | Keep, add scope and cancel |
| 32 | Web and deep scan | 🟡 | Real checks; no ownership confirmation | Add consent, reports |
| 33 | Process manager | 🟡 | Works; kills by name matching | Safer |
| 34 | Oversight and watchdog | 🟡 | Site checks real; diagnostics panel has fake text | Fix, schedule |
| 45 | Wi-Fi security | 🟡 | New; needs real-world use, and live status text is English-only | Harden |
| **Platform** | | | | |
| 35 | Settings | 🟡 | Config is Python plus plaintext JSON | Typed settings |
| 36 | Vault and API keys | 🟡 | Two vaults; base64 fallback | One vault |
| 37 | Backup and restore | 🟡 | Includes settings unencrypted; no verify | Encrypted, verified |
| 38 | Cloud sync | 🟠 | Uses server admin credentials on the desktop | Cut, replace |
| 39 | Setup wizard | 🟡 | Separate UI, too many steps | New first run |
| 40 | Updater | 🔴 | Runs installers with no consent | Rebuild |
| 41 | Telemetry | 🟢 | Off by default, but the README says "Zero Telemetry" | Fix the claim |
| 42 | Desktop pet | 🔴 | `/pet` crashes | Fix, later polish |
| 43 | Command palette and hotkey | 🟢 | Works; some search paths are unused | Extend |
| 44 | Linux and macOS builds | 🟠 | Version mismatch; limited testing | Experimental |

---

## 4. Foundations (build these first)

Every feature depends on these. Doing features first would mean building them twice.

### F1. Stop the crashes and close the holes (Phase 0)
- Fix the shadowed imports in `server.py` that break chat, status and approvals.
- Add the missing `get_auth_token` path and remove the `body` reference in the GET handler.
- Remove the unauthenticated exemption ([server.py:5721](../app/server.py)). Telegram and the pet currently depend on it, so give both proper auth in the same change.
- Check the exact `Host` and `Origin`, including the port. Reject `Origin: null`.
- Gate or remove `run` / `exec` / `terminal` / `powershell` in `handle_local`.
- Remove `shell=True` wherever user text reaches a command string.
- Respect `AUTO_IP_LOCATION`: `core/location_provider.py` looked up the location at boot with the setting off, over plain `http://`.
- Make auto-update ask first. Require an exact release host, not a substring match.
- Return "not scanned" when a scan can't read a file. Today it returns `clean: True`.
- Remove hardcoded status text (§5.1).

### F2. Safety net
- Add `pytest`, plus Ruff (F821/F823 and more) and Bandit. CI blocks merges on failure.
- Make chat a hard failure in `feature_check.py`. It's only a warning today.
- Add Playwright UI tests for the main journeys, with screenshots.
- Pin dependencies with a lock file. Add `plyer` or its replacement and `winrt`, which aren't in the requirements.
- Release gate: a build only ships from green CI, plus a manual test on clean Windows 10 and 11 machines.
- Add one version source. `package_linux.sh` still says 2.0.0.

### F3. New backend structure
Move from the stdlib `http.server` to **FastAPI**, one route group at a time, so the app works throughout.

```text
app/
  api/        thin HTTP routes with typed requests and responses
  services/   feature logic (chat, memory, tasks, mail ...)
  tools/      AI tools, each with a declared risk level
  integrations/  Google, Spotify, Telegram ...
  db/         SQLite models and migrations
  platform/   Windows-specific code behind one interface
```

- **Goal:** `server.py` shrinks from 7,893 lines to a small entry point.
- **Rule:** no function over about 80 lines, and imports only at the top of the file.
- **Live updates:** one WebSocket event stream replaces most polling. The UI now polls status and media constantly, and the pet polls about every second.

### F4. One data store
- **SQLite** for threads, messages, tasks, notes, reminders, activity, memory and settings. Migrations are versioned.
- Automatic one-time import from today's JSON files, with a backup first.
- Replaces scattered direct JSON writes, which can corrupt data on a crash.

### F5. Secrets and settings
- Stop treating `config.py` as settings. Use typed settings with validation.
- **One vault** using DPAPI on Windows and the OS keychain elsewhere. Today there are two (`vault.py`, `core/api_vault.py`).
- Remove the base64 fallback and the memory key derived from computer and user name. Show an error instead.
- Never lose data silently: a failed decrypt must raise an error and keep the original, not return an empty string.

### F6. The approval system
This is what makes an AI that controls a PC safe. Every tool declares a risk level:

| Level | Examples | What happens |
|---|---|---|
| **Read** | Search notes, read calendar | Runs, shown in Activity |
| **Reversible** | Add a task, set volume | Runs, with Undo |
| **Consequential** | Send email, delete event, close apps | Approval card showing the exact content |
| **Dangerous** | Shell commands, delete files, kill processes | Approval every time, never remembered |

- Text from the web, email and documents is **untrusted**. After the AI reads it, Consequential actions always need approval, whatever the settings. This is the main defence against prompt injection.
- Replace the blocklist of "dangerous" commands. Blocklists are easy to bypass.
- The server decides on approval. The client can't approve by sending `confirmed: true`.
- Replace phrase-matching shell access with narrow tools.

### F7. Observability
- Structured logs with rotation and no secrets. A Diagnostics screen and "copy report" button.
- Remove the 593 broad `except` handlers gradually: log them or handle them specifically.
- One error format, mapped to plain messages in the UI.

---

## 5. UI and UX plan

The Filament identity (cold graphite, warm light) is good and worth keeping. The problems are honesty, clarity and consistency, not the concept.

### 5.1 Problems I saw in the running app

| Problem | Evidence |
|---|---|
| **Fake information** | "Updated 14:02" is hardcoded ([ask.js:998](../app/ui/features/ask.js)). Oversight shows sample diagnostics ([oversight.js:221](../app/ui/features/oversight.js)). "Synced just now" is hardcoded ([today.js:569](../app/ui/features/today.js)). "Sandbox ready" is hardcoded ([workbench.js:1402](../app/ui/features/workbench.js)). |
| **False status** | "Mic ready" with no listener running. "0 unread" with no mail connected. "Protected" while Defender reads "Unavailable". |
| **Dead calls** | `GET /api/briefing/get` and `GET /api/skills/list` return 404 because the routes are POST-only. |
| **Icon-only navigation** | Six unlabelled rail icons, plus a separate conversation list. New users must guess. |
| **Cluttered top bar** | "DESKTOP OS CORE", "Local IPC", Pet, pin and mic chips compete with search. |
| **Too many cards** | Everything is a similar dark card, so nothing stands out. Today shows "Not connected" twice in one card. |
| **Jargon** | "Sovereign", "Neural intelligence", "Executive Daily Briefing", "Sir" hardcoded in greetings. |
| **Foundation gaps** | The Instrument Sans font is named but never loaded. Only colours are tokens: no type or spacing scale. Text encoding is broken in places ("KALKIâ€™s"). |
| **Little responsiveness** | `components.css` (1,423 lines) has no media queries. |

### 5.2 Principles
1. **Truth first.** Show a state only if the app measured it. Otherwise show "Unknown".
2. **One main thing per screen.** One clear primary action.
3. **Show the AI's work.** What it's doing, what it used, what it changed, and how to undo it.
4. **Keyboard first.** Everything reachable with Ctrl+K and shortcuts.
5. **Plain language.** "Couldn't reach Gmail. Reconnect?", never a raw exception.
6. **Calm by default.** Motion only communicates state. Respect reduced motion.

### 5.3 New navigation

```text
┌──────────┬──────────────────────────────────────────┐
│ ◉ KALKI  │  [ Search or run a command  Ctrl+K ]  ● │  ● = one status menu
│          ├──────────────────────────────────────────┤
│ Ask      │                                          │
│ Today    │               Main content               │
│ Library  │                                          │
│ Automate │                                          │
│ Studio   │                                          │
│ Security │                                          │
│ ──────   │                                          │
│ Activity │                                          │
│ Settings │                                          │
└──────────┴──────────────────────────────────────────┘
```

| Section | Contains |
|---|---|
| **Ask** | Conversations, voice, attachments, approvals |
| **Today** | Next event, tasks, reminders, focus, briefing |
| **Library** | Memory, notes, documents, meeting transcripts (one search box) |
| **Automate** | Routines, schedules, triggers |
| **Studio** | Terminal, files and editor, code runner |
| **Security** | Check-up, tools, site monitoring (hidden until enabled) |
| **Activity** | Everything KALKI did, with undo and pending approvals |
| **Settings** | Searchable |

The rail shows labels and can collapse to icons. The top bar has only search and one status dot. The dot opens a single menu with the true state of AI, mic, integrations, and updates.

### 5.4 Key screens
- **Ask:** A centred conversation with a composer. Tool calls appear as small expandable cards ("Searched the web, 3 sources"). Approvals appear inline with exact content and Approve/Deny. Visible: model used, retry, stop, edit, and clear errors. Web answers show sources.
- **Today:** Ordered by urgency, not a grid of equal cards. "Next up" comes first, then tasks and reminders together. Disconnected services collapse into one "Connect your accounts" row.
- **Library:** One search across memory, notes, documents and transcripts. KALKI says when it saves a memory, with Undo. "Why did you say that?" shows what memory it used.
- **Automate:** A step builder with a preview of exactly what will happen before it runs. Run history with per-step results.
- **Studio:** Terminal and editor side by side. Run location always visible, e.g. "Runs on your PC".
- **Security:** One big honest result: "Defender is on, definitions 2 days old, 1 item to review". Tools live behind it.
- **Settings:** Search, grouped pages, a Test button by every integration. Secrets show only Set / Not set.
- **First run:** Inside the main app, three steps: name, AI setup (free key or local Ollama, with a test), and optional mic. It ends with a real first answer. Integrations come later, when needed.

### 5.5 Design system work
- **Tokens:** add type scale, 4px spacing, radius, elevation and motion to the existing colour tokens.
- **Font:** bundle the font for real, or formally adopt Segoe UI Variable, which suits Windows and adds no weight.
- **Components:** one tested set: button, input, select, dialog, menu, tabs, table, toast, approval card, tool card, status dot, empty state, skeleton. Replace one-offs in `components.css`.
- **Six states on each screen**, using shared components.
- **Blur:** decide on it. `--disable-gpu` and `backdrop-filter` conflict, so use solid surfaces unless testing proves otherwise.
- **Window:** a stable title bar that follows Windows snap and resize behaviour. Use Fluent 2 for behaviour cues, not a copy of its look.

### 5.6 Accessibility and performance targets
- WCAG 2.2 AA: contrast, 24×24px minimum targets, focus never hidden, full keyboard use, screen-reader labels, and live regions for streaming replies.
- Window visible within 2 seconds. Input response under 100ms. No layout shifts during streaming.
- Works from 900px to 4K, at 125% and 150% Windows scaling.
- Idle CPU under 1% once polling is gone (to be measured).

### 5.7 How we'll work on the design
1. Clickable prototype of Ask, Today and first run. You approve it before any rewrite.
2. Build tokens and components.
3. Move screens one by one, keeping old routes alive.
4. Screenshot tests in dark and light.
5. Watch 3–5 real people try first run and one daily task. Fix what confuses them.

---

## 6. Feature plans: assistant core

### 1. AI chat 🔴
- **Today:** 500 error. Server history is a flat list of 20 entries. Threads live only in the browser's IndexedDB, so voice and Telegram are separate.
- **Build:** Threads and messages in SQLite, shared by all inputs. Context based on tokens: recent messages plus a running summary. Streaming with stop, retry, edit and regenerate. Tool cards. Attachments stored by reference.
- **Done when:** A 200-message thread stays fast and coherent. A chat started by voice continues in the app. Stop works within a second. Network loss keeps partial text and offers retry.

### 2. Models and providers 🟡
- **Today:** Separate functions per provider and hardcoded names. Meeting mode still uses `llama3-8b-8192`, which Groq shut down on 30 August 2025. `ROLE_MODELS` is decided once, at import.
- **Build:** One provider interface for Groq, OpenAI, Gemini, Anthropic, Ollama and LM Studio. Fetch available models from each provider, with a tested fallback list. A visible fallback note ("Groq failed, used Gemini"). Usage screen with a clear "estimate" label on costs. Remove `g4f`.
- **Done when:** A retired model can't crash a feature. With no key, the user gets a clear setup screen rather than a hang.

### 3. Memory 🟡
- **Today:** A legacy list and a "semantic" store. Semantic search needs an OpenAI or Gemini key, sending memories to the cloud, but the UI still shows a green "Semantic" chip. `_auto_extract_topic_memory` is 218 lines and needs review.
- **Build:** SQLite with **FTS5 keyword search + sqlite-vec vectors + fastembed local embeddings**, merged with rank fusion. Check early that the packaged Python can load the extension. Importance and pinning stay. Save notices with Undo, plus export and delete-all.
- **Done when:** Search works offline with no key. The UI states the true search mode. Users can see and remove anything stored, and each answer can show what memory it used.

### 4. Voice 🟠
- **Today:** In always-listening mode with the default speech engine, the wake phrase is found by sending speech to Google through `recognize_google`, so speech leaves the PC even before you say "Kalki". Today's uncommitted edits make push-to-talk the default, which helps but doesn't fix always-listening mode. Vosk is opt-in. TTS relies on `edge-tts`, an unofficial use of a Microsoft service. The UI can't tell listening from transcribing.
- **Build:**
  - **Wake word:** openWakeWord, local, with a trained "Hey Kalki" model. Avoid Porcupine: reports say its free keys stopped in mid-2026, so check before use.
  - **Speech detection:** Silero VAD.
  - **Speech to text:** faster-whisper locally (benchmark on real PCs), or Groq Whisper by choice, clearly labelled as cloud.
  - **Speech out:** Keep edge-tts for quality, with Windows SAPI as a guaranteed fallback. Evaluate Piper for offline use, noting it's now GPL-3.0.
  - **States:** Real events (idle, heard wake word, listening, transcribing, thinking, speaking).
  - **Talk over it:** Stop speech when the user speaks. Echo cancellation needs testing with speakers.
- **Done when:** With "local" selected, a network monitor shows no audio leaving the PC. Wake works in a noisy room at an agreed success rate, with under one false wake per hour in testing. Mic unplug and Bluetooth changes recover without restart.

### 5. Quick commands 🔴
- **Today:** `handle_local` is 1,555 lines of phrase matching. **Any message starting with "run ", "exec ", "terminal " or "powershell " goes to the shell**, so "run a marathon plan for me" is treated as a command.
- **Build:** A small registry of exact, typed commands (volume, lock, timers). Everything else goes through AI with tools. Each command is unit tested. Shell access only in Studio.
- **Done when:** Natural sentences never reach a shell. There's a table test of 200+ phrases and the intended result of each.

### 6. AI tools, approvals, activity 🟡
- **Today:** Some actions confirm; `send_email`, `delete_calendar_event`, and clearing tasks don't. `read_local_document` searches with an unvalidated filename.
- **Build:** F6 for every tool. Folder-scoped file access. Persistent Activity (it's lost on restart now) with real Undo.
- **Done when:** A test web page or email containing malicious instructions can't send mail or read files without an approval card. These attacks stay in the test suite.

---

## 7. Feature plans: daily use

### 7. Tasks 🟢
- **Build:** Due dates, priority, simple projects, natural-language entry, Undo. Tasks created by AI are announced. Meeting action items become separate tasks.
- **Done when:** Keyboard-only use works, and voice, chat and UI all change the same list.

### 8. Reminders 🟡
- **Today:** Time parsing works and they fire while the app runs. No repeats or snooze; delete exists in the module but isn't routed. `plyer` isn't in the requirements, and `notify.py` hides failures, so notifications may silently never show.
- **Build:** Repeat rules, snooze, delete. Windows toast notifications with action buttons. Run in the tray after the window closes. Show missed reminders on next launch.
- **Done when:** A reminder survives a reboot, fires within 30 seconds on time, and a missed one is never lost.

### 9. Notes 🟢
- **Today (14 Nov 2026):** Search, tags, edit, delete with Undo and Markdown export all have a UI, and notes appear in Library search. Still to do: links to chat threads, and showing Markdown formatted.
- **Build:** Add search and delete to the UI. Markdown, tags, link to threads. Include in Library search.
- **Done when:** Every note function has a working UI, and notes can be exported.

### 10. Focus sessions 🟡
- **Today (14 Nov 2026):** A stored timer that survives restarts, with history and an honest description. Still to do: optional linked automation, and a button that opens Windows Focus / Do Not Disturb settings, since Windows offers no reliable public API to switch it on.
- **Build:** Timer that survives restart, optional linked automation, session history. Windows has limited public API control over Do Not Disturb, so research and label honestly, opening the settings if it can't be automated.
- **Done when:** Every promise on the screen is something the session really does.

### 11. Screen time 🟢
- **Today (14 Nov 2026):** Opt-in, pause, exclusions, retention, a week view, "see what's stored" and one-click delete are built. Still to do: a weekly view beyond 7 days.
- **Today:** Real tracking by process. Saves to JSON without an atomic write.
- **Build:** Clear opt-in, pause, retention limit, delete, per-app exclusions, weekly view. Local only.
- **Done when:** A user can see exactly what's stored and clear it in one click.

### 12. Daily briefing 🟡
- **Today (14 Nov 2026):** On demand, readable and spoken, with chosen sections and per-section status. Still to do: a scheduled briefing, and news once there's a real source.
- **Build:** Sections the user chooses (calendar, tasks, weather, mail, news). Show which ones are unavailable. Scheduled or on demand; readable or spoken.
- **Done when:** It loads in under 10 seconds, and one failed source doesn't break the rest.

---

## 8. Feature plans: integrations

Each needs: **Connect → Test → Use → Disconnect**, with a clear state if not connected.

### 13. Google Calendar 🟡
- **Today:** Read works and `create` exists. Token stored with `pickle`, which is unsafe if the file is replaced. Asks for full calendar access.
- **Build:** Token in the vault as JSON. Week view, create and edit with approval, join-meeting links, time zones. Sync with caching so the UI doesn't wait on Google.
- **Google rule:** Distributing with shared OAuth credentials needs Google verification. Keep "bring your own Google credentials" until then, with a guided setup. Ask only for needed scopes.
- **Done when:** Reconnect after token expiry is one click. Tested across time zones and all-day events.

### 14. Mail 🟠
- **Today:** Reads only headers over IMAP, marks "important" by keywords like "due" and "security". The app password sits in config. `send_email` has no approval. Gmail code also exists separately in `gcal.py`.
- **Build:** One mail service. Start with IMAP/SMTP plus vault, then Gmail OAuth. Note: Gmail read scopes are "restricted", meaning Google verification and possibly a security assessment for wide distribution. Read bodies safely as plain text. AI summaries, smart importance, a draft-first flow, and approval for every send. Email text is always treated as untrusted (F6).
- **Done when:** You can triage 20 messages in the app, nothing sends without approval, and injection tests pass.

### 15. Music and media 🟡
- **Today:** Good logic exists for Windows media controls and Spotify. But `winrt` isn't in the requirements, so the system controls may be falling back. The UI polls about once a second.
- **Spotify rule:** Since February 2026, developer-mode apps need Premium and are limited to 5 users per client ID, with fewer endpoints. So one shared app won't scale.
- **Build:** **Make system media controls the default**: works with any player, with no account. Spotify becomes optional, with the user's own client ID, and only adds search-and-play.
- **Done when:** Play/pause/next and now-playing work in Spotify, Apple Music and a browser with no keys.

### 16. WhatsApp 🟠
- **Today:** `pywhatkit` opens WhatsApp Web, waits, and simulates sending. It breaks easily and could send to the wrong chat. "Fuzzy" contact matching makes that worse.
- **Official API:** The Cloud API is for businesses, with templates and a 24-hour window, not personal messaging.
- **Build:** **"Draft in WhatsApp"**: pick a confirmed contact, open the chat with text filled in, you press Send. Exact-match contacts with confirmation.
- **Done when:** It never sends by itself, and the button says so. Remove `pywhatkit`.

### 17. Telegram 🟠
- **Today:** Sender allowlist is good. But it calls `/api/chat` with no token, relying on the hole, and reaches shell commands through `handle_local`.
- **Build:** Internal authenticated service call. Telegram gets Read and Reversible by default. Approvals via inline buttons. Split long replies. Off until set up.
- **Done when:** Other users are ignored, and no dangerous action can run from Telegram.

### 18. GitHub 🟡
- **Today:** Solid backend respecting polling limits. No screen beyond a count.
- **Build:** Notifications list, PR/issue review summaries, token in vault.
- **Done when:** The count opens a real list you can act on.

### 19. YouTube download 🟡
- **Today:** Works through `yt-dlp` with a 10-minute limit and no progress.
- **Build:** Decide first: does this fit the assistant? If kept: progress, queue, cancel, destination, `ffmpeg` handling, updates, and a note about respecting copyright and site terms.
- **Done when:** A long download shows progress and can be cancelled.

---

## 9. Feature plans: workbench

### 20. Workflows → Automate 🔴
- **Today, cards vs code:**

| Card promises | Code does |
|---|---|
| Study: silences notifications, opens notes, 50-minute timer | Opens VS Code and a Spotify playlist, sets volume |
| Dev: checks Git, starts servers | Opens VS Code and a terminal |
| Deep focus: blocks sites | Sets volume, closes Discord |
| Gaming: raises performance, pauses sync | Opens apps, force-kills Chrome and VS Code, which can lose unsaved work |

- **Build:** A real engine: typed steps with parameters, preview, per-step results, stop on failure. Triggers: voice, hotkey, schedule, event. Close apps gracefully and ask about unsaved work. Generated text describes actual steps, so it can't drift. Ship 4–5 templates users can edit.
- **Done when:** The preview matches what runs, each step reports success or failure, and a failed step is clear.

### 21. Terminal 🟠
- **Today:** One command at a time, 30-second limit, no interactivity, policy differs between `server.py` and `main_app.py`.
- **Build:** **ConPTY through `pywinpty`, with `xterm.js`** over a local WebSocket. Tabs, resize, copy/paste, Ctrl+C. Only the user types; if AI suggests a command, the user approves it.
- **Done when:** `python`, `git`, `npm run dev`, and `vim` all work interactively, and processes close with the tab.

### 22. Workspace and editor 🟠
- **Today:** A textarea and a file list. Direct overwrites.
- **Build:** **CodeMirror 6**, which is lighter than Monaco and enough for this. Tabs, syntax highlighting, search, unsaved markers, atomic save, detection of outside changes. Move to Monaco later only if IntelliSense becomes a goal.
- **Done when:** You can't lose edits by accident, and a 5 MB file doesn't freeze the UI.

### 23. Code studio 🔴
- **Today:** The UI says "verification sandbox" and "Sandbox ready". In reality code either runs directly on the PC or is blocked. `coder.py` itself admits a timeout isn't a sandbox.
- **Your PC:** Windows 11 **Home**. As far as I know, Windows Sandbox needs Pro or higher, so it can't be the default. Confirm before relying on it.
- **Build:** Offer honest levels: **Docker** if installed (no network, limited resources), then **Limited** (restricted process, Job Object limits, temp folder, clearly labelled "not a full sandbox"), then **On your PC** with approval. Evaluate AppContainer later. Show the level beside Run.
- **Done when:** A test script trying to read personal files or reach the network is stopped at any level that claims to stop it.

### 24. Screen and image vision 🟡
- **Today:** Works with Groq vision models, with hardcoded names. OCR needs Tesseract installed separately. Replies are spoken automatically.
- **Build:** Use the provider layer. Screenshot picker: window, region, or monitor, with a preview before sending. Evaluate built-in Windows OCR so no install is needed.
- **Done when:** Users always see the exact image before it leaves the PC.

### 25. Documents 🟡
- **Today:** Extracts PDF, DOCX, XLSX, PPTX text. No scanned PDFs. `.doc` is likely mishandled by `docx2txt`. Long files can overflow context.
- **Build:** Chunk, index locally, and answer with page citations. OCR for scans. Clear size limits. Add to Library.
- **Done when:** A 300-page PDF can be queried with accurate citations.

### 26. Skills catalog 🔴
- **Today:** Hardcoded list. The GET call fails, and toggles affect only a few tools.
- **Build:** Generated from the real tool registry. Toggles enforced in one place, with risk level shown.
- **Done when:** Turning a skill off is enforced by a test.

### 27. Plugins 🟠
- **Today:** Runs any `.py` in the plugins folder with full access.
- **Plan:** **Pause for v2.** Later, support MCP servers with permissions and approvals, rather than inventing a plugin system.

### 28. Meeting mode 🔴
- **Today:** No screen calls it. It records the mic only, holds audio in memory, fails silently with `print`, and uses a retired model. Results land in one long task.
- **Build:** Mic plus system audio through WASAPI loopback (`PyAudioWPatch`). Save to disk as it records. Visible recording indicator with a **required reminder to tell participants**, since consent laws vary. Local or chosen-cloud transcription. Output: transcript, summary, decisions, separate tasks. Delete controls.
- **Done when:** A 2-hour meeting finishes with no memory growth, and a crash keeps the audio recorded so far.

### 29. Vision Recall 🟠
- **Today:** Off by default, periodically OCRs the screen into memory, which can capture passwords and private messages.
- **Plan:** **Pause for v2.** Later only with app exclusions, encryption, retention limits, and a visible pause.

---

## 10. Feature plans: security

### 30. Shield → Security Check-up 🟡
- **Today (14 Nov 2026):** Defender decides by exit code; four honest verdicts; no invented names; EICAR and locked-file checks pass on a real PC. The "Today" list below is the starting state from the original review.
**This has the widest gap between claim and reality.**

- **Today:**
  - All five "Active shields" are just saved settings. **No code runs behind them.**
  - `system_protected` defaults to true even if Defender is unavailable (`antivirus.py:680`).
  - Failed scans return `clean: True` (`antivirus.py:185,190,235`).
  - Findings get invented names like `Trojan.DoubleExtension.Dropper`.
  - Defender results are found by text matching on output.
  - Patterns only scan the first 64 KB. Port 8888 counts as a mining port, and it's KALKI's own default port.
  - Quick scan stops at 250 files and may hit noisy temp folders.
- **Build:**
  - **Name and message:** "Security Check-up. KALKI isn't an antivirus. It works with Windows Defender."
  - **Engine:** Defender (`MpCmdRun`) using documented exit codes. Report "couldn't scan" separately.
  - **Status:** Real Defender state, signature age, last scan.
  - **Features that can be real:** Downloads folder watch (scans new files with Defender), startup items review, optional process check with fewer false alarms, clipboard address-swap warning.
  - **Extras:** Optional YARA rules with a credible source. Optional VirusTotal hash lookup, user's own key, sending only hashes after consent. The free tier has strict limits and non-commercial terms.
  - **Language:** "Suspicious because…" rather than a fake malware name. Quarantine with restore; no automatic removal.
- **Done when:** The EICAR test is detected through Defender. A locked file shows "couldn't scan". Turning a watcher off stops it. False-alarm rate is measured on a clean PC. No screen says "Protected" unless Defender confirms it.

### 31. Cyber tools 🟡 — keep all, make each real
- **Keep every tool:** Hash and hash identify, hash cracking (dictionary), encode/decode, DNS, HTTP headers, TLS certificate, CVE lookup, subdomains, GitHub dorks, attack-surface brief, port scan, Wi-Fi profile and password read, public IP and IP info, ping, Wi-Fi profiles.
- **Build:** Real progress and cancel for long jobs (scans, cracking, subdomains). Result history and export. One consistent tool layout. Replace today's rate limiting, which only covers GET requests, so these POST tools have none today.
- **Wi-Fi (your own PC):** Built as its own tab (feature 45). Showing a saved password needs a Windows prompt every time, and it hides itself after 30 seconds.
- **Anything touching another host** (port scan, web/deep scan, subdomains, attack surface): one-time per-domain "I'm authorized to test this" confirmation, recorded, then it runs fully.
- **Reverse-shell payloads:** Stay disabled, and this plan doesn't rebuild them.
- **Done when:** every tool returns real results, long jobs can be cancelled, and each tool has a test.

### 32. Web and deep scan 🟡
- **Today:** Real checks (TLS, headers, paths, secrets, Playwright), with active SQLi and XSS probes.
- **Build:** "I own or may test this site" confirmation, recorded per domain. Passive by default, active by choice. Reports with severity and fixes. Deep scan downloads its browser only when needed.
- **Done when:** Active tests can't run without consent, and tested against a known vulnerable local test site, with known false-positive rate.

### 33. Process manager 🟡
- **Build:** Kill by exact PID, not name fragments (`proc_name in name` could match many apps). Protect system processes. Show publisher and signature where possible. Approval for each kill.
- **Done when:** A vague name can't kill several apps by accident.

### 34. Oversight and watchdog 🟡
- **Today:** Site and certificate checks and thresholds are real. Sample text fills the empty diagnostics panel. Checks mostly run on demand.
- **Build:** Scheduled checks, downtime history, certificate expiry warnings, alert rules with quiet hours, real logs. Merge approvals into Activity.
- **Done when:** A site going down produces one alert, recovery produces one, and no alert storms.

---

## 11. Feature plans: platform

### 35. Settings 🟡
- **Build:** Typed settings (F5), search, per-setting validation, and tests. Only secret status displayed. Export never includes secrets.
- **Done when:** A settings file with bad values can't stop the app starting.

### 36. Vault 🟡
- **Today:** Save-only in the UI by design, and two implementations. Base64 "encryption" fallback.
- **Decide:** Is a password manager in scope? **Recommendation:** Use the vault only for KALKI's own keys and tokens. Dedicated password managers do the rest better, and an AI-connected password store carries risk.
- **Done when:** No secret appears in files, logs, backups, or AI prompts. Tested by scanning for planted fake secrets.

### 37. Backup and restore 🟡
- **Today:** A plain zip, which may contain plaintext settings. DPAPI data won't restore on another PC.
- **Build:** Password-encrypted backup, schedule, integrity check, restore preview, and automatic backup before each migration or restore. Clearly show which secrets need re-entering on a new PC.
- **Done when:** Tested restore on a clean machine or profile succeeds, and a corrupted backup is rejected safely.

### 38. Cloud sync 🟠
- **Today:** Firebase Admin credentials on the desktop are the wrong model: admin keys bypass access rules and aren't meant to be distributed. The encryption itself looks reasonable.
- **Plan:** **Cut.** Replace with encrypted backups saved to a folder the user picks, such as OneDrive or Google Drive. No server for you to run and secure.

### 39. First run 🟡
- **Plan:** Replace the separate 8-step CustomTkinter wizard (§5.4). Keys are tested live. Skip anything optional.
- **Done when:** A new user gets a real AI answer within 3 minutes, tested with real people.

### 40. Updater 🔴
- **Today:** Downloads and runs at boot with no consent. Weak URL check. Hash comes from the same place as the file, so it detects corruption, not a compromised release.
- **Build:** "Update available" with notes, then the user chooses. Exact host check. Signature verified before running. Rollback path. No self-update in Store builds.
- **Signing:** Microsoft's Artifact Signing is only open to individuals in the US and Canada. If you're in India, the options are an OV certificate (about $150–300 a year per Microsoft) or the Microsoft Store. SmartScreen warnings may remain until reputation builds.
- **Done when:** A tampered installer is refused, and declining an update is respected.

### 41. Telemetry 🟢
- **Today:** Off by default, which is right, but the README badge says "Zero Telemetry" while Sentry and PostHog code exist.
- **Build:** Keep opt-in. Crash reports with scrubbing and a preview. Correct the wording.
- **Done when:** Privacy page, README, and behaviour all match, verified with a network capture.

### 42. Desktop pet 🔴
- **Today:** `/pet` hits a missing function. It polls about once a second. It builds HTML with unescaped text (`pet_overlay.html:519`). The README says 3D; the latest commit says pixel.
- **Build:** Proper auth, event-driven updates, click-through handling, low CPU, and off by default. Do this after the core is solid.
- **Done when:** Idle CPU is near zero, with no taskbar or fullscreen-game issues.

### 43. Command palette and hotkey 🟢
- **Build:** Search across all content through the new search API. Show shortcuts, make the global hotkey configurable with conflict handling.
- **Done when:** Every main action can be reached from Ctrl+K.

### 44. Linux and macOS 🟠
- **Plan:** Move Windows code behind `platform/`. Mark as experimental. Fix `package_linux.sh` version. Promote only when CI and manual checks pass.

### Website and README
- Remove or correct claims before the next release: "100% Local-First", "Zero Telemetry", "Antivirus", "Real-time", "3D". Claims must come from the feature status, and be re-checked before each release.
- Remove the duplicate zip, one-off `tools/` patch scripts, hardcoded `e:\` paths, and outdated docs (the docs mention v2.0.0).

---

## 12. Roadmap

Estimates are rough, assuming one developer working full-time with AI help. They'll change once we see real progress.

| Phase | Goal | Includes | Rough time | Finished when |
|---|---|---|---|---|
| **0. Stop the bleeding** | Safe and working | F1 | 2–3 days | Chat works; attack tests fail; feature check passes |
| **1. Foundations** | Safe to change code | F2, F4, F5, F7, start F3; real-account testing to confirm ratings | 2–3 weeks | CI gates live; data migrated with a tested rollback |
| **2. Design system and shell** | New look and structure | §5.5, navigation, first run, status menu | 2–3 weeks, partly alongside Phase 3 | Prototype approved; no fake status anywhere |
| **3. Core assistant** | The product's heart | F6, features 1–6 | 4–6 weeks | Daily chat and voice for a week without critical bugs |
| **4. Daily and integrations** | Daily usefulness | 7–19 | 4–5 weeks | Each integration passes the 8 rules with a real account |
| **5. Workbench** | Power features | 20–26, 28 | 4–5 weeks | Terminal, editor, and automations pass their tests |
| **6. Security (moved up: do right after Phase 0)** | Every security feature really works | 30–34, 45 | 2–3 weeks | EICAR and false-alarm tests pass |
| **7. Release** | Ship v2 | 35–44, signing, docs, website | 2–3 weeks | Clean-machine tests pass; signed build; 5–10 beta testers |

**Total:** roughly 5–7 months full-time. Doing all of it isn't required before releasing. A strong **v2.0 could be Phases 0–4 plus 7, around 3–4 months**, with Studio and Security marked Beta.

### Priorities if time is short
1. **Must have:** Phase 0, foundations, chat, memory, approvals, tasks and reminders, new UI shell.
2. **Should have:** Voice, calendar, mail, media, automations.
3. **Nice to have:** Terminal, editor, meetings, check-up improvements.
4. **Later:** Pet polish, plugins/MCP, Vision Recall, Linux and macOS.

### First work items once you approve
1. Commit or review the 5 uncommitted files, so fixes stay separate.
2. Fix the shadowed imports, with a test that fails before the fix.
3. Close the auth hole, moving Telegram and the pet to proper auth in the same change.
4. Remove hardcoded status text and correct the "Protected" logic.
5. Turn on Ruff F821/F823 in CI.
6. Decide on replacing v1.5.0 if it's public, since the same bugs appear in its source.

---

## 13. Research sources and gaps

Many sources are vendor blogs or community posts. **Check official docs and test on real hardware before committing to anything.**

**Voice:** [openWakeWord](https://github.com/cnhup/openWakeWord) · [wake-word comparison](https://www.promptquorum.com/power-local-llm/build-local-voice-assistant-2026) · [Picovoice free-tier report](https://community.home-assistant.io/t/fyi-picovoice-confirmed-free-tier-accesskeys-will-stop-working-after-june-30-2026/1012744) · [faster-whisper VAD filter](https://theneuralbase.com/faster-whisper/learn/intermediate/vad-filter-true-silero-vad/) · [Piper releases](https://github.com/OHF-Voice/piper1-gpl/releases)

**AI providers:** [Groq deprecations](https://console.groq.com/docs/deprecations) · [g4f prompt-routing report](https://letsdatascience.com/news/gen-digital-report-flags-unclear-prompt-routing-in-gpt4frees-205e62a2)

**Security:** [Excessive agency write-up](https://aembit.io/blog/owasp-top-10-llm-risks-explained/) · [Chrome Local Network Access](https://developer.chrome.com/blog/local-network-access) · [MpCmdRun reference](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus) · [YARA from Python](https://github.com/VirusTotal/yara/blob/v4.3.1/docs/yarapython.rst) · [VirusTotal API notes](https://documentation.wazuh.com/4.2/user-manual/capabilities/virustotal-scan/about.html)

**Data:** [Hybrid search with FTS5 and sqlite-vec](https://dev.to/soytuber/building-a-hybrid-rag-in-200-lines-sqlite-fts5-sqlite-vec-rrf-38h1) · [fastembed provider notes](https://glama.ai/mcp/servers/@basicmachines-co/basic-memory/blob/07778790d33c0d002361204b166c755326d84312/docs/semantic-search.md)

**Integrations:** [Spotify 2026 update](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security) · [Spotify migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) · [Google restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) · [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) · [WhatsApp send messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages)

**Workbench:** [pywinpty](https://pypi.org/project/pywinpty/2.0.1/) · [node-pty and xterm pattern](https://docsearch.algolia.com/mcp/docs/repo/microsoft/node-pty) · [Sourcegraph: Monaco to CodeMirror](https://sourcegraph.com/blog/migrating-monaco-codemirror) · [Replit: CodeMirror](https://blog.repl.it/codemirror) · [Windows app isolation](https://learn.microsoft.com/en-us/windows/security/book/application-security-application-isolation) · [Windows sandboxing write-up](https://explore.n1n.ai/blog/building-secure-sandboxes-code-execution-windows-2026-05-14)

**Meetings:** [PyAudioWPatch](https://pypi.org/project/PyAudioWPatch) · [WASAPI loopback](https://msdn.microsoft.com/en-us/library/vs/alm/dd316551) · [Recording-law overview](https://www.avoma.com/blog/call-recording-laws)

**Release:** [Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) · [Artifact Signing quickstart](https://learn.microsoft.com/azure/artifact-signing/quickstart)

**UX:** [Designing for agentic AI](https://smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/) · [Fluent 2 for Windows](https://fluent2.microsoft.design/components/windows) · [What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)

**Not confirmed, must check before relying on it:**
- Microsoft Store policy on security tools and `runFullTrust` apps.
- `MpCmdRun` full exit-code meanings.
- Whether a local-only desktop app avoids Google's security assessment.
- How reliable `edge-tts` is, and its terms (research came up empty; "unofficial" is my understanding).
- Windows Sandbox on Home editions (my understanding, not checked in this research).
- WhatsApp click-to-chat details (`wa.me`), which the search didn't cover.
- Real speed of local speech models and wake accuracy on your hardware.
- Windows Do Not Disturb automation options.
