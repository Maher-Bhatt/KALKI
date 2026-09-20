# KALKI_DESIGN_SYSTEM.md

## Filament

> **Status: implemented as specified, v2.0.0.** Every hex value in this document was checked against the shipped `app/ui/tokens.css` — all 34 explicitly documented colors match exactly, with no drift. The light theme in `tokens.css` extends slightly beyond what §6 spells out here (a handful of additional light-mode semantic-color and disabled-text values), computed following the same "designed independently, not inverted" principle stated below; those extra values are additive, not a deviation. The one implementation bug this design produced — the voice overlay's presence mark never actually reaching its documented 10rem "bloom" size, because `shell.js` and `app.css` disagreed on an element id — was found by the functional test suite and is fixed; see `KALKI_COMPLETE_SYSTEM_DOCUMENTATION.md` §D for the correction.

**KALKI's surfaces are cold machined graphite. KALKI's presence is warm light. Nothing else in the interface is warm.**

That single temperature split is the whole identity. It makes KALKI's state legible at a glance without putting a glow on every border, and it cannot be produced by recolouring someone else's template.

A filament does not spin, orbit, or scan. It changes intensity and size. That gives the motion system a physical rule with a real consequence: presence animates `opacity` and `scale` and nothing else — which happens to be the cheapest thing a GPU-disabled renderer can draw. The aesthetic decision and the performance decision are the same decision.

The conceptual root is the name — a pale light arriving in darkness. It informs the palette and it stops there. It never becomes ornament. No motif, no script, no mandala, no saffron. If it shows up as decoration, it has been misapplied.

**Every contrast ratio in this document was computed, not estimated.**

---

## 1. Colour

### Surfaces

Near-black, hue ≈ 215°, very low chroma — anodized aluminium reads cool in shadow, not violet.

| Token | Hex | Use | Step from previous |
|---|---|---|---|
| `--surface-void` | `#070809` | Behind everything; window background | — |
| `--surface-inset` | `#0A0C0E` | Wells: inputs, code blocks, scan output | recessed |
| `--surface-base` | `#0D0F12` | Main work area | — |
| `--surface-raised` | `#191D22` | Rail, panels, cards, composer | **1.13** |
| `--surface-overlay` | `#262C33` | Menus, popovers, tooltips, dialogs | **1.20** |
| `--surface-float` | `#323941` | Selected rows, hovered overlay items | **1.21** |

**Elevation is a luminance step *plus* a 1px border, together.** A near-black ramp physically cannot exceed about 1.2 between adjacent steps, so the step alone is too quiet to carry hierarchy. The border is not decoration; it is half the elevation signal. Real shadows are spent on exactly two levels (§5).

### Lines

| Token | Hex | vs base | Use |
|---|---|---|---|
| `--line-subtle` | `#232930` | 1.31 | Dividers inside a surface, table rules |
| `--line` | `#333B44` | 1.69 | Panel and card edges |
| `--line-strong` | `#59636F` | **3.14** | Wherever the border *is* the control — input outlines, ghost buttons. Meets WCAG 1.4.11 |
| `--line-focus` | `#FFF4E2` | 17.63 | Focus ring only |

### Text

| Token | Hex | vs base | vs raised | Use |
|---|---|---|---|---|
| `--text` | `#E6EBEF` | 15.99 | 14.11 | Body, headings, assistant output |
| `--text-2` | `#B3BCC6` | 9.99 | 8.81 | Secondary copy, descriptions |
| `--text-muted` | `#8A95A1` | 6.30 | 5.56 | Labels, timestamps, counts |
| `--text-faint` | `#7E8894` | 5.33 | 4.71 | Metadata at the smallest sizes |
| `--text-disabled` | `#4A535D` | 2.46 | 2.17 | Disabled controls only |

**Two hard rules.** `--text-faint` is **banned on `--surface-overlay` and `--surface-float`** — it drops to 3.92 there, below AA. Use `--text-muted` inside dialogs and menus. And `--text-disabled` never carries information on its own; a disabled control always pairs it with a tooltip explaining why.

### Filament — the signature

| Token | Value | Use |
|---|---|---|
| `--filament` | `#FFF4E2` | Presence at full intensity · active nav indicator · focus ring |
| `--filament-2` | `#E2D6C2` | Presence at rest · hovered nav |
| `--filament-3` | `#9C9384` | Presence dormant |
| `--filament-halo` | `rgba(255,244,226,.13)` | The single radial glow behind the presence mark |

**Budget: filament pixels never exceed roughly 2% of the screen.** It appears on the presence mark, the active rail indicator (a 2px bar), and the focus ring. Nowhere else. The moment it becomes a button fill or a card border, the identity collapses into the glowing-accent cliché this design exists to avoid.

### Semantic

Status only. Never branding, never decoration, never larger than a badge, icon, or 1px border.

| Role | Base | On overlay | Tint | Border |
|---|---|---|---|---|
| Danger | `--danger #F0565B` (5.65) | `--danger-text #FF8A8E` | `rgba(240,86,91,.12)` | `rgba(240,86,91,.32)` |
| Success | `--success #4CC061` (8.24) | `--success-text #7BD98A` | `rgba(76,192,97,.12)` | `rgba(76,192,97,.30)` |
| Warning | `--warning #E08C33` (7.28) | `--warning-text #EFA95F` | `rgba(224,140,51,.12)` | `rgba(224,140,51,.30)` |

`--danger` falls to 4.15 on `--surface-overlay`, so destructive text inside dialogs uses `--danger-text`. Warning is an orange-amber signal, deliberately not a decorative gold — and it is never used as an accent.

**There is no info colour.** Informational states use `--text-muted` and a shape. Fewer hues read as more expensive.

### Light theme

Designed independently, not inverted. Same ratios, same roles, warmth still reserved for presence.

```
--surface-void #E8EAED  --surface-base #F4F6F8  --surface-raised #FFFFFF
--surface-inset #EDF0F3  --surface-overlay #FFFFFF (+ shadow)
--line #D5DADF  --line-strong #949DA8
--text #14181D  --text-2 #3E464F  --text-muted #5D6874  --text-faint #6E7884
--filament #7A5E2E   (warm light against a light field must darken to stay warm)
```

### Migration from the old theme

`THEME_PRESET`, `THEME_MODE`, `THEME_PRIMARY`, `THEME_PEACOCK`, `THEME_INDIGO`, `THEME_SAFFRON`, `THEME_MOTION`, `THEME_GLOW` are still read from config. `THEME_MODE` maps to the theme switch, `THEME_MOTION` to motion intensity, `THEME_GLOW` to presence intensity. The four hue keys are ignored. Existing installs upgrade cleanly instead of resetting.

---

## 2. Typography

**Instrument Sans** for interface and prose. **JetBrains Mono** for code, metrics, hashes and scan output. Both shipped as local `.woff2` under `app/ui/fonts/` — no network, correct in an offline packaged install.

```css
--font-ui: "Instrument Sans", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Cascadia Mono", Consolas, ui-monospace, monospace;
```

No serif display face. Cream ground + high-contrast serif + terracotta is the single most recognizable generated-design signature, and it is exactly what `index.html` currently runs.

| Role | Size / line | Weight | Tracking | Use |
|---|---|---|---|---|
| `display` | 28 / 34 | 500 | −0.02em | Empty states, onboarding. Rare |
| `title-1` | 20 / 26 | 500 | −0.015em | Destination heading (one per screen) |
| `title-2` | 16 / 22 | 500 | −0.01em | Section and dialog headings |
| `body` | 14 / 21 | 400 | 0 | Prose, assistant output, inputs |
| `body-sm` | 13 / 19 | 400 | 0 | Dense lists, secondary panels |
| `label` | 12 / 16 | 500 | 0.005em | Field labels, buttons, nav |
| `meta` | 11 / 15 | 450 | 0.01em | Timestamps, counts, hints |
| `mono` | 13 / 20 | 400 | 0 | Code, hashes, metrics |
| `mono-sm` | 12 / 18 | 400 | 0 | Inline code, log lines |

**Rules.** Assistant prose caps at **72ch** — longer and the eye loses the line. Nothing is ALL-CAPS; the current `.kicker` (uppercase, `letter-spacing: .16em`) above every card is both harder to scan and a template tell. Sentence case everywhere including buttons. Weight carries hierarchy before size does. Tabular numerals (`font-variant-numeric: tabular-nums`) on every metric, timer and counter so digits stop jittering.

---

## 3. Space, size, radius

```
--space-0  0     --space-1  2px   --space-2  4px   --space-3  6px
--space-4  8px   --space-5  12px  --space-6  16px  --space-7  20px
--space-8  24px  --space-9  32px  --space-10 40px  --space-11 56px
```

Controls: `--size-xs 20px` · `--size-sm 24px` · `--size-md 28px` · `--size-lg 32px` · `--size-xl 40px`.
**Every interactive target is ≥24×24 CSS px at every Windows scale factor** (WCAG 2.5.8). `--size-xs` is decorative only.

Radius encodes hierarchy. One radius on everything is the SaaS-card tell.

| Token | Value | Applies to |
|---|---|---|
| `--radius-xs` | 3px | Chips, badges, meters, inline code |
| `--radius-sm` | 6px | Buttons, inputs, list rows, message actions |
| `--radius-md` | 10px | Panels, cards, composer, code blocks |
| `--radius-lg` | 14px | Dialogs, command palette, voice overlay |
| `--radius-full` | 999px | The presence mark and avatars only |

---

## 4. Elevation

With `--disable-gpu`, a large shadow is a full-surface software rasterization. Two levels get real shadows; everything else uses surface + border.

| Level | Recipe | Used by |
|---|---|---|
| `e0` | `--surface-base`, no border | Work area |
| `e1` | `--surface-raised` + `1px --line` | Panels, cards, composer, rail |
| `e2` | `--surface-raised` + `1px --line` + `0 1px 2px rgba(0,0,0,.45)` | Sticky headers, pinned composer |
| `e3` | `--surface-overlay` + `0 8px 24px rgba(0,0,0,.55)` + `0 0 0 1px --line` | Menus, popovers, toasts |
| `e4` | `--surface-overlay` + `0 24px 64px rgba(0,0,0,.68)` + `0 0 0 1px --line` | Dialogs, command palette |

**`backdrop-filter` does not appear in the default path.** With no GPU compositor every visible backdrop is re-blurred in software each frame on the main thread — the documented cause of sluggish UI in comparable apps, and the reason the current `index.html` already ships a `.safe-renderer` class to switch nine blurred selectors off. It returns only as Settings → Appearance → *Enhanced visuals*, off by default, applied to at most two surfaces.

---

## 5. Motion

```
--dur-instant  80ms    press, hover
--dur-fast    140ms    toggles, tooltips, chips
--dur-base    200ms    menus, tabs, panel expand
--dur-slow    320ms    dialogs, route change
--dur-presence 600ms   filament intensity

--ease-out      cubic-bezier(.16, 1, .3, 1)     entering
--ease-in       cubic-bezier(.7, 0, .84, 0)     exiting
--ease-standard cubic-bezier(.4, 0, .2, 1)      moving in place
--ease-filament cubic-bezier(.37, 0, .63, 1)    sine, breathing only
```

Durations scale with element size and travel distance — a tooltip at 140ms and a dialog at 320ms feel equally quick. Stagger for lists: 24ms per item, capped at 6 items, then all remaining items appear together.

### Four non-negotiable rules

1. **Animate `opacity` and `transform` only.** Never `width`, `height`, `top`, `left`, `box-shadow`, `filter`, or `backdrop-filter`.
2. **No animation while idle.** Every loop is bound to an application state and stops when that state ends. The current UI runs seven perpetual keyframe loops — `coreOrbit`, `dotOrbit` ×3, `coreScan`, `coreBreath`, `flameFloat`, `signalBreath`, `centerHalo` — regardless of what KALKI is doing. All are deleted.
3. **Every animation reports a state change.** If it is not telling the user what changed, it is removed.
4. **Reduced motion is a real experience.** `prefers-reduced-motion: reduce` and the Settings toggle both set every duration to 0, freeze the presence mark at its state luminance, and replace route cross-fades with instant swaps. State remains fully legible — intensity still differs between dormant, ready, thinking and speaking. Nothing is lost except movement.

### The presence mark

28px, at the top of the rail. It is the KALKI logo and the state indicator in one object. It **never** occupies the centre of the screen.

Two DOM nodes: a `--filament` core and a radial-gradient halo. Only `opacity` and `scale` ever change.

| State | Core opacity | Scale | Motion |
|---|---|---|---|
| Dormant | 0.10 | 1.00 | none |
| Ready | 0.22 | 1.00 | none |
| Attending | 0.60 | 1.06 | rise over 180ms, hold 4s |
| Thinking | 0.45 → 0.65 | 1.00 → 1.03 | 2.4s sine |
| Speaking | 0.55 → 0.75 | 1.00 → 1.05 | 900ms sine |
| Interrupted | 0.20 | 0.98 | fall over 120ms |
| Unavailable | 0.10, desaturated | 0.96 | none |

During an explicit voice session the mark blooms into a 160px overlay form — same two nodes, same two properties, `scale` interpolated. It returns to 28px on exit. There is no second presence object anywhere in the product.

---

## 6. Components

Every component implements the full state set: **default · hover · focus-visible · active · selected · disabled · loading · error**. Async components add **pending · streaming · interrupted · retry**.

### Focus

```css
:focus-visible {
  outline: 2px solid var(--line-focus);
  outline-offset: 2px;
  border-radius: inherit;
}
```

`--line-focus` is `#FFF4E2` — 17.63 against base, far past the 3:1 floor (WCAG 1.4.11). Focus is the one place warm light appears outside the presence mark, which is deliberate: attention and presence share a visual language. `outline: none` is banned. Scroll containers carry `scroll-padding-block: var(--space-8)` so a focused control is never fully hidden by sticky chrome (WCAG 2.4.11).

### Buttons

| Variant | Rest | Hover | Active | Disabled |
|---|---|---|---|---|
| Primary | `--surface-float` + `--text` | `+6%` luminance | `scale(.98)`, 80ms | `--surface-raised` + `--text-disabled` |
| Secondary | `--surface-raised` + `1px --line` | border → `--line-strong` | `scale(.98)` | as above |
| Ghost | transparent + `--text-2` | `--surface-raised` | `scale(.98)` | `--text-disabled` |
| Danger | `--danger-bg` + `1px --danger-line` + `--danger` | tint → 18% | `scale(.98)` | as above |

There is no filament-filled button. The accent stays reserved.

Loading replaces the label with three 3px dots pulsing at 120ms offsets, keeps the button's measured width so nothing reflows, and sets `aria-busy="true"`.

### Input, textarea, select

`--surface-inset`, `1px --line-strong` (3.14 — the border is the only thing defining the field), `--radius-sm`, 8px/10px padding, 14px text. Focus swaps the border to `--line-focus` and adds the outline. Error swaps to `--danger-line` with the message in `--danger`, linked by `aria-describedby`. Placeholders use `--text-faint` and never replace a label.

### Dialog

Native `<dialog>` + `showModal()`. The top layer makes the rest of the document inert — no hand-written focus trap, `Escape` works for free, focus returns to the trigger on close. `e4` elevation, `--radius-lg`, 480px default width and 720px for settings, max height `min(720px, 85vh)`. Enters at `opacity 0 → 1`, `scale .97 → 1` over `--dur-slow` with `--ease-out`; backdrop `rgba(7,8,9,.72)`, no blur.

### Command palette

`e4`, `--radius-lg`, 640px wide, anchored 18vh from the top. The input takes focus on open, not the close button. Results are a `role="listbox"` with `aria-activedescendant`; DOM focus stays in the input throughout. Groups are labelled but not focusable. Each row shows icon, label, context, and its shortcut in a `Kbd` chip. Selected row gets `--surface-float` plus a 2px `--filament` bar on its leading edge — the same active-indicator language as the rail. Opens in under 100ms; no animation on the results list, only on the container.

### Message

Assistant turns are prose on `--surface-base` with a 2px `--line-subtle` rule on the leading edge and a small `--filament-3` mark at the top. **No bubbles for KALKI** — bubbles fight long-form output. User turns sit on `--surface-raised` with `--radius-md`, indented to 88% width.

Markdown: headings at `title-2`; lists with 20px hanging indent; code blocks on `--surface-inset` with `--radius-md`, a language label, and a copy button; inline code on `--surface-raised` at `--radius-xs`; tables with `--line-subtle` rules and horizontal scroll; blockquotes with a 2px `--line` leading rule.

Actions (copy, regenerate, edit and resend, report) appear on hover and on focus-within, at 24px, `--text-muted` → `--text` on hover. They are always reachable by keyboard, never hover-only.

Streaming: text appends live; code blocks buffer until the closing fence lands to stop fence flicker. A 2px `--filament` caret sits at the tail. A polite live region carries the accumulated text on a 400ms throttle — never per token, or screen readers are flooded.

### ToolRun

One row per action: icon, plain-language name, status, elapsed time, and a disclosure for detail.

| State | Presentation |
|---|---|
| Pending | `--text-muted`, "Queued" |
| Running | `--text-2`, elapsed counter, 2px indeterminate bar |
| Needs confirmation | `--warning-bg`, what will run, Confirm / Cancel, **visible 30s countdown** matching `_PENDING_TTL` |
| Succeeded | `--success` check, collapsed, expandable |
| Failed | `--danger` mark, human message, Retry, raw detail behind a disclosure |

Names are what the user asked for — "Checked your calendar", not `gcal.today_events`.

### Composer

`--surface-raised`, `1px --line`, `--radius-md`, `e2`. Auto-grows from 1 to 8 lines then scrolls. Trailing controls: microphone, attach, send — each 28px, ≥24px hit target. Send becomes Stop while streaming, same position, colour shift to `--danger`, no layout movement.

Below the field, one 11px `--text-faint` line: model name · context meter · voice state when not idle. **The context meter tells the truth about `MAX_HISTORY = 20`** — "6 of 10 turns in context". A limitation surfaced is a trust signal; a limitation hidden is the "why did it forget?" complaint.

Drag-over paints a 2px dashed `--line-strong` border on the composer only, never a full-screen overlay. The attach button is the required non-drag equivalent (WCAG 2.5.7).

### EmptyState and ErrorState

Empty: a 32px outlined glyph in `--text-faint`, a `title-2` line of what this is for, one `body-sm` line in `--text-muted`, one primary action, one shortcut hint. Left-aligned, capped at 380px, positioned at 38% height — not vertically centred, which reads as an error.

Error: `--danger` mark, plain statement of what failed, what to do, a Retry, and "View details" opening the diagnostics drawer. `str(e)` from `_safe_call` lives in the drawer and nowhere else.

### Toast

`e3`, `--radius-sm`, bottom-right, stacked to 3 with the oldest collapsing. Enters `translateY(8px) → 0` + fade over `--dur-base`. Auto-dismiss at 5s; never for errors, which stay until dismissed. A 2px leading bar in the semantic colour. Announced via `aria-live` — polite for success, assertive for failure.

### Rail

56px collapsed, 208px expanded, `--surface-raised`, `1px --line` on the trailing edge. Presence mark at top with 16px below it. Items are 40px tall, icon at 20px.

Active is a **2px `--filament` bar on the leading edge** plus `--text` label — not a filled pill, not a glow. Hover raises the row to `--surface-overlay`. Expansion animates `width` on the rail only, using `transform` on the labels so no text reflows. State persists to `localStorage`.

### Others

**Tooltip** — `e3`, 11px, 120ms delay in / 0 out, `aria-describedby`, never the only source of an accessible name.
**Menu** — `e3`, `--radius-sm`, 28px items, arrow-key movement, type-ahead, `Escape` closes and restores focus.
**Tabs** — full `tablist` / `tab` / `tabpanel`, manual activation, 2px `--filament` underline on the active tab, arrow keys move.
**Toggle** — 32×18 track, `--surface-float` off / `--success` on, 14px knob sliding on `transform`, 140ms.
**Slider** — 3px track, 14px thumb, `--line-strong` rail, `--text` fill, arrow and Page keys, value announced.
**Chip** — `--radius-xs`, 11px, `--surface-raised` + `1px --line-subtle`. Removable chips carry a 20px × with a 24px hit area.
**Meter** — 3px bar, `--surface-inset` track, `--text-muted` fill, `--warning` above 80%, `--danger` above 92%. Never animated on a timer; only on value change.
**MemoryItem** — text at `body`, type chip, importance as three 3px dots, `created_at` in `meta`. Pinned items carry a 2px `--filament-3` leading rule and sort first, matching the backend's real behaviour for `type: "pinned"`.
**IntegrationCard** — logo, name, status dot, one line of state. Unconfigured is a designed state, not an error: `--text-muted` copy plus a "Connect" action.

---

## 7. Iconography

One set, drawn in-house as inline SVG: 20px grid, 1.5px stroke, round caps and joins, `currentColor`, no fills except status dots. Shipped as a single sprite under `app/ui/`, never fetched from a CDN.

No emoji anywhere in the interface. The current UI uses `＋ ■ ◉ → 📬 ◇` as controls; emoji render inconsistently across Windows versions, ignore `currentColor`, and cannot be sized reliably. Every icon-only control carries an `aria-label` and a tooltip with identical text.

---

## 8. Writing

Sentence case. Active verbs. Plain nouns. An action keeps its name through the whole flow — the button that says "Save changes" produces a toast that says "Changes saved".

Never expose backend vocabulary. Not "GROQ_API_KEY invalid" but "That Groq key wasn't accepted." Not "gcal.is_configured() false" but "Google Calendar isn't connected yet."

Errors state what happened and what to do, in the product's voice. They do not apologise and they are never vague. Empty states are invitations. Loading states name the phase — "Reaching the model", "Running the scan", "Waiting for you to confirm" — because an unlabelled spinner is an admission that the interface does not know what is happening.

---

## 9. Quality bar

Before any screen is called done:

- [ ] Every interactive element has all eight base states implemented
- [ ] Keyboard alone completes the task; focus is visible at every step
- [ ] `prefers-reduced-motion` leaves the screen fully legible
- [ ] Correct at 960×680 (the window minimum) and at 200% Windows scaling
- [ ] No `backdrop-filter`, no animated `box-shadow`, no idle animation loop
- [ ] Filament appears only as presence, active indicator, or focus ring
- [ ] Nothing is ALL-CAPS; no emoji; one radius per hierarchy level
- [ ] Every control calls a real endpoint, does real local work, or says plainly that the capability is not configured
- [ ] Contrast verified against the surface the element actually sits on, not against `--surface-base` by default
- [ ] Zero console errors
