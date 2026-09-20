# KALKI_FRONTEND_ARCHITECTURE.md

> **Status: implemented as specified, v2.0.0.** The stack decision (no build step, native ES modules), the directory layout, the routing approach, the polling policy, and the explicit non-goals below were all followed without deviation. Two things changed during implementation and are called out at point of use rather than silently: the `/api/history` route (§2) exists but its reconciliation is not yet wired into the boot sequence — voice turns are currently reconciled from `/api/status`'s `recentExchange` alone, which is sufficient but doesn't yet use the new route; and the packaging changes in §10 were written into the pipeline scripts but no EXE/MSIX/Linux archive was actually built or tested end-to-end in this pass (no Windows/Linux GUI environment was available) — see `KALKI_COMPLETE_SYSTEM_DOCUMENTATION.md` §Q for exactly what was and wasn't validated.

The technical and structural plan for the rebuilt KALKI frontend. Decisions here are binding for Message 2.

---

## 1. The big product decision

**KALKI stops being a dashboard and becomes a workspace.**

The current interface is a fixed three-column HUD: a left rail of four cards, a centre stage dominated by a `min(58vh, 520px)` animated presence object, and a right rail of four more cards. There is no navigation, no history, and no way to reach two thirds of the product. The centre — the most valuable real estate — is occupied by an animation.

The replacement is a single-window workspace with a narrow rail, one primary work area, and a collapsible context panel. **Asking is not a destination; it is the application.** Everything else is either context sitting beside the work, or a place you visit occasionally.

### Information architecture

```
KALKI
├── Ask                  ← default; thread + composer + attachments + voice
├── Today                ← tasks · reminders · calendar · mail · notes · focus · now playing
├── Memory               ← semantic memory: search, pin, edit, importance, types
├── Workbench            ← workflows · code generate/run · screen & vision
├── Security             ← hidden unless configured or explicitly enabled
└── Settings             ← rail footer, not a destination in the list
```

Five visible destinations at most, usually four. The brief warns against fifteen permanent icons; this is the discipline that avoids it. Notes live inside Today rather than as a sixth item. Integrations live inside Settings. Everything not in the rail is one keystroke away in the command palette.

### Why Security is conditional

Thirteen offensive-security endpoints displayed to every user is what makes software look like a hacking tool. It appears in the rail only when `SHODAN_API_KEY` is configured or the user turns it on in Settings → Advanced. This is the single highest-leverage change for moving KALKI's identity away from "cyber terminal".

### Shell layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ KALKI                                                    ⌘K      — □ × │  36px title strip (drag)
├──────┬──────────────────────────────────────────────┬──────────────────┤
│  ◉   │                                              │  Context         │
│      │   you                                        │  ──────────      │
│ Ask  │   how long until the odoo session            │  ▸ 3 tasks       │
│      │                                              │  ▸ 14:30 Odoo    │
│ Today│   KALKI                                      │  ▸ mic ready     │
│      │   Two hours. It starts at 14:30.             │                  │
│ Mem  │   ┌ calendar · 2 events ────────────┐        │  llama-3.3-70b   │
│      │   └─────────────────────────────────┘        │  local · 42% cpu │
│ Work │                                              │                  │
│      │                                              │                  │
│ ─────│                                              │                  │
│  ⚙   │  ┌────────────────────────────────────────┐  │                  │
│      │  │ Ask KALKI                   ◎  ⊕   ↵  │  │                  │
│      │  │ llama-3.3-70b · 6 of 10 turns in context│ │                  │
│      │  └────────────────────────────────────────┘  │                  │
└──────┴──────────────────────────────────────────────┴──────────────────┘
  56px            fluid · thread capped at 72ch              280px
```

- **Rail** 56px icon-only; expands to 208px with labels on hover, focus, or when pinned. State persists.
- **Work area** fluid. Thread text capped at 72ch and left-aligned — no centred prose, no chat bubbles for KALKI.
- **Context panel** 280px, collapsible, hidden automatically below 1100px. Contents change per destination.
- **Presence (the filament)** lives at rail top as the KALKI mark. It is the brand and the state indicator in one object. It never occupies the centre of the screen.

---

## 2. Technical stack

### Decision: no build step. Native ES modules, plain JavaScript with JSDoc types, no framework, no bundler.

The frontend ships as static files under `app/ui/`, served by a new `/ui/*` route, loaded with `<script type="module">`.

**Why this is the right call here, not the lazy one:**

1. **The packaging model forbids anything else cheaply.** Releases run five separate PyInstaller one-dir bundles, an Inno Setup script, an MSIX pipeline and a Linux packager. Adding Node to that chain means a solo maintainer's Microsoft Store release can now break on `npm ci`. That is a permanent tax for a one-time convenience.
2. **WebView2 is evergreen Chromium.** ES modules, `<dialog>`, `:has()`, native CSS nesting, container queries, custom properties, `structuredClone` — all available. There is nothing to transpile and nothing to polyfill.
3. **Zero build means zero drift.** Edit a file, press F5. That matches the client's stated requirement that things work immediately with minimal setup, and it keeps the debugging story identical in development and in a packaged install.
4. **Installer size stays flat.** No `node_modules`, no bundle, no sourcemaps to ship or omit.

**The honest trade-off:** no JSX and no reactive framework, so roughly 120 lines of glue are needed — a signal store and a template helper. That is written once and is the total framework cost.

**The escape hatch, designed in now:** every module exports pure functions over a plain state object and touches the DOM only through the render layer. Nothing imports a global. If the project later wants Preact + Vite, the migration is mechanical: replace `render()` and `signal()`, keep every `api/`, `state/` and `lib/` module unchanged. Module boundaries are drawn with that in mind.

**Rejected:**
- *React + Vite + Tailwind.* Familiar to the maintainer, genuinely better component ergonomics, but the packaging cost above is not worth paying for a single-window local app of this size.
- *Web Components with Shadow DOM.* Real encapsulation with no build, but design tokens across shadow boundaries get awkward and the accessibility footguns are not worth it.
- *Keeping one giant `index.html`.* Explicitly ruled out by the brief, and it is the reason the current code is unmaintainable.

### Directory layout

```
app/
  index.html                 ← ~60 lines: shell skeleton, boot, module entry
  ui/
    main.js                  ← boot, router, global key handling
    tokens.css               ← every design token, light + dark + contrast
    base.css                 ← reset, type, focus, scrollbars, reduced motion
    app.css                  ← shell layout, rail, panels, responsive
    fonts/                   ← InstrumentSans-*.woff2, JetBrainsMono-*.woff2
    lib/
      signal.js              ← reactive primitive (~40 lines)
      render.js              ← html`` template + keyed list diff (~80 lines)
      dom.js                 ← query, class, focus, portal helpers
      markdown.js            ← streaming-safe markdown → DOM
      format.js              ← dates, durations, bytes, relative time
      keys.js                ← shortcut registry + conflict detection
      idb.js                 ← IndexedDB wrapper for conversations
    api/
      client.js              ← fetch wrapper: token, timeout, abort, retry, error map
      stream.js              ← SSE reader for /api/chat
      chat.js  memory.js  tasks.js  notes.js  calendar.js  mail.js
      spotify.js  workflows.js  code.js  vision.js  cyber.js
      settings.js  vault.js  system.js
    state/
      store.js               ← root store + persistence
      status.js              ← /api/status poller + derived voice machine
      conversations.js       ← IndexedDB-backed threads
      settings.js  toasts.js
    components/
      Button.js  IconButton.js  Tooltip.js  Menu.js  Dialog.js  Drawer.js
      Tabs.js  Select.js  Input.js  Textarea.js  Toggle.js  Slider.js
      Card.js  List.js  EmptyState.js  ErrorState.js  Toast.js
      Avatar.js  StatusDot.js  Meter.js  Chip.js  Kbd.js
    features/
      shell/      AppShell.js  Rail.js  TitleStrip.js  ContextPanel.js
      presence/   Filament.js  VoiceOverlay.js
      palette/    CommandPalette.js  commands.js
      ask/        Thread.js  Message.js  Composer.js  Attachments.js
                  ToolRun.js  ModelPicker.js  ContextMeter.js
      today/      Today.js  TaskList.js  Reminders.js  Agenda.js
                  MailDigest.js  NotesStrip.js  FocusTimer.js  NowPlaying.js
      memory/     Memory.js  MemoryItem.js  MemoryEditor.js  MemoryImport.js
      workbench/  Workbench.js  WorkflowLibrary.js  WorkflowRun.js
                  CodeStudio.js  ScreenVision.js
      security/   Security.js  TargetBar.js  ScanResult.js
      settings/   Settings.js  sections/*.js
      system/     SystemPopover.js  Diagnostics.js  UpdateBanner.js
```

`index.html` drops from 2,529 lines to about 60. No file in `ui/` should exceed 300 lines; if one does, it is doing two jobs.

---

## 3. State

A single observable store. No global mutation from feature code.

```js
{
  route:   { name, params },
  status:  { /* last /api/status, normalised */ },
  voice:   { state, since, canInterrupt },        // derived, see §5
  models:  { available[], current, loading },
  conv:    { activeId, threads[], streaming, abort },
  memory:  { items[], query, filters, loading },
  today:   { tasks[], reminders[], events[], mail, focus, nowPlaying },
  settings:{ values, secretStatus, dirty, saving },
  ui:      { railExpanded, contextOpen, paletteOpen, theme, motion, density },
  toasts:  []
}
```

Rules:

- Features read via selectors and write via actions. Nothing calls `fetch` from a component.
- `conv.threads` is the IndexedDB projection. `history.json` is the model's context window, surfaced in the composer meter — never conflated with the thread.
- `ui.*` persists to `localStorage` under `kalki.ui.v1`. Everything else is memory-only or server-owned.
- One re-render per frame: actions mark dirty, `requestAnimationFrame` flushes.

---

## 4. API layer

### Contract

```js
// api/client.js
async function call(path, { method='POST', body, signal, timeout=15000 })
  → { ok: true,  data }
  | { ok: false, kind, message, detail, status }
```

`kind` is one of `offline` · `auth` · `timeout` · `not-configured` · `invalid` · `server` · `unavailable`.

Every UI error message is chosen from `kind`. The raw `error` string from `_safe_call` goes to `detail` and is only ever shown in the diagnostics drawer. Users never read a Python exception as the primary message.

### Rules

- Send `X-KALKI-Token` when a token is known; otherwise rely on the `kalki_session` cookie that `_public_html()` sets. Never put a token in a URL.
- Every request carries an `AbortController`. Navigating away or resubmitting cancels the previous request.
- The server takes `{"ok": false}` with HTTP 200 in several handlers. The client normalises: **`data.ok === false` is a failure regardless of status code.**
- `/api/settings/reset` and `/api/settings/clear_cache` return **405 on GET**. POST only.
- Adapter functions, not raw payloads. `/api/dashboard` nests under `data.productivity`; `/api/cyber/*` spreads module output into the top level; `/api/mail/inbox` returns the module's shape unwrapped. Each `api/*.js` normalises at the boundary so no component ever branches on backend inconsistency. This is the adapter layer the brief calls for — and it is why the backend does not need rewriting.

### Streaming

```js
// api/stream.js
streamChat(messages, { onToken, onDone, onError, signal })
```

Reads the SSE body with `ReadableStream` + `TextDecoder`, splits on `\n\n`, parses each `data:` line. Handles the two documented shapes: `{token}` repeatedly then `{done, model}`, and the local-command fast path `{token, done:true}` in a single frame. On abort it calls `/api/stop` so TTS halts too — stopping the text without stopping the voice is the current behaviour and it is wrong.

### Polling policy

The current UI issues roughly 2,400 status requests an hour and re-parses the memory file on each one.

| Source | Now | New |
|---|---|---|
| `/api/status` | 1,500ms always | 2s while a turn is in flight · 10s idle · **suspended on `document.hidden`** · immediate revalidate on focus |
| `updateBars` | 800ms | folded into `/api/status`; no separate timer |
| `/api/dashboard` | 5s | 30s, plus on navigating to Today |
| `/api/models` | 60s | on load and when the model picker opens |
| `/api/focus` | 1s | once, then count down locally, resync every 30s |
| `/api/github/status` | — | honours the server's own `pollInterval` and `notModified` |

A single `PollController` owns every timer. One `visibilitychange` listener suspends and resumes the lot.

---

## 5. Voice state machine

The frontend does not own voice. `listener.py` runs out of process and can hold a full conversation with the window closed. The UI observes.

```
                ┌──────────── /api/status unreachable ──────────┐
                ▼                                                │
           unavailable                                           │
                                                                 │
  listenerPaused ──► mic-released ──resume──► ready ◄─────────────┘
  listenerMicMuted ──► mic-muted ──────────────┘
                                                │
                            wakeRequested ──────┤
                                                ▼
                                            attending ──4s──► ready
                                                │
                        request in flight ──────┤
                                                ▼
                                             thinking
                                                │
                            speaking === true ──┤
                                                ▼
                                            speaking ──► ready
                                                │
                                /api/stop ──────┤
                                                ▼
                                          interrupted ──► ready
```

`ttsProbeError` or `ttsLastError` overlays a `tts-failed` badge on any state without replacing it.

**`wakeRequested` is a one-shot flag consumed by the server on read.** Exactly one poller may read `/api/status`, or wake events will be lost. `state/status.js` is that single owner; every other module subscribes.

**Two states are deliberately absent: `listening` and `interpreting`.** The backend does not report them. Animating them would be a lie, and the brief forbids controls that only play animations. They are unlocked by the six-line listener change in the capability map (§10, item 7), not by guessing.

Reconciling voice turns: when `conversationSeq` increments, `recentExchange` is appended to the active thread with an origin marker so the user can see which turns came from speaking.

---

## 6. Routing

Hash-based: `#/ask`, `#/ask/:threadId`, `#/today`, `#/memory`, `#/workbench/workflows`, `#/settings/models`.

Hash rather than History API because the app is also loaded from `file://` in some Linux and recovery paths, where `pushState` is unreliable. Cheap insurance.

Route changes: fade out 120ms, swap, fade in 160ms — opacity only, no slide, no transform of large subtrees. On every route change, move focus to the new region's `<h1>` and announce it politely.

---

## 7. Command palette

`Ctrl/Cmd + K` anywhere. Built on native `<dialog>.showModal()` so the rest of the document becomes inert with no hand-written focus trap. The text input takes focus on open, not the close button.

Sources, in ranked order: recent conversations · navigation · actions · models · workflows · memory search · tasks · notes · settings pages.

Prefixes: `>` actions · `@` memory · `#` tasks · `/` settings · plain text searches everything.

Keyboard: `↑ ↓` move, `Enter` run, `Tab` completes a prefix, `Esc` closes and restores focus. Results are `role="listbox"` with `aria-activedescendant`; the input keeps DOM focus throughout.

Performance: results are computed synchronously over in-memory indexes, capped at 8 per group. Target under 100ms from keypress to painted list.

---

## 8. Responsive and DPI

Breakpoints are driven by the work area, not the viewport, using container queries where it helps.

| Width | Behaviour |
|---|---|
| ≥ 1600px | Rail expanded if pinned · context panel open · thread 72ch centred in its column |
| 1280–1599px | Rail collapsed to 56px · context panel open |
| 1100–1279px | Context panel collapses to a toggle |
| 900–1099px | Rail overlays instead of pushing; context is a drawer |
| < 900px | Single column; rail becomes a bottom bar; composer pinned |

Tested at 1280×720, 1366×768, 1600×900, 1920×1080, 2560×1440, 3840×2160, and at Windows scaling of 100 / 125 / 150 / 175 / 200%.

**DPI rules.** All sizing in `rem` off a 16px root; no `px` in layout except hairline borders. Nothing sized in `vh` — the current `#center-container` uses `min(58vh, 520px)` and collapses at 150% scaling on a 768px-tall panel. Icons are SVG with `stroke-width` in `rem`. Minimum hit target 24×24 CSS px at every scale factor (WCAG 2.5.8), verified at 200%.

The window minimum is `min_size=(960, 680)` in `main_app.py`. The layout must be correct at exactly that size — it is reachable by the user.

---

## 9. Accessibility architecture

| Concern | Implementation |
|---|---|
| Dialogs | Native `<dialog>` + `showModal()`. Top layer, document inert, `Escape` free, focus restored on close |
| Landmarks | `<nav>` rail, `<main>` work area, `<aside>` context, `<header>` title strip |
| Route changes | Focus moves to the region `<h1>`; `aria-live="polite"` announces the destination |
| Streaming output | One `aria-live="polite"` region per message, updated on a 400ms throttle with the accumulated text — never per token |
| Tool runs and errors | `aria-live="assertive"` status region |
| Icon-only controls | `aria-label` plus a tooltip; label and tooltip text are identical |
| Lists | `role="listbox"` / `option` with roving tabindex, or plain `<ul>` where no selection semantics exist |
| Tabs | Full `tablist` / `tab` / `tabpanel` with arrow-key movement and manual activation |
| Focus ring | 2px warm-white at 2px offset, ≥3:1 against adjacent colours (WCAG 1.4.11). `outline: none` is banned |
| Sticky chrome | `scroll-padding-block` on every scroll container so focus is never fully hidden (WCAG 2.4.11) |
| Drag | Every drag interaction has a button equivalent (WCAG 2.5.7) |
| Motion | `prefers-reduced-motion` plus a Settings toggle; both collapse all durations to 0 and disable presence animation |
| Contrast | `prefers-contrast: more` raises border and text tokens one step |

---

## 10. Packaging and runtime

### Required changes

**1. Static route for `/ui/*`** — blocking. Add to `_do_get_inner` alongside the existing `/assets/` branch:

```python
if path.startswith("/ui/"):
    rel = path.lstrip("/")
    safe = os.path.normpath(os.path.join(APP_ROOT, rel))
    if not safe.startswith(os.path.join(APP_ROOT, "ui")):
        self._text("Not found", status=404); return
    ctype = {
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".woff2": "font/woff2",
        ".svg": "image/svg+xml",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
    }.get(os.path.splitext(safe)[1], "application/octet-stream")
    try:
        with open(safe, "rb") as f:
            self._text(f.read(), ctype=ctype)
    except Exception:
        self._text("Not found", status=404)
    return
```

Note the `normpath` prefix check — without it this route is a directory traversal. `/ui/*` is placed **after** `_require_auth`, so it inherits the existing token model. `index.html` is public and sets the cookie, so module loads from within the page are authorised.

**2. Service worker.** Bump `CACHE_NAME`, and either serve `/ui/*` network-first or hash filenames. The current `caches.match(request) || fetch(request)` makes frontend updates permanently undeliverable.

**3. Installer.** `installer.iss` ships `..\index.html`, `..\manifest.json` and `..\service-worker.js` and nothing else from the frontend. Add:

```
Source: "..\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
```

Mirror in `microsoft_store/` packaging and `linux/package_linux.sh`. A release that ships the new `index.html` without `ui/` produces a blank window.

### Runtime constraints

- `--disable-gpu` is set for WebView2. No `backdrop-filter` in the default path. Animate `opacity` and `transform` only. No perpetual loops.
- `frameless=False`, so the OS draws the window chrome. The 36px title strip is app content with `-webkit-app-region: drag`; interactive children need `no-drag`.
- `background_color='#f4ecdf'` in `main_app.py` is the old cream. Change it to the new base — otherwise every launch flashes cream before first paint.
- The safe-mode page (`crash.log` present) and the updating page (`updating.lock`) are inline HTML served instead of `index.html`. They bypass the SPA entirely. Restyle them to match, but keep them dependency-free — they must render when everything else is broken.
- Linux browser mode (`linux_launcher.py`) loads the same URL in a system browser. No WebView2-only assumptions.

---

## 11. Error, loading and empty state architecture

**Three error scopes:**

1. *Global* — backend unreachable. A persistent banner under the title strip. `/api/health` is the probe: public, cheap, no token. Retries with backoff; the rest of the UI stays usable against cached state.
2. *Surface* — one destination failed to load. Inline `ErrorState` with what failed, a retry, and a diagnostics link. Navigation keeps working.
3. *Action* — one operation failed. A toast with an inline retry. Never a dialog.

**Loading is contextual, never a page spinner.** Skeleton rows that match final geometry for lists; a named phase for the thread ("Reaching the model…" → streaming); determinate progress where the server gives a number (`updateProgress.pct`); indeterminate shimmer only for scans with no progress signal.

**Empty states are the entry point to their feature**, not an apology: one line of what this is for, one primary action, one shortcut hint. Required for conversations, memory, tasks, reminders, notes, workflows, integrations, search results, security results, and voice.

---

## 12. Implementation order

| Phase | Contents | Gate |
|---|---|---|
| 0 | `/ui/*` route · SW fix · installer lines · `background_color` · status caching | New `index.html` loads a module and paints |
| 1 | tokens, base, app CSS · `signal` · `render` · `client` · `store` · AppShell · Rail · Filament · router | Shell renders, rail navigates, presence reflects `/api/status` |
| 2 | Ask: thread, streaming, composer, attachments, model picker, stop, message actions, context meter | Journeys 1 and 6 pass |
| 3 | Command palette · keyboard registry · dialogs · toasts | Journey 8 passes |
| 4 | Memory (+ legacy import) · Today (tasks, reminders, agenda, focus) | Journeys 3 and 4 pass |
| 5 | Settings (all sections) · integrations · backup · diagnostics | Journey 5 passes |
| 6 | Workbench: workflows + confirmation dialog · code studio · screen vision | Journey 7 passes |
| 7 | Security workspace, gated | Not visible unless enabled |
| 8 | Voice overlay · reduced motion · contrast · DPI sweep · offline pass | Journeys 2, 9, 10, 11, 12 pass |

Each phase leaves the app runnable. No phase leaves old and new UI side by side.

---

## 13. Development and debugging

```bash
python app/server.py          # serves index.html + /ui/* directly from disk
# edit any file under app/ui/, press F5
```

No build, no watcher, no Node. Packaged installs load identical files from `{app}\ui`, so a bug reproduces the same way in both.

Three debugging affordances built in:

- `?debug=1` renders a diagnostics drawer with the raw `/api/status` payload, the poll schedule, the last twenty API calls with timings, and current voice state.
- `window.__kalki` exposes the store read-only in development builds.
- Every `client.call` failure logs `{path, kind, status, detail, ms}` once, grouped — not a wall of repeated network noise.

---

## 14. Explicit non-goals

- No server-side conversation storage. IndexedDB owns threads; `history.json` stays the model's context window.
- No rewrite of `server.py` routing, `listener.py`, or any `core/` module.
- No new runtime Python dependencies.
- No network-loaded fonts, icons, scripts, or styles. The app must be correct with the network down.
- No telemetry added by the frontend beyond what `core/telemetry.py` already does under its existing consent flag.
- No second theme system. `THEME_*` config keys are read for backward compatibility and mapped onto the new tokens; the saffron / peacock / indigo palette is retired.
