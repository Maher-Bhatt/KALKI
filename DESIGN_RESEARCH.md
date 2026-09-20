# DESIGN_RESEARCH.md

> **Status: the direction below was carried through to implementation without reversal.** Every pattern this document recommended adopting shipped; every pattern it recommended avoiding is absent from the shipped CSS (verified: zero perpetual `animation: ... infinite` rules outside state-bound presence/streaming/loading indicators, zero `backdrop-filter` in the default path, zero ALL-CAPS labels, zero emoji-as-control). The one visual promise this document did not fully deliver on its own: the voice overlay's presence mark was supposed to visibly bloom to a larger size on entering voice mode (§7, "it blooms into a larger form"), and an id mismatch between two files meant it never did until the functional test suite caught it — see `KALKI_COMPLETE_SYSTEM_DOCUMENTATION.md` §D.

Research backing the KALKI frontend rebuild. Written to be acted on, not read once.

Repo state at time of writing: `server.py` 5,931 lines, `index.html` 2,529 lines, 83 API endpoints, 27 of them reachable from the UI.

---

## 1. Products and standards studied

| Source | What was taken from it |
|---|---|
| [Windows 11 design principles](https://learn.microsoft.com/en-us/windows/apps/design/design-principles) | Elevation-and-layering as the foundation of app hierarchy; motion as feedback and wayfinding, not decoration |
| [Fluent 2 Motion](https://fluent2.microsoft.design/motion) | Duration scaled to element size and travel distance; mandatory no-motion path |
| [Fluent 2 overview](https://designbycurio.com/learn/microsoft-fluent-2) | Disciplined translucency and a single restrained accent against a neutral field — the restraint, not the blue |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Conformance target. Nine new criteria over 2.1; 4.1.1 Parsing removed |
| [WAI-ARIA / native dialog guidance](https://accessibility.build/guides/accessible-dialog) | `<dialog>.showModal()` puts the dialog in the top layer and makes the rest of the document inert — no hand-rolled focus trap |
| [Primer dialog accessibility](https://primer.style/product/components/dialog/accessibility/) | Command-palette focus order: the input takes focus first, not the close button |
| [Agent UX patterns 2026](https://fuselabcreative.com/ui-design-for-ai-agents/) | Planning visibility, tool-use disclosure, memory surfacing, workflow tracking, recovery routing |
| [AI chat UX in production](https://www.metacto.com/blogs/ai-chat-ux-patterns-production) | Trust comes from verify/correct/undo affordances, not from answer quality |
| [Chat UI practice 2026](https://thefrontkit.com/blogs/ai-chat-ui-best-practices) | Defer code-block rendering until the closing fence arrives; announce streamed text via live regions |
| [Linux WebKit backdrop-blur perf fix](https://github.com/block/buzz/pull/3533) | With no GPU path, every visible backdrop re-blurs per frame on the main thread |
| [Codex Intel-GPU backdrop-filter bug](https://github.com/openai/codex/issues/23458) | `backdrop-filter` is the first thing to fail on constrained renderers; opaque fallbacks are the fix |
| Raycast, Linear, Superhuman, Arc | Command palette as a primary interaction system; keyboard-first navigation; sub-100ms perceived response |
| ChatGPT, Claude, Perplexity, Copilot | Composer anatomy, streaming affordances, stop/regenerate placement, attachment handling |

---

## 2. Patterns worth adopting

**Elevation by luminance step, not by shadow.** Windows 11 builds hierarchy from overlapping surfaces. On a GPU-disabled renderer (see §5) a 1px border plus a background step costs nothing; a 70px shadow costs a full-surface rasterization. Reserve real shadows for the two layers that genuinely float: overlays and dialogs.

**Native `<dialog>` + `showModal()`.** Promotes the dialog into the top layer and makes everything else inert. Tab cannot escape because there is nothing outside to reach. This removes the single most bug-prone piece of hand-written a11y code from the project.

**Three named async states instead of a spinner.** The production-chat literature is blunt: a spinner is an admission that the interface does not know what is happening. KALKI has enough signal to name states precisely — *reaching the model*, *streaming*, *running a tool*, *waiting for your confirmation*, *speaking*.

**Visible stop, visible tool call, visible edit-and-resend.** Each is a small contract that the system will not act without the user being able to see and reverse it. KALKI already has `_queue_confirmation()` with a 30-second TTL for destructive workflows — that is a confirmation UI waiting to be built, not a feature to invent.

**Context-window transparency.** `MAX_HISTORY = 20` means KALKI actually carries ten exchanges. Hiding that produces the classic "why did it forget?" failure. Showing it on the composer turns a limitation into a trust signal.

**Memory as a first-class, editable surface.** An inspectable "what KALKI knows" panel is now baseline in serious products. `semantic_memory` already stores `id`, `text`, `tags`, `importance` (1–10), `type`, `created_at`, and treats `type: "pinned"` as always-retrieved. The entire memory UI the brief asks for is buildable against the existing schema with zero backend change.

**Command palette as a system, not a search box.** Every destination, every action, every model switch, every workflow, and every memory reachable from one keystroke. With 83 endpoints and a 56px rail, the palette is how depth stays reachable without a wall of icons.

**Buffer incomplete markdown.** Render text immediately; hold code blocks until the closing fence lands. Prevents the flicker of half-parsed fences during token streaming.

---

## 3. Patterns worth avoiding

**The current visual direction is a documented generated-design cliché.** `index.html` runs a warm-cream field (`#f4ecdf`), a Georgia serif display, and a terracotta accent (`--terracotta: #c77752`, `THEME_PRIMARY = "#b6553f"`). That exact combination — cream ground, high-contrast serif, terracotta near `#D97757` — is the most recognizable signature of AI-generated design. It has to go, and not because of the brief's "no Indianization" rule.

**The obvious replacement is also a cliché.** Near-black plus one bright acid accent is the second most common generated-design default. Avoided here by making the accent achromatic warm-white rather than a saturated hue (§6).

**Identical cards with one radius and one shadow.** The three rail cards, the editorial card, the focus card, the tools card and the activity card are all `.glass-card`: same 26px radius, same `0 24px 70px` shadow, same padding. Radius and elevation should encode hierarchy, not be applied uniformly.

**Perpetual animation loops.** `coreOrbit` (24s), `dotOrbit` (×3, 8/11/14s), `coreScan` (3.4s), `coreBreath` (4.8s), `flameFloat` (2.8s), `signalBreath` (4.6s), `centerHalo` (8s) all run forever regardless of application state. On an idle window this is continuous compositing for zero information.

**ALL-CAPS eyebrow labels above every heading.** `.kicker` is `text-transform: uppercase` + `letter-spacing: .16em` and appears above every card. Uppercase micro-labels are harder to scan and are a template tell.

**Backdrop-filter as a default surface treatment.** Nine selectors apply `backdrop-filter: blur(22px)`. See §5 — on this runtime, it is the most expensive possible way to draw a box.

**A giant presence object at screen center.** `#center-container` is `min(58vh, 520px)`, with a `min(62%, 390px)` animated core inside it. It occupies the majority of the primary workspace and displaces the actual work.

**Raw Python exceptions as UX.** `_safe_call` returns `{"ok": false, "error": str(e)}` with a 500 on any handler failure. Rendering `str(e)` is fine for a diagnostics drawer, not for the primary message.

---

## 4. KALKI-specific design opportunities

These exist because of what KALKI *is*, and would not transfer to another product.

1. **Voice is out-of-process.** `listener.py` runs as a separate Python process, posts to `/api/wake` and `/api/chat`, and reaches the frontend only through polled `/api/status`. KALKI can be mid-conversation with the user while the window is closed. The UI is therefore an *observer* of a conversation it does not own — closer to a call-status display than a chat app. Design for that honestly instead of pretending the browser drives voice.

2. **Local-first is visible.** Everything runs on `127.0.0.1` behind a token in `data/api_token.txt`. Ollama fallback means KALKI still answers with the network down. Most AI products cannot show a genuine local/offline state; KALKI can, and it is worth surfacing.

3. **Two-thirds of the product has never been drawn.** Tasks, reminders, notes, calendar, mail, Spotify, WhatsApp, GitHub, workflows, vault, code generation, screen vision, and thirteen security endpoints all work today with no interface at all. The rebuild's largest single win is exposure, not aesthetics.

4. **Hardware presence.** `/api/status` carries CPU, RAM, disk, battery, uptime, and a live hardware profile. Used sparingly — one place, small — this grounds KALKI in *this machine*, which is exactly the "my AI" feeling the brief asks for. Used as five meters in a rail card, it is a HUD.

5. **The security toolkit is a liability by default.** Thirteen `/api/cyber/*` routes plus `webscan` and `deepscan`. Shown to everyone, they make KALKI look like a hacking tool. Gated behind a configured key and an explicit Settings toggle, they become a credible professional workspace.

6. **Memory already has an importance scale and a pinned type.** Unusual, and directly designable.

---

## 5. Performance requirements (this runtime, not general advice)

**The binding constraint:** `main_app.py` sets `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--disable-gpu"` on Windows to avoid driver-specific WebView hangs after first paint. Every frame is rasterized on the CPU.

Consequences, in priority order:

- **No `backdrop-filter` in the default path.** With no GPU compositor, each visible backdrop is re-blurred in software every frame, on the main thread. Opaque surfaces only; blur may be re-enabled as a user-opt-in "Enhanced visuals" setting that is off by default.
- **Animate `opacity` and `transform` only.** Never `width`, `height`, `top`, `left`, `box-shadow`, or `filter`.
- **No animation while idle.** Every loop is bound to an application state and stops when that state ends. `prefers-reduced-motion` and a Settings toggle both kill motion entirely.
- **Budget large shadows.** Two elevation levels carry real shadows. Everything else uses a background step and a 1px border.
- **Virtualize long lists.** Chat threads, memory lists, and scan results render windowed above 60 rows.
- **Fix the polling.** Current behaviour: `/api/status` every 1,500ms, `updateBars` every 800ms, dashboard every 5s, models every 60s, focus ticker every 1s. That is ~2,400 status requests per hour. Worse, the handler calls `len(load_memory())`, which reads and JSON-parses the entire memory file on **every** status request. New policy: 2s while a turn is in flight, 10s idle, suspended entirely on `document.hidden`, revalidate on focus.
- **Kill the stale-cache trap.** `service-worker.js` is cache-first for any non-API, non-HTML request (`caches.match(...) || fetch(...)`). Ship `/ui/app.js` under that policy and users never receive an update. Requires content-hashed filenames or a network-first strategy before any multi-file frontend lands.

Targets: first paint under 400ms on the local server; palette open under 100ms; no interaction over 16ms of main-thread work; idle CPU at 0%.

---

## 6. Accessibility requirements

Target: **WCAG 2.2 Level AA.** WCAG 2.2 adds nine criteria over 2.1 and removes 4.1.1 Parsing; conforming to 2.2 means conforming to 2.1.

Criteria that actually change this build:

- **2.4.11 Focus Not Obscured (AA)** — the rail, composer and title strip are all sticky. `scroll-padding` on scroll containers, and no sticky element may fully cover a focused control.
- **2.5.8 Target Size (AA)** — minimum 24×24 CSS px. The current composer buttons are 38px and pass; icon-only rail and message-action buttons must be audited at every scale factor.
- **2.5.7 Dragging Movements (AA)** — attachment drag-and-drop needs a non-drag equivalent. The attach button covers this; the rail resize handle needs keyboard arrows.
- **3.2.6 Consistent Help (A)** — help and diagnostics live in the same place on every screen.
- **1.4.11 Non-text Contrast** — the focus indicator must hit 3:1 against adjacent colours.

Beyond the criteria:

- Semantic HTML first. ARIA only where no element exists.
- Native `<dialog>` for every modal. `Escape` closes; focus returns to the trigger.
- Streaming assistant output announced through a polite live region, throttled so screen readers are not flooded per token.
- Tool execution and errors announced through an assertive status region.
- Every icon-only control carries an accessible name plus a tooltip.
- Visible focus everywhere, with a warm-white 2px ring at 2px offset — never `outline: none`.
- Full keyboard operation for the palette, rail, thread, composer, and every list.
- Motion respects `prefers-reduced-motion`; contrast respects `prefers-contrast: more`.

---

## 7. The visual direction

Working name: **Filament.**

**The idea.** KALKI's surfaces are cold machined graphite. KALKI's presence is warm light. Nothing else in the interface is warm. That single temperature split is the whole signature — it makes KALKI legible at a glance without a glow on every border, and it cannot be produced by recolouring a template.

The conceptual root is the name itself: a pale light arriving in darkness. It informs the palette and it stops there. It never becomes ornament — no motif, no script, no mandala, no saffron. If it ever shows up as decoration, it has been misapplied.

**Why a filament rather than an orb, eye, or ring.** A filament does not spin, orbit, or scan. It only changes intensity and size. That gives the motion system a physical rule with real consequences: KALKI's presence animates `opacity` and `scale` and nothing else — which is also the cheapest thing a GPU-disabled renderer can draw. The aesthetic decision and the performance decision are the same decision.

**Where it lives.** At the top of the navigation rail, 28px, as the KALKI mark. The brand mark and the state indicator are one object. It never takes the centre of the screen. It blooms into a larger form only when the user deliberately enters voice mode, and it returns to 28px when they leave.

**Palette.** Cool graphite ramp for every surface and all text. Warm platinum for presence, the active navigation indicator, and focus. Semantic red, green and amber for status only — never for branding, never decoratively, never larger than a badge, icon, or 1px border. No gold, no cyan, no neon; those are the client's standing constraints and they align with the restraint the direction needs anyway.

**Typography.** Instrument Sans for interface and prose, JetBrains Mono for code and metrics, both shipped as local `.woff2` files under `app/ui/fonts/` — no network, no Google Fonts, correct in an offline packaged install. Falls back to `Segoe UI Variable Text`, `Segoe UI`, `system-ui`. No serif display face anywhere. No ALL-CAPS labels.

**Radius encodes hierarchy.** 3px chips, 6px controls, 10px panels, 14px dialogs, full round for presence only. One radius on everything is the tell being avoided.

---

## 8. Final design principles

1. **The work is the interface.** The thread and composer hold visual priority. Everything else earns its pixels or collapses.
2. **Warm light is KALKI. Everything else is cold.** One temperature split carries the identity; no second accent gets added later.
3. **Motion is a state report.** If an animation is not telling the user what changed, it is deleted. Nothing animates while idle.
4. **Depth comes from luminance, not blur.** A background step and a 1px border beat a shadow on this runtime, and usually look better.
5. **Name the state.** "Reaching the model", "Running a scan", "Waiting for you to confirm" — never an unlabelled spinner.
6. **Show the limits.** Context window, offline model, unconfigured integration, disabled capability. Stated plainly, not hidden.
7. **Depth lives in the palette.** The rail stays at five destinations; everything else is one keystroke away.
8. **No dead UI.** A control calls a real endpoint, performs a real local operation, or says clearly that the capability is not configured — and links to where to configure it.
9. **Keyboard is the primary input; mouse is the convenience.** Every action has a path that never touches the pointer.
10. **Sound like a person, in the product's voice.** Sentence case, active verbs, plain nouns. Errors say what happened and what to do. Empty states are invitations, not apologies.

---

## 9. Sources

- W3C — Web Content Accessibility Guidelines 2.2: https://www.w3.org/TR/WCAG22/
- Microsoft — Windows 11 design principles: https://learn.microsoft.com/en-us/windows/apps/design/design-principles
- Microsoft — Fluent 2 Motion: https://fluent2.microsoft.design/motion
- Microsoft — Fluent 2 Windows components: https://fluent2.microsoft.design/components/windows
- Fluent 2 analysis (translucency, neutral palette, layered materials): https://designbycurio.com/learn/microsoft-fluent-2
- Accessible dialogs with native `<dialog>` and `showModal()`: https://accessibility.build/guides/accessible-dialog
- GitHub Primer — Dialog accessibility: https://primer.style/product/components/dialog/accessibility/
- TetraLogical — What's new in WCAG 2.2: https://tetralogical.com/blog/2023/10/05/whats-new-wcag-2.2/
- Deque University — WCAG 2.2 resources: https://dequeuniversity.com/resources/wcag-2.2/
- Agent UX patterns for 2026: https://fuselabcreative.com/ui-design-for-ai-agents/
- AI chat UX patterns in production: https://www.metacto.com/blogs/ai-chat-ux-patterns-production
- AI chat UI best practices 2026: https://thefrontkit.com/blogs/ai-chat-ui-best-practices
- Designing AI chat interfaces: https://shantiinfosoft.com/blog/designing-ai-chat-interfaces/
- backdrop-blur software-rendering cost, real-world fix: https://github.com/block/buzz/pull/3533
- backdrop-filter failure on constrained GPU paths: https://github.com/openai/codex/issues/23458
- backdrop-filter and Chromium 2D rendering cost: https://github.com/shadcn-ui/ui/issues/327
