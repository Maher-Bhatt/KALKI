"""KALKI viral reel: a 16-second, beat-synced 9:16 edit built from the real app screens.

Every cut lands on a beat at 120 BPM (one beat = 0.5 s), so any trending sound at 120 BPM
(or 60/240) lines up when its drop is placed at 0:02. Three versions are written:
  kalki_reel_beat.mp4    original beat + sound effects (post as is, no copyright issues)
  kalki_reel_sfx.mp4     sound effects only (add a trending sound in Instagram on top)
  kalki_reel_silent.mp4  no audio (for CapCut / Instagram editors)
Run from the repo root:  python tools/marketing/make_reel.py
"""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import array
import json
import math
import random
import subprocess
import sys
import tempfile
import wave
import pathlib

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

SHOTS = REPO / "marketing" / "store" / "screenshots" / "dark" / "3840x2160"
OUT = REPO / "marketing" / "video" / "reel"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_reel_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H = 30, 1080, 1920
BPM = 120
B = 60 / BPM          # one beat, 0.5 s
TOTAL = 32 * B        # 8 bars, 16 s
DROP, CTA = 4 * B, 28 * B

ROAST_USER = "bro you're kinda useless ngl"
ROAST_REPLY = ("Useless? Bro, I've reminded you to drink water three times today and you're still dehydrated. "
               "Your Saturday plan is done, your report's due Friday, and you're here picking fights with your laptop. 💀")

# Screen segments: start/end in beats, screenshot, centre at start/end (fractions of the image),
# region width at start/end (fraction of the image width shown across the reel), caption lines.
SHOT_SEGS = [
    (4, 8, "04_voice_mode", (0.50, 0.30), (0.50, 0.33), 0.20, 0.34, ["just say", "“HEY KALKI”"]),
    (8, 10, "04_voice_mode", (0.48, 0.80), (0.48, 0.80), 0.37, 0.345, ["and it", "TALKS BACK"]),
    (18, 19, "03_today_briefing", (0.33, 0.24), (0.33, 0.25), 0.30, 0.27, ["PLANS", "YOUR DAY"]),
    (19, 20, "03_today_briefing", (0.36, 0.57), (0.36, 0.57), 0.27, 0.24, ["READS YOUR", "CALENDAR"]),
    (20, 21, "03_today_briefing", (0.61, 0.60), (0.61, 0.60), 0.27, 0.24, ["TRACKS", "YOUR TASKS"]),
    (21, 22, "02_conversation", (0.93, 0.44), (0.93, 0.44), 0.19, 0.17, ["PLAYS", "YOUR MUSIC"]),
    (22, 23, "06_notes", (0.50, 0.46), (0.50, 0.46), 0.31, 0.28, ["TAKES", "NOTES"]),
    (23, 24, "07_security_checkup", (0.40, 0.20), (0.40, 0.20), 0.29, 0.26, ["GUARDS", "YOUR PC"]),
    (24, 25, "08_screen_time", (0.56, 0.52), (0.56, 0.52), 0.31, 0.28, ["SCREEN", "TIME"]),
    (25, 26, "05_onboarding", (0.57, 0.32), (0.57, 0.32), 0.35, 0.32, ["ANY AI", "YOU WANT"]),
    (26, 28, "01_ask_home", (0.55, 0.30), (0.50, 0.40), 0.30, 0.62, ["ALL IN", "ONE APP"]),
]
HOOK_WORDS = ["POV:", "your PC", "finally", "talks back 🗣️"]
CHAT = {"user": 10, "kalki": 11, "type_from": 11.5, "type_to": 15.5, "punch": 16}  # beats

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
RIDGES = ('<svg class="ridges" viewBox="0 0 640 300" preserveAspectRatio="xMidYMax slice"><g fill="currentColor">'
          '<path opacity=".3" d="M0 238 C50 230 85 218 120 210 C170 190 205 160 250 150 C290 140 310 112 345 92 C362 82 372 66 392 52 C404 44 414 46 424 58 C440 76 452 90 474 98 C500 108 520 128 548 132 C580 136 610 150 640 160 L640 300 L0 300 Z"/>'
          '<path opacity=".42" d="M0 264 C20 258 40 254 60 250 C120 236 170 214 220 206 C270 198 300 176 340 166 C380 156 400 142 432 138 C466 134 488 152 520 162 C556 174 600 178 640 190 L640 300 L0 300 Z"/>'
          '<path opacity=".55" d="M0 284 C80 268 150 256 220 252 C300 248 340 232 400 226 C470 220 520 236 580 240 C606 242 624 246 640 250 L640 300 L0 300 Z"/></g></svg>')

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#0f0f0e;color:#f4eee4;font-family:"Segoe UI Variable Display","Segoe UI",sans-serif}
#cam{position:absolute;inset:0;overflow:hidden}
.layer{position:absolute;inset:0;display:none;overflow:hidden}
.shot img{position:absolute;max-width:none}
.bgimg{position:absolute;inset:-80px;background-size:cover;background-position:center;filter:blur(22px) brightness(.5) saturate(.8)}
.shade{position:absolute;inset:0;pointer-events:none;background:
  linear-gradient(180deg,rgba(10,10,9,.92) 0%,rgba(10,10,9,.55) 26%,rgba(10,10,9,0) 42%,rgba(10,10,9,0) 70%,rgba(10,10,9,.75) 100%)}
.vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 55%,rgba(0,0,0,.55) 100%)}
#cap{position:absolute;left:0;right:0;top:250px;text-align:center;z-index:5;display:none;transform-origin:50% 50%}
#cap .l1{font-weight:900;font-size:76px;letter-spacing:.01em;line-height:1.05;text-shadow:0 6px 30px rgba(0,0,0,.8)}
#cap .l2{display:inline-block;margin-top:14px;font-weight:900;font-size:104px;line-height:1;padding:10px 30px 18px;border-radius:22px;
  background:#efe4cf;color:#151413;box-shadow:0 20px 60px -10px rgba(0,0,0,.7)}
#hook{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:6px}
#hook .w{font-weight:900;font-size:132px;line-height:1.04;opacity:0;text-shadow:0 10px 40px rgba(0,0,0,.8)}
#hook .w.pov{font-size:84px;color:#efe4cf;letter-spacing:.06em}
#hook .w.last{display:inline-block;background:#efe4cf;color:#151413;padding:4px 34px 18px;border-radius:26px;margin-top:14px;text-shadow:none}
.chatwrap{position:absolute;left:76px;right:76px;top:600px}
.ubub{margin-left:auto;width:fit-content;max-width:820px;background:#2a2826;border:2px solid #3b3834;border-radius:30px 30px 8px 30px;padding:22px 34px;font-size:50px;font-weight:600}
.ubub .who{font-size:28px;opacity:.55;font-weight:600;margin-bottom:6px}
.kcard{margin-top:44px;background:#1d1c1a;border:2px solid #34312d;border-radius:30px;padding:34px 40px 40px;font-size:48px;line-height:1.36;min-height:120px}
.kcard .who{display:flex;align-items:center;gap:14px;font-size:30px;font-weight:700;letter-spacing:.12em;margin-bottom:16px;color:#efe4cf}
.kcard .who svg{width:40px;height:40px}
.caret{display:inline-block;width:4px;height:52px;background:#efe4cf;vertical-align:-8px;margin-left:4px}
#cta{background:#0f0f0e;display:none}
.ridges{position:absolute;left:-5%;bottom:-2%;width:110%;height:42%;color:#6b6357;opacity:.5}
.ctabox{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.ctamark{width:250px;height:250px;color:#efe4cf}
.ctamark svg{width:100%;height:100%}
.ctaname{font-weight:800;font-size:150px;letter-spacing:.2em;margin:26px 0 0 .2em}
.ctasub{font-size:56px;opacity:.8;margin-top:22px;font-weight:600}
.ctapill{margin-top:60px;font-size:58px;font-weight:900;background:#efe4cf;color:#151413;padding:18px 44px 24px;border-radius:999px}
#flash{position:absolute;inset:0;background:#fff;opacity:0;z-index:9;pointer-events:none}
</style></head><body><div id="cam">
__LAYERS__
<div id="cap"><div class="l1"></div><div class="l2"></div></div>
</div><div id="flash"></div>
<script>
const S = __DATA__;
const B = S.B, W = 1080, H = 1920, IW = 3840, IH = 2160;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const eo = x => 1 - Math.pow(1 - clamp(x), 3);
const back = x => { x = clamp(x); const c = 2.2; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const $ = id => document.getElementById(id);
function rnd(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function show(id, on) { $(id).style.display = on ? (id === 'hook' ? 'flex' : 'block') : 'none'; }
function placeShot(seg, t) {
  const el = $('shot' + seg.i), img = el.querySelector('img');
  const t0 = seg.b0 * B, t1 = seg.b1 * B, p = clamp((t - t0) / (t1 - t0));
  const e = seg.b1 - seg.b0 > 1 ? eo(p) : p;
  const rw = seg.rw0 + (seg.rw1 - seg.rw0) * e;
  const cx = seg.c0[0] + (seg.c1[0] - seg.c0[0]) * e, cy = seg.c0[1] + (seg.c1[1] - seg.c0[1]) * e;
  const local = t - t0;
  const punch = 1 + 0.16 * Math.exp(-local / 0.07);
  const s = (W / (rw * IW)) * punch;
  img.style.width = (IW * s) + 'px';
  const iw = IW * s, ih = IH * s;
  let left = W / 2 - cx * iw, top = H * 0.56 - cy * ih;
  if (iw >= W) left = Math.min(0, Math.max(W - iw, left));
  if (ih >= H) top = Math.min(0, Math.max(H - ih, top));
  img.style.left = left + 'px';
  img.style.top = top + 'px';
  img.style.filter = local < 0.1 ? `blur(${(1 - local / 0.1) * 10}px)` : 'none';
}
function caption(lines, start, t) {
  const cap = $('cap');
  if (!lines) { cap.style.display = 'none'; return; }
  cap.style.display = 'block';
  cap.querySelector('.l1').textContent = lines[0];
  cap.querySelector('.l2').textContent = lines[1];
  const k = clamp((t - start) / 0.14);
  cap.style.opacity = clamp(k * 1.6);
  cap.style.transform = `scale(${1.35 - 0.35 * back(k)})`;
}
window.render = (t) => {
  const beat = t / B;
  let capLines = null, capStart = 0;
  // hook
  const hook = beat < 4;
  show('hook', hook);
  if (hook) {
    document.querySelectorAll('#hook .w').forEach((w, i) => {
      const k = clamp((t - i * B) / 0.12);
      w.style.opacity = k > 0 ? 1 : 0;
      w.style.transform = `scale(${1.6 - 0.6 * back(k)})`;
    });
    const pulse = 1 + 0.05 * Math.exp(-((t % B) / 0.12));
    $('hookbg').style.transform = `scale(${1.1 * pulse})`;
  }
  // screens
  for (const seg of S.shots) {
    const on = beat >= seg.b0 && beat < seg.b1;
    show('shot' + seg.i, on);
    if (on) { placeShot(seg, t); capLines = seg.cap; capStart = seg.capAt * B; }
  }
  // chat
  const chat = beat >= S.chat.user && beat < 18;
  show('chat', chat);
  if (chat) {
    const u = clamp((t - S.chat.user * B) / 0.18), k = clamp((t - S.chat.kalki * B) / 0.18);
    $('ubub').style.opacity = u; $('ubub').style.transform = `translateY(${(1 - eo(u)) * 60}px) scale(${0.9 + 0.1 * back(u)})`;
    $('kcard').style.opacity = k; $('kcard').style.transform = `translateY(${(1 - eo(k)) * 60}px)`;
    const tp = clamp((t - S.chat.type_from * B) / ((S.chat.type_to - S.chat.type_from) * B));
    const chars = Array.from(S.reply);
    $('ktext').textContent = chars.slice(0, Math.round(tp * chars.length)).join('');
    $('caret').style.opacity = (tp < 1 && k > 0) || Math.floor(t * 3) % 2 ? 1 : 0;
    capLines = beat < S.chat.punch ? ['me, being rude', 'TO MY PC 🙄'] : ['it roasts you', 'BACK 💀'];
    capStart = (beat < S.chat.punch ? S.chat.user : S.chat.punch) * B;
    const zoom = beat >= S.chat.punch ? 1 + 0.025 * eo((t - S.chat.punch * B) / (2 * B)) : 1;
    $('chatin').style.transform = `scale(${zoom})`;
  }
  // CTA
  const cta = beat >= 28;
  show('cta', cta);
  if (cta) {
    const lt = t - S.cta;
    const m = clamp(lt / 0.16);
    $('ctamark').style.transform = `scale(${2.2 - 1.2 * back(m)})`; $('ctamark').style.opacity = m;
    const n = clamp((lt - 0.08) / 0.2); $('ctaname').style.opacity = n; $('ctaname').style.letterSpacing = (0.5 - 0.3 * eo(n)) + 'em';
    const sb = clamp((lt - B) / 0.18); $('ctasub').style.opacity = sb; $('ctasub').style.transform = `translateY(${(1 - eo(sb)) * 30}px)`;
    const pl = clamp((lt - 2 * B) / 0.16); $('ctapill').style.opacity = pl; $('ctapill').style.transform = `scale(${1.4 - 0.4 * back(pl)})`;
  }
  caption(capLines, capStart, t);
  // flash on the drop, the CTA and every rapid cut
  let f = 0;
  for (const h of S.flashes) if (t >= h[0]) f = Math.max(f, h[1] * Math.exp(-(t - h[0]) / 0.09));
  $('flash').style.opacity = f;
  // camera shake: strong on impacts, light on beats after the drop
  let sh = 0;
  for (const h of [S.drop, S.cta]) if (t >= h) sh = Math.max(sh, 26 * Math.exp(-(t - h) / 0.12));
  if (t >= S.drop && beat < 28) sh = Math.max(sh, 7 * Math.exp(-((t % B) / 0.08)));
  if (beat < 4) sh = Math.max(sh, 9 * Math.exp(-((t % B) / 0.08)));
  const fr = Math.round(t * 30);
  $('cam').style.transform = `translate(${(rnd(fr) - .5) * sh}px, ${(rnd(fr + 99) - .5) * sh}px)`;
};
</script></body></html>"""


def build_html():
    uri = lambda name: (SHOTS / f"{name}.png").as_uri()
    layers = [f'<div class="layer" id="hook"><div class="bgimg" id="hookbg" style="background-image:url({uri("04_voice_mode")})"></div>'
              f'<div class="vig"></div>' +
              "".join(f'<div class="w{" pov" if i == 0 else ""}{" last" if i == 3 else ""}">{w}</div>' for i, w in enumerate(HOOK_WORDS)) +
              '</div>']
    shots = []
    for i, (b0, b1, name, c0, c1, rw0, rw1, cap) in enumerate(SHOT_SEGS):
        layers.append(f'<div class="layer shot" id="shot{i}"><img src="{uri(name)}"><div class="shade"></div><div class="vig"></div></div>')
        cap_at = b0 if i == 0 or SHOT_SEGS[i - 1][7] != cap else SHOT_SEGS[i - 1][0]
        shots.append({"i": i, "b0": b0, "b1": b1, "c0": c0, "c1": c1, "rw0": rw0, "rw1": rw1, "cap": cap, "capAt": cap_at})
    layers.append(f'<div class="layer" id="chat"><div class="bgimg" style="background-image:url({uri("09_savage_roast")})"></div>'
                  f'<div class="vig"></div><div class="chatwrap" id="chatin">'
                  f'<div class="ubub" id="ubub"><div class="who">You</div>{ROAST_USER}</div>'
                  f'<div class="kcard" id="kcard"><div class="who">{MARK}KALKI</div><span id="ktext"></span><span class="caret" id="caret"></span></div>'
                  f'</div></div>')
    layers.append(f'<div class="layer" id="cta">{RIDGES}<div class="ctabox">'
                  f'<div class="ctamark" id="ctamark">{MARK}</div><div class="ctaname" id="ctaname">KALKI</div>'
                  f'<div class="ctasub" id="ctasub">Free AI assistant for Windows</div>'
                  f'<div class="ctapill" id="ctapill">Link in bio 🔗</div></div></div>')
    flashes = [[DROP, 0.95], [CTA, 0.9]] + [[b0 * B, 0.28] for b0, *_ in SHOT_SEGS[2:]] + [[CHAT["punch"] * B, 0.35]]
    data = {"B": B, "shots": shots, "chat": CHAT, "reply": ROAST_REPLY, "drop": DROP, "cta": CTA, "flashes": flashes}
    return PAGE.replace("__LAYERS__", "\n".join(layers)).replace("__DATA__", json.dumps(data, ensure_ascii=False))


# ── Audio: an original 120 BPM beat and sound effects, synthesised here ─────
SR = 44100
rng = random.Random(7)


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def kick(length=0.42, base=46, amp=1.0):
    out, ph = [], 0.0
    for i in range(int(length * SR)):
        t = i / SR
        ph += 2 * math.pi * (base + 80 * math.exp(-t * 32)) / SR
        click = rng.uniform(-1, 1) * 0.35 * math.exp(-t * 900)
        out.append(amp * (math.sin(ph) * math.exp(-t * 7.5) + click))
    return out


def bass808(freq, length=0.48, amp=0.75):
    out, ph = [], 0.0
    for i in range(int(length * SR)):
        t = i / SR
        f = freq * (1 + 0.5 * math.exp(-t * 40))
        ph += 2 * math.pi * f / SR
        s = math.tanh(2.2 * math.sin(ph)) / math.tanh(2.2)
        out.append(amp * s * math.exp(-t * 3.6) * min(1, t * 400))
    return out


def clap(amp=0.55):
    n, out, lp, prev = noise(int(0.28 * SR)), [], 0.0, 0.0
    for i, x in enumerate(n):
        t = i / SR
        env = sum(math.exp(-(t - d) * 220) for d in (0, 0.011, 0.022) if t >= d) + 0.5 * math.exp(-t * 16)
        hp = x - prev
        prev = x
        lp += 0.45 * (hp - lp)
        out.append(amp * lp * env)
    return out


def hat(amp=0.22, decay=70):
    n, out, prev = noise(int(0.07 * SR)), [], 0.0
    for i, x in enumerate(n):
        out.append(amp * (x - prev) * math.exp(-i / SR * decay))
        prev = x
    return out


def snare(amp=0.45):
    out = []
    for i, x in enumerate(noise(int(0.18 * SR))):
        t = i / SR
        out.append(amp * (0.7 * x * math.exp(-t * 22) + 0.5 * math.sin(2 * math.pi * 190 * t) * math.exp(-t * 30)))
    return out


def riser(length, amp=0.35):
    out, lp, ph = [], 0.0, 0.0
    n = int(length * SR)
    for i, x in enumerate(noise(n)):
        p = i / n
        lp += (0.02 + 0.5 * p * p) * (x - lp)
        ph += 2 * math.pi * (180 + 900 * p * p) / SR
        out.append(amp * p * p * (lp + 0.25 * math.sin(ph)))
    return out


def impact(amp=1.0):
    out, lp, ph = [], 0.0, 0.0
    k = kick(1.2, base=36, amp=1.0)
    for i, x in enumerate(noise(int(1.2 * SR))):
        t = i / SR
        lp += 0.08 * (x - lp)
        ph += 2 * math.pi * 38 / SR
        out.append(amp * (0.8 * k[i] + 1.4 * lp * math.exp(-t * 7) + 0.45 * math.sin(ph) * math.exp(-t * 2.4)))
    return out


def whoosh(length=0.32, amp=0.4):
    out, lp = [], 0.0
    n = int(length * SR)
    for i, x in enumerate(noise(n)):
        p = i / n
        env = math.sin(math.pi * p) ** 2
        lp += (0.03 + 0.35 * env) * (x - lp)
        out.append(amp * lp * env * 2.2)
    return out


def tick(amp=0.18):
    out, prev = [], 0.0
    for i, x in enumerate(noise(int(0.012 * SR))):
        out.append(amp * (x - prev) * math.exp(-i / SR * 500))
        prev = x
    return out


def pad(length, freqs, amp=0.05):
    out, lp = [], 0.0
    n = int(length * SR)
    for i in range(n):
        t = i / SR
        s = sum(math.sin(2 * math.pi * f * h * t) / h for f in freqs for h in (1, 2, 3))
        env = min(1, t / 0.25) * min(1, (n - i) / (0.2 * SR))
        lp += 0.2 * (s - lp)
        out.append(amp * lp * env)
    return out


def add(buf, sample, at, gain=1.0):
    start = int(at * SR)
    for i, x in enumerate(sample):
        j = start + i
        if 0 <= j < len(buf):
            buf[j] += x * gain


def make_audio():
    n = int(TOTAL * SR)
    music, sfx = [0.0] * n, [0.0] * n
    roots = [55.0, 43.65, 65.41, 49.0]          # A1, F1, C2, G1
    chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392], [196, 246.94, 293.66]]
    k, c, h, sn = kick(), clap(), hat(), snare()
    # intro: pad, ticking hats, a soft thump per hook word, riser into the drop
    add(music, pad(DROP, chords[0], 0.05), 0)
    for i in range(8):
        add(music, h, i * B / 2, 0.6)
    for i in range(4):
        add(sfx, kick(0.3, base=55, amp=0.55), i * B)
    add(sfx, riser(DROP - 0.1, 0.4), 0.1)
    # drop and the half-time groove (beats 4 to 18)
    add(sfx, impact(1.0), DROP)
    for bar in range(1, 5):
        t0 = bar * 4 * B
        add(music, pad(4 * B, chords[bar % 4], 0.035), t0)
        for b, g in ((0, 1.0), (1.5, 0.8)):
            add(music, k, t0 + b * B, g)
        add(music, c, t0 + 2 * B)
        for e in range(8):
            add(music, h, t0 + e * B / 2, 0.9 if e % 2 else 0.6)
        add(music, bass808(roots[bar % 4]), t0)
        add(music, bass808(roots[bar % 4] * 1.5, 0.3, 0.5), t0 + 1.5 * B)
    # typing and the roast punchline
    t = CHAT["type_from"] * B
    while t < CHAT["type_to"] * B:
        add(sfx, tick(rng.uniform(0.1, 0.22)), t)
        t += rng.uniform(0.045, 0.085)
    add(sfx, kick(0.5, base=40, amp=0.8), CHAT["punch"] * B)
    add(sfx, whoosh(0.3, 0.35), CHAT["user"] * B - 0.15)
    # rapid cuts: four on the floor, 16th hats, a whoosh on every cut (beats 18 to 26)
    for b in range(18, 26):
        t0 = b * B
        add(music, k, t0)
        if b % 2:
            add(music, c, t0)
        for e in range(4):
            add(music, h, t0 + e * B / 4, 0.8)
        add(music, bass808(roots[(b // 4) % 4], 0.45), t0)
        add(sfx, whoosh(0.22, 0.32), t0 - 0.11)
    # build: snare roll and riser (beats 26 to 28)
    for i in range(8):
        add(music, sn, 26 * B + i * B / 4, 0.35 + 0.08 * i)
    add(sfx, riser(2 * B, 0.45), 26 * B)
    # CTA impact and outro groove
    add(sfx, impact(1.0), CTA)
    add(music, pad(TOTAL - CTA, chords[0], 0.045), CTA)
    for b in (28, 29.5, 30):
        add(music, k, b * B, 0.9)
    add(music, c, 30 * B)
    add(music, bass808(roots[0], 0.9), CTA)
    for e in range(8):
        add(music, h, CTA + e * B / 2, 0.6)
    fade = int(0.12 * SR)
    for buf in (music, sfx):
        for i in range(fade):
            buf[n - 1 - i] *= i / fade
    return music, sfx


def write_wav(path, samples):
    peak = max(1e-9, max(abs(x) for x in samples))
    gain = 0.89 / peak
    data = array.array("h")
    for x in samples:
        v = int(max(-1.0, min(1.0, x * gain)) * 32767)
        data.append(v)
        data.append(v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def render_video(path):
    page = TMP / "reel.html"
    page.write_text(build_html(), encoding="utf-8")
    frames = int(TOTAL * FPS)
    ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                           "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-movflags", "+faststart", str(path)],
                          stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=["--allow-file-access-from-files"])
        pg = browser.new_context(viewport={"width": W, "height": H}).new_page()
        pg.goto(page.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        for i in range(frames):
            pg.evaluate(f"window.render({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
            if i % 120 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        pg.evaluate(f"window.render({1.9})")
        pg.screenshot(path=str(OUT / "kalki_reel_cover.png"))
        for t in [float(a) for a in sys.argv[1:]]:
            pg.evaluate(f"window.render({t})")
            pg.screenshot(path=str(TMP / f"check_{t:05.2f}.png"))
        browser.close()
    ff.stdin.close()
    ff.wait()


def mux(video, audio, out, lufs):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-c:v", "copy",
                    "-af", f"loudnorm=I={lufs}:TP=-1.0:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)], check=True)


def main():
    silent = OUT / "kalki_reel_silent.mp4"
    render_video(silent)
    print("video done", flush=True)
    music, sfx = make_audio()
    write_wav(TMP / "sfx.wav", sfx)
    write_wav(TMP / "beat.wav", [m * 0.85 + s for m, s in zip(music, sfx)])
    mux(silent, TMP / "beat.wav", OUT / "kalki_reel_beat.mp4", -14)
    mux(silent, TMP / "sfx.wav", OUT / "kalki_reel_sfx.mp4", -20)
    print("done", TMP, flush=True)


if __name__ == "__main__":
    main()
