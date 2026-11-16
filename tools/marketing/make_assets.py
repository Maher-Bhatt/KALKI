"""Render KALKI's Store art and social posts from HTML designs and the real screenshots."""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import os
import pathlib
import tempfile
from playwright.sync_api import sync_playwright

ROOT = REPO / "marketing"
SHOTS = ROOT / "store" / "screenshots"
STORE = ROOT / "store"
SOCIAL = ROOT / "social"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_art_"))


def shot(theme, name):
    return (SHOTS / theme / "3840x2160" / f"{name}.png").as_uri()


MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" '
        'stroke-linecap="round"><path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
RIDGES = ('<svg class="ridges" viewBox="0 0 640 300" preserveAspectRatio="xMidYMax slice"><g fill="currentColor">'
          '<circle cx="470" cy="70" r="34" opacity=".10"/>'
          '<path opacity=".30" d="M0 238 C50 230 85 218 120 210 C170 190 205 160 250 150 C290 140 310 112 345 92 C362 82 372 66 392 52 C404 44 414 46 424 58 C440 76 452 90 474 98 C500 108 520 128 548 132 C580 136 610 150 640 160 L640 300 L120 300 Z"/>'
          '<path opacity=".42" d="M0 264 C20 258 40 254 60 250 C120 236 170 214 220 206 C270 198 300 176 340 166 C380 156 400 142 432 138 C466 134 488 152 520 162 C556 174 600 178 640 190 L640 300 L60 300 Z"/>'
          '<path opacity=".55" d="M0 284 C80 268 150 256 220 252 C300 248 340 232 400 226 C470 220 520 236 580 240 C606 242 624 246 640 250 L640 300 L0 300 Z"/></g></svg>')

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%}
body{font-family:"Segoe UI Variable Display","Segoe UI",system-ui,sans-serif;background:#f7f4ef;color:#1e1b17;overflow:hidden;position:relative;-webkit-font-smoothing:antialiased}
body.dark{background:#141413;color:#ece6dc}
.serif{font-family:"Sitka Display","Sitka Heading","Palatino Linotype",Georgia,serif;font-weight:400;letter-spacing:-.015em}
.ridges{position:absolute;left:-5%;right:-5%;bottom:-2%;width:110%;height:38%;color:#b9ad9b;opacity:.55;z-index:0}
body.dark .ridges{color:#6b6357;opacity:.45}
.mark{display:inline-flex;align-items:center;gap:.5em;font-weight:650;letter-spacing:.16em}
.mark svg{width:1.25em;height:1.25em}
.win{position:relative;z-index:1;border-radius:.62vw;overflow:hidden;background:#fcfbf8;border:1px solid #d9d1c4;box-shadow:0 3vw 7vw -2.5vw rgba(40,30,15,.45)}
body.dark .win{background:#1b1a18;border-color:#3a3631;box-shadow:0 3vw 7vw -2vw rgba(0,0,0,.8)}
.win .bar{height:2.3vw;min-height:16px;display:flex;align-items:center;gap:.5vw;padding:0 0 0 .9vw;background:#efebe4;border-bottom:1px solid #e2dbcf;font-family:"Segoe UI Variable Text","Segoe UI",sans-serif;font-size:.78vw;color:#3a342c}
.win .bar .ttl{display:flex;align-items:center;gap:.45vw;flex:1}
.win .bar .ttl svg{width:1vw;height:1vw}
.win .bar .cap{display:flex;height:100%}
.win .bar .cap span{width:3.4vw;height:100%;display:flex;align-items:center;justify-content:center}
.win .bar .cap svg{width:.72vw;height:.72vw}
body.dark .win .bar{color:#e6dfd3}
body.dark .win .bar{background:#23211e;border-color:#34312c}
.win img{display:block;width:100%}
.pill{display:inline-block;padding:.45em 1.1em;border-radius:999px;border:1px solid currentColor;opacity:.8;font-size:.9em}
.ink{background:#2a2520;color:#f7f2ea}
"""


WINCAPS = ('<span><svg viewBox="0 0 10 10"><path d="M0 5h10" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9" rx="1.2" fill="none" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><path d="M.5 .5l9 9M9.5 .5l-9 9" stroke="currentColor" stroke-width=".9"/></svg></span>')


def page(body, cls=""):
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body class="{cls}">{body}</body></html>'


def window(src, extra=""):
    return f'<div class="win" style="{extra}"><div class="bar"><div class="ttl">{MARK}<span>KALKI</span></div><div class="cap">{WINCAPS}</div></div><img src="{src}"></div>'


# ── Store screenshots with a headline (kept in the top third, per Store guidance) ──
CAPTIONS = {
    "01_ask_home": ("Your personal AI assistant,", "right on your PC."),
    "02_conversation": ("Ask anything.", "Get answers that fit your day."),
    "03_today_briefing": ("Your day, briefed.", "Calendar, reminders, tasks and weather."),
    "04_voice_mode": ("Just talk.", "It listens, answers, and lets you interrupt."),
    "05_onboarding": ("Ready in three minutes.", "A guide for every key, and a real test."),
    "06_notes": ("Notes that stay findable.", "Search, #tags, edit and export."),
    "07_security_checkup": ("Safer, with Windows Defender.", "Plain answers, never made-up threats."),
    "08_screen_time": ("See where your time goes.", "Kept only on your PC. Delete any time."),
}


def captioned(theme, name):
    a, b = CAPTIONS[name]
    return page(f"""
    {RIDGES}
    <div style="position:absolute;inset:0;padding:4.2vw 6vw 0;display:flex;flex-direction:column;align-items:center;z-index:1">
      <div class="mark" style="font-size:1.25vw;opacity:.85;margin-bottom:1.2vw">{MARK}KALKI</div>
      <h1 class="serif" style="font-size:3.5vw;line-height:1.08;text-align:center">{a}<br><span style="opacity:.62">{b}</span></h1>
      <div style="margin-top:2.6vw;width:74vw">{window(shot(theme, name))}</div>
    </div>""", theme)


# ── Store logos and hero art ──
def tile(size_px):
    return page(f"""<div class="ink" style="position:absolute;inset:0;display:grid;place-items:center">
      <div style="width:56%;color:#f7f2ea">{MARK}</div></div>""")


def box_art():
    return page(f"""{RIDGES}<div style="position:absolute;inset:0;display:grid;place-items:center;z-index:1">
      <div style="text-align:center"><div style="width:30vw;margin:0 auto 3vw;color:#2a2520">{MARK}</div>
      <div class="mark" style="font-size:7vw;letter-spacing:.2em;justify-content:center">KALKI</div></div></div>""")


def poster(theme="light"):
    return page(f"""{RIDGES}
    <div style="position:absolute;inset:0;padding:9vw 8vw;display:flex;flex-direction:column;z-index:1">
      <div class="mark" style="font-size:4.4vw">{MARK}KALKI</div>
      <h1 class="serif" style="font-size:10.5vw;line-height:1.02;margin-top:7vw">An assistant<br>that lives on<br>your PC, and<br>talks back.</h1>
      <p style="font-size:3.8vw;line-height:1.45;opacity:.72;margin-top:4vw">Plans your day, plays your music, opens your apps, keeps you safe.</p>
      <div style="margin-top:auto">{window(shot(theme, "03_today_briefing"))}</div>
    </div>""", theme)


def hero(theme="light"):
    return page(f"""{RIDGES}
    <div style="position:absolute;right:4vw;top:10vw;width:60vw;z-index:1">{window(shot(theme, "01_ask_home"))}</div>""", theme)


# ── Social posts ──
def social_cover(w, h, theme="light"):
    tall = h > w
    shot_w = "112%" if tall else "100%"
    return page(f"""{RIDGES}
    <div style="position:absolute;inset:0;padding:{'9vw 8vw' if tall else '6vw 6vw'};display:flex;flex-direction:column;z-index:1">
      <div class="mark" style="font-size:{'4.2vw' if tall else '2.4vw'}">{MARK}KALKI</div>
      <h1 class="serif" style="font-size:{'10vw' if tall else '6.2vw'};line-height:1.04;margin-top:{'6vw' if tall else '3vw'}">Meet your AI<br>assistant for Windows.</h1>
      <p style="font-size:{'3.9vw' if tall else '2.2vw'};opacity:.72;margin-top:{'3vw' if tall else '1.6vw'}">Talk to it. It plans your day, plays your music and keeps you in charge.</p>
      <div style="{'margin-top:12vw;width:150%;margin-left:-25vw' if tall else 'margin-top:auto;width:' + shot_w}">{window(shot(theme, "04_voice_mode" if tall else "01_ask_home"))}</div>
    </div>""", theme)


def social_feature(w, h, theme, name, kicker, title, body):
    return page(f"""{RIDGES}
    <div style="position:absolute;inset:0;padding:7vw 7vw 0;display:flex;flex-direction:column;z-index:1">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="mark" style="font-size:3vw">{MARK}KALKI</div><span class="pill" style="font-size:2.6vw">{kicker}</span></div>
      <h1 class="serif" style="font-size:8.2vw;line-height:1.05;margin-top:5vw">{title}</h1>
      <p style="font-size:3.6vw;line-height:1.45;opacity:.72;margin-top:2.4vw">{body}</p>
      <div style="margin-top:auto;margin-bottom:-6vw;width:118%">{window(shot(theme, name))}</div>
    </div>""", theme)


def social_cta(theme="dark"):
    return page(f"""{RIDGES}
    <div style="position:absolute;inset:0;padding:9vw;display:flex;flex-direction:column;justify-content:center;z-index:1">
      <div style="width:16vw;margin-bottom:6vw">{MARK}</div>
      <h1 class="serif" style="font-size:10vw;line-height:1.04">Free for Windows.<br>Open source.</h1>
      <p style="font-size:4.2vw;opacity:.72;margin-top:4vw">Download KALKI from the Microsoft Store or GitHub.</p>
      <div style="margin-top:6vw"><span class="pill" style="font-size:3.6vw;opacity:1">github.com/Maher-Bhatt/KALKI</span></div>
    </div>""", theme)


def thumbnail():
    return page(f"""{RIDGES}
    <div style="position:absolute;left:5vw;top:7vw;width:44vw;z-index:2">
      <div class="mark" style="font-size:2.6vw">{MARK}KALKI</div>
      <h1 class="serif" style="font-size:7.4vw;line-height:1.02;margin-top:2.4vw">I talk.<br>My PC<br>answers.</h1></div>
    <div style="position:absolute;right:-8vw;top:10vw;width:60vw;z-index:1">{window(shot("dark", "04_voice_mode"))}</div>""", "")


JOBS = []


def add(path, w, h, html, scale=1):
    JOBS.append((path, w, h, html, scale))


def plan():
    for theme in ("light", "dark"):
        for name in CAPTIONS:
            add(STORE / "screenshots-captioned" / theme / f"{name}.png", 1920, 1080, captioned(theme, name), 2)
    add(STORE / "logos" / "tile_icon_300x300.png", 300, 300, tile(300))
    add(STORE / "logos" / "box_art_2160x2160.png", 1080, 1080, box_art(), 2)
    add(STORE / "logos" / "box_art_1080x1080.png", 1080, 1080, box_art())
    add(STORE / "logos" / "poster_2x3_720x1080.png", 720, 1080, poster())
    add(STORE / "logos" / "poster_2x3_1440x2160.png", 720, 1080, poster(), 2)
    add(STORE / "logos" / "hero_16x9_1920x1080.png", 1920, 1080, hero())
    add(STORE / "logos" / "hero_16x9_3840x2160.png", 1920, 1080, hero(), 2)
    add(SOCIAL / "instagram" / "01_cover_1080x1080.png", 1080, 1080, social_cover(1080, 1080))
    features = [
        ("02_voice", "dark", "04_voice_mode", "Voice", "Just talk.", "It listens, answers out loud, and stops the moment you interrupt."),
        ("03_today", "light", "03_today_briefing", "Your day", "Your day, briefed.", "Calendar, reminders, tasks and weather, read to you each morning."),
        ("04_chat", "light", "02_conversation", "Ask", "Answers that fit your life.", "Plans, emails, ideas. In English, Hindi or Hinglish."),
        ("05_security", "light", "07_security_checkup", "Security", "Safer, with Windows Defender.", "Real status and plain reasons. Never a made-up threat."),
    ]
    for slug, theme, name, kicker, title, body in features:
        add(SOCIAL / "instagram" / f"{slug}_1080x1080.png", 1080, 1080, social_feature(1080, 1080, theme, name, kicker, title, body))
        add(SOCIAL / "instagram" / f"{slug}_portrait_1080x1350.png", 1080, 1350, social_feature(1080, 1350, theme, name, kicker, title, body))
    add(SOCIAL / "instagram" / "06_cta_1080x1080.png", 1080, 1080, social_cta())
    add(SOCIAL / "stories" / "story_cover_1080x1920.png", 1080, 1920, social_cover(1080, 1920, "dark"))
    add(SOCIAL / "x_twitter" / "post_1600x900.png", 1600, 900, social_cover(1600, 900))
    add(SOCIAL / "linkedin" / "post_1200x627.png", 1200, 627, social_cover(1200, 627))
    add(SOCIAL / "youtube" / "thumbnail_1280x720.png", 1280, 720, thumbnail())


def main():
    plan()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=["--allow-file-access-from-files"])
        for i, (path, w, h, html, scale) in enumerate(JOBS):
            path.parent.mkdir(parents=True, exist_ok=True)
            src = TMP / f"art_{i}.html"
            src.write_text(html, encoding="utf-8")
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale)
            pg = ctx.new_page()
            pg.goto(src.as_uri())
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(250)
            pg.screenshot(path=str(path))
            ctx.close()
            print("made", path.relative_to(ROOT), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
