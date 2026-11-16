"""KALKI phonk Reel: a 16-second, 150 BPM glitch edit with an original phonk track.

Everything is made here: the music (cowbell melody, distorted 808 with slides, hard drums,
a pitched-down "Hey KALKI" vocal, tape stop) and the visuals (typewriter intro, three drops,
RGB split, strobe, grain, half-beat cuts) from the real dark-theme screenshots.
Run from the repo root:  python tools/marketing/make_reel_phonk.py [check times in seconds...]
Writes marketing/video/reel_phonk/.
"""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import array
import asyncio
import json
import math
import pathlib
import random
import subprocess
import sys
import tempfile
import wave

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

SHOTS = REPO / "marketing" / "store" / "screenshots" / "dark" / "3840x2160"
OUT = REPO / "marketing" / "video" / "reel_phonk"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_phonk_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H = 30, 1080, 1920
BPM = 150
B = 60 / BPM                      # 0.4 s, exactly 12 frames
BEATS = 40
TOTAL = BEATS * B                 # 16 s
SR = 44100

# ── The edit ─────────────────────────────────────────────────────────────────
# (from beat, to beat, screenshot, centre x/y as fractions, region width, big word)
CUTS = [
    (8, 10, "04_voice_mode", (0.50, 0.30), 0.21, "IT TALKS"),
    (10, 12, "09_savage_roast", (0.49, 0.31), 0.335, "IT ROASTS 💀"),
    (12, 13, "03_today_briefing", (0.33, 0.24), 0.29, "PLANS"),
    (13, 14, "02_conversation", (0.93, 0.44), 0.18, "PLAYS"),
    (14, 15, "06_notes", (0.50, 0.46), 0.30, "REMEMBERS"),
    (15, 16, "07_security_checkup", (0.40, 0.20), 0.28, "GUARDS"),
    (16, 16.5, "03_today_briefing", (0.36, 0.57), 0.25, "CALENDAR"),
    (16.5, 17, "03_today_briefing", (0.61, 0.60), 0.25, "TASKS"),
    (17, 17.5, "02_conversation", (0.40, 0.42), 0.30, "ANSWERS"),
    (17.5, 18, "08_screen_time", (0.56, 0.52), 0.30, "FOCUS"),
    (18, 18.5, "05_onboarding", (0.57, 0.32), 0.33, "ANY AI"),
    (18.5, 19, "07_security_checkup", (0.88, 0.14), 0.20, "DEFENDER"),
    (19, 19.5, "04_voice_mode", (0.48, 0.80), 0.34, "VOICE"),
    (19.5, 20, "01_ask_home", (0.55, 0.62), 0.30, "ALL OF IT"),
    (20, 23.75, "01_ask_home", (0.52, 0.40), 0.30, None),      # zoom out, words per beat below
    (24, 25, "09_savage_roast", (0.71, 0.16), 0.22, "FREE."),
    (25, 26, "05_onboarding", (0.57, 0.40), 0.30, "OFFLINE MODE"),
    (26, 27, "07_security_checkup", (0.40, 0.30), 0.30, "OPEN SOURCE"),
    (27, 28, "04_voice_mode", (0.50, 0.30), 0.17, "NO CAP 🥶"),
    (28, 32, "04_voice_mode", (0.50, 0.30), 0.22, None),       # "JUST SAY HEY KALKI"
]
BEAT_WORDS = {20: "ALL.", 21: "IN.", 22: "ONE.", 23: "APP.", 28: "JUST", 29: "SAY", 30: "HEY", 31: "KALKI"}
TYPE_LINES = [(0.0, 2.6, "my PC used to be boring"), (3.6, 5.8, "until I installed this")]
DROPS = [8, 24, 32]
VOCAL_AT = [6.25, 30]             # beats

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000;color:#f5efe4}
#cam{position:absolute;inset:0;overflow:hidden;transform-origin:50% 50%}
.layer{position:absolute;inset:0;display:none;overflow:hidden;background:#000}
.grp{position:absolute;inset:0;isolation:isolate;filter:contrast(1.22) saturate(.55) brightness(.92)}
.grp img{position:absolute;max-width:none;mix-blend-mode:screen}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35) 0%,rgba(0,0,0,0) 30%,rgba(0,0,0,0) 48%,rgba(0,0,0,.82) 72%,rgba(0,0,0,.92) 100%)}
#word{position:absolute;left:40px;right:40px;top:1210px;text-align:center;z-index:6;display:none;
  font-family:Bahnschrift,"Segoe UI",sans-serif;font-stretch:75%;font-weight:700;text-transform:uppercase;
  font-size:190px;line-height:.92;letter-spacing:.01em;color:#f5efe4}
#type{position:absolute;left:90px;right:90px;top:820px;font-family:"Cascadia Mono",Consolas,monospace;font-size:62px;line-height:1.5;color:#efe4cf;z-index:6}
#type .cur{display:inline-block;width:.6em;height:1.05em;background:#efe4cf;vertical-align:-.15em;margin-left:6px}
#type .dim{opacity:.45}
#hk{position:absolute;left:0;right:0;top:1180px;text-align:center;font-family:Bahnschrift,sans-serif;font-stretch:75%;font-weight:700;font-size:120px;letter-spacing:.06em;z-index:6;opacity:0}
#intro{display:block}
#introbg{position:absolute;inset:-100px;background-size:cover;background-position:50% 30%;filter:blur(30px) grayscale(1) brightness(.35)}
#cta .box{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#cta .mk{width:300px;height:300px;color:#efe4cf}
#cta .mk svg{width:100%;height:100%}
#cta .nm{font-family:Bahnschrift,sans-serif;font-stretch:75%;font-weight:700;font-size:230px;letter-spacing:.14em;margin:10px 0 0 .14em;line-height:1}
#cta .sb{font-family:"Segoe UI",sans-serif;font-weight:600;font-size:52px;opacity:.8;margin-top:26px}
#cta .pl{margin-top:56px;font-family:Bahnschrift,sans-serif;font-stretch:75%;font-weight:700;font-size:76px;background:#efe4cf;color:#000;padding:10px 46px 16px;border-radius:999px;letter-spacing:.04em}
#grain{position:absolute;inset:-200px;z-index:8;opacity:.075;pointer-events:none;background-size:540px 960px;image-rendering:pixelated}
#scan{position:absolute;inset:0;z-index:8;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.22) 0 2px,rgba(0,0,0,0) 2px 5px)}
#vig{position:absolute;inset:0;z-index:7;pointer-events:none;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 50%,rgba(0,0,0,.7) 100%)}
#flash{position:absolute;inset:0;z-index:9;background:#fff;opacity:0;pointer-events:none}
#inv{position:absolute;inset:0;z-index:10;background:#fff;mix-blend-mode:difference;opacity:0;pointer-events:none}
#black{position:absolute;inset:0;z-index:11;background:#000;opacity:0;pointer-events:none}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs>
<filter id="fr"><feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>
<filter id="fg"><feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>
<filter id="fb"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
</defs></svg>
<div id="cam">__LAYERS__
<div id="word"></div><div id="hk">“HEY KALKI”</div>
</div>
<div id="vig"></div><div id="scan"></div><div id="grain"></div><div id="flash"></div><div id="inv"></div><div id="black"></div>
<script>
const S = __DATA__;
const B = S.B, W = 1080, H = 1920, IW = 3840, IH = 2160;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const eo = x => 1 - Math.pow(1 - clamp(x), 3);
const $ = id => document.getElementById(id);
function rnd(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
// grain texture, made once
(() => { const c = document.createElement('canvas'); c.width = 270; c.height = 480; const g = c.getContext('2d');
  const d = g.createImageData(270, 480); let s = 1;
  for (let i = 0; i < d.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = s % 256; d.data[i] = d.data[i+1] = d.data[i+2] = v; d.data[i+3] = 255; }
  g.putImageData(d, 0, 0); $('grain').style.backgroundImage = `url(${c.toDataURL()})`; })();
function spike(t, from, to, k = 0.07) { if (t < from * B || t >= to * B) return 0; return Math.exp(-((t % B) / k)); }
function place(cut, t) {
  const el = $('cut' + cut.i);
  const t0 = cut.b0 * B, t1 = cut.b1 * B, local = t - t0, p = clamp(local / (t1 - t0));
  let rw = cut.rw;
  if (cut.zoomOut) rw = cut.rw + (0.95 - cut.rw) * eo(p);
  else rw = cut.rw * (1 - 0.06 * p);                  // slow push in
  const punch = 1 + 0.28 * Math.exp(-local / 0.06);    // zoom punch on the cut
  const pulse = cut.pulse ? 1 + 0.07 * Math.exp(-(((t + 1e-6) % (B / 2)) / 0.06)) : 1;
  const s = (W / (rw * IW)) * punch * pulse;
  const iw = IW * s, ih = IH * s;
  let left = W / 2 - cut.c[0] * iw, top = H * 0.42 - cut.c[1] * ih;
  if (iw >= W) left = Math.min(0, Math.max(W - iw, left));
  if (ih >= H) top = Math.min(0, Math.max(H - ih, top));
  const split = 4 + 26 * Math.exp(-local / 0.07) + 14 * spike(t, 8, 32);
  const imgs = el.querySelectorAll('img');
  imgs.forEach((im, k) => {
    const dx = k === 0 ? split : k === 2 ? -split : 0;
    im.style.width = iw + 'px'; im.style.left = (left + dx) + 'px'; im.style.top = (top + (k === 1 ? 0 : dx * .25)) + 'px';
  });
  el.querySelector('.grp').style.filter = `contrast(1.22) saturate(.55) brightness(.92) blur(${Math.max(0, 8 * (1 - local / 0.08))}px)`;
}
function word(text, start, t) {
  const w = $('word');
  if (!text) { w.style.display = 'none'; return; }
  w.style.display = 'block'; w.textContent = text;
  const local = t - start, k = clamp(local / 0.08);
  const ab = 6 + 22 * Math.exp(-local / 0.08) + 10 * spike(t, 8, 32);
  w.style.transform = `scale(${1.5 - 0.5 * eo(k)}) skewX(${-8 * Math.exp(-local / 0.1)}deg)`;
  w.style.opacity = k > 0 ? 1 : 0;
  w.style.textShadow = `${ab}px 0 rgba(255,30,70,.85), ${-ab}px 0 rgba(20,220,255,.85), 0 10px 50px rgba(0,0,0,.9)`;
}
window.render = (t) => {
  const beat = t / B;
  // intro
  const intro = beat < 8;
  $('intro').style.display = intro ? 'block' : 'none';
  if (intro) {
    let html = '';
    for (const [a, b, line] of S.type) {
      if (beat < a) continue;
      const n = Math.round(clamp((beat - a) / (b - a)) * line.length);
      const done = beat >= b;
      html += `<div class="${beat >= S.type[S.type.length - 1][0] && line === S.type[0][2] ? 'dim' : ''}">&gt; ${line.slice(0, n)}${!done || (Math.floor(t * 3) % 2 && line === S.type[S.type.length - 1][2]) ? '<span class="cur"></span>' : ''}</div>`;
    }
    $('type').innerHTML = html;
    $('type').style.display = beat >= 7.5 ? 'none' : 'block';
    $('introbg').style.transform = `scale(${1.05 + 0.08 * beat / 8})`;
    $('introbg').style.opacity = beat >= 7.5 ? 0 : 0.5 + 0.5 * beat / 8;
    const hk = beat >= 6.25 && beat < 7.5;
    $('hk').style.opacity = hk ? 1 : 0;
    if (hk) { const l = t - 6.25 * B; $('hk').style.transform = `scale(${1.25 - 0.25 * eo(l / 0.1)})`;
      $('hk').style.textShadow = `${10 * Math.exp(-l / 0.1) + 4}px 0 rgba(255,30,70,.8), ${-(10 * Math.exp(-l / 0.1) + 4)}px 0 rgba(20,220,255,.8)`; }
  } else { $('hk').style.opacity = 0; }
  // cuts
  let wtext = null, wstart = 0;
  for (const cut of S.cuts) {
    const on = beat >= cut.b0 && beat < cut.b1;
    $('cut' + cut.i).style.display = on ? 'block' : 'none';
    if (on) { place(cut, t); if (cut.word) { wtext = cut.word; wstart = cut.b0 * B; } }
  }
  const bw = S.beatWords[Math.floor(beat)];
  if (bw && beat < 32 && !(beat >= 23.75 && beat < 24)) { wtext = bw; wstart = Math.floor(beat) * B; }
  if (beat >= 23.75 && beat < 24) wtext = null;
  word(wtext, wstart, t);
  // CTA
  const cta = beat >= 32;
  $('cta').style.display = cta ? 'block' : 'none';
  if (cta) {
    const l = t - 32 * B;
    const m = clamp(l / 0.12);
    const ab = 4 + 30 * Math.exp(-l / 0.1) + 8 * spike(t, 32, 37);
    $('ctamk').style.transform = `scale(${2.4 - 1.4 * eo(m)})`;
    $('ctamk').style.filter = `drop-shadow(${ab}px 0 rgba(255,30,70,.85)) drop-shadow(${-ab}px 0 rgba(20,220,255,.85))`;
    const n = clamp((l - 0.1) / 0.15); $('ctanm').style.opacity = n;
    $('ctanm').style.textShadow = `${ab}px 0 rgba(255,30,70,.8), ${-ab}px 0 rgba(20,220,255,.8)`;
    const sb = clamp((l - B) / 0.12); $('ctasb').style.opacity = sb;
    const pl = clamp((l - 2 * B) / 0.12); $('ctapl').style.opacity = pl; $('ctapl').style.transform = `scale(${1.4 - 0.4 * eo(pl)})`;
    const slow = clamp((beat - 37) / 2);              // tape stop: sink and fade
    $('ctabox').style.transform = `translateY(${slow * slow * 120}px) scale(${1 - 0.06 * slow})`;
    $('ctabox').style.filter = `brightness(${1 - 0.85 * slow * slow})`;
  }
  // flashes, invert, strobe
  let f = 0;
  for (const c of S.cuts) if (t >= c.b0 * B && c.b0 >= 8) f = Math.max(f, 0.22 * Math.exp(-(t - c.b0 * B) / 0.05));
  if (beat >= 24 && beat < 28) f = Math.max(f, (Math.floor(t * FPS_) % 6 < 1) ? 0.3 : 0);
  $('flash').style.opacity = f;
  let inv = 0;
  for (const d of S.drops) if (t >= d * B && t < d * B + 0.1) inv = 1;
  $('inv').style.opacity = inv;
  $('black').style.opacity = (beat >= 7.5 && beat < 8) ? 1 : (beat >= 23.75 && beat < 24) ? 1 : beat >= 39 ? clamp((beat - 39) / 0.6) : 0;
  // camera: kick bumps, drop shake
  let sh = 0, bump = 1;
  for (const d of S.drops) if (t >= d * B) sh = Math.max(sh, 34 * Math.exp(-(t - d * B) / 0.15));
  const sp = spike(t, 8, 37, 0.06);
  sh = Math.max(sh, 9 * sp); bump = 1 + 0.025 * sp;
  const fr = Math.round(t * 30);
  $('cam').style.transform = `translate(${(rnd(fr) - .5) * sh}px, ${(rnd(fr + 7) - .5) * sh}px) scale(${bump}) rotate(${(rnd(fr + 3) - .5) * sh * 0.04}deg)`;
  const g2 = Math.floor(fr / 2); $('grain').style.transform = `translate(${Math.floor(rnd(g2 + 1) * 200) - 100}px, ${Math.floor(rnd(g2 + 2) * 200) - 100}px)`;
};
const FPS_ = 30;
</script></body></html>"""


def build_html():
    uri = lambda name: (SHOTS / f"{name}.png").as_uri()
    layers = [f'<div class="layer" id="intro"><div id="introbg" style="background-image:url({uri("04_voice_mode")})"></div><div id="type"></div></div>']
    cuts = []
    for i, (b0, b1, name, c, rw, word) in enumerate(CUTS):
        imgs = "".join(f'<img src="{uri(name)}" style="filter:url(#{f})">' for f in ("fr", "fg", "fb"))
        layers.append(f'<div class="layer" id="cut{i}"><div class="grp">{imgs}</div><div class="shade"></div></div>')
        cuts.append({"i": i, "b0": b0, "b1": b1, "c": c, "rw": rw, "word": word,
                     "zoomOut": name == "01_ask_home" and word is None, "pulse": b0 in (8, 28)})
    layers.append(f'<div class="layer" id="cta"><div class="box" id="ctabox"><div class="mk" id="ctamk">{MARK}</div>'
                  f'<div class="nm" id="ctanm">KALKI</div><div class="sb" id="ctasb">free AI assistant for Windows</div>'
                  f'<div class="pl" id="ctapl">LINK IN BIO</div></div></div>')
    data = {"B": B, "cuts": cuts, "beatWords": BEAT_WORDS, "type": [[a, b, s] for a, b, s in TYPE_LINES], "drops": DROPS}
    return PAGE.replace("__LAYERS__", "\n".join(layers)).replace("__DATA__", json.dumps(data, ensure_ascii=False))


# ── Music: an original phonk track ──────────────────────────────────────────
rng = random.Random(150)
N = int(TOTAL * SR)
STEP = B / 4                                         # one 16th note


def hz(note):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    return 440 * 2 ** ((names[note[:-1]] + 12 * (int(note[-1]) + 1) - 69) / 12)


def cowbell(f, length=0.22):
    out, p1, p2, lp, slow = [], 0.0, 0.0, 0.0, 0.0
    for i in range(int(length * SR)):
        t = i / SR
        p1 = (p1 + f / SR) % 1
        p2 = (p2 + f * 1.4836 / SR) % 1
        x = (1 if p1 < .5 else -1) + 0.7 * (1 if p2 < .5 else -1)
        lp += 0.35 * (x - lp)
        slow += 0.02 * (lp - slow)
        out.append((lp - slow) * min(1, t * 900) * (0.65 * math.exp(-t * 9) + 0.35 * math.exp(-t * 30)))
    return out


def bass(f_from, f_to, length):
    out, ph = [], 0.0
    for i in range(int(length * SR)):
        t = i / SR
        f = f_to + (f_from - f_to) * math.exp(-t / 0.045)
        ph += 2 * math.pi * f / SR
        x = math.sin(ph) + 0.25 * math.sin(2 * ph)
        env = min(1, t * 300) * math.exp(-t * 1.6)
        out.append(math.tanh(5.0 * x * env) * 0.9)
    return out


def kick(amp=1.0):
    out, ph = [], 0.0
    for i in range(int(0.38 * SR)):
        t = i / SR
        ph += 2 * math.pi * (50 + 160 * math.exp(-t * 38)) / SR
        out.append(amp * math.tanh(2.6 * (math.sin(ph) * math.exp(-t * 9) + rng.uniform(-1, 1) * 0.4 * math.exp(-t * 700))))
    return out


def clap(amp=0.75):
    out, lp, prev = [], 0.0, 0.0
    for i in range(int(0.3 * SR)):
        t = i / SR
        x = rng.uniform(-1, 1)
        hp = x - prev
        prev = x
        lp += 0.5 * (hp - lp)
        env = sum(math.exp(-(t - d) * 260) for d in (0, .009, .018, .027) if t >= d) * .8 + 0.55 * math.exp(-t * 13)
        out.append(amp * lp * env)
    return out


def hat(amp=0.25, decay=85):
    out, prev = [], 0.0
    for i in range(int(0.06 * SR)):
        x = rng.uniform(-1, 1)
        out.append(amp * (x - prev) * math.exp(-i / SR * decay))
        prev = x
    return out


def snare(amp=0.5):
    return [amp * (0.75 * rng.uniform(-1, 1) * math.exp(-i / SR * 24) + 0.5 * math.sin(2 * math.pi * 200 * i / SR) * math.exp(-i / SR * 30))
            for i in range(int(0.16 * SR))]


def riser(length, amp=0.4):
    out, lp = [], 0.0
    n = int(length * SR)
    for i in range(n):
        p = i / n
        lp += (0.02 + 0.6 * p ** 2) * (rng.uniform(-1, 1) - lp)
        out.append(amp * p ** 2.2 * lp)
    return out


def impact():
    out, lp, ph = [], 0.0, 0.0
    for i in range(int(1.4 * SR)):
        t = i / SR
        lp += 0.06 * (rng.uniform(-1, 1) - lp)
        ph += 2 * math.pi * (32 + 90 * math.exp(-t * 20)) / SR
        out.append(math.tanh(1.6 * (math.sin(ph) * math.exp(-t * 2.6) + 1.6 * lp * math.exp(-t * 5))))
    return out


def add(buf, sample, at, gain=1.0):
    s = int(at * SR)
    for i, x in enumerate(sample):
        j = s + i
        if 0 <= j < N:
            buf[j] += x * gain


def comb_reverb(x, mix=0.3):
    out = [0.0] * len(x)
    for d, fb in ((1557, .78), (1617, .77), (1491, .79), (1422, .8), (1277, .76)):
        buf = [0.0] * len(x)
        for i in range(len(x)):
            y = x[i] + (fb * buf[i - d] if i >= d else 0)
            buf[i] = y
            out[i] += y * mix / 5
    return out


def vocal():
    """KALKI's own voice saying "Hey KALKI", pitched down and slowed like a phonk vocal."""
    try:
        import edge_tts
        mp3 = TMP / "hey.mp3"
        asyncio.run(edge_tts.Communicate("Hey, KALKI.", "en-US-AndrewMultilingualNeural", rate="-10%").save(str(mp3)))
        wav = TMP / "hey.wav"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp3), "-af",
                        "aresample=44100,asetrate=44100*0.74,aresample=44100,highpass=f=90,lowpass=f=4200,"
                        "aecho=0.8:0.55:110|230:0.35|0.2,volume=2.2", "-ac", "1", "-ar", "44100", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            raw = array.array("h", w.readframes(w.getnframes()))
        return [v / 32768 for v in raw]
    except Exception as e:                    # no internet: the track still works without it
        print("vocal skipped:", e, flush=True)
        return []


# 2-bar phrase in C# minor, 16ths (None = rest)
MELODY = ["C#5", None, "C#5", None, "E5", None, "C#5", "G#4", None, "C#5", None, "E5", "F#5", None, "E5", None,
          "C#5", None, "C#5", None, "E5", None, "C#5", "G#4", None, "B4", None, "A4", "G#4", None, "E4", None]
BASS = [(0, "C#2", 6), (6, "C#2", 4), (10, "E2", 6), (16, "C#2", 6), (22, "B1", 4), (26, "A1", 6)]   # step, note, length in 16ths
KICKS = [0, 6, 10, 16, 22, 26]
CLAPS = [4, 12, 20, 28]


def make_music():
    drums, mel, low, fx, claps = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
    k, c, h, sn = kick(), clap(), hat(), snare()
    bells = {n: cowbell(hz(n)) for n in set(m for m in MELODY if m)}
    sidechain = [1.0] * N

    def phrase(bar0, intro=False, hard=False):
        t0 = bar0 * 4 * B
        for i, n in enumerate(MELODY):
            if n:
                add(mel, bells[n], t0 + i * STEP, 0.55 if not intro else 0.42)
                if hard:
                    add(mel, cowbell(hz(n) * 2), t0 + i * STEP, 0.16)
        if intro:
            return
        prev = None
        for step, n, ln in BASS:
            f = hz(n)
            add(low, bass(prev or f, f, ln * STEP + 0.05), t0 + step * STEP)
            prev = f
        for s in KICKS:
            add(drums, k, t0 + s * STEP)
            a = int((t0 + s * STEP) * SR)
            for j in range(int(0.16 * SR)):
                if a + j < N:
                    sidechain[a + j] = min(sidechain[a + j], 1 - 0.55 * math.exp(-j / SR / 0.07))
        for s in CLAPS:
            add(claps, c, t0 + s * STEP)
        for s in range(0, 32, 2):
            add(drums, h, t0 + s * STEP, 0.8 if s % 4 else 0.55)
        for s in (14, 30):                    # 32nd-note hat rolls at the end of each bar
            for r in range(4):
                add(drums, hat(0.2 + 0.05 * r), t0 + s * STEP + r * STEP / 2)
        if hard:
            for s in range(1, 32, 2):
                add(drums, h, t0 + s * STEP, 0.45)

    # intro (beats 0-8): the melody alone, filtered open as it builds
    phrase(0, intro=True)
    add(fx, riser(7.5 * B, 0.35), 0)
    add(drums, kick(0.6), 0)
    add(drums, kick(0.6), 4 * B)
    # drop 1 (beats 8-24)
    add(fx, impact(), 8 * B, 0.9)
    phrase(2)
    phrase(4)
    # beat 23: snare roll up into a gap at 23.75
    for r in range(6):
        add(drums, sn, 23 * B + r * B / 8, 0.3 + 0.1 * r)
    # drop 2 (beats 24-32): harder, octave bells and extra hats
    add(fx, impact(), 24 * B, 0.9)
    phrase(6, hard=True)
    # outro (beats 32-40): impact, one more phrase, then a tape stop
    add(fx, impact(), 32 * B, 1.0)
    phrase(8)

    # filter sweep on the intro melody
    lp, out_mel = 0.0, mel[:]
    for i in range(int(8 * B * SR)):
        a = 0.04 + 0.5 * (i / (8 * B * SR)) ** 2
        lp += a * (mel[i] - lp)
        out_mel[i] = lp
    mel = out_mel
    # melody echo (dotted 8th), left and right offset for width
    d1, d2 = int(3 * STEP * SR), int(4 * STEP * SR)
    left, right = [0.0] * N, [0.0] * N
    wet = comb_reverb(claps, 0.28)
    voc = vocal()
    for i in range(N):
        sc = sidechain[i]
        m = mel[i] * sc
        el = 0.38 * mel[i - d1] * sc if i >= d1 else 0
        er = 0.38 * mel[i - d2] * sc if i >= d2 else 0
        base = drums[i] + 0.95 * low[i] * sc + claps[i] + wet[i] + fx[i]
        left[i] = base + m + el
        right[i] = base + m + er
    for at in VOCAL_AT:
        s = int(at * B * SR)
        for j, v in enumerate(voc):
            if s + j < N:
                left[s + j] += v * 0.9
                right[s + j] += v * 0.9
    # gaps: silence at 7.5-8 and 23.75-24 (the vocal tail rings through the first one)
    for a, b, keep_voc in ((7.5, 8, True), (23.75, 24, False)):
        for i in range(int(a * B * SR), int(b * B * SR)):
            vl = 0.0
            if keep_voc:
                j = i - int(VOCAL_AT[0] * B * SR)
                vl = voc[j] * 0.9 if 0 <= j < len(voc) else 0.0
            left[i] = right[i] = vl
    # tape stop from beat 37 to 39, silence after
    for ch in (left, right):
        s0, s1 = int(37 * B * SR), int(39 * B * SR)
        src, pos = ch[s0:], 0.0
        for i in range(s1 - s0):
            j = int(pos)
            fr = pos - j
            ch[s0 + i] = (src[j] * (1 - fr) + src[j + 1] * fr) if j + 1 < len(src) else 0.0
            pos += (1 - i / (s1 - s0)) ** 1.5
        for i in range(s1, N):
            ch[i] = 0.0
    # master: soft clip
    for ch in (left, right):
        peak = max(1e-9, max(abs(x) for x in ch))
        for i in range(N):
            ch[i] = math.tanh(1.6 * ch[i] / peak) / math.tanh(1.6)
    return left, right


def write_wav(path, left, right):
    data = array.array("h")
    for l, r in zip(left, right):
        data.append(int(max(-1, min(1, l * 0.95)) * 32767))
        data.append(int(max(-1, min(1, r * 0.95)) * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def render_video(path, checks):
    page = TMP / "reel.html"
    page.write_text(build_html(), encoding="utf-8")
    frames = int(TOTAL * FPS)
    ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                           "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "14M", "-bufsize", "28M", "-movflags", "+faststart", str(path)],
                          stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=["--allow-file-access-from-files"])
        pg = browser.new_context(viewport={"width": W, "height": H}).new_page()
        pg.goto(page.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        for i in range(frames):
            pg.evaluate(f"window.render({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=94))
            if i % 120 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        pg.evaluate(f"window.render({10.4 * B})")
        pg.screenshot(path=str(OUT / "kalki_reel_phonk_cover.png"))
        for t in checks:
            pg.evaluate(f"window.render({t})")
            pg.screenshot(path=str(TMP / f"check_{t:05.2f}.png"))
        browser.close()
    ff.stdin.close()
    ff.wait()


def main():
    checks = [float(a) for a in sys.argv[1:]]
    silent = OUT / "kalki_reel_phonk_silent.mp4"
    render_video(silent, checks)
    print("video done", flush=True)
    left, right = make_music()
    write_wav(TMP / "phonk.wav", left, right)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(TMP / "phonk.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-12:TP=-1.0:LRA=9", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / "kalki_reel_phonk.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(TMP / "phonk.wav"), "-af", "loudnorm=I=-12:TP=-1.0:LRA=9",
                    "-ar", "48000", str(OUT / "kalki_phonk_track.wav")], check=True)
    print("done", TMP, flush=True)


if __name__ == "__main__":
    main()
