# Marketing kit generators

These scripts rebuild everything in `marketing/` from the real app: screenshots, Store art,
social images and the promo videos. Nothing is mocked in the UI itself. The demo server runs
the real KALKI in a throwaway profile with example data (the name "Aarav", sample tasks,
calendar and weather), so your own data is never touched or shown.

## Requirements
- Python 3.11+ with: `playwright`, `Pillow`, `edge-tts`, `imageio-ffmpeg`
- Microsoft Edge (Playwright drives it with `channel="msedge"`, so no browser download is needed)

```bash
pip install playwright Pillow edge-tts imageio-ffmpeg
```

## Steps (from the repo root)
1. Start the demo studio and leave it running. It serves on port 10031 (set `KALKI_DEMO_PORT` to change it).
   ```bash
   python tools/marketing/run_demo.py
   ```
2. In a second terminal, capture the raw screenshots (light and dark, 3840×2160, saved to `marketing/store/screenshots/`):
   ```bash
   python tools/marketing/capture.py
   ```
3. Build the captioned screenshots, Store logos and social images:
   ```bash
   python tools/marketing/make_assets.py
   ```
4. Render the videos (`h` = 1920×1080, `v` = 1080×1920) with the voiceover:
   ```bash
   python tools/marketing/make_video.py h v
   ```
5. Stop the demo studio (Ctrl+C).

`edge-tts` needs an internet connection for the voiceover. Everything else runs offline.

## Where things go
| Output | Folder |
|---|---|
| Store listing text | `marketing/store/LISTING.md` |
| Raw and captioned screenshots | `marketing/store/screenshots/`, `marketing/store/screenshots-captioned/` |
| Tile icon, poster, box art, hero | `marketing/store/logos/` |
| Instagram, story, X, LinkedIn, YouTube images and captions | `marketing/social/` |
| Promo videos, thumbnail and script | `marketing/video/` |
