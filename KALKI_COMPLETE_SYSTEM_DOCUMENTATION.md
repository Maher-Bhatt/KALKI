# KALKI Complete System Documentation

**Version 2.0.0 · Filament frontend rebuild · Written September 19, 2026**

This is the canonical technical and product reference for KALKI as it exists after the v2.0.0 rebuild. It describes the actual repository — every route, file, and constraint below was read from source, not designed and left unverified. Where a section covers something outside this rebuild's scope (a Windows GUI acceptance pass, a live PyInstaller build), that is stated explicitly rather than implied.

A new developer or AI agent should be able to work on KALKI from this document alone, without first reading all 6,000+ lines of `server.py`.

---

## A. Product overview

**What KALKI is.** A local-first, voice-capable personal AI assistant that runs entirely on one machine: a Python HTTP server (`server.py`), a desktop shell (`main_app.py`, PyWebView), an out-of-process voice listener (`listener.py`), and — as of this release — a 27-module frontend under `app/ui/`. Every capability (chat, memory, tasks, voice, vision, workflows, a cybersecurity toolkit) is reached through one authenticated local API on `127.0.0.1`.

**The problem it solves.** Most AI assistants are either cloud chat windows with no access to the user's actual machine, or narrow single-purpose tools. KALKI is the reverse bet: a single personal intelligence layer with real system access (voice, screen, files, calendar, tasks), running under the user's own control, with no data leaving the machine unless the user explicitly connects an integration.

**Interaction model.** Five destinations — Ask, Today, Memory, Workbench, Settings — plus a gated Security workspace. Ask is the primary surface: a streaming chat thread with a composer that also accepts voice, attachments, and screen capture. A command palette (`Ctrl/Cmd+K`) reaches every action, conversation, and setting from one keystroke, so the navigation rail can stay at five items instead of becoming a wall of icons.

**Design philosophy.** Documented in full in `KALKI_DESIGN_SYSTEM.md`; summarized here: cold graphite surfaces, one warm-platinum presence mark that lives in the navigation rail rather than at screen center, and a strict rule that every animation reports a state change — nothing animates while idle, because the packaged app runs WebView2 with GPU compositing disabled (`--disable-gpu`, set in `main_app.py` to avoid driver-specific hangs), so every frame is rasterized on the CPU.

---

## B. Complete architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Desktop shell (main_app.py)                                        │
│  PyWebView window, --disable-gpu, min 960×680, system tray,         │
│  single-instance lock, safe-mode / updating fallback pages          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  WebView2 / Chromium (Linux: system browser)                 │   │
│  │  loads http://127.0.0.1:<port>/                               │  │
│  │  ┌───────────────────────────────────────────────────────┐   │  │
│  │  │  Frontend — app/ui/ (27 ES modules, no build step)     │   │  │
│  │  │  shell → router → features (ask/today/memory/          │   │  │
│  │  │  workbench/security/settings) → api/ adapters          │   │  │
│  │  └───────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬────────────────────────────────────┘
                                │ HTTP + SSE, token/cookie auth
┌──────────────────────────────▼────────────────────────────────────┐
│  server.py — stdlib http.server, ThreadingHTTPServer                │
│  83 routes: chat, memory, tasks, notes, calendar, mail, spotify,    │
│  whatsapp, github, workflows, code, vision, cyber/*, settings,      │
│  vault, backup, /ui/* static assets                                 │
│  ├─ core/ subsystems: model routing, productivity, meeting mode,    │
│  │   file intelligence, vision memory, telegram, cloud sync,        │
│  │   API vault, telemetry, updater, state, location                 │
│  ├─ semantic_memory.py — embeddings + pinned-always-retrieved        │
│  ├─ tasks.py, notes.py, workflows.py, vault.py, vision.py,           │
│  │   coder.py, webscan.py, deepscan.py, runtime_security.py          │
│  └─ config.py (user-writable) / config.example.py (template)         │
└──────────────────────────────┬────────────────────────────────────┘
                                │ POST /api/wake, /api/chat (source: voice)
┌──────────────────────────────▼────────────────────────────────────┐
│  listener.py — separate process                                     │
│  wake-word matching (WAKE_WORDS, optional offline Vosk),             │
│  audio capture, posts to the server; can hold a full conversation    │
│  while the desktop window is closed                                  │
└─────────────────────────────────────────────────────────────────────┘

Model providers: Groq (primary, llama-3.3-70b-versatile chat /
llama-4-scout vision) → Ollama (local fallback) → optional OpenAI /
Anthropic / Gemini per role. TTS: edge-tts, default voice
en-GB-RyanNeural, provider fallback chain surfaced via ttsProvider /
ttsLastError / ttsProbeError on /api/status.
```

**Processes.** Up to three run concurrently: the desktop shell (`main_app.py`), the HTTP server (`server.py` — may run in the same process as the shell or as a spawned child depending on packaging; both source and packaged layouts start it before the window loads), and the voice listener (`listener.py`). On Linux, `linux_launcher.py` starts the server and opens the system browser instead of embedding WebView2.

**Storage.** Everything is flat JSON or an encrypted blob under one per-user data directory (§L) — no database server, no ORM. This is why conversation history has no ID scheme (§H) and why the frontend, not the backend, now owns conversation organization.

---

## C. Full runtime lifecycle

```
launch
  → runtime_paths.prepare_runtime()
      resolves app_root, provisions config.py from config.example.py
      on first run (or a per-user copy if the install directory is
      read-only, e.g. an MSIX install), sets sys.path
  → config.py imported (secrets, model choice, theme keys, feature flags)
  → server.py starts: ThreadingHTTPServer on 127.0.0.1:<port>,
      per-install token written to <user_data_dir>/api_token.txt
  → listener.py started as a separate process (unless disabled)
  → main_app.py opens the PyWebView window
      --disable-gpu injected into WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
      window loads http://127.0.0.1:<port>/  (or a safe-mode/updating
      page instead — see below)
  → index.html (41 lines) loads /ui/main.js as an ES module
  → main.js: loadUi() → buildShell() → installShortcuts() →
      loadThreads() (IndexedDB) → ensureActive() → startStatus()
      (single /api/status poller) → startRouter() → first render
  → steady state: user interacts; listener.py may independently
      call /api/wake or /api/chat with source: "voice" at any time,
      even while the window is closed
shutdown
  → tray "Quit" or window close → server and listener processes
      terminated; system tray icon removed (pystray)
```

**Degraded-start paths**, both served as static HTML instead of `index.html` (they bypass the SPA entirely and must stay dependency-free):

| Condition | What loads | File |
|---|---|---|
| `crash.log` present from a prior run | Safe-mode page — offers "Clear crash log and restart" | inline HTML in `main_app.py` / `server.py` |
| `updating.lock` present | Updating page — polls `updateProgress` from `/api/status` | inline HTML |

**Failure behavior by subsystem:**

| Failure | User-visible effect |
|---|---|
| Server unreachable | Frontend's offline banner ("KALKI's local service isn't responding"), `/api/health` used to detect recovery. App stays interactive against cached state |
| Listener process dies | `/api/status` stops advancing `conversationSeq`; voice UI settles to `unavailable` since no fresh status confirms `ready` |
| Model provider down | `groqConfigured` false or the Groq call itself fails → falls back to Ollama if `ollamaOnline`; if neither, chat surfaces "No model is available" |
| Microphone unavailable | `listenerCapabilityNotice` on `/api/status`, shown verbatim in Settings → Voice |
| TTS fails | `ttsLastError` / `ttsProbeError` populate; presence mark shows a warning badge; text reply still completes |
| Integration not configured | Never treated as an error — `configured: false` is a designed state with a "Connect" action (Today, Settings → Integrations) |

---

## D. Frontend architecture

Full detail in `KALKI_FRONTEND_ARCHITECTURE.md`; summary here.

**No build step.** Native ES modules, served directly by `server.py`'s `/ui/*` route (§K). Edit a file, reload — identical in development and in a packaged install.

```
app/index.html        41 lines: boot screen, #app, <script type="module" src="/ui/main.js">
app/ui/
  main.js             boot, router wiring, global shortcuts
  tokens.css          every design token (color, type, space, radius, motion)
  base.css            reset, type roles, control primitives
  app.css             shell layout, rail, thread, composer, dialogs, responsive rules
  lib/                dom.js (h() hyperscript), format.js, icons.js (41 inline SVGs),
                       markdown.js (streaming-safe), idb.js, keys.js
  api/                client.js (fetch wrapper + error-kind mapping), stream.js (SSE),
                       endpoints.js (typed adapters over all 83 routes)
  state/              store.js (single observable store), status.js (the one
                       /api/status poller — see §F), conversations.js (IndexedDB)
  components/         dialog.js (native <dialog>), presence.js (the filament),
                       states.js (empty/error/skeleton)
  features/           shell.js, router.js, palette.js, diagnostics.js,
                       ask.js, today.js, memory.js, workbench.js,
                       security.js, settings.js
```

**Routing.** Hash-based (`#/ask`, `#/memory`, `#/settings/models`) rather than the History API, because recovery and Linux browser-mode paths can load from `file://`, where `pushState` is unreliable.

**State.** One observable store (`state/store.js`); features read via selectors and write via actions, never call `fetch` directly. Re-renders are coalesced to one per animation frame.

**Conversations.** The backend has no conversation database — `history.json` is a flat, unindexed list capped at `MAX_HISTORY` (20 entries = 10 exchanges). The frontend owns organization (title, pin, search, timestamps) in IndexedDB; `history.json` stays what it actually is, the model's rolling context window, stated honestly on the composer ("N of 10 turns in context") rather than hidden. Full rationale in §H.

**Design tokens.** Centralized in `tokens.css`. Surfaces run a six-step near-black luminance ramp (`--surface-void` through `--surface-float`); the one warm color, `--filament` (`#fff4e2`), is reserved for the presence mark, the active-nav indicator, and the focus ring — never more than roughly 2% of any screen.

---

## E. Backend / API architecture

`server.py` is a single `ThreadingHTTPServer` subclass with one `Handler(BaseHTTPRequestHandler)`. Routing is a flat `if path == "..."` chain in `_do_get_inner` / `_do_post_inner` — there is no framework, no decorator-based routing, and no ORM.

**Authentication.** Every route except `/`, `/index.html`, `/manifest.json`, `/service-worker.js`, `/api/health`, `/favicon.ico`, and `/assets/*` requires either the `X-KALKI-Token` header or the `kalki_session` cookie set when `/` is first served. `_require_auth` enforces this before any handler body runs, including the new `/ui/*` route (§K).

**Error shape.** `_safe_call` wraps handler bodies and returns `{"ok": false, "error": str(exception)}`, sometimes with HTTP 200 and sometimes with a non-2xx status — callers must check `data.ok === false` regardless of status code. The frontend's `api/client.js` does exactly this and never surfaces the raw exception text as a primary message (§P).

**Full route reference.** The authoritative, generated-from-source table is `KALKI_FRONTEND_CAPABILITY_MAP.md` §1–§9 (87 rows post-rebuild, covering all 83 pre-existing routes plus `/api/history` and the `/ui/*` static route). It is not duplicated here to avoid the two documents drifting apart; treat the capability map as the single source of truth for request/response shapes and read it alongside this section. The table below covers only what changed in this release:

| Route | Method | Added in | Purpose | Auth | Frontend consumer |
|---|---|---|---|---|---|
| `/ui/*` | GET | v2.0.0 | Serves the frontend bundle with a content-type allowlist | required (after `_require_auth`) | Every `<script>`/`<link>` in `index.html` |
| `/api/history` | GET | v2.0.0 | Returns `load_history()` and `MAX_HISTORY` | required | `state/status.js`'s voice-exchange reconciliation (available but not yet wired into the boot sequence — see §S) |

**Server-side changes made for this release** (all additive; see `CHANGES.md` v2.0.0 for the full list): the `/ui/*` route itself (§K), `GET /api/history`, and `cached_mem_count()` / `cached_hardware_stats()`, which cache `/api/status`'s two most expensive fields for 5 seconds — previously `len(load_memory())` re-read and JSON-parsed the entire memory file on every poll, which at the old fixed 1.5-second polling interval ran roughly 2,400 times an hour.

---

## F. Voice pipeline

```
listener.py (separate process)
  → continuous audio capture
  → wake-word match against WAKE_WORDS
      ["hey kalki", "kalki", "hey sir", "ok kalki"]
      (optional offline Vosk model for wake detection without network)
  → POST /api/wake  (sets wakeRequested; may carry an inline {cmd})
  → POST /api/chat  {source: "voice", clientSpeech: true, messages: [...]}
  → server.py routes to the configured model provider
  → reply spoken via edge-tts (default voice en-GB-RyanNeural)
  → server.py appends the exchange to history.json and increments
    an in-memory conversationSeq, exposed via /api/status as
    { conversationSeq, recentExchange: {seq, user, reply, ts} }
```

**The frontend does not drive voice — it observes it.** This is a deliberate, stated design constraint (`KALKI_FRONTEND_ARCHITECTURE.md` §5), not an oversight: KALKI can hold a full conversation with the desktop window closed, and the only way the frontend learns about it is by polling `/api/status`.

**Voice states the UI can actually verify**, derived in `state/status.js`: `unavailable`, `mic-released`, `mic-muted`, `ready`, `attending` (a 4-second window after `wakeRequested`, which the server clears on read — exactly one poller may consume it, or wake events are lost), `thinking` (a request from this client is in flight), `speaking` (`speaking === true`), `interrupted` (after `/api/stop` succeeds). **`listening` and `interpreting` are deliberately absent** — the backend does not report whether audio is currently being captured or transcribed, and animating an unverified state would be exactly the "dead UI" the rebuild brief prohibited. Unlocking them needs one additive change: `listener.py` reporting a coarse phase (`idle` / `heard-wake` / `capturing` / `transcribing`) that `/api/status` echoes. Not made in this release; documented as the next voice-fidelity improvement.

**TTS failure surfaces** as `ttsLastError` / `ttsProbeError` / `ttsProvider` / `ttsLastLatencyMs` on `/api/status`, shown as a warning badge on the presence mark and tested from Settings → Voice → "Test voice" (`POST /api/tts/test`).

---

## G. Chat pipeline

```
composer (features/ask.js)
  → conv.addMessage({role:'user', ...})        [IndexedDB, immediate]
  → conv.addMessage({role:'assistant', streaming:true})
  → api/stream.js: streamChat(wireMessages, handlers)
      POST /api/chat {messages, stream:true}
      reads the SSE body: data:{token} ... data:{done, model}
      (a local-command fast path may answer {token, done:true} in one frame)
  → onToken: patchStreaming() updates only the streaming message's
      DOM node directly (not a full re-render — the single most
      expensive thing this app could do per token)
  → onDone: conv.updateMessage(..., {content, streaming:false, model})
  → aria-live region announces the accumulated text on a 400ms
      throttle, never per token
```

**Markdown rendering** (`lib/markdown.js`) builds DOM nodes directly — never `innerHTML` — so model output can never inject markup. An unterminated ` ``` ` fence is held back as plain text until the closing fence arrives, which is what stops half-parsed code blocks flickering mid-stream.

**Stopping** calls both `AbortController.abort()` (halts the fetch) and `POST /api/stop` (halts server-side generation and speech) — stopping the text without stopping speech was identified as a real defect during design and is why both calls exist together in `api/stream.js`.

**Context transparency.** The composer shows "N of 10 turns in context", computed from `MAX_HISTORY = 20` (10 exchanges). This is stated, not enforced by the frontend — the server truncates independently, and the number is informational.

---

## H. Memory pipeline

**Two systems exist in the codebase**, and the UI is built entirely on the second:

1. **Legacy** (`/api/memories` GET, `/api/memory` POST) — a flat list of strings, no metadata, never called by the v2.0.0 frontend except once.
2. **Semantic** (`semantic_memory.py`, `/api/memory/list|add|update|delete`) — records with `{id, text, tags, importance (1–10), type, created_at}`. `type: "pinned"` is not a cosmetic label: `semantic_memory.search()` merges every pinned document into results regardless of similarity score, so pinning in the UI performs the real backend behavior, not a client-side sort hint.

```
capture: user or KALKI writes a memory
  → POST /api/memory/add {text, tags, importance, type}
  → semantic_memory.py stores it and computes an embedding
retrieval: a chat turn is being answered
  → semantic_memory.search(query) — pinned docs always included,
      others ranked by embedding similarity
  → relevant memories are folded into the model's prompt context
    (server-side; the frontend has no visibility into this step)
UI management (features/memory.js)
  → list, search (substring, client-side, over the fetched set),
    filter by type/importance, pin/unpin, edit, delete-with-undo
```

**Legacy import.** On first visit to Memory, the frontend checks the legacy endpoint; if non-empty, a one-time banner offers "Import N older memories", which re-POSTs each entry through `/api/memory/add` and never shows the banner again for that session (`sessionStorage` flag). This was a deliberate product decision to avoid presenting two memory systems as two competing products.

**Degraded state.** If the embedding backend is unavailable, the memory list still loads and edits still work; search degrades to substring matching, and the UI states this plainly rather than silently returning fewer results.

---

## I. Task / reminder pipeline

```
tasks.py: {id, text, added, done}
  list  → POST /api/tasks/list {all}
  add   → POST /api/tasks/add {text}           (400 on empty text)
  complete → POST /api/tasks/complete {id|text}
  delete → POST /api/tasks/delete {id|text}

reminders: {id, text, due}
  list → POST /api/reminders/list
  add  → POST /api/reminders/add {text, due}   (400 without both)
  tasks.parse_when() accepts natural language for `due` — the UI
  sends the user's raw phrase rather than forcing a date picker
```

**Voice-created tasks.** `POST /api/wake` parses `[TASK: ...]` and `[REMIND: ... @ ...]` tokens out of model replies and creates records automatically — a task can appear in Today that the user never typed. This is why Today exists as a real surface rather than a notification: it is the place those auto-created items become visible and actionable.

**Known gap, not closed in this release.** `tasks.delete_reminder()` exists in `tasks.py` but has no route, so reminders can be listed and added but not deleted from the UI. The frontend omits a delete control for reminders rather than pointing at a non-existent endpoint (per the "no dead UI" rule) — adding the three-line route is a documented next step (`KALKI_FRONTEND_CAPABILITY_MAP.md` §10).

---

## J. Workflow / tool pipeline

```
intent: user runs a mode from Workbench, or a chat reply requests a
  workflow
  → POST /api/workflow {mode}
tool selection: workflows.py resolves the mode (list_modes(),
  find_mode() for fuzzy matching), including user-defined routines
  via add_custom_routine()
confirmation gate: destructive modes call
  _queue_confirmation() server-side, which holds a pending action
  for a 30-second TTL
  → the frontend's confirmDialog() shows what will run and a
    countdown matching that real deadline, not an invented one
execution: the mode's effect is applied (voice profile change,
  system volume, etc.)
result: {ok, result|message} → toast in the UI; failures show the
  mapped message with raw detail behind "View details"
```

Code generation/execution (`/api/code/generate`, `/api/code/run`) is a separate, adjacent capability surfaced in the same Workbench view: generation is unguarded, but running generated code always shows a confirmation dialog first and is gated by `coder.host_execution_enabled()` server-side — the sandbox model is described in `SANDBOX.md` / `verification_sandbox.py` and this documentation does not weaken it.

---

## K. Security architecture

**Network exposure.** `ThreadingHTTPServer` binds `127.0.0.1` only. It is never exposed through port forwarding, a reverse proxy, or a non-loopback interface — this is a stated operational requirement, not something the server enforces itself.

**API token.** A per-installation token is written to `<user_data_dir>/api_token.txt` on first run and required (via `X-KALKI-Token` or the `kalki_session` cookie) on every route except the small public set listed in §E. `_require_auth` runs before any handler body.

**Secrets.** `SECRET_SETTING_KEYS` (12 entries: Groq, OpenAI, Anthropic, Gemini, ElevenLabs, email app password, GitHub, Shodan, Spotify client secret, Google client secret, cloud-sync passphrase, Telegram bot token) are masked by `_public_settings_value()` before `/api/settings/get` ever returns them. The frontend renders **status only** (`Set` / `Not set`) via `secretStatus`, and writes a replacement value through `/api/settings/save` — it never round-trips a masked string back to the server, and never logs one (`api/client.js`'s call log stores path/kind/status/timing only).

**Vault.** `vault.py`, DPAPI-backed (hardware-bound encryption on Windows), exposed via `/api/vault/save|get|delete`. The Settings → Security UI treats every save as a write-only action — nothing saved to the vault is ever displayed again inside the interface.

**Confirmation model.** Destructive workflows (`_queue_confirmation`, 30s TTL) and code execution both require an explicit confirmation dialog before the server acts. The frontend never lowers a backend gate to make an interaction feel smoother — where the server already asks for confirmation, the UI surfaces that gate; it does not add extra gates the server doesn't have, and it does not remove ones that exist.

**Cybersecurity toolkit.** Thirteen `/api/cyber/*` routes plus `webscan.py`/`deepscan.py` (Playwright-backed). **Hidden from the navigation rail by default** in v2.0.0 — shown only when `SHODAN_API_KEY` is configured or the user enables it in Settings → Advanced. This is the single largest change in how KALKI presents itself: exposing thirteen offensive-security tools to every user by default is what made the previous interface read as a hacking utility. Every tool in the workspace states its scope ("this scans the host you enter — authorised targets only") before running, and port scans remain capped by the server's own `CYBER_SCAN_PORT_LIMIT`.

**No signing certificate ships in this repository.** The `.pfx` present in prior releases has been removed. Local MSIX signing now resolves `KALKI_DEV_CERT_PATH` / `KALKI_DEV_CERT_PASSWORD` from the environment; an unset pair produces an unsigned MSIX, which is what Microsoft Partner Center expects to receive for submission (§M).

---

## L. Data storage

All mutable state lives under one per-user directory, resolved by `runtime_paths.prepare_runtime()`:

| Platform | Base | Full path |
|---|---|---|
| Windows | `%APPDATA%` | `%APPDATA%\KALKI\` |
| macOS | `~/Library/Application Support` | `~/Library/Application Support/KALKI/` |
| Linux | `$XDG_DATA_HOME` or `~/.local/share` | `~/.local/share/KALKI/` |

None of it belongs in source control (`.gitignore` excludes it). Files observed in the codebase: `config.py` (user-writable, provisioned from `config.example.py` on first run — or from a per-user copy when the install directory is read-only, as under MSIX), `user_config.json`, `history.json` (the model's rolling context window, capped at `MAX_HISTORY`), `memory.json` (legacy flat memory), `semantic_memory.json` (the real memory store), `tasks.json`, `reminders.json`, `notes.json`, `productivity.json`, `custom_routines.json`, `contacts.json`, `watchlist.json`, `jokes_seen.json`, `storage.json`, `secure_api_vault.enc` + `vault_integrity.sha256` (the credential vault), `credentials.json` / `google_credentials.json` / `token.json` / `spotify_token.json` (OAuth artifacts), `ai_usage.json` (the data behind `/api/metrics`), `api_token.txt` (the local auth token), and `kalki.log` / `console.log` / `launcher.log` / `linux_launcher.log` / `listener.log` / `crash.log` (diagnostics).

**IndexedDB** (browser-side, new in v2.0.0) holds conversation organization — this is the one piece of KALKI's state that lives in the WebView's storage rather than a server-side file, because it is frontend-owned data with no backend equivalent (§D, §H rationale).

---

## M. Packaging

Five distinct outputs, all built from the same `app/` source tree; none are produced by this documentation pass (§Q states exactly what was and wasn't run).

| Target | Entry point | Notes |
|---|---|---|
| Windows development | `python app/main_app.py` | Loads `app/ui/` directly from disk |
| Portable build | `app/build_tools/build_installer.py` (PyInstaller `--onedir`) | Helper executables under `services/`, per `runtime_paths.py`'s bundle-marker resolution |
| Windows installer (.exe) | `app/build_tools/installer.iss` (Inno Setup) | Now stages `app\ui\*` recursively (v2.0.0 fix — previously only `index.html` was copied, which would have shipped a blank window) |
| MSIX / Microsoft Store | `app/build_tools/build_msix.py`, `microsoft_store/scripts/package.ps1` | MSIX installs are read-only; `prepare_runtime()` provisions a per-user config copy. Both scripts now `shutil.copytree`/`Copy-Item -Recurse` on `app/ui/` and hard-fail if it's missing |
| Linux | `linux/package_linux.sh`, `linux_launcher.py` | Already tarred `app/` recursively, so `app/ui/` was carried automatically; version string bumped to match |

**Signing.** Local development signing resolves `KALKI_DEV_CERT_PATH` / `KALKI_DEV_CERT_PASSWORD` from the environment (§K). Production Store signing and certification are Microsoft Partner Center's responsibility, not this pipeline's — `build_msix.py` explicitly produces an unsigned package when no dev certificate is configured, which is the correct input for Store submission.

**Validation.** Local Store package validation (via `microsoft_store/scripts/package.ps1` and the checklist in `microsoft_store/docs/StoreChecklist.md`) confirms package structure, manifest identity, required assets, entry-point files, and size limits — it does not replace Partner Center's own signing and certification pass.

---

## N. Build prerequisites

- **Python 3.11+** (per `README.md`; `app/requirements.txt` pins ~35 packages including `pywebview>=4.4.1`, `groq>=0.4.2`, `edge-tts>=6.1.9`, `cryptography>=42.0.0`, `pywin32`/`pycaw`/`comtypes`/`wmi` on Windows, optional `vosk` for offline wake-word and `playwright` for the deep-scan security tool)
- **Node.js** — not required to run or package KALKI. Used only for the frontend's own validation tooling (`.github/scripts/validate-ui-modules.mjs`) and CI; the shipped application has zero Node/npm dependency
- **Windows SDK / Inno Setup** for the `.exe` installer build; **MSIX packaging tooling** (`makeappx`, `signtool` if signing) for the Store path
- **WebView2 Runtime** on the target Windows machine (evergreen; KALKI does not bundle it) — `index.html` includes a `<script nomodule>` fallback message if the runtime is too old to execute ES modules
- **Linux**: a system browser for `linux_launcher.py`'s browser-mode path; no WebView2 equivalent needed
- **Environment variables for signing** (optional, dev-only): `KALKI_DEV_CERT_PATH`, `KALKI_DEV_CERT_PASSWORD`

---

## O. Configuration

**Precedence, highest to lowest:** environment variables read directly by specific modules (signing, in particular) → `config.py` (user-writable, in the per-user data directory when the install is read-only, otherwise alongside the app) → `config.example.py` (the shipped template, copied to `config.py` on first run) → hardcoded defaults in `server.py` for any key neither file sets.

**Settings surface.** `GET /api/settings/get` returns `{settings, secretStatus, spotifyConfigured, googleConfigured, cacheSize}`; `POST /api/settings/save` writes a partial patch. The frontend's Settings view (`features/settings.js`) organizes this into thirteen sections (General, Appearance, Voice, Models, Memory, Integrations, Privacy, Security, Performance, Shortcuts, Backup, Advanced, About) — a rebuild of what was previously a flat two-column grid of raw config keys.

**Legacy theme keys.** `THEME_PRESET`, `THEME_MODE`, `THEME_PRIMARY`, `THEME_PEACOCK`, `THEME_INDIGO`, `THEME_SAFFRON`, `THEME_MOTION`, `THEME_GLOW` are all still read from config for backward compatibility. `THEME_MODE` maps to the dark/light switch and `THEME_MOTION`/`THEME_GLOW` map to the new motion and presence-intensity settings; the four hue keys (`THEME_PRIMARY`, `THEME_PEACOCK`, `THEME_INDIGO`, `THEME_SAFFRON`) are read but never applied as visual accents — confirmed by grep: the frontend contains zero references to any of them. An existing install upgrades cleanly rather than resetting, and never silently reintroduces the retired cream/terracotta or saffron/peacock/indigo palette.

---

## P. Frontend design system

Full specification with computed contrast ratios: `KALKI_DESIGN_SYSTEM.md`. Load-bearing rules restated here because they constrain any future change:

- **Colour.** A six-step near-black surface ramp; `--filament` (`#fff4e2`) reserved for presence, active-nav, and focus — never more than ~2% of a screen's pixels.
- **Typography.** Instrument Sans (UI/prose) and JetBrains Mono (code/metrics), loaded locally when the optional `.woff2` files are present (`app/ui/fonts/`), falling back to `Segoe UI Variable Text` / `Segoe UI` / `system-ui` — the fallback path is a designed-for case, not a degradation, since KALKI never loads a font over the network.
- **Motion.** Only `opacity` and `transform` ever animate; nothing animates while idle; `prefers-reduced-motion` and a Settings toggle both collapse every duration to zero without losing state legibility.
- **Elevation.** A luminance step plus a 1px border carries most hierarchy; real shadows are spent on exactly two levels (menus/toasts, dialogs/palette) because a large shadow is a full-surface software rasterization under `--disable-gpu`.
- **Accessibility target.** WCAG 2.2 AA. Native `<dialog>` + `showModal()` for every modal (no hand-written focus trap), 2px warm-white focus ring at 17.6:1 contrast, 24×24px minimum hit targets, `scroll-padding-block` so sticky chrome never fully hides a focused control.
- **Responsive.** Container-driven breakpoints from 900px (single-column, rail becomes a bottom bar) to 1600px+ (full three-pane layout); correct at the window's actual minimum size, 960×680.

---

## Q. User workflows

**First launch** — `prepare_runtime()` provisions `config.py`; the server starts and writes a fresh API token; the desktop window opens to the Ask view with an empty-state invitation rather than a blank screen.

**Normal chat** — type or speak → composer locks to "sending" → SSE opens → first token flips to "streaming" with a live stop control → markdown renders with code fences buffered until they close → the reply is spoken unless muted → message actions (copy, regenerate, edit-and-resend, report) appear once complete.

**Voice** — say a wake word (or use the in-app voice overlay) → `attending` for 4 seconds → `thinking` while a reply is generated → `speaking` while it's read aloud → `interrupted` if stopped. Exchanges are appended to the active thread with a "Spoken" origin tag even if the window was closed when they happened.

**Memory** — search, filter by type/importance, pin (which is a real retrieval-priority change, not a label), edit, delete-with-undo; a one-time banner offers importing older flat-format memories.

**Tasks / reminders / notes** — Today surfaces all three plus the day's agenda, an unread-mail count, and a focus timer; every empty or unconfigured state states what the surface is for and offers a next action rather than a bare "nothing here".

**Workflows** — pick a mode from Workbench; destructive modes show a confirmation dialog with a real 30-second countdown matching the server's own `_queue_confirmation` TTL.

**Vision** — attach an image (routed to `/api/vision/image`) or capture the screen (`/api/screen`, with an explicit confirmation since it reads the whole desktop); both replies are spoken aloud, and the stop control is available throughout.

**Settings** — thirteen sections; every secret shows as `Set`/`Not set` and is replaced, never revealed; unconfigured integrations show "Connect", not an error.

**Advanced tools** — Workbench exposes code generation and gated local execution; Security (hidden unless enabled) exposes the cybersecurity toolkit with per-tool scope warnings.

**Errors and recovery** — a persistent offline banner when the backend is unreachable (probed via the free, public `/api/health`); inline retry/diagnostics on any surface that fails to load; a diagnostics drawer (`Ctrl/Cmd+Shift+D`) exposing the raw status payload, recent API calls, and — only there — unmapped exception text.

---

## R. Update strategy

**Frontend.** `app/ui/*` is served network-first by the rewritten service worker (§ below); a new release simply replaces the files on disk and the running app picks them up on next load, without the permanent-cache trap the previous cache-first policy created.

**Service worker.** `/api/*` and the HTML shell are network-only (never cached — an API response served stale would be actively wrong); `/ui/*` is network-first with a cache fallback for true offline use; other static assets are stale-while-revalidate. `CACHE_VERSION` is bumped alongside the app version, and `activate` deletes every cache that doesn't match the current version, so an upgrade cannot leave a previous build's JavaScript behind.

**Versioning.** A single version string, synchronized across `app/version.py`, `app/config.example.py`, `app/build_tools/installer.iss`, `app/build_tools/build_msix.py`, `app/build_tools/build_installer.py`, `app/build_tools/file_version_info.txt`, `microsoft_store/AppxManifest.xml`, `linux/package_linux.sh`, `microsoft_store/release.ps1`, `TERMS.md`, and `PRIVACY.md`. Currently `2.0.0` / package identity `2.0.0.0`.

**EXE / MSIX updates.** Both are rebuilt from source by the pipelines in §M; this release updates the pipelines to include `app/ui/` but does not itself produce new binaries (§Q states this explicitly — no EXE or MSIX was built as part of this documentation pass).

**GitHub releases.** `microsoft_store/release.ps1` stages the portable build for GitHub Releases; it now copies `app/ui/` alongside `index.html`, `manifest.json`, `service-worker.js`, and `config.example.py`.

---

## S. Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| App window is blank | `app/ui/` wasn't packaged alongside `index.html` | Confirm the installer/MSIX/Linux archive actually contains `ui/` — this is exactly the bug the v2.0.0 packaging changes were made to prevent (§M) |
| `/ui/*.js` returns 404 or the wrong content-type | A file extension outside `Handler.UI_CONTENT_TYPES`, or a path that resolves outside `app/ui/` (the traversal guard rejects it) | `server.py`'s `_serve_ui_asset` |
| Frontend never updates after a new release | Old service worker still cache-first (pre-v2.0.0 installs) | Confirm `CACHE_VERSION` bumped and the client has cycled through `activate` once — this is the exact defect v2.0.0 fixed |
| Local server unavailable | Port already in use, or the server process crashed | `kalki.log`, `crash.log` in the user data directory; the frontend's offline banner and `/api/health` probe |
| API token / 401 errors | Stale `kalki_session` cookie after a token rotation | Reload the window to re-fetch `/` and re-issue the cookie |
| Model unavailable | No Groq key configured and Ollama not running | Settings → Models secret status; `ollamaOnline` on `/api/status` |
| Voice unavailable | Microphone permission denied, or `listener.py` not running | `listenerCapabilityNotice` on `/api/status`, shown verbatim in Settings → Voice |
| TTS silent | Audio device failed to initialize | `ttsProbeError` / `ttsLastError` on `/api/status` |
| Integration setup fails | OAuth flow interrupted or credentials revoked | `/api/settings/test_google` / `test_spotify`; re-run `/api/setup/tool` |
| MSIX/Store packaging fails with a missing-`ui` error | Intentional — `build_msix.py` and `package.ps1` both hard-fail rather than silently shipping a blank window | Ensure `app/ui/` exists before packaging |
| Unsigned MSIX | No `KALKI_DEV_CERT_PATH`/`KALKI_DEV_CERT_PASSWORD` set | Expected for Store submission; set both only for local test signing |
| Stale frontend assets in a browser cache during development | Browser HTTP cache, not the service worker | `/ui/*` responses are sent with `Cache-Control: no-cache`, so a hard reload is sufficient |

---

## T. Extension guide

**Add a UI surface.** Create `features/<name>.js` exporting a `<name>View()` function returning an element with a `.render()` method (see any existing feature for the pattern); add it to the `VIEWS` map in `main.js`, a rail entry in `features/shell.js` if it should be visible by default, and route names to `ROUTES` in `features/router.js`.

**Add an API route.** Add the branch in `server.py`'s `_do_get_inner`/`_do_post_inner`; add the corresponding adapter function to `app/ui/api/endpoints.js` (never call `fetch` directly from a feature module); update `KALKI_FRONTEND_CAPABILITY_MAP.md`'s route table.

**Add a tool / workflow mode.** Extend `workflows.py`'s mode registry; if it's destructive, route it through `_queue_confirmation()` so the existing confirmation-dialog UI in `features/workbench.js` picks it up automatically — no frontend change needed for a new confirmed mode.

**Add an integration.** Add its `configured` flag to `/api/status` or `/api/settings/get`; add an `IntegrationCard`-style row in `features/settings.js`'s integrations section, following the existing "Connect" pattern for the unconfigured state.

**Add a setting.** Add the key to `config.example.py` with a sensible default; add a `row`/`toggleRow`/`textRow`/`secretRow` call in the relevant `features/settings.js` section — never render a secret's value, only its status.

**Add a model provider.** Add it to the provider chain in `server.py`'s chat handler; surface it in the model picker via `/api/models`'s returned list — `features/ask.js`'s model picker requires no code change for a new entry in that list.

**Update documentation.** This file, the four design/architecture docs, `README.md`, and `CHANGES.md` should all move together — a change that alters a route, a design token, or a packaging step is not done until all of them agree. `KALKI_FRONTEND_CAPABILITY_MAP.md` is the single source of truth for route shapes; do not duplicate route tables elsewhere.

**Update packaging.** Any new top-level frontend asset directory beyond `app/ui/` needs the same treatment given to `ui/` in this release: a static-serving route with a content-type allowlist and traversal guard, and a corresponding staging line in `installer.iss`, `build_msix.py`, `package.ps1`, `release.ps1`, and the Linux packager.

---

## U. Release checklist

- [ ] `python -m ast` (or equivalent) confirms `server.py` and every touched `build_tools/*.py` still parse
- [ ] `node --experimental-vm-modules .github/scripts/validate-ui-modules.mjs` — every `app/ui/*.js` module parses and every import resolves
- [ ] Functional journey suite passes (boot, chat streaming, palette, memory CRUD, tasks, settings, workflows, gated security, keyboard nav, offline/recovery) — see `README.md`'s "v2.0.0 frontend validation" table for exactly what this covers and does not cover
- [ ] Zero console errors across every journey
- [ ] Every icon-only control has an accessible name; native `<dialog>` used for every modal
- [ ] No secret value ever rendered — only `Set`/`Not set` status
- [ ] `.gitignore` excludes `*.pfx`/`*.cer`, runtime data, `__pycache__`, build trees, and generated binaries; no signing certificate committed
- [ ] Version string identical across all locations listed in §R
- [ ] `installer.iss`, `build_msix.py`, `package.ps1`, `release.ps1`, and the Linux packager all stage `app/ui/`
- [ ] `CHANGES.md` and `release_notes.md` describe this release accurately, with no fabricated checksums for binaries not actually built
- [ ] `README.md`, the four design/architecture docs, and this document agree with the current source — none describe the previous HUD as current
- [ ] Store-facing metadata (`microsoft_store/docs/`, package descriptions) reviewed for stale UI claims
- [ ] Target-device acceptance pass performed before distribution — real WebView2, real backend process (not a stub), Windows display scaling, physical microphone/speaker — since none of this was exercised in a sandbox without a GUI or audio device (explicitly out of scope for this pass; see §Q)
