# Fonts

KALKI's type stack is **Instrument Sans** (interface and prose) and
**JetBrains Mono** (code, hashes, metrics), declared in `ui/tokens.css`:

```css
--font-ui:   "Instrument Sans", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Cascadia Mono", Consolas, ui-monospace, monospace;
```

The repository does **not** ship the font binaries. Both families are
OFL-licensed and free to redistribute, but a source tree should not carry
unnecessary binaries, and KALKI must never fetch a font over the network — the
packaged app has to render correctly offline.

## Behaviour without the files

The stack falls back to Segoe UI Variable Text on Windows 11, Segoe UI on
Windows 10, and the platform UI font elsewhere. Every layout, metric and
contrast value in the design system was checked against those fallbacks, so an
install with no font files is fully correct — slightly less distinctive, not
broken.

## Adding them

Drop these files into this directory:

```
InstrumentSans-Regular.woff2
InstrumentSans-Medium.woff2
JetBrainsMono-Regular.woff2
```

then uncomment the `@font-face` block at the bottom of `ui/tokens.css`.
The `/ui/` static route already serves `font/woff2` with the correct MIME
type, and `installer.iss`, the MSIX staging step and the Linux packager all
copy `app/ui/` recursively, so no packaging change is needed.

Sources: <https://github.com/Instrument/instrument-sans> and
<https://github.com/JetBrains/JetBrainsMono>.
