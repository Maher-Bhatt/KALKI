# KALKI_FRONTEND_CAPABILITY_MAP.md

> **Status: post-implementation, v2.0.0.** This document was written before implementation
> as a pre-build audit; every "Today" cell below has been updated to reflect what actually
> shipped. Where a row still says "Never called" or was left unrouted, that is a real,
> current gap — not a stale note — and is cross-referenced in
> `KALKI_COMPLETE_SYSTEM_DOCUMENTATION.md` §E/§S. Original audit figures are kept in the
> "Headline finding" table below since they are what motivated the rebuild's priorities;
> they describe the *starting* state, not the current one.

Every capability the backend exposes, where it lives, and what the frontend owes it.
This document's job is to make it impossible to ship a prettier UI that quietly loses features.

**Originally audited against:** `app/server.py` (5,931 lines pre-patch), `app/index.html`
(2,529 lines, now 41), and the `app/core/` modules. **Now current against:** `app/server.py`
(6,044 lines post-patch), `app/ui/` (27 modules), and the same backend modules, unchanged
in substance.

---

## Headline finding

| | Count |
|---|---|
| API endpoints implemented in `server.py` | **83** |
| Reachable from the current UI | **27** |
| **Never drawn — backend works, no interface exists** | **56 (67%)** |

The rebuild is not primarily a restyle. Two thirds of the product has never had an interface.

**What is invisible today:** tasks, reminders, notes, calendar, mail, Spotify, WhatsApp, GitHub, YouTube download, workflows, the credential vault, code generation and execution, screen vision, meeting mode, semantic search, usage metrics, and thirteen security endpoints.

### Cross-cutting facts that shape every surface

| Fact | Consequence |
|---|---|
| Server is stdlib `http.server`, not Flask | Routing is a flat `if path == ...` chain in `_do_get_inner` / `_do_post_inner`. Adding a route is trivial and safe |
| Everything except `/`, `/index.html`, `/manifest.json`, `/service-worker.js`, `/api/health`, `/favicon.ico`, `/assets/*` requires the token | Frontend must send `X-KALKI-Token` or rely on the `kalki_session` cookie set by `_public_html()` |
| Only `/assets/*` serves static files, and it types everything as png / ico / octet-stream | **A multi-file frontend cannot load today.** A `/ui/*` route with correct MIME types is a prerequisite |
| `service-worker.js` is cache-first for non-API non-HTML requests | Any `/ui/*.js` shipped under the current SW is cached permanently. Must be fixed before the rebuild lands |
| `MAX_HISTORY = 20`, single flat `history.json`, no conversation IDs | There is no backend concept of a conversation. See §1.2 |
| Voice runs in a separate process (`listener.py`) | The UI observes voice; it does not drive it. See §3 |
| `--disable-gpu` is set for WebView2 | No `backdrop-filter`; animate `opacity`/`transform` only |
| `_safe_call` returns `{ok:false, error:str(e)}` + HTTP 500 on any handler exception | Every call site needs a mapped, human error; raw `error` goes to the diagnostics drawer only |

### Legend

`Surface` = where it lives in the new IA. `P0` = must ship with the rebuild. `P1` = ships in the same release, after P0. `P2` = designed now, built next.

---

## 1. Conversation

### 1.1 Endpoints

| Endpoint | Method | Request | Response | Today | New surface |
|---|---|---|---|---|---|
| `/api/chat` | POST | `{messages[], stream, source, clientSpeech}` | SSE `data:{token}` … `data:{done,model}`, or `{reply, source, model}` | **Shipped** — `api/stream.js`, streaming path only; the non-streaming shape is still unused | Ask — thread + composer |
| `/api/stop` | POST | — | `{ok}` | **Shipped** — composer stop control, `Escape` shortcut, and voice overlay | Ask — stop control |
| `/api/model` | POST | `{model}` | `{ok, model}` | **Shipped** — composer model chip dialog, and palette `Use <model>` commands | Composer model chip + palette |
| `/api/models` | GET | — | `{models[]}` | **Shipped** — fetched on boot and whenever the model picker opens; no longer a fixed 60s timer | Composer model chip + palette |
| `/api/command` | POST | `{cmd}` | local command result | **Partially shipped** — only called from Today's "Start a focus session" action; the palette's `>` prefix runs its own client-side action list rather than this endpoint | Today; palette actions are separate |
| `/api/search` | POST | `{q}` or `{query}` | search result | **Gap — still never called.** The palette searches conversations, memory, and settings client-side but never queries this endpoint | Real gap for P1 |
| `/api/report` | POST | `{response, reason, details, prompt}` | `{ok}` | **Shipped** — a dedicated dialog from each assistant message's action row, with a reason picker matching the server's accepted values | Message actions |
| `/api/parse_document` | POST | `{filename, data}` | extracted text | **Shipped** — composer attachment pipeline extracts and prefixes document text before sending | Composer attachments |

`reason` must be one of `harmful`, `hateful`, `sexual`, `privacy`, `misleading`, `other` — the server rejects anything else with a 400.

### 1.2 The conversation-history gap — decide this before building

The brief asks for conversation history, search, folders, pinning, rename and archive. **None of it has a backend.** What exists:

- One `history.json`, a flat alternating `[{role, content}, …]`, truncated to the last 20 entries.
- No IDs, no titles, no timestamps, no grouping.
- `listener.py` appends to the same file out-of-band when the window is closed.

**Decision: the frontend owns conversations in IndexedDB; the backend keeps owning the model's context window.**

- IndexedDB stores full threads: id, title, created/updated, pinned, archived, messages, model, attachments.
- `history.json` is treated for what it is — the rolling 10-exchange window the model actually sees — and is *shown* as such on the composer ("6 of 10 turns in context").
- Voice-originated turns are reconciled by polling `conversationSeq` / `recentExchange` from `/api/status` and appending them to the active thread.

**One additive backend route makes this materially better:** `GET /api/history` returning `load_history()` (three lines). It lets the frontend reconcile turns it missed while the window was closed, instead of inferring them. Recommended, not required.

**Rejected alternative:** raising `MAX_HISTORY` and inventing server-side threads. That is a backend rewrite the brief explicitly warns against, and it would break the listener's assumptions.

### 1.3 Workflow

Type or speak → composer locks to *sending* → SSE opens → first token flips to *streaming* with a live stop control → tokens append with markdown buffered until code fences close → `done` carries the model name → message actions appear (copy, regenerate, edit and resend, report) → thread persists to IndexedDB.

### 1.4 States

`empty` · `composing` · `sending` · `streaming` · `stopped` · `complete` · `failed` · `retrying`

### 1.5 Errors

| Condition | Message | Recovery |
|---|---|---|
| Server unreachable | "KALKI's local service isn't responding." | Retry, plus a "How to restart KALKI" link |
| `groqConfigured` false and Ollama offline | "No model is available. Add a provider key or start Ollama." | Deep-link to Settings → Models |
| SSE drops mid-stream | Keep partial text, mark it truncated | Regenerate |
| Body over 32MB | "That attachment is too large — 32 MB is the limit." | Remove attachment |
| 401 | "Your session expired." | Reload to re-issue the cookie |

---

## 2. Memory

Two independent systems are in the codebase. This is the single most confusing area for a user.

| Endpoint | Method | Request | Response | System | Today |
|---|---|---|---|---|---|
| `/api/memories` | GET | — | `{memories[]}` | Legacy flat list | **Shipped, deliberately limited** — read once per session to populate the "Import N older memories" banner, never used to build a second memory UI |
| `/api/memory` | POST | `{fact}` | `{ok, count}` | Legacy flat list | **Not called** — the legacy add endpoint is never used; the import flow re-adds legacy entries through `/api/memory/add` (semantic) instead, so they gain real metadata rather than staying in the flat format |
| `/api/memory/list` | GET + POST | — | `{ok, memories[]}` | `semantic_memory` | Wired |
| `/api/memory/add` | POST | `{text, tags[], importance, type}` | `{ok, id}` | `semantic_memory` | Wired |
| `/api/memory/update` | POST | `{id, text, importance, type}` | `{ok}` | `semantic_memory` | **Shipped** — the edit dialog and the pin/unpin toggle both call this |
| `/api/memory/delete` | POST | `{id}` | `{ok}` | `semantic_memory` | Wired |

**Record shape** (`semantic_memory.list_all`): `{id, text, tags, importance (1–10), type, created_at}`.

**`type: "pinned"` is functionally special** — `search()` merges every pinned document into the result set regardless of similarity. That is a real pin, not a label.

**Decision:** the Memory surface is built entirely on `semantic_memory`. The legacy pair (`/api/memories`, `/api/memory`) is presented once, as a one-time "Import N older memories" banner that reads the flat list and re-adds each entry through `/api/memory/add`. After import, the legacy path is never shown again. Do not build two memory UIs.

**Required UI (P0):** searchable list; filters by type and importance; pinned section first; inline edit; delete with undo; an "Add memory" composer with type and importance controls; empty state explaining what memory is for and that it stays on this machine.

**States:** `loading` · `empty` · `populated` · `filtered` · `no-results` · `editing` · `saving` · `deleted (undo window)` · `import-available`

**Errors:** embedding backend unavailable → memory still lists and edits, search degrades to substring match, and the surface says so plainly. Never silently return zero results.

---

## 3. Voice

### 3.1 The architecture, stated honestly

`listener.py` is a separate Python process. It captures audio, performs wake-word matching (`WAKE_WORDS = ["hey kalki", "kalki", "hey sir", "ok kalki"]`, optional offline Vosk), and POSTs to `/api/wake` or `/api/chat` with `source: "voice"`. The frontend learns about any of it only by polling `/api/status`.

**The frontend is an observer of a conversation it does not own.** KALKI can hold a full exchange while the window is closed.

| Endpoint | Method | Purpose | Today |
|---|---|---|---|
| `/api/wake` | POST | Wake, with optional inline `{cmd}` | **Shipped from the UI too** — palette's "Wake KALKI" command and the voice overlay's Wake button, in addition to the listener |
| `/api/listener/pause` | POST | Release the microphone | **Shipped** — Settings → Voice and the palette both expose it |
| `/api/listener/resume` | POST | Reclaim the microphone | Wired |
| `/api/listener_state` | POST | Listener reports hardware mute | Listener → server only |
| `/api/stop` | POST | Interrupt speech | Wired |
| `/api/tts/test` | POST | Speak a test phrase | **Shipped** — Settings → Voice "Test voice" |

### 3.2 Signals actually available from `/api/status`

`speaking` · `listenerPaused` · `listenerMicMuted` · `wakeRequested` (one-shot, consumed on read) · `conversationSeq` · `recentExchange{seq,user,reply,ts}` · `ttsProvider` · `ttsLastProvider` · `ttsLastError` · `ttsLastLatencyMs` · `ttsProbeError` · `listenerCapabilityNotice`

**Not available:** whether the user is currently speaking, and whether speech is being transcribed.

### 3.3 State machine — only states we can actually verify

| State | Derived from | Filament |
|---|---|---|
| `unavailable` | `/api/status` failing, or `listenerCapabilityNotice` set | 10%, desaturated, still |
| `mic-released` | `listenerPaused === true` | 12%, still, muted badge |
| `mic-muted` | `listenerMicMuted === true` | 12%, still, muted badge |
| `ready` | listener alive, not speaking | 22%, still |
| `attending` | `wakeRequested` consumed this poll | rise to 60% over 180ms, hold 4s |
| `thinking` | request in flight from this client | 45–65% breathing, 2.4s sine |
| `speaking` | `speaking === true` | 55–75% modulation, 900ms |
| `interrupted` | `/api/stop` succeeded | drop to 20% over 120ms |
| `tts-failed` | `ttsLastError` or `ttsProbeError` non-empty | 22% + amber dot |

**Rule: do not animate a "listening" state we cannot verify.** Faking it is exactly the dead UI the brief forbids. Two options to earn the two missing states, in order of preference:

1. **Additive backend field (~6 lines).** Have `listener.py` POST a coarse phase to `/api/listener_state` (`idle` / `heard-wake` / `capturing` / `transcribing`) and echo it in `/api/status`. Low risk, high payoff.
2. **Browser `SpeechRecognition`** for typed-window voice only. The composer already sends `clientSpeech: true`, so the plumbing exists. Does not cover the out-of-process path.

Until one lands, `attending` and `thinking` carry the interaction and the UI stays truthful.

### 3.4 Errors

| Condition | Message |
|---|---|
| `ttsProbeError` set | "Voice output is unavailable — audio device didn't initialise." + diagnostics link |
| `ttsLastError` set | "Couldn't speak that reply." + retry |
| `listenerCapabilityNotice` set | Show it verbatim; it is already written for humans |
| `listenerPaused` | Persistent, dismissible "Microphone released" chip with a Resume action |

---

## 4. Today — context and productivity

### 4.1 Tasks and reminders

| Endpoint | Method | Request | Response | Today |
|---|---|---|---|---|
| `/api/tasks/list` | POST | `{all}` | `{ok, tasks[]}` | **Shipped** — Today |
| `/api/tasks/add` | POST | `{text}` | `{ok, id}` | **Shipped** — Today and the palette |
| `/api/tasks/complete` | POST | `{id}` or `{text}` | `{ok, task}` | **Shipped** — Today's complete control |
| `/api/tasks/delete` | POST | `{id}` or `{text}` | `{ok}` | **Shipped** — Today's delete control, with a confirmation dialog |
| `/api/reminders/list` | POST | — | `{ok, reminders[]}` | **Shipped** — Today |
| `/api/reminders/add` | POST | `{text, due}` | `{ok, id}` | **Shipped** — Today, two-step prompt (text, then a natural-language due phrase) |

Task record: `{id, text, added, done}`. `add` and `reminders/add` return 400 on empty text; `reminders/add` also requires `due`.

`tasks.parse_when()` accepts natural language for `due` — the UI should send the user's raw phrase and show the resolved time back, not force a date picker.

**Notable:** `/api/wake` parses `[TASK: …]` and `[REMIND: … @ …]` out of model replies and creates records automatically. The Ask surface must show a "task created" affordance when this happens, or tasks appear from nowhere.

**Required UI (P0):** task list with inline add, complete with undo, delete; reminders grouped by due window; empty state. **No delete endpoint exists for reminders** (`tasks.delete_reminder()` exists in the module but is not routed) — either add the route or omit the control. Do not ship a dead button.

### 4.2 Notes

| Endpoint | Method | Request | Response | Today |
|---|---|---|---|---|
| `/api/notes/add` | POST | `{text}` | `{ok, id}` | **Shipped** — Today and the palette |
| `/api/notes/list` | POST | `{n}` | `{ok, notes[]}` | **Shipped** — Today |
| `/api/notes/search` | POST | `{q}` | `{ok, notes[]}` | **Gap — still never called.** No search box was built for notes specifically; the palette does not query this endpoint either |

`notes.py` also implements `notes_on`, `notes_yesterday`, `notes_this_week` and `delete_note` with no routes. Surface as a capture strip inside Today plus palette search. **P1.**

### 4.3 Calendar, mail, music, messaging

| Endpoint | Method | Request | Response | Today | Priority |
|---|---|---|---|---|---|
| `/api/calendar/today` | POST | — | `{ok, events[], summary}` | **Shipped** — Today's Agenda card, with `gcalConfigured: false` as a designed "Connect" state | shipped |
| `/api/calendar/upcoming` | POST | `{n}` | `{ok, events[], summary}` | **Gap — still never called.** Today only shows today's events | real gap |
| `/api/mail/check` | POST | `{importantOnly, limit}` | `{ok, summary}` | **Gap — still never called.** `/api/status`'s `unreadImportant` count is shown in the Ask context panel, but no dedicated mail card was built despite being planned for Today | real gap, cut from this release |
| `/api/mail/inbox` | POST | `{limit, onlyUnread}` | inbox payload | **Gap — still never called** | real gap |
| `/api/spotify/play` `/pause` `/next` `/now` | POST | — | player state | **Partially shipped** — play/pause/next are wired in Today's Music card (shown only when `spotifyConfigured`); `/now` is not called, since `/api/status`'s cached `nowPlaying` is used instead | play/pause/next shipped |
| `/api/whatsapp/send` | POST | `{to, message}` | send result | **Gap — still never called**, as planned for P2 | on schedule |
| `/api/github/status` | GET | — | `{ok, configured, count, notifications[], pollInterval, notModified}` | **Gap — still never called.** An adapter exists (`api/endpoints.js`) but no GitHub notifications surface was built this pass | real gap |
| `/api/ytdl` | POST | `{url, audio}` | download result | **Gap — still never called**, as planned for P2 | on schedule |

`/api/status` already caches `todayEvents`, `unreadImportant` and `nowPlaying` — read those for the at-a-glance row instead of adding four more polls.

`/api/github/status` returns its own `pollInterval` and a `notModified` flag. Honour both; do not poll on a fixed timer.

**Every one of these must handle `configured: false` as a designed state**, not an error: a quiet "Connect Google Calendar" row that deep-links to Settings → Integrations.

### 4.4 Focus, dashboard, metrics

| Endpoint | Method | Response | Today |
|---|---|---|---|
| `/api/focus` | GET | `{ok, active, remainingSec, minutes}` | Wired, polled every 1s |
| `/api/dashboard` | GET | `{ok, data:{productivity, screenTime, uptimeSec, state, focus, memCount}}` | Wired, polled every 5s |
| `/api/metrics` | GET | `{ok, metrics}` — per-model tokens and latency | **Shipped** — Settings → Models "View usage" dialog |

`/api/focus` at 1Hz for a countdown is wasteful — fetch once, count down locally, resync every 30s.

`/api/metrics` belongs in Settings → Models as a real usage panel. It is the only place in the product that can answer "which model am I actually using and how fast is it".

---

## 5. Vision and files

| Endpoint | Method | Request | Response | Today |
|---|---|---|---|---|
| `/api/vision/image` | POST | `{image: base64, question}` | `{ok, reply, …}` | Wired |
| `/api/screen` | POST | `{question}` | analysis result | **Shipped** — composer's "Ask about my screen" action, with an explicit confirmation prompt before capture |
| `/api/parse_document` | POST | `{filename, data}` | extracted text | **Shipped** — see §1, called from the same composer attachment pipeline |

`vision.py` also exposes `ocr_screen()` and `screenshot_save()` with no routes.
`core/file_intelligence.parse_binary_document` handles PDF, DOCX, XLSX and PPTX — that is a full document-ingestion pipeline with no interface.

**Both vision paths speak the reply aloud** (`speak(result.get("reply"))`). The UI must reflect that a screenshot analysis will talk, and offer the stop control.

**Required UI (P0):** drag-and-drop and paste onto the composer; attachment chips with type, name, size, and a remove control; images preview inline; documents show an extraction summary before send. Screen capture is a composer action with an explicit confirmation, because it reads the whole desktop.

**States:** `idle` · `dragover` · `reading` · `extracting` · `attached` · `too-large` (>32MB) · `unsupported` · `analysing` · `complete`

---

## 6. Workbench — code and workflows

| Endpoint | Method | Request | Response | Today |
|---|---|---|---|---|
| `/api/code/generate` | POST | `{prompt, lang, run}` | `{ok, code, path, run}` | **Shipped** — Workbench code studio (`run` is always sent `false`; execution is a separate, explicitly confirmed step) |
| `/api/code/run` | POST | `{code, lang}` | `{ok, …stdout/stderr/exit}` | **Shipped** — Workbench, gated behind a confirmation dialog stating it runs locally |
| `/api/workflow` | POST | `{mode}` | mode result, or a queued confirmation | **Shipped** — Workbench mode cards; modes marked `advanced` show a confirmation dialog before the call is made |

**Code execution is gated.** `coder.host_execution_enabled()` guards real execution and `verification_sandbox.py` / `SANDBOX.md` describe the containment model. The UI must show which mode is active before a Run button is ever pressed, and disable Run with an explanation when host execution is off.

**Workflows have real depth that has never been shown.** `workflows.py` defines modes (`gaming`, `ctf`, `dev`, `focus`, `study`, …) each with a voice profile and description, supports user-defined routines via `add_custom_routine`, resolves fuzzy names with `find_mode`, and marks destructive modes with `requires_confirmation`.

**`_queue_confirmation()` is a designed interaction waiting for a UI.** Destructive workflows return a pending confirmation with a 30-second TTL. Build the confirmation dialog: what will run, what it will change, confirm / cancel, and a visible countdown.

**Required UI (P1):** workflow library from `list_modes()`; cards showing name, description and voice profile; a run control; a confirmation dialog for destructive modes; a live step/status region; last-run outcome.

---

## 7. Security workspace

Thirteen routes, plus `webscan.py` (635 lines) and `deepscan.py` (400 lines, Playwright-backed). **Status: mostly shipped, one route deliberately omitted, one never called.**

| Endpoint | Request | Notes | Today |
|---|---|---|---|
| `/api/cyber/hash` | `{text, algo}` | Returns `{algo, hash}` | **Shipped** |
| `/api/cyber/identify` | `{hash}` | `{guesses[]}` | **Shipped** |
| `/api/cyber/crack` | `{hash, wordlist}` | Long-running, dictionary-bounded | **Gap** — not in the shipped tool list; a long-running, wordlist-dependent tool needs a file-upload and progress affordance this pass didn't build |
| `/api/cyber/portscan` | `{host, ports[]}` | Capped by `CYBER_SCAN_PORT_LIMIT = 64` | **Shipped**, with the scope-warning banner |
| `/api/cyber/dns` | `{host}` | | **Shipped** |
| `/api/cyber/headers` | `{url}` | | **Shipped** |
| `/api/cyber/encode` / `/decode` | `{text, fmt}` | `decode` returns `{ok:false}` on bad input | **Shipped**, as two separate tool tabs |
| `/api/cyber/cve` | `{id}` | | **Shipped** |
| `/api/cyber/subdomains` | `{domain, …}` | | **Shipped** |
| `/api/cyber/revshell` | `{type, lhost, lport}` | | **Deliberately not shipped.** A UI for generating reverse-shell payloads was cut during implementation as a judgment call beyond this rebuild's scope, not an oversight. The backend route and its existing gates are untouched; revisiting this needs an explicit product decision, not just adding it back to a tool list |
| `/api/cyber/dorks` | `{target}` | | **Shipped** |
| `/api/cyber/surface` | `{target, …}` | Composite attack-surface brief | **Shipped**, as the first tab, with its own scope warning |

**Product decision, implemented as specified: Security is hidden by default.** Confirmed absent from the navigation rail unless `SHODAN_API_KEY` is configured or the user enables it in Settings → Advanced (verified in the functional test suite). Reachable directly by route (`#/security`) regardless, since hiding a destination from navigation is not the same as blocking it.

**Shipped UI:** a single target field with per-tool tabs; results rendered as labeled rows with the raw JSON payload behind a `<details>` disclosure; explicit scope text before every scan. **Not shipped from the original plan:** long-scan progress/cancel affordances — scans currently show only a busy state, with no cancel control and no incremental progress.

---

## 8. Settings, security and lifecycle

| Endpoint | Method | Response | Today |
|---|---|---|---|
| `/api/settings/get` | GET | `{ok, settings, secretStatus, spotifyConfigured, googleConfigured, cacheSize}` | Wired |
| `/api/settings/save` | POST | `{ok}` | Wired |
| `/api/settings/reset` | POST | `{ok}` — GET returns 405 | Wired |
| `/api/settings/clear_cache` | POST | `{ok}` — GET returns 405 | Wired |
| `/api/settings/export` | GET | file download | Wired |
| `/api/settings/test` | GET | `{ok, groq, spotify, google}` | Wired |
| `/api/settings/test_google` / `test_spotify` | GET | `{ok, message}` | Wired |
| `/api/setup/tool` | POST | launches a setup helper | Wired |
| `/api/backup/create` / `restore` | POST | `{ok, …}` | Wired |
| `/api/cloud_restore` | POST | `{ok}` | Wired |
| `/api/vault/save` / `get` / `delete` | POST | credential ops | **Partially shipped** — Settings → Security "Open vault" calls `save` only, by design: the vault is treated as write-only in the UI, so a saved entry is never read back or displayed. `get` and `delete` have adapters (`api/endpoints.js`) but no calling UI yet |
| `/api/telemetry/checkin` | POST | `{ok}` | **Gap — still never called** from the frontend; telemetry check-in remains backend-only, gated by the existing `TELEMETRY_ENABLED` flag surfaced in Settings → Privacy |
| `/api/support` | GET | opens a browser URL | **Shipped** — Settings → About "Support the project" |
| `/api/recovery/clear` | POST | clears `crash.log` | Only from the safe-mode page |
| `/api/health` | GET | `{ok, ts}` — public, no token | **Shipped** — the offline-banner recovery probe in `api/client.js`, exactly as recommended |

**`secretStatus` is the security contract.** `_public_settings_value()` masks every key in `SECRET_SETTING_KEYS` (Groq, OpenAI, Anthropic, Gemini, ElevenLabs, email app password, GitHub token, Shodan). The UI renders **status only** — *Set* / *Not set* — with a "Replace" action that writes a new value. It never renders a stored secret, never round-trips a masked value back to `save`, and never logs one.

**The vault (`vault.py`, DPAPI hardware-bound) has three endpoints and no UI.** Surface as Settings → Vault: labels list, add, reveal-on-explicit-action with auto-hide, delete with confirmation. Mark **P1**, and treat reveal as a deliberate, logged action.

**`/api/health` is the correct connectivity probe** — it is public and cheap. Use it for the offline banner instead of hammering `/api/status`.

**Required settings IA:** Profile · Appearance · Voice · Models · Memory · Integrations · Privacy · Security · Performance · Shortcuts · Backup · Advanced · About. Progressive disclosure throughout; the current flat two-column `setup-grid` of raw config keys is replaced.

**Theme keys to migrate:** `THEME_PRESET`, `THEME_MODE`, `THEME_PRIMARY`, `THEME_PEACOCK`, `THEME_INDIGO`, `THEME_SAFFRON`, `THEME_MOTION`, `THEME_GLOW`. The saffron/peacock/indigo trio goes away with the old visual language. Keep reading the keys for backward compatibility, ignore the discarded hues, and map `THEME_MOTION`/`THEME_GLOW` onto the new motion and presence-intensity settings so existing installs upgrade cleanly rather than resetting.

---

## 9. System status and shell

`GET /api/status` is the heartbeat and carries ~35 fields:

`online` · `model` · `groqConfigured` · `ollamaOnline` · `speaking` · `tts*` (6 fields) · `memCount` · `time` · `timeFull` · `date` · `uptimeSec` · `cpu` · `ram` · `disk` · `batteryPct` · `batteryPlugged` · `owner` · `title` · `city` · `hardware` · `hudQuality` · `wakeRequested` · `conversationSeq` · `recentExchange` · `listenerPaused` · `listenerMicMuted` · `listenerCapabilityNotice` · `platform` · `cpuAlertsEnabled` · `gcalConfigured` · `spotifyConfigured` · `todayEvents` · `unreadImportant` · `nowPlaying` · `updateProgress` · `terminalLogs` · `clipboardPromptPending`

**Two performance bugs to fix in the same pass:**

1. `"memCount": len(load_memory())` reads and JSON-parses the entire memory file on **every** status request — currently 2,400 times an hour.
2. `get_hardware_stats()` runs `psutil` sampling on every request.

Neither needs to be hot. Cache both server-side for 5s, or drop `memCount` from `/api/status` entirely and read it from `/api/dashboard`.

**Where these fields surface:** `owner`/`title`/`city` personalise greetings quietly, never as a name badge. `cpu`/`ram`/`disk`/`battery` live in a single small system popover, not five rail meters. `updateProgress` drives a determinate update indicator. `terminalLogs` and `clipboardPromptPending` feed the diagnostics drawer.

**`clipboardPromptPending` + `/api/clipboard_response`** is a genuine proactive interaction: KALKI notices clipboard content and asks whether to analyse it. It deserves a real inline prompt with Yes / Ignore, not a hidden voice-only path. **P1.**

---

## 10. Backend changes required

Everything below is additive. No existing route changes behaviour. No module is rewritten.

| # | Change | Size | Why | Priority |
|---|---|---|---|---|
| 1 | `/ui/*` static route with correct MIME types for `.js` `.css` `.woff2` `.svg` `.json` | ~15 lines in `_do_get_inner` | **Blocking.** Only `/assets/*` serves files and it types JS as `octet-stream`; `<script type="module">` will refuse it | **P0** |
| 2 | Bump `CACHE_NAME`; make `/ui/*` network-first or use content-hashed filenames | ~5 lines in `service-worker.js` | Current cache-first policy makes frontend updates undeliverable | **P0** |
| 3 | `installer.iss`: add `Source: "..\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs` | 1 line | The installer currently ships exactly one frontend file | **P0** |
| 4 | Mirror #3 in `microsoft_store/` packaging and `linux/package_linux.sh` | packaging only | Store and Linux builds must not ship a broken UI | **P0** |
| 5 | Cache `memCount` and hardware stats for 5s in `/api/status` | ~8 lines | Removes a full memory-file parse from the hot path | **P0** |
| 6 | `GET /api/history` → `load_history()` | ~3 lines | Lets the frontend reconcile voice turns instead of guessing | P1 |
| 7 | `listener.py` reports a coarse phase; echo it in `/api/status` | ~6 lines | Earns two honest voice states instead of two faked ones | P1 |
| 8 | Route `tasks.delete_reminder()` | ~3 lines | Otherwise the reminder delete control has to be omitted | P1 |
| 9 | Route `notes.delete_note()` | ~3 lines | Same | P2 |

If #1–#4 are not acceptable, the fallback is a single generated `index.html` with everything inlined, built from the module sources by a small Python script at release time. It works, and it keeps the packaging model untouched — but it makes debugging materially worse and reintroduces the 2,500-line file the rebuild exists to remove. Recommend taking #1–#4.

---

## 11. Coverage checklist

Ship gate: no item below may be worse than it is today.

- [ ] All 27 currently-wired endpoints still work from the new UI
- [ ] Settings round-trip: change → save → reload → value persists
- [ ] Secrets never rendered; `secretStatus` drives all key UI
- [ ] Voice exchanges initiated with the window closed appear on next open
- [ ] `/api/stop` interrupts both streaming and speech
- [ ] Every integration has a designed `configured: false` state
- [ ] Destructive workflows show the confirmation dialog with its countdown
- [ ] No control calls a non-existent endpoint
- [ ] No endpoint listed here is silently dropped
- [ ] Backup → restore → reload verified end-to-end
- [ ] Safe-mode and updating pages still render (they bypass the SPA entirely)
- [ ] Zero console errors across all twelve journeys


## v2.1.0 Additions
- **Oversight Panel (`app/ui/features/oversight.js`)**: Real-time Shodan/monitoring dashboard with CPU/RAM limits, watched sites (API endpoints added in v2.1.0), and 50-item alert history.
- **Desktop Notifications (`app/notify.py`)**: Native plyer toasts when KALKI is backgrounded.
- **Fallback Chain (`app/server.py`)**: Zero-downtime model fallback with unified errors.
