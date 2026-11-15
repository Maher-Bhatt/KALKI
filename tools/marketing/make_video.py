"""KALKI promo video: real screenshots, motion, captions and KALKI's own voice.

Frames are rendered one by one in Edge (deterministic, no dropped frames) and piped to
ffmpeg. Makes 1920x1080 (Store trailer, YouTube, X, LinkedIn) and 1080x1920 (Reels, Shorts)."""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import asyncio
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import edge_tts
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = REPO / "marketing"
SHOTS = ROOT / "store" / "screenshots"
OUT = ROOT / "video"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_video_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
VOICE = "en-US-AndrewMultilingualNeural"

# id, screenshot (theme/name) or None, caption, sub, voice line, focus x% for the vertical cut
SCENES = [
    ("intro", None, "Meet KALKI", "Your personal AI assistant for Windows.",
     "Meet KALKI. A personal AI assistant that lives on your Windows PC.", 50),
    ("voice", "dark/04_voice_mode", "Just talk.", "It listens, answers, and lets you interrupt.",
     "Just talk. It listens, answers out loud, and stops the moment you interrupt.", 50),
    ("today", "light/03_today_briefing", "Your day, briefed.", "Calendar, reminders, tasks and weather.",
     "Every morning, it briefs you on your calendar, reminders, tasks, and the weather.", 40),
    ("ask", "light/02_conversation", "Ask anything.", "Answers that fit your day.",
     "Ask anything, and get answers that fit your day.", 52),
    ("setup", "light/05_onboarding", "Ready in three minutes.", "A guide for every key, and a real test.",
     "Setup takes three minutes, with a guide for every key.", 58),
    ("security", "light/07_security_checkup", "Safer, with Windows Defender.", "Plain answers. Never made-up threats.",
     "And it works with Windows Defender to keep your PC safe.", 45),
    ("outro", None, "Free for Windows.", "Open source<br><span style=\"white-space:nowrap\">github.com/Maher-Bhatt/KALKI</span>",
     "KALKI. Free for Windows, and open source.", 50),
]


async def tts_lines():
    out = []
    for i, scene in enumerate(SCENES):
        path = TMP / f"line_{i}.mp3"
        await edge_tts.Communicate(scene[4], VOICE, rate="-4%").save(str(path))
        out.append(path)
    return out


def duration(path):
    info = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def timeline(lines):
    t, plan = 0.0, []
    for scene, line in zip(SCENES, lines):
        speak_at = t + (0.6 if not plan else 0.35)
        length = max(duration(line) + 1.15, 4.6)
        plan.append({"id": scene[0], "shot": scene[1], "caption": scene[2], "sub": scene[3], "focus": scene[5],
                     "start": round(t, 3), "end": round(t + length, 3), "voice_at": round(speak_at, 3)})
        t += length
    return plan, t + 0.8


PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden;background:#f7f4ef;font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;color:#1e1b17}
.serif{font-family:"Sitka Display","Sitka Heading","Palatino Linotype",Georgia,serif;letter-spacing:-.015em;font-weight:400}
.scene{position:absolute;inset:0;opacity:0}
.scene.dark{background:#141413;color:#ece6dc}.scene.light{background:#f7f4ef}
.ridges{position:absolute;left:-5%;bottom:-2%;width:110%;height:40%;color:#b9ad9b;opacity:.5}
.dark .ridges{color:#6b6357;opacity:.45}
.cap{position:absolute;z-index:2}
.cap h1{line-height:1.04}.cap p{opacity:.7;margin-top:.5em}
.frame{position:absolute;overflow:hidden;border-radius:18px;border:1px solid rgba(120,105,85,.35);box-shadow:0 40px 90px -30px rgba(40,30,15,.55);background:#fcfbf8}
.dark .frame{border-color:#3a3631;box-shadow:0 40px 90px -30px rgba(0,0,0,.9);background:#1b1a18}
.frame .img{position:absolute;inset:0;background-repeat:no-repeat;transform-origin:50% 40%}
.mark{display:flex;align-items:center;gap:.55em;font-weight:650;letter-spacing:.18em}
.mark svg{width:1.3em;height:1.3em}
.center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;z-index:2}
</style></head><body>__SCENES__
<script>
const PLAN = __PLAN__; const VERTICAL = __VERTICAL__; const FADE = 0.45;
const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
window.render = (t) => {
  for (const s of PLAN) {
    const el = document.getElementById('s-' + s.id);
    const local = t - s.start, len = s.end - s.start;
    let o = 0;
    if (t >= s.start - FADE && t <= s.end + FADE) o = Math.min(ease((local + FADE) / FADE), ease((s.end + FADE - t) / FADE));
    if (s === PLAN[0]) o = local < len ? 1 : ease((s.end + FADE - t) / FADE);
    if (s === PLAN[PLAN.length - 1] && t >= s.start) o = Math.min(1, ease((local + FADE) / FADE));
    el.style.opacity = o;
    const p = Math.min(1, Math.max(0, local / len));
    const img = el.querySelector('.img');
    if (img) img.style.transform = `scale(${1.0 + 0.06 * p})`;
    const cap = el.querySelector('.cap, .center');
    if (cap) { const k = ease(local / 0.7); cap.style.transform = `translateY(${(1 - k) * 26}px)`; cap.style.opacity = k; }
  }
};
</script></body></html>"""

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
RIDGES = ('<svg class="ridges" viewBox="0 0 640 300" preserveAspectRatio="xMidYMax slice"><g fill="currentColor">'
          '<circle cx="470" cy="70" r="34" opacity=".1"/><path opacity=".3" d="M0 238 C50 230 85 218 120 210 C170 190 205 160 250 150 C290 140 310 112 345 92 C362 82 372 66 392 52 C404 44 414 46 424 58 C440 76 452 90 474 98 C500 108 520 128 548 132 C580 136 610 150 640 160 L640 300 L120 300 Z"/>'
          '<path opacity=".42" d="M0 264 C20 258 40 254 60 250 C120 236 170 214 220 206 C270 198 300 176 340 166 C380 156 400 142 432 138 C466 134 488 152 520 162 C556 174 600 178 640 190 L640 300 L60 300 Z"/>'
          '<path opacity=".55" d="M0 284 C80 268 150 256 220 252 C300 248 340 232 400 226 C470 220 520 236 580 240 C606 242 624 246 640 250 L640 300 L0 300 Z"/></g></svg>')


def scenes_html(plan, vertical):
    parts = []
    for s in plan:
        dark = s["id"] in ("voice", "outro") or (s["shot"] or "").startswith("dark")
        cls = "dark" if dark else "light"
        if not s["shot"]:
            big = "15vw" if vertical else "7.6vw"
            parts.append(f'<div class="scene {cls}" id="s-{s["id"]}">{RIDGES}<div class="center">'
                         f'<div class="mark" style="font-size:{"5.5vw" if vertical else "2.2vw"};margin-bottom:{"5vw" if vertical else "2vw"}">{MARK}KALKI</div>'
                         f'<div class="cap" style="position:static"><h1 class="serif" style="font-size:{big}">{s["caption"]}</h1>'
                         f'<p style="font-size:{"4.4vw" if vertical else "1.9vw"};padding:0 6vw">{s["sub"]}</p></div></div></div>')
            continue
        src = (SHOTS / (s["shot"].split("/")[0]) / "3840x2160" / (s["shot"].split("/")[1] + ".png")).as_uri()
        if vertical:
            frame = (f'<div class="frame" style="left:6%;right:6%;top:31%;bottom:9%">'
                     f'<div class="img" style="background-image:url({src});background-size:auto 100%;background-position:{s["focus"]}% 0"></div></div>')
            cap = (f'<div class="cap" style="left:8%;right:8%;top:9%"><h1 class="serif" style="font-size:10.5vw">{s["caption"]}</h1>'
                   f'<p style="font-size:4.4vw">{s["sub"]}</p></div>')
        else:
            frame = (f'<div class="frame" style="left:20%;right:4%;top:11%;aspect-ratio:16/9">'
                     f'<div class="img" style="background-image:url({src});background-size:100% auto"></div></div>')
            cap = (f'<div class="cap" style="left:4.5%;top:36%;width:15%"><h1 class="serif" style="font-size:3.4vw">{s["caption"]}</h1>'
                   f'<p style="font-size:1.25vw">{s["sub"]}</p></div>')
        parts.append(f'<div class="scene {cls}" id="s-{s["id"]}">{RIDGES}{cap}{frame}</div>')
    return "".join(parts)


def render(plan, total, w, h, vertical, out_path, audio_path):
    html = PAGE.replace("__SCENES__", scenes_html(plan, vertical)).replace("__PLAN__", json.dumps(plan)).replace(
        "__VERTICAL__", "true" if vertical else "false")
    page_path = TMP / ("v.html" if vertical else "h.html")
    page_path.write_text(html, encoding="utf-8")
    frames = int(total * FPS)
    ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                           "-i", str(audio_path), "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(out_path)],
                          stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=["--allow-file-access-from-files"])
        ctx = browser.new_context(viewport={"width": w, "height": h})
        pg = ctx.new_page()
        pg.goto(page_path.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(600)
        for i in range(frames):
            pg.evaluate(f"window.render({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
            if i % 150 == 0:
                print(f"  {out_path.name}: frame {i}/{frames}", flush=True)
        if not vertical:
            pg.evaluate("window.render(2.2)")
            pg.screenshot(path=str(OUT / "kalki_promo_thumbnail.png"))
        browser.close()
    ff.stdin.close()
    ff.wait()


def mix_audio(plan, lines, total):
    out = TMP / "voice.m4a"
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for line in lines:
        cmd += ["-i", str(line)]
    filters = [f"[{i}:a]adelay={int(s['voice_at'] * 1000)}|{int(s['voice_at'] * 1000)}[a{i}]" for i, s in enumerate(plan)]
    filters.append("".join(f"[a{i}]" for i in range(len(plan))) + f"amix=inputs={len(plan)}:normalize=0,apad,atrim=0:{total:.2f}[out]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(out)]
    subprocess.run(cmd, check=True)
    return out


def main():
    lines = asyncio.run(tts_lines())
    plan, total = timeline(lines)
    for s in plan:
        print(f"{s['id']:9} {s['start']:6.2f}s to {s['end']:6.2f}s", flush=True)
    print(f"total {total:.1f}s", flush=True)
    audio = mix_audio(plan, lines, total)
    which = sys.argv[1:] or ["h", "v"]
    if "h" in which:
        render(plan, total, 1920, 1080, False, OUT / "kalki_promo_1920x1080.mp4", audio)
    if "v" in which:
        render(plan, total, 1080, 1920, True, OUT / "kalki_promo_1080x1920.mp4", audio)
    (OUT / "SCRIPT.md").write_text("# KALKI promo · narration\n\n" + "\n".join(
        f"- **{s['start']:.1f}s, {s['caption']}**: {sc[4]}" for s, sc in zip(plan, SCENES)) +
        f"\n\nLength: {total:.1f} s. Voice: Microsoft Edge neural voice {VOICE} (KALKI's default voice).\n", encoding="utf-8")


if __name__ == "__main__":
    main()
