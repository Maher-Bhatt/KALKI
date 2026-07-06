# Fix log — 2026-07-05

## Theme (corrected mid-pass)
First pass wrongly went with a gold/saffron "Indian theme" based on a stale
note — not what was asked. Reverted. Current palette is monochrome dark:
graphite/charcoal background, platinum-grey primary accent, muted bronze for
the "listening" state, muted slate-plum for "thinking," desaturated brick red
for danger. No gold, no cyan, no neon anywhere. `SYSTEM CORE` / `SYSTEM` tag
are back to their original names (the BHARAT rename was part of the same
wrong direction). All still driven from the `:root` CSS variables in
index.html, so the whole orb/mandala visual re-themes from one place.

## System commands (sleep/shutdown/restart/lock) — actually execute now
The functions were correct, but the phrase-matching that triggers them only
caught a handful of exact strings (`"put pc to sleep"`). Natural phrasing
("put my computer on sleep") missed every one of them and fell through to
the chat LLM, which has no tool to actually run these — it just replied as
if it had. Fixed: matching now checks for the verb + any PC-ish noun
(pc/computer/laptop/system/machine), or the bare word alone. Also added
sleep/restart/shutdown to the `system_control` LLM tool as a second path,
gated behind the same "say confirm" safety check either way.

## Weather / location showing the wrong city
`update_location_from_ip()` ran on every startup and unconditionally
overwrote `OWNER_CITY` with an IP-geolocation guess — which resolves to
whatever city your ISP routes through, not your actual town. It was
silently overwriting a correctly-configured city every time. Fixed: it now
only fills in a city if none is configured. Set your real city in
config.py / the Setup Wizard and it will be respected.

## Spotify 403
`_safe()` — a helper that detects a stale OAuth token scope, clears it, and
tells you to reconnect — existed but was never actually called by any of
the playback functions (`play`, `pause`, `next_track`, etc. all had their
own bare try/except that just surfaced the raw error). Wired all of them
through it. If the 403 isn't a stale-scope issue, the message now says
plainly that Spotify's Web API rejects playback control on non-Premium
accounts — recreating the app registration doesn't fix that specific case.

## Setup Wizard
Added a "Voice & Personality" step — voice selection, Listen Mode
(always-on wake word vs. push-to-talk), personality spice toggle. These
previously required hand-editing config.py.

Also rethemed the wizard itself — it was using CustomTkinter's stock blue
theme, which didn't match the platinum/graphite palette in index.html at
all. Overrode the theme's colors in place (kept every other CTk default —
corner radius, border widths, disabled states — untouched, only swapped
colors) so it matches now.

## What was actually tested
Installed `customtkinter` + a virtual X display in the sandbox and ran the
real wizard code — instantiated it, stepped through all 8 screens, filled
in every field like a real user would, called `save_config()`, and
confirmed config.py came out with the right values. Screenshotted before
and after the retheme to confirm the colors actually changed and nothing
broke. This is a genuine run of your code, not just a read-through.

What I could NOT test from here: anything that needs Windows itself —
pywebview rendering the actual main window, real sleep/shutdown/restart
execution, hardware detection via WMI, TTS voices actually speaking, a real
Spotify OAuth round-trip, the mic/wake-word pipeline. Those need a run on
your machine. Syntax and logic are verified; live Windows behavior isn't
something I can fully claim I confirmed from a Linux sandbox.

## Greeting
Now pulls real weather into the line, and the system-check tone actually
varies with how the day looks (packed calendar + unread mail reads
differently than a clear day) instead of always reading the same.

## Screen Time (dashboard panel)
Was categorizing by window title text and dumping anything unmatched into
a flat "Other" with no detail. Now categorizes by the actual process name
(far more reliable — a browser title varies, `chrome.exe` doesn't), covers
far more apps (office suite, design tools, terminals, file managers, IDEs
beyond VS Code), and — the actual complaint — "Other" now names the real
apps inside it instead of hiding them. Old data files still read fine
(falls back gracefully if you have no per-app detail yet).
