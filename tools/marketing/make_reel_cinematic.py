"""KALKI cinematic Reel: a 21-second, one-take 3D fly-through with trailer-style music.

KALKI's orb and interface float in a 3D world. The camera pushes in, orbits, flies through the
light and past the floating UI, lands on the real app, pulls back and ends on the logo. Depth of
field, god rays, lens flares, dust and bokeh, letterboxing, a colour grade and real motion blur
(three sub-frames per frame) give it a film look. The music is an original trailer-style score.
Run from the repo root:  python tools/marketing/make_reel_cinematic.py [check times...] [--checks-only]
Writes marketing/video/reel_cinematic/.
"""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import array
import io
import json
import math
import pathlib
import random
import subprocess
import sys
import tempfile
import wave

import imageio_ffmpeg
from PIL import Image
from playwright.sync_api import sync_playwright

SHOT = REPO / "marketing" / "store" / "screenshots" / "dark" / "3840x2160" / "03_today_briefing.png"
OUT = REPO / "marketing" / "video" / "reel_cinematic"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_cine_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H = 30, 1080, 1920
TOTAL = 21.0
SUB = 3                      # motion-blur sub-frames per frame
SR = 44100

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
WINCAPS = ('<span><svg viewBox="0 0 10 10"><path d="M0 5h10" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9" rx="1.2" fill="none" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><path d="M.5 .5l9 9M9.5 .5l-9 9" stroke="currentColor" stroke-width=".9"/></svg></span>')
SHIELD = '<svg viewBox="0 0 24 24" fill="none" stroke="#8fd19e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="width:56px;height:56px"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>'

CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#050505;color:#f5efe4;font-family:"Segoe UI Variable Text","Segoe UI",sans-serif}
#sky{position:absolute;inset:0;width:100%;height:100%}
#vp{position:absolute;inset:0;perspective:1400px;perspective-origin:50% 50%;overflow:hidden}
#world{position:absolute;left:50%;top:50%;width:0;height:0;transform-style:preserve-3d}
.o{position:absolute;left:0;top:0;will-change:transform,filter,opacity}
#fx{position:absolute;inset:0;mix-blend-mode:screen}
.orb{width:420px;height:420px;margin:-210px 0 0 -210px;border-radius:50%;
  background:radial-gradient(circle at 40% 34%,#fffdf7 0%,#f6ead4 34%,#d8c3a0 70%,#9c8565 100%);
  box-shadow:0 0 160px 50px rgba(255,226,180,.35),0 0 420px 120px rgba(255,190,120,.18),inset -30px -40px 90px rgba(110,80,40,.45)}
.card{width:760px;margin-left:-380px;margin-top:-150px;border-radius:40px;padding:36px 44px;
  background:linear-gradient(160deg,rgba(44,40,36,.92),rgba(20,19,17,.94));border:1.5px solid rgba(255,235,205,.16);
  box-shadow:0 60px 120px -40px rgba(0,0,0,.95),inset 0 1px 0 rgba(255,240,220,.12);color:#ece6dc}
.lbl{font-size:24px;font-weight:700;letter-spacing:.22em;color:#a59b8c;text-transform:uppercase;margin-bottom:14px}
.row{display:flex;align-items:center;gap:20px;font-size:38px;margin:10px 0}
.time{font-family:"Cascadia Mono",Consolas,monospace;font-size:28px;padding:6px 14px;border-radius:12px;background:#2f2c28}
.bub{width:auto;max-width:720px;border-radius:40px;padding:26px 38px;font-size:44px;line-height:1.35}
.ub{background:rgba(52,48,44,.95);border:1.5px solid rgba(255,235,205,.18);font-weight:600;margin-left:-330px;margin-top:-60px;border-bottom-right-radius:12px}
.kb{width:760px;background:rgba(24,23,21,.95);border:1.5px solid rgba(255,235,205,.16);margin-left:-380px;margin-top:-120px;border-bottom-left-radius:12px}
.who{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:700;letter-spacing:.14em;color:#efe4cf;margin-bottom:10px}
.who svg{width:34px;height:34px}
.win{width:900px;margin-left:-450px;margin-top:-270px}
.win .frame{border-radius:14px;overflow:hidden;border:1.5px solid rgba(255,235,205,.18);background:#1b1a18;box-shadow:0 80px 160px -50px rgba(0,0,0,1),0 0 120px rgba(255,210,160,.08)}
.win .bar{height:44px;display:flex;align-items:center;background:#23211e;border-bottom:1px solid #34312c;font-size:17px;color:#e6dfd3;padding-left:16px}
.win .bar .ttl{display:flex;align-items:center;gap:10px;flex:1}
.win .bar .ttl svg{width:20px;height:20px}
.win .bar .cap{display:flex;height:100%}
.win .bar .cap span{width:62px;display:flex;align-items:center;justify-content:center}
.win .bar .cap svg{width:13px;height:13px}
.win img{display:block;width:100%}
.win .refl{margin-top:14px;height:300px;overflow:hidden;opacity:.22;transform:scaleY(-1);
  -webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.9),transparent 70%);filter:blur(3px)}
.win .refl img{display:block;width:100%}
.sweep{position:absolute;inset:0;background:linear-gradient(105deg,transparent 38%,rgba(255,245,230,.22) 50%,transparent 62%);transform:translateX(-130%)}
.t2d{position:absolute;left:60px;right:60px;text-align:center;font-family:"Sitka Display","Sitka Heading","Palatino Linotype",Georgia,serif;
  font-weight:400;color:#f7f1e6;text-shadow:0 0 40px rgba(255,220,170,.35),0 4px 30px rgba(0,0,0,.8);opacity:0}
.cap{font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;font-size:28px;letter-spacing:.42em;text-transform:uppercase;color:#cfc3b0;text-shadow:0 2px 20px rgba(0,0,0,.9)}
#roast{position:absolute;inset:0;background:#000;opacity:0}
#rub,#rkb{position:absolute;opacity:0}
#rub{right:80px;top:720px}
#rkb{left:70px;top:900px;width:900px}
#skull{position:absolute;left:800px;top:1260px;font-size:170px;opacity:0}
#logo{position:absolute;left:0;right:0;top:640px;text-align:center;opacity:0}
#logo .mk{width:300px;height:300px;margin:0 auto;color:#f3e7d1;filter:drop-shadow(0 0 30px rgba(255,210,150,.6))}
#logo .mk svg{width:100%;height:100%}
#logo .mk path{stroke-dasharray:40;stroke-dashoffset:40}
#logo .nm{font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;font-weight:600;font-size:150px;letter-spacing:.2em;margin:40px 0 0 .2em;
  background:linear-gradient(100deg,#cdb994 0%,#fff8ea 45%,#fff 50%,#fff8ea 55%,#cdb994 100%);background-size:300% 100%;-webkit-background-clip:text;background-clip:text;color:transparent}
#logo .sb{font-size:44px;color:#c9bda9;margin-top:24px}
#logo .pl{display:inline-block;margin-top:60px;font-size:44px;font-weight:700;background:#efe4cf;color:#151413;padding:16px 48px 20px;border-radius:999px}
#grade{position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;opacity:.55;
  background:linear-gradient(180deg,rgba(40,90,110,.9) 0%,rgba(0,0,0,0) 45%,rgba(255,170,90,.7) 100%)}
#vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 45%,rgba(0,0,0,.78) 100%)}
#grain{position:absolute;inset:-160px;pointer-events:none;opacity:.07;background-size:540px 960px}
#flash{position:absolute;inset:0;background:#fff6e6;opacity:0;pointer-events:none}
.lb{position:absolute;left:0;right:0;background:#000;height:0}
#lbt{top:0}#lbb{bottom:0}
"""


def html():
    shot = SHOT.as_uri()
    cards = [
        ("c1", '<div class="lbl">Weather · Bengaluru</div><div class="row" style="font-size:84px;font-weight:300">☀️ 27°<span style="font-size:32px;color:#a59b8c;margin-left:14px">Sunny · H 30° L 21°</span></div>'),
        ("c2", '<div class="lbl">Today</div><div class="row"><span class="time">10:00</span>Team standup</div><div class="row"><span class="time">14:00</span>Design review</div><div class="row"><span class="time">18:30</span>Gym with Kabir</div>'),
        ("c3", '<div class="lbl">Now playing</div><div class="row" style="gap:28px"><div style="width:130px;height:130px;border-radius:20px;background:linear-gradient(135deg,#3b2f5c,#b5566b 55%,#e8a265)"></div><div><div style="font-size:42px;font-weight:600">Midnight Drive</div><div style="font-size:30px;color:#a59b8c">Lo-fi Lounge · Apple Music</div></div></div>'),
        ("c4", '<div class="lbl">Tasks · 4 open</div><div class="row">◉ Finish the quarterly report</div><div class="row" style="color:#a59b8c">○ Book flights to Bengaluru</div><div class="row" style="color:#a59b8c">○ Renew car insurance</div>'),
        ("c5", f'<div class="lbl">Security</div><div class="row">{SHIELD}<div><div style="font-size:42px;font-weight:600">Windows Defender is on</div><div style="font-size:30px;color:#a59b8c">Nothing to review</div></div></div>'),
        ("c6", '<div class="lbl">Reminder</div><div class="row">💧 Stretch and drink water</div><div class="row" style="font-size:30px;color:#a59b8c">every day · 5:00 PM</div>'),
    ]
    world = ['<div class="o orb" id="orb"></div>',
             '<div class="o bub ub" id="ub">Hey KALKI, what\'s on today?</div>',
             f'<div class="o bub kb" id="kb"><div class="who">{MARK}KALKI</div><span id="kt"></span></div>']
    world += [f'<div class="o card" id="{i}">{c}</div>' for i, c in cards]
    world.append(f'<div class="o win" id="win"><div class="frame" style="position:relative"><div class="bar"><div class="ttl">{MARK}<span>KALKI</span></div><div class="cap">{WINCAPS}</div></div>'
                 f'<img src="{shot}"><div class="sweep" id="sweep"></div></div><div class="refl"><img src="{shot}"></div></div>')
    body = f"""
<canvas id="sky" width="540" height="960"></canvas>
<div id="vp"><div id="world">{''.join(world)}</div></div>
<canvas id="fx" width="1080" height="1920"></canvas>
<div class="t2d" id="tA" style="top:1110px;font-size:70px">For years, your PC<br>just listened.</div>
<div class="t2d" id="tB" style="top:1150px;font-size:100px">Now, it <i>answers.</i></div>
<div class="t2d" id="tC" style="top:230px"><div class="cap">Voice mode</div><div style="font-size:104px;margin-top:10px">Just talk.</div></div>
<div class="t2d" id="tD" style="top:250px;font-size:120px"></div>
<div class="t2d" id="tE" style="top:240px"><div class="cap">Not a mockup</div><div style="font-size:112px;margin-top:10px">This is <i>KALKI.</i></div></div>
<div class="t2d" id="tF" style="top:1380px"><div class="cap" style="letter-spacing:.3em">Real app · real Windows</div></div>
<div id="roast"></div>
<div class="bub ub" id="rub" style="margin:0">bro you're kinda useless ngl</div>
<div class="bub kb" id="rkb" style="margin:0"><div class="who">{MARK}KALKI <span style="font-size:20px;background:#efe4cf;color:#151413;padding:4px 12px;border-radius:999px;letter-spacing:.08em">SAVAGE</span></div>Useless? I've reminded you to drink water three times today and you're still dehydrated. 💀</div>
<div id="skull">💀</div>
<div class="t2d" id="tG" style="top:700px;font-size:100px;line-height:1.25"></div>
<div id="logo"><div class="mk" id="lmk">{MARK}</div><div class="nm" id="lnm">KALKI</div><div class="sb" id="lsb">Your AI assistant for Windows</div><div class="pl" id="lpl">Free · link in bio</div></div>
<div id="grade"></div><div id="vig"></div><div id="grain"></div><div id="flash"></div>
<div class="lb" id="lbt"></div><div class="lb" id="lbb"></div>
"""
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>'


JS = r"""
const $ = id => document.getElementById(id);
const W = 1080, H = 1920, P = 1400;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, x) => a + (b - a) * x;
const P_ = (t, a, d) => clamp((t - a) / d);
const ioC = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const oE = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
const iQ = x => x * x;
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

// world objects (x, y, z) · the camera looks toward -z
const OBJ = {orb: [0, 0, 0], ub: [-200, 330, 500], kb: [170, 560, -60],
  c1: [-160, -240, -700], c2: [160, 260, -1400], c3: [-160, -220, -2100], c4: [160, 270, -2800], c5: [-160, -240, -3500], c6: [160, 250, -4200],
  win: [0, -40, -5750]};
// dust and bokeh
const DUST = Array.from({length: 520}, () => [lerp(-1800, 1800, rnd()), lerp(-2600, 2600, rnd()), lerp(-7500, 5200, rnd()), rnd()]);

function camera(t) {
  let z, x = 0, y = 0, ry = 0;
  if (t < 3) { z = lerp(4300, 2600, ioC(t / 3)); }
  else if (t < 6) { const p = (t - 3) / 3; z = lerp(2600, 950, iQ(p) * 0.6 + p * 0.4); ry = lerp(-0.22, 0.12, ioC(p)); x = lerp(-120, 40, ioC(p)); y = lerp(80, 20, p); }
  else if (t < 9.6) { z = 950 - 1400 * (t - 6); ry = lerp(0.12, 0, P_(t, 6, 0.8)); x = lerp(40, 0, P_(t, 6, 1)); }
  else if (t < 10.4) { const p = (t - 9.6) / 0.8; z = lerp(-4090, -4320, 1 - Math.pow(1 - p, 2)); }
  else if (t < 15) { z = lerp(-4320, -4420, (t - 10.4) / 4.6); }
  else if (t < 17.6) { const p = ioC((t - 15) / 2.6); z = lerp(-4420, 3900, p); y = lerp(0, -380, p); ry = lerp(0, 0.1, p); }
  else { z = 3900; y = -380; ry = 0.1; }
  return {x, y, z, ry};
}
function view(c, X, Y, Z) {
  const dx = X - c.x, dy = Y - c.y, dz = c.z - Z;
  const cs = Math.cos(c.ry), sn = Math.sin(c.ry);
  return {vx: dx * cs - dz * sn, vy: dy, vz: dz * cs + dx * sn};
}
function proj(v) { const s = P / v.vz; return {x: W / 2 + v.vx * s, y: H / 2 + v.vy * s, s}; }

function focusAt(t, c) {
  const vz = id => view(c, ...OBJ[id]).vz;
  if (t < 3.35) return vz('orb');
  if (t < 3.95) return vz('ub');
  if (t < 6) return vz('kb');
  if (t < 9.8) return 1100;
  if (t < 15) return vz('win');
  return 3000;
}
function suck(t) { return ioC(P_(t, 17.5, 1.0)); }

// grain texture
(() => { const c = document.createElement('canvas'); c.width = 270; c.height = 480; const g = c.getContext('2d');
  const d = g.createImageData(270, 480); let s = 3;
  for (let i = 0; i < d.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = s % 256; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  g.putImageData(d, 0, 0); $('grain').style.backgroundImage = `url(${c.toDataURL()})`; })();

function sky(t) {
  const g = $('sky').getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 960);
  gr.addColorStop(0, '#07090b'); gr.addColorStop(0.55, '#0b0a09'); gr.addColorStop(1, '#120d09');
  g.fillStyle = gr; g.fillRect(0, 0, 540, 960);
  const neb = g.createRadialGradient(270 + 60 * Math.sin(t * .2), 420, 10, 270, 420, 520);
  neb.addColorStop(0, 'rgba(120,90,60,.16)'); neb.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = neb; g.fillRect(0, 0, 540, 960);
}

function rays(g, x, y, r, a, t) {
  if (a <= 0.003) return;
  g.save(); g.translate(x, y); g.globalCompositeOperation = 'lighter';
  const n = 16;
  for (let i = 0; i < n; i++) {
    const ang = i / n * Math.PI * 2 + t * 0.12 + Math.sin(i * 7.3) * 0.2;
    const w = 0.05 + 0.04 * Math.sin(i * 3.1 + t);
    const len = r * (0.7 + 0.5 * Math.abs(Math.sin(i * 1.7)));
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, len);
    gr.addColorStop(0, `rgba(255,225,180,${0.22 * a})`); gr.addColorStop(1, 'rgba(255,200,140,0)');
    g.fillStyle = gr; g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, len, ang - w, ang + w); g.closePath(); g.fill();
  }
  const glow = g.createRadialGradient(0, 0, 0, 0, 0, r * 0.9);
  glow.addColorStop(0, `rgba(255,240,215,${0.55 * a})`); glow.addColorStop(0.25, `rgba(255,205,150,${0.22 * a})`); glow.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = glow; g.beginPath(); g.arc(0, 0, r * 0.9, 0, Math.PI * 2); g.fill();
  g.restore();
}
function flare(g, x, y, a) {
  if (a <= 0.003) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  const st = g.createLinearGradient(x - 900, 0, x + 900, 0);
  st.addColorStop(0, 'rgba(120,180,255,0)'); st.addColorStop(0.5, `rgba(200,225,255,${0.75 * a})`); st.addColorStop(1, 'rgba(120,180,255,0)');
  g.fillStyle = st; g.beginPath(); g.ellipse(x, y, 900, 9 + 10 * a, 0, 0, Math.PI * 2); g.fill();
  const core = g.createRadialGradient(x, y, 0, x, y, 260 * a + 40);
  core.addColorStop(0, `rgba(255,250,240,${a})`); core.addColorStop(1, 'rgba(255,220,180,0)');
  g.fillStyle = core; g.beginPath(); g.arc(x, y, 260 * a + 40, 0, Math.PI * 2); g.fill();
  for (const [k, r, al] of [[0.45, 70, .14], [0.8, 34, .2], [1.35, 120, .08], [1.7, 26, .18]]) {
    const gx = x + (W / 2 - x) * 2 * k, gy = y + (H / 2 - y) * 2 * k;
    const gg = g.createRadialGradient(gx, gy, 0, gx, gy, r);
    gg.addColorStop(0, `rgba(170,210,255,${al * a})`); gg.addColorStop(0.7, `rgba(255,200,150,${al * a * .6})`); gg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gg; g.beginPath(); g.arc(gx, gy, r, 0, Math.PI * 2); g.fill();
  }
  g.restore();
}

window.render = (t) => {
  sky(t);
  const c = camera(t);
  const focus = focusAt(t, c);
  const sk = suck(t);
  // world objects
  for (const [id, pos] of Object.entries(OBJ)) {
    const el = $(id);
    let [X, Y, Z] = pos;
    if (id !== 'orb' && sk > 0) { X *= 1 - sk; Y *= 1 - sk; Z *= 1 - sk; }
    const v = view(c, X, Y, Z);
    let op = clamp((v.vz - 120) / 380) * clamp((14000 - v.vz) / 3000);
    if (id === 'ub') op *= P_(t, 3.3, 0.35);
    if (id === 'kb') op *= P_(t, 3.9, 0.35);
    if (id[0] === 'c') op *= P_(t, 5.4, 0.6);
    if (id === 'win') op *= P_(t, 8.6, 0.6);
    if (sk > 0 && id !== 'orb') op *= 1 - clamp((sk - 0.6) / 0.4);
    if (t >= 18.5 && id === 'orb') op = 0;
    if (op <= 0.001 || v.vz < 60) { el.style.display = 'none'; continue; }
    el.style.display = 'block';
    let sc = 1;
    if (id === 'orb') sc = (t < 3 ? 0.55 : 1) * (1 + (t >= 3 ? 0.04 * Math.sin(t * 6) : 0)) * (1 + 0.6 * oE(P_(t, 2.95, 0.5)) * (t < 3.5 ? 1 : 0)) * (1 + 0.8 * sk);
    if (id !== 'orb' && sk > 0) sc *= 1 - 0.8 * sk;
    const blur = Math.min(18, Math.abs(v.vz - focus) * 0.0075);
    el.style.opacity = op;
    el.style.transform = `translate3d(${v.vx}px, ${v.vy}px, ${P - v.vz}px) scale(${sc})`;
    el.style.filter = blur > 0.4 ? `blur(${blur}px)` : 'none';
    el.style.zIndex = Math.round(20000 - v.vz);
  }
  // typed reply
  const reply = "Standup at 10, design review at 2, and it's 27° and sunny. Book those flights first.";
  const ws = reply.split(' ');
  $('kt').textContent = ws.slice(0, Math.round(P_(t, 4.0, 1.5) * ws.length)).join(' ');
  $('sweep').style.transform = `translateX(${-130 + 260 * ioC(P_(t, 11.0, 0.9))}%)`;

  // light: rays from the orb, flares, dust
  const g = $('fx').getContext('2d');
  g.clearRect(0, 0, W, H);
  const ov = view(c, 0, 0, 0);
  if (ov.vz > 60 && t < 18.5) {
    const p = proj(ov);
    const ign = t < 3 ? 0.25 + 0.15 * Math.sin(t * 3) : 1;
    rays(g, p.x, p.y, Math.min(2600, 1300 * p.s), ign * clamp((ov.vz - 150) / 500) * (1 + sk), t);
  }
  // flares: ignition, passing through the light, final burst
  let fl = 0, fx = W / 2, fy = H / 2;
  if (ov.vz > 60) { const p = proj(ov); fx = p.x; fy = p.y; }
  fl = Math.max(fl, Math.exp(-Math.max(0, t - 3.0) / 0.35) * (t >= 2.95 ? 1 : 0));
  fl = Math.max(fl, 0.9 * Math.exp(-Math.pow((t - 6.62) / 0.16, 2)));
  if (t >= 18.5) { fx = W / 2; fy = 790; fl = Math.max(fl, Math.exp(-(t - 18.5) / 0.5)); }
  flare(g, fx, fy, fl);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [X, Y, Z, k] of DUST) {
    const v = view(c, X * (1 - 0.5 * sk), Y, Z);
    if (v.vz < 40 || v.vz > 9000) continue;
    const p = proj(v);
    if (p.x < -200 || p.x > W + 200 || p.y < -200 || p.y > H + 200) continue;
    const near = v.vz < 700;
    const r = near ? 18 + 60 * (1 - v.vz / 700) : Math.max(1.2, 3.2 * p.s);
    const a = (near ? 0.10 : 0.55) * clamp((9000 - v.vz) / 4000) * (0.5 + 0.5 * k);
    const gg = g.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
    gg.addColorStop(0, `rgba(255,225,185,${a})`); gg.addColorStop(near ? 0.7 : 0.4, `rgba(255,210,160,${a * 0.5})`); gg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gg; g.beginPath(); g.arc(p.x, p.y, r, 0, Math.PI * 2); g.fill();
  }
  g.restore();

  // titles
  const fade = (id, a, b, inD = 0.5, outD = 0.4, track = true) => {
    const el = $(id), pi = oE(P_(t, a, inD)), po = P_(t, b - outD, outD);
    el.style.opacity = pi * (1 - po);
    el.style.letterSpacing = track ? (0.12 * (1 - pi)) + 'em' : '';
    el.style.transform = `translateY(${(1 - pi) * 20 - po * 20}px)`;
    el.style.filter = `blur(${(1 - pi) * 8 + po * 8}px)`;
  };
  fade('tA', 0.35, 1.85, 0.7, 0.35); fade('tB', 1.9, 3.0, 0.5, 0.25);
  fade('tC', 3.3, 6.0, 0.6, 0.35, false);
  const words = [[6.62, 7.55, 'Your day.'], [7.6, 8.55, 'Your music.'], [8.6, 9.55, 'Your PC, protected.']];
  const cur = words.find(([a, b]) => t >= a && t < b);
  if (cur) { $('tD').textContent = cur[2]; fade('tD', cur[0], cur[1], 0.35, 0.25); } else $('tD').style.opacity = 0;
  fade('tE', 10.5, 13.0, 0.7, 0.3, false); fade('tF', 11.3, 13.0, 0.6, 0.3, false);
  // roast: lights out, then the slam
  const rd = P_(t, 12.95, 0.15) * (1 - P_(t, 14.85, 0.2));
  $('roast').style.opacity = rd * 0.94;
  const ru = P_(t, 13.2, 0.3) * (1 - P_(t, 14.85, 0.2));
  $('rub').style.opacity = ru; $('rub').style.transform = `translateY(${(1 - oE(ru)) * 40}px)`;
  const rk = (t >= 14.0 ? 1 : 0) * (1 - P_(t, 14.85, 0.2));
  const slam = Math.exp(-Math.max(0, t - 14.0) / 0.12);
  $('rkb').style.opacity = rk; $('rkb').style.transform = `scale(${1 + 0.35 * slam * (t >= 14 ? 1 : 0)}) translate(${(Math.sin(t * 90) * 14 * slam)}px, 0)`;
  const sku = P_(t, 14.25, 0.3) * (1 - P_(t, 14.85, 0.2));
  $('skull').style.opacity = clamp(sku * 3); $('skull').style.transform = `scale(${2 - oE(sku)}) rotate(${10 - 20 * (1 - sku)}deg)`;
  // promises during the pull-back
  const lines = [[15.4, 'Free.'], [15.9, 'Open source.'], [16.4, 'Private by design.'], [16.9, 'Built for Windows.']];
  $('tG').innerHTML = lines.map(([a, s]) => `<div style="opacity:${oE(P_(t, a, 0.4))};transform:translateY(${(1 - oE(P_(t, a, 0.4))) * 30}px);filter:blur(${(1 - oE(P_(t, a, 0.4))) * 10}px)">${s}</div>`).join('');
  $('tG').style.opacity = (t >= 15.3 ? 1 : 0) * (1 - P_(t, 17.4, 0.35));
  // logo
  const lg = t >= 18.5;
  $('logo').style.opacity = lg ? 1 : 0;
  if (lg) {
    const ps = $('lmk').querySelectorAll('path');
    ps[0].style.strokeDashoffset = 40 * (1 - ioC(P_(t, 18.5, 0.6))); ps[1].style.strokeDashoffset = 40 * (1 - ioC(P_(t, 18.7, 0.55)));
    const n = P_(t, 18.9, 0.8); $('lnm').style.opacity = n; $('lnm').style.letterSpacing = (0.6 - 0.4 * oE(n)) + 'em';
    $('lnm').style.backgroundPosition = `${100 - 100 * ioC(P_(t, 19.4, 1.0))}% 0`;
    const s = P_(t, 19.4, 0.5); $('lsb').style.opacity = s;
    const l = P_(t, 19.8, 0.5); $('lpl').style.opacity = l; $('lpl').style.transform = `scale(${0.9 + 0.1 * oE(l)})`;
  }
  // flash, letterbox, grain
  let f = 0;
  f = Math.max(f, 0.75 * Math.exp(-Math.max(0, t - 3.0) / 0.12) * (t >= 3 ? 1 : 0));
  f = Math.max(f, 0.85 * Math.exp(-Math.pow((t - 6.62) / 0.09, 2)));
  f = Math.max(f, 0.5 * Math.exp(-Math.max(0, t - 14.0) / 0.08) * (t >= 14 ? 1 : 0));
  f = Math.max(f, 0.9 * Math.exp(-Math.max(0, t - 18.5) / 0.15) * (t >= 18.5 ? 1 : 0));
  $('flash').style.opacity = f;
  let lb = t < 3 ? 560 : lerp(560, 0, oE(P_(t, 3.0, 0.9)));
  lb = Math.max(lb, 300 * ioC(P_(t, 19.2, 1.2)));
  $('lbt').style.height = $('lbb').style.height = lb + 'px';
  const fr = Math.floor(t * 15);
  $('grain').style.transform = `translate(${(fr * 37) % 160 - 80}px, ${(fr * 61) % 160 - 80}px)`;
  // gentle camera shake on hits
  let sh = 0;
  for (const h of [3.0, 6.0, 14.0, 18.5]) if (t >= h) sh = Math.max(sh, 16 * Math.exp(-(t - h) / 0.2));
  if (t >= 6 && t < 12.9) sh = Math.max(sh, 3 * Math.exp(-((t - 6) % 0.5) / 0.1));
  if (t >= 15 && t < 17.5) sh = Math.max(sh, 3 * Math.exp(-((t - 15) % 0.5) / 0.1));
  $('vp').style.transform = `translate(${Math.sin(t * 77) * sh}px, ${Math.cos(t * 59) * sh}px)`;
};
"""


# ── Music: an original trailer-style score ──────────────────────────────────
rng = random.Random(21)
N = int(TOTAL * SR)


def hz(n):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    return 440 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def saws(freqs, length, cut, decay=0.0, attack=0.01, release=None, amp=0.2, detune=(-9, 9), drive=1.0):
    n = int(length * SR)
    vs = [(f * 2 ** (d / 1200), rng.random()) for f in freqs for d in detune]
    ph = [p for _, p in vs]
    inc = [f / SR for f, _ in vs]
    out, a1, a2 = [], 0.0, 0.0
    rel = release or length
    for i in range(n):
        t = i / SR
        s = 0.0
        for k in range(len(ph)):
            ph[k] = (ph[k] + inc[k]) % 1.0
            s += 2 * ph[k] - 1
        c = cut(t)
        a1 += c * (s - a1)
        a2 += c * (a1 - a2)
        env = min(1, t / attack) * (math.exp(-t * decay) if decay else 1) * min(1, (length - t) / 0.08) * (min(1, (rel - t) / 0.4) if release else 1)
        x = a2 / len(ph) * 2.2 * env
        out.append(amp * (math.tanh(drive * x) / math.tanh(drive) if drive > 1 else x))
    return out


def braam(length=3.2, amp=0.55):
    notes = [hz("A1"), hz("E2"), hz("A2"), hz("C3")]
    b = saws(notes, length, lambda t: 0.015 + 0.16 * (1 - math.exp(-t * 14)) * math.exp(-t * 1.6), attack=0.03, amp=amp, detune=(-14, 0, 14), drive=2.6)
    out, ph = [], 0.0
    for i, x in enumerate(b):
        t = i / SR
        ph += 2 * math.pi * (55 + 40 * math.exp(-t * 6)) / SR
        out.append(x + 0.5 * amp * math.sin(ph) * math.exp(-t * 1.2) * min(1, t * 200))
    return out


def taiko(amp=0.9, f0=95, f1=48):
    out, ph = [], 0.0
    for i in range(int(0.6 * SR)):
        t = i / SR
        ph += 2 * math.pi * (f1 + (f0 - f1) * math.exp(-t * 22)) / SR
        out.append(amp * math.tanh(2.0 * (math.sin(ph) * math.exp(-t * 6) + rng.uniform(-1, 1) * 0.35 * math.exp(-t * 60))))
    return out


def snare(amp=0.55):
    return [amp * (0.8 * rng.uniform(-1, 1) * math.exp(-i / SR * 14) + 0.5 * math.sin(2 * math.pi * 180 * i / SR) * math.exp(-i / SR * 24))
            for i in range(int(0.35 * SR))]


def tick(amp=0.12):
    out, prev = [], 0.0
    for i in range(int(0.03 * SR)):
        x = rng.uniform(-1, 1)
        out.append(amp * (x - prev) * math.exp(-i / SR * 160))
        prev = x
    return out


def riser(length, amp=0.32):
    out, lp, ph = [], 0.0, 0.0
    n = int(length * SR)
    for i in range(n):
        p = i / n
        lp += (0.01 + 0.45 * p ** 2) * (rng.uniform(-1, 1) - lp)
        ph += 2 * math.pi * (110 + 880 * p ** 2) / SR
        out.append(amp * p ** 2.2 * (lp + 0.3 * math.sin(ph)))
    return out


def impact(amp=1.0):
    out, lp, ph = [], 0.0, 0.0
    for i in range(int(2.0 * SR)):
        t = i / SR
        lp += 0.04 * (rng.uniform(-1, 1) - lp)
        ph += 2 * math.pi * (30 + 70 * math.exp(-t * 14)) / SR
        out.append(amp * math.tanh(1.5 * (math.sin(ph) * math.exp(-t * 1.8) + 1.4 * lp * math.exp(-t * 4.5))))
    return out


def whoosh(length=0.6, amp=0.32):
    out, lp = [], 0.0
    n = int(length * SR)
    for i in range(n):
        p = i / n
        env = math.sin(math.pi * p) ** 2
        lp += (0.015 + 0.3 * env) * (rng.uniform(-1, 1) - lp)
        out.append(amp * lp * env * 2.4)
    return out


def bell(f, length=3.0, amp=0.16):
    return [amp * sum(a * math.sin(2 * math.pi * f * m * i / SR) * math.exp(-i / SR * d) for m, a, d in ((1, 1, 1.2), (2.0, .45, 1.8), (2.76, .25, 2.6), (5.4, .1, 5)))
            * min(1, i / SR * 300) for i in range(int(length * SR))]


def add(buf, sample, at, gain=1.0):
    s = int(at * SR)
    for i, x in enumerate(sample):
        j = s + i
        if 0 <= j < N:
            buf[j] += x * gain


def reverb(x, mix, fb_scale=1.0):
    out = [0.0] * len(x)
    for d, fb in ((1687, .84), (1601, .83), (2053, .85), (2251, .86), (1931, .84), (1777, .85)):
        buf = [0.0] * len(x)
        f = fb * fb_scale
        for i in range(len(x)):
            y = x[i] + (f * buf[i - d] if i >= d else 0)
            buf[i] = y
            out[i] += y * mix / 6
    return out


CHORDS = [["A2", "E3", "A3", "C4"], ["F2", "C3", "F3", "A3"], ["C3", "G3", "C4", "E4"], ["G2", "D3", "G3", "B3"]]


def make_music():
    big, drums, strings, fx = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
    # drone under everything except the gaps
    drone = saws([hz("A1"), hz("E2")], TOTAL, lambda t: 0.004 + 0.012 * min(1, t / 6), attack=1.5, amp=0.22, detune=(-6, 6))
    add(big, drone, 0)
    # braams
    for at, a in ((0.25, 0.55), (3.0, 0.75), (18.5, 0.85)):
        add(big, braam(3.4 if at > 18 else 3.0, a), at)
    add(big, braam(1.4, 0.6), 14.0)
    # ticking pulse
    t = 1.0
    while t < 18.5:
        if not (5.85 <= t < 6.0 or 12.95 <= t < 14.0):
            add(fx, tick(0.13 if int(round(t * 4)) % 2 == 0 else 0.07), t)
        t += 0.25
    # string ostinato (16ths), quiet in the build, full in the drops
    cache = {}

    def pl(f):
        if f not in cache:
            cache[f] = saws([f], 0.16, lambda t: 0.06 + 0.25 * math.exp(-t * 25), attack=0.004, decay=10, amp=0.16, detune=(-7, 7))
        return cache[f]

    for bar in range(10):
        t0 = 3.0 + bar * 2.0
        if t0 >= 18.5:
            break
        ch = CHORDS[bar % 4] if t0 >= 6 else CHORDS[0]
        notes = [hz(n) * 2 for n in ch]
        for s in range(16):
            tt = t0 + s * 0.125
            if 5.85 <= tt < 6.0 or 12.95 <= tt < 15.0 or tt >= 18.5:
                continue
            g = 0.45 if tt < 6 else 0.9
            add(strings, pl(notes[[0, 2, 1, 3, 2, 1, 3, 2][s % 8]]), tt, g)
        if t0 >= 6 and not (12.9 <= t0 < 15):
            add(strings, saws([hz(n) for n in ch], 2.0, lambda t: 0.02, attack=0.2, amp=0.12, detune=(-8, 0, 8)), t0)
    # drums: 6-13 and 15-18.5
    tk, sn = taiko(), snare()
    for start, end, hard in ((6.0, 12.95, False), (15.0, 18.5, True)):
        t = start
        i = 0
        while t < end - 1e-6:
            pos = i % 8                                  # eighth notes in a bar of 4 beats
            if pos in (0, 3, 4, 6) or (hard and pos in (1, 5, 7)):
                add(drums, tk, t, 1.0 if pos in (0, 4) else 0.7)
            if pos in (2, 6):
                add(drums, sn, t, 0.9)
            t += 0.25
            i += 1
    for r in range(8):
        add(drums, sn, 17.5 + r * 0.125, 0.25 + 0.08 * r)
    # risers, impacts, whooshes
    add(fx, riser(2.8, 0.3), 3.1)
    add(fx, riser(2.4, 0.3), 16.1)
    for at, a in ((3.0, 0.9), (6.0, 1.0), (12.95, 0.7), (14.0, 0.9), (18.5, 1.0)):
        add(fx, impact(a), at)
    for at in (6.45, 6.9, 7.4, 7.9, 8.4, 8.9, 9.4):
        add(fx, whoosh(0.5, 0.26), at - 0.2)
    add(fx, whoosh(2.4, 0.3), 15.0)
    add(fx, whoosh(1.0, 0.3), 17.5)
    add(fx, bell(hz("A5")), 18.6)
    add(fx, bell(hz("E6"), amp=0.09), 18.7)
    # gaps: the breath before each drop
    for a, b in ((5.85, 6.0), (12.95, 13.05)):
        for buf in (big, drums, strings):
            for i in range(int(a * SR), int(b * SR)):
                buf[i] *= 0.05
    wet_big = reverb(big, 0.35)
    wet_dr = reverb([d * 0.6 for d in drums], 0.25, 0.97)
    wet_st = reverb(strings, 0.3)
    left, right = [0.0] * N, [0.0] * N
    d1, d2 = int(0.375 * SR), int(0.5 * SR)
    for i in range(N):
        st = strings[i]
        el = 0.22 * strings[i - d1] if i >= d1 else 0
        er = 0.22 * strings[i - d2] if i >= d2 else 0
        base = big[i] + drums[i] + fx[i] + wet_big[i] + wet_dr[i] + wet_st[i]
        left[i] = base + st + el
        right[i] = base + st + er
    fade = int(1.5 * SR)
    for ch in (left, right):
        for i in range(fade):
            ch[N - 1 - i] *= (i / fade) ** 1.3
        peak = max(1e-9, max(abs(x) for x in ch))
        for i in range(N):
            ch[i] = math.tanh(1.4 * ch[i] / peak) / math.tanh(1.4)
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
    page.write_text(html(), encoding="utf-8")
    frames = int(TOTAL * FPS)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=["--allow-file-access-from-files"])
        pg = browser.new_context(viewport={"width": W, "height": H}).new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(page.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        for t in checks:
            pg.evaluate(f"window.render({t})")
            pg.screenshot(path=str(TMP / f"check_{t:05.2f}.png"))
        if "--checks-only" in sys.argv:
            print("errors:", errors, "\nchecks in", TMP, flush=True)
            browser.close()
            return
        ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                               "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",
                               "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M",
                               "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
        for i in range(frames):
            acc = None
            for k in range(SUB):                       # motion blur: average sub-frames across the shutter
                pg.evaluate(f"window.render({(i + k / SUB * 0.75) / FPS})")
                im = Image.open(io.BytesIO(pg.screenshot(type="jpeg", quality=95))).convert("RGB")
                acc = im if acc is None else Image.blend(acc, im, 1 / (k + 1))
            buf = io.BytesIO()
            acc.save(buf, "JPEG", quality=94)
            ff.stdin.write(buf.getvalue())
            if i % 90 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        pg.evaluate("window.render(11.8)")
        pg.screenshot(path=str(OUT / "kalki_reel_cinematic_cover.png"))
        if errors:
            print("page errors:", errors[:3], flush=True)
        browser.close()
        ff.stdin.close()
        ff.wait()


def main():
    checks = [float(a) for a in sys.argv[1:] if not a.startswith("--")]
    silent = OUT / "kalki_reel_cinematic_silent.mp4"
    render_video(silent, checks)
    if "--checks-only" in sys.argv:
        return
    print("video done", flush=True)
    left, right = make_music()
    write_wav(TMP / "score.wav", left, right)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(TMP / "score.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-13:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / "kalki_reel_cinematic.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(TMP / "score.wav"), "-af", "loudnorm=I=-13:TP=-1.0:LRA=11",
                    "-ar", "48000", str(OUT / "kalki_cinematic_score.wav")], check=True)
    print("done", TMP, flush=True)


if __name__ == "__main__":
    main()
