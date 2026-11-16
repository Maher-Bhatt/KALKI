"""KALKI epic Reel: a 34-second cinematic one-take through a world built around KALKI.

A dawn landscape of mountains, stars, fog and a reflective ground grid. The orb rises like a
sunrise, the camera flies through the light and through zones of floating interface (your day,
focus, notes, music, commands, apps, memory), orbits a ring of AI choices, passes a security
zone with a glowing shield, lands on the real app under sweeping searchlights, cuts to black for
the roast, then pulls back high over the whole world and ends on the logo.
Depth of field, god rays, anamorphic flares, dust, bokeh, letterboxing, a colour grade and real
motion blur (three sub-frames per frame). The score is original.
Run from the repo root:  python tools/marketing/make_reel_epic.py [check times...] [--checks-only]
Writes marketing/video/reel_epic/.
"""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import array
import io
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
OUT = REPO / "marketing" / "video" / "reel_epic"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_epic_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H = 30, 1080, 1920
TOTAL = 34.0
SUB = 3
SR = 44100

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M2.5 20 10 5.5 17.5 20"/><path d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
WINCAPS = ('<span><svg viewBox="0 0 10 10"><path d="M0 5h10" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9" rx="1.2" fill="none" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><path d="M.5 .5l9 9M9.5 .5l-9 9" stroke="currentColor" stroke-width=".9"/></svg></span>')
SV = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
SHIELD_SM = f'<svg {SV} style="width:56px;height:56px;color:#8fd19e"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>'
MIC = f'<svg {SV} style="width:44px;height:44px;color:#efe4cf"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>'

CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#050505;color:#f5efe4;font-family:"Segoe UI Variable Text","Segoe UI",sans-serif}
canvas.full{position:absolute;inset:0;width:100%;height:100%}
#vp{position:absolute;inset:0;perspective:1400px;perspective-origin:50% 50%;overflow:hidden}
#world{position:absolute;left:50%;top:50%;width:0;height:0;transform-style:preserve-3d}
.o{position:absolute;left:0;top:0;display:none;will-change:transform,filter,opacity}
#fx{mix-blend-mode:screen}
.orb{width:420px;height:420px;margin:-210px 0 0 -210px;border-radius:50%;
  background:radial-gradient(circle at 40% 34%,#fffdf7 0%,#f6ead4 34%,#d8c3a0 70%,#9c8565 100%);
  box-shadow:0 0 160px 50px rgba(255,226,180,.35),0 0 420px 120px rgba(255,190,120,.18),inset -30px -40px 90px rgba(110,80,40,.45)}
.card{width:760px;margin-left:-380px;margin-top:-150px;border-radius:40px;padding:36px 44px;
  background:linear-gradient(160deg,rgba(44,40,36,.93),rgba(20,19,17,.95));border:1.5px solid rgba(255,235,205,.16);
  box-shadow:0 60px 120px -40px rgba(0,0,0,.95),inset 0 1px 0 rgba(255,240,220,.12);color:#ece6dc}
.lbl{font-size:24px;font-weight:700;letter-spacing:.22em;color:#a59b8c;text-transform:uppercase;margin-bottom:14px}
.row{display:flex;align-items:center;gap:20px;font-size:38px;margin:10px 0}
.sub{font-size:30px;color:#a59b8c}
.time{font-family:"Cascadia Mono",Consolas,monospace;font-size:28px;padding:6px 14px;border-radius:12px;background:#2f2c28}
.tag{font-size:26px;padding:4px 14px;border-radius:999px;background:#33302b;color:#d9cdb8;margin-left:10px}
.bub{max-width:760px;border-radius:40px;padding:26px 38px;font-size:44px;line-height:1.35}
.ub{background:rgba(52,48,44,.96);border:1.5px solid rgba(255,235,205,.18);font-weight:600;margin-left:-360px;margin-top:-60px;border-bottom-right-radius:12px;width:720px}
.kb{width:780px;background:rgba(24,23,21,.96);border:1.5px solid rgba(255,235,205,.16);margin-left:-390px;margin-top:-130px;border-bottom-left-radius:12px}
.who{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:700;letter-spacing:.14em;color:#efe4cf;margin-bottom:10px}
.who svg{width:34px;height:34px}
.chip3{white-space:nowrap;margin-left:-300px;margin-top:-55px;width:600px;display:flex;align-items:center;justify-content:center;gap:18px;font-size:44px;font-weight:600;
  padding:26px 40px;border-radius:999px;background:rgba(30,28,26,.94);border:2px solid rgba(239,228,207,.45);box-shadow:0 0 60px rgba(239,228,207,.18)}
.apps{margin-left:-380px;margin-top:-140px;width:760px;display:flex;justify-content:space-between}
.apps div{text-align:center;font-size:30px;color:#ddd3c3}
.apps i{display:flex;width:200px;height:200px;border-radius:48px;margin-bottom:16px;align-items:center;justify-content:center;box-shadow:0 30px 70px -20px rgba(0,0,0,.9)}
.apps svg{width:100px;height:100px;color:#fff}
.aic{width:400px;margin-left:-200px;margin-top:-70px;display:flex;align-items:center;gap:24px;padding:28px 34px;border-radius:34px;
  background:linear-gradient(160deg,rgba(44,40,36,.94),rgba(20,19,17,.96));border:1.5px solid rgba(255,235,205,.18);box-shadow:0 40px 90px -30px rgba(0,0,0,.95)}
.aic b{display:flex;width:80px;height:80px;flex:none;border-radius:28px;align-items:center;justify-content:center;font-size:40px;font-weight:700;color:#151413}
.aic .n{font-size:34px;font-weight:600}.aic .d{font-size:25px;color:#a59b8c;margin-top:2px}
.shield{width:420px;height:420px;margin:-210px 0 0 -210px;color:#efe4cf;filter:drop-shadow(0 0 40px rgba(255,220,170,.55)) drop-shadow(0 0 120px rgba(143,209,158,.25))}
.shield svg{width:100%;height:100%}
.win{width:900px;margin-left:-450px;margin-top:-270px}
.win .frame{position:relative;border-radius:14px;overflow:hidden;border:1.5px solid rgba(255,235,205,.18);background:#1b1a18;box-shadow:0 80px 160px -50px rgba(0,0,0,1),0 0 140px rgba(255,210,160,.12)}
.win .bar{height:44px;display:flex;align-items:center;background:#23211e;border-bottom:1px solid #34312c;font-size:17px;color:#e6dfd3;padding-left:16px}
.win .bar .ttl{display:flex;align-items:center;gap:10px;flex:1}
.win .bar .ttl svg{width:20px;height:20px}
.win .bar .cap{display:flex;height:100%}
.win .bar .cap span{width:58px;display:flex;align-items:center;justify-content:center}
.win .bar .cap svg{width:13px;height:13px}
.win img{display:block;width:100%;filter:brightness(1.35) contrast(1.05)}
.win .refl{margin-top:14px;height:300px;overflow:hidden;opacity:.24;transform:scaleY(-1);-webkit-mask-image:linear-gradient(0deg,rgba(0,0,0,.9),transparent 70%);filter:blur(3px)}
.win .refl img{display:block;width:100%}
.sweep{position:absolute;inset:0;background:linear-gradient(105deg,transparent 38%,rgba(255,245,230,.22) 50%,transparent 62%);transform:translateX(-130%)}
.t2d{position:absolute;left:60px;right:60px;text-align:center;font-family:"Sitka Display","Sitka Heading","Palatino Linotype",Georgia,serif;
  font-weight:400;color:#f7f1e6;text-shadow:0 0 40px rgba(255,220,170,.35),0 4px 30px rgba(0,0,0,.85);opacity:0}
.cap{font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;font-size:28px;letter-spacing:.42em;text-transform:uppercase;color:#cfc3b0;text-shadow:0 2px 20px rgba(0,0,0,.9)}
.big{font-size:104px;margin-top:10px;line-height:1.05}
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
#grade{position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;opacity:.55;background:linear-gradient(180deg,rgba(40,90,110,.9) 0%,rgba(0,0,0,0) 45%,rgba(255,170,90,.7) 100%)}
#vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 45%,rgba(0,0,0,.78) 100%)}
#grain{position:absolute;inset:-160px;pointer-events:none;opacity:.07;background-size:540px 960px}
#flash{position:absolute;inset:0;background:#fff6e6;opacity:0;pointer-events:none}
.lb{position:absolute;left:0;right:0;background:#000;height:0}
#lbt{top:0}#lbb{bottom:0}
"""


def tile(color, path, label):
    return f'<div><i style="background:{color}"><svg {SV}>{path}</svg></i>{label}</div>'


def html():
    shot = SHOT.as_uri()
    obj = {
        "orb": '<div class="o orb" id="orb"></div>',
        "orb2": '<div class="o orb" id="orb2"></div>',
        "ub": '<div class="o bub ub" id="ub">Hey KALKI, aaj ka plan kya hai?</div>',
        "kb": f'<div class="o bub kb" id="kb"><div class="who">{MARK}KALKI</div><span id="kt"></span></div>',
        "c1": '<div class="o card" id="c1"><div class="lbl">Weather · Bengaluru</div><div class="row" style="font-size:84px;font-weight:300">☀️ 27°<span class="sub" style="margin-left:14px">Sunny · H 30° L 21°</span></div></div>',
        "c2": '<div class="o card" id="c2"><div class="lbl">Today</div><div class="row"><span class="time">10:00</span>Team standup</div><div class="row"><span class="time">14:00</span>Design review</div><div class="row"><span class="time">18:30</span>Gym with Kabir</div></div>',
        "c3": '<div class="o card" id="c3"><div class="lbl">Tasks · 4 open</div><div class="row">◉ Finish the quarterly report</div><div class="row sub">○ Book flights to Bengaluru</div><div class="row sub">○ Renew car insurance</div></div>',
        "c4": '<div class="o card" id="c4"><div class="lbl">Reminder · every day</div><div class="row">💧 Stretch and drink water</div><div class="row sub">5:00 PM · snooze or done</div></div>',
        "c5": ('<div class="o card" id="c5"><div class="lbl">Focus session</div><div class="row" style="gap:32px">'
               '<svg viewBox="0 0 100 100" style="width:140px;height:140px;flex:none"><circle cx="50" cy="50" r="42" stroke="#3a3632" stroke-width="8" fill="none"/>'
               '<circle id="fring" cx="50" cy="50" r="42" stroke="#efe4cf" stroke-width="8" fill="none" stroke-linecap="round" stroke-dasharray="264" stroke-dashoffset="264" transform="rotate(-90 50 50)"/></svg>'
               '<div><div id="ftime" style="font-size:66px;font-family:Cascadia Mono,Consolas,monospace">25:00</div><div class="sub">Quarterly report · Do Not Disturb</div></div></div></div>'),
        "c6": ('<div class="o card" id="c6"><div class="lbl">Notes</div><div class="row" style="font-size:34px">Gift ideas for Mom<span class="tag">#family</span></div>'
               '<div class="row" style="font-size:34px">Q4: ship voice mode<span class="tag">#work</span></div><div class="row" style="font-size:34px">The Psychology of Money<span class="tag">#ideas</span></div></div>'),
        "m1": ('<div class="o card" id="m1"><div class="lbl">Now playing</div><div class="row" style="gap:28px"><div style="width:130px;height:130px;border-radius:20px;flex:none;background:linear-gradient(135deg,#3b2f5c,#b5566b 55%,#e8a265)"></div>'
               '<div><div style="font-size:42px;font-weight:600">Midnight Drive</div><div class="sub">Lo-fi Lounge · Apple Music</div>'
               '<div style="height:6px;border-radius:3px;background:#3a3632;margin-top:18px;width:420px"><div id="mprog" style="height:100%;width:30%;background:#efe4cf;border-radius:3px"></div></div></div></div></div>'),
        "k1": f'<div class="o chip3" id="k1">{MIC}“play some music”</div>',
        "k2": f'<div class="o chip3" id="k2">{MIC}“open WhatsApp”</div>',
        "k3": f'<div class="o chip3" id="k3">{MIC}“remind me at 5”</div>',
        "ap": ('<div class="o apps" id="ap">' +
               tile("linear-gradient(160deg,#3cd27a,#1c9e57)", '<path d="M4 18.5V7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H8z"/>', "WhatsApp") +
               tile("linear-gradient(160deg,#4aa3ff,#1f6fd6)", '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>', "VS Code") +
               tile("linear-gradient(160deg,#ff6f91,#c2335c)", '<path d="M9 18V6l10-2v12"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>', "Music") + '</div>'),
        "mem": '<div class="o card" id="mem"><div class="lbl">Memory · encrypted</div><div class="row">🔒 You take oat milk in your coffee</div><div class="row sub">Kept on your PC · forget it any time</div></div>',
        "ai1": '<div class="o aic" id="ai1"><b style="background:#8ab4ff">G</b><div><div class="n">Google Gemini</div><div class="d">Free tier</div></div></div>',
        "ai2": '<div class="o aic" id="ai2"><b style="background:#ff9a6b">Gq</b><div><div class="n">Groq</div><div class="d">Fastest replies</div></div></div>',
        "ai3": '<div class="o aic" id="ai3"><b style="background:#9de0c4">O</b><div><div class="n">OpenAI</div><div class="d">GPT models</div></div></div>',
        "ai4": '<div class="o aic" id="ai4"><b style="background:#e8c39e">C</b><div><div class="n">Claude</div><div class="d">by Anthropic</div></div></div>',
        "ai5": '<div class="o aic" id="ai5"><b style="background:#efe4cf">⌂</b><div><div class="n">Ollama</div><div class="d">Fully offline</div></div></div>',
        "sh": f'<div class="o shield" id="sh"><svg {SV} style="stroke-width:.9"><path d="M12 2.5l8.5 3.2v6.3c0 5.3-3.7 8.6-8.5 9.7-4.8-1.1-8.5-4.4-8.5-9.7V5.7z"/><path d="M8.3 12.2l2.6 2.6 4.8-5.3" style="stroke-width:1.3"/></svg></div>',
        "d1": f'<div class="o card" id="d1"><div class="lbl">Protection</div><div class="row">{SHIELD_SM}<div><div style="font-size:42px;font-weight:600">Windows Defender is on</div><div class="sub">Scanned today · nothing to review</div></div></div></div>',
        "q1": '<div class="o card" id="q1"><div class="lbl">Quarantine</div><div class="row">⚠️ invoice.pdf.exe</div><div class="row sub">Disguised as a PDF · locked away safely</div></div>',
        "win": (f'<div class="o win" id="win"><div class="frame"><div class="bar"><div class="ttl">{MARK}<span>KALKI</span></div><div class="cap">{WINCAPS}</div></div>'
                f'<img src="{shot}"><div class="sweep" id="sweep"></div></div><div class="refl"><img src="{shot}"></div></div>'),
    }
    t2d = """
<div class="t2d" id="tA" style="top:640px;font-size:70px">For years, your PC<br>just listened.</div>
<div class="t2d" id="tB" style="top:650px;font-size:100px">Now, it <i>answers.</i></div>
<div class="t2d" id="tC" style="top:230px"><div class="cap">Hey KALKI</div><div class="big">Just talk.</div></div>
<div class="t2d" id="tC2" style="top:500px;font-size:46px">English · हिंदी · Hinglish</div>
<div class="t2d" id="tD" style="top:250px;font-size:116px"></div>
<div class="t2d" id="tH" style="top:230px"><div class="cap">Choose its brain</div><div class="big">Any AI.<br><i>Even offline.</i></div></div>
<div class="t2d" id="tI" style="top:230px"><div class="cap">Security</div><div class="big" style="font-size:92px">Safer, with<br>Windows Defender.</div></div>
<div class="t2d" id="tI2" style="top:1600px;font-size:46px">Plain answers. Never made-up threats.</div>
<div class="t2d" id="tE" style="top:240px"><div class="cap">Not a mockup</div><div class="big" style="font-size:112px">This is <i>KALKI.</i></div></div>
<div class="t2d" id="tF" style="top:1380px"><div class="cap" style="letter-spacing:.3em">Real app · real Windows</div></div>
"""
    rest = f"""
<div id="roast"></div>
<div class="bub ub" id="rub" style="margin:0;width:auto">bro you're kinda useless ngl</div>
<div class="bub kb" id="rkb" style="margin:0"><div class="who">{MARK}KALKI <span style="font-size:20px;background:#efe4cf;color:#151413;padding:4px 12px;border-radius:999px;letter-spacing:.08em">SAVAGE</span></div>Useless? I've reminded you to drink water three times today and you're still dehydrated. 💀</div>
<div id="skull">💀</div>
<div class="t2d" id="tG" style="top:1240px;font-size:84px;line-height:1.22"></div>
<div id="logo"><div class="mk" id="lmk">{MARK}</div><div class="nm" id="lnm">KALKI</div><div class="sb" id="lsb">Your AI assistant for Windows</div><div class="pl" id="lpl">Free · link in bio</div></div>
"""
    body = (f'<canvas class="full" id="sky" width="540" height="960"></canvas>'
            f'<div id="vp"><div id="world">{"".join(obj.values())}</div></div>'
            f'<canvas class="full" id="fg" width="1080" height="1920"></canvas>'
            f'<canvas class="full" id="fx" width="1080" height="1920"></canvas>'
            f'{t2d}{rest}<div id="grade"></div><div id="vig"></div><div id="grain"></div><div id="flash"></div>'
            f'<div class="lb" id="lbt"></div><div class="lb" id="lbb"></div>')
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}<script>{JS}</script></body></html>'


JS = r"""
const $ = id => document.getElementById(id);
const W = 1080, H = 1920, P = 1400, GROUND = 900;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, x) => a + (b - a) * x;
const P_ = (t, a, d) => clamp((t - a) / d);
const ioC = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const oE = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

const RING = [0, -8200], RING_R = 420;
const OBJ = {orb: [0, 0, 0], ub: [-170, 230, 300], kb: [150, 470, -60],
  c1: [-160, -240, -700], c2: [160, 260, -1400], c3: [-160, -230, -2100], c4: [160, 260, -2800], c5: [-160, -240, -3500], c6: [160, 250, -4200],
  m1: [-160, -240, -4900], k1: [200, 120, -5250], k2: [-210, 330, -5400], k3: [190, -330, -5550], ap: [0, 230, -5850], mem: [-150, -240, -6250],
  orb2: [RING[0], 0, RING[1]],
  sh: [0, -330, -11150], d1: [-190, 300, -10800], q1: [210, 560, -11000],
  win: [0, -40, -13700]};
['ai1', 'ai2', 'ai3', 'ai4', 'ai5'].forEach((id, k) => {
  const a = k / 5 * Math.PI * 2 + 0.35;
  OBJ[id] = [RING[0] + RING_R * Math.sin(a), (k % 2 ? 230 : -260), RING[1] + RING_R * Math.cos(a)];
});
const SHOW = {ub: [5.3, 99], kb: [5.9, 99], c1: [7.4, 99], c2: [7.4, 99], c3: [7.4, 99], c4: [7.4, 99], c5: [7.4, 99], c6: [7.4, 99],
  m1: [8.5, 99], k1: [8.5, 99], k2: [8.5, 99], k3: [8.5, 99], ap: [8.5, 99], mem: [8.5, 99],
  orb2: [11, 99], ai1: [11, 99], ai2: [11, 99], ai3: [11, 99], ai4: [11, 99], ai5: [11, 99],
  sh: [15, 99], d1: [15, 99], q1: [15, 99], win: [18, 99]};
const DUST = Array.from({length: 600}, () => [lerp(-2000, 2000, rnd()), lerp(-2600, 850, rnd()), lerp(-15000, 6000, rnd()), rnd()]);
const STARS = Array.from({length: 260}, () => [rnd() * 1.6 - 0.3, rnd() * 0.46, rnd(), rnd()]);
const RIDGES = [[52000, 4200, '#2b2620', 1.0], [36000, 3400, '#1f1b17', 1.7], [24000, 2500, '#15130f', 2.6], [15000, 1700, '#0d0c0a', 3.8]];
const PH = Array.from({length: 4}, () => [rnd() * 9, rnd() * 9, rnd() * 9]);
function ridgeH(k, x) { const p = PH[k]; return 0.55 + 0.22 * Math.sin(x * 0.00011 + p[0]) + 0.16 * Math.sin(x * 0.00031 + p[1]) + 0.07 * Math.sin(x * 0.0011 + p[2]); }

function camera(t) {
  if (t < 4) { const p = ioC(t / 4); return {x: 0, y: lerp(-80, 0, p), z: lerp(4300, 2650, p), ry: 0}; }
  if (t < 8) { const p = (t - 4) / 4; return {x: lerp(-120, 40, ioC(p)), y: lerp(60, 20, p), z: lerp(2650, 950, p * 0.45 + p * p * 0.55), ry: lerp(-0.2, 0.1, ioC(p))}; }
  if (t < 13.2) { const q = P_(t, 8, 0.8); return {x: lerp(40, 0, q), y: lerp(20, 0, q), z: 950 - 1400 * (t - 8), ry: lerp(0.1, 0, q)}; }
  const D = 1350, a0 = -0.55, a1 = 0.6;
  const orbitPos = a => ({x: RING[0] + D * Math.sin(a), y: 0, z: RING[1] + D * Math.cos(a), ry: -a});
  if (t < 14.5) { const p = ioC((t - 13.2) / 1.3), o = orbitPos(a0); return {x: lerp(0, o.x, p), y: 0, z: lerp(-6330, o.z, 1 - Math.pow(1 - (t - 13.2) / 1.3, 2)), ry: lerp(0, o.ry, p)}; }
  if (t < 18.5) return orbitPos(lerp(a0, a1, ioC((t - 14.5) / 4)));
  if (t < 19.6) { const p = ioC((t - 18.5) / 1.1), o = orbitPos(a1); return {x: lerp(o.x, 0, p), y: 0, z: lerp(o.z, -9500, p), ry: lerp(o.ry, 0, p)}; }
  if (t < 22) return {x: 0, y: 0, z: lerp(-9500, -9800, (t - 19.6) / 2.4), ry: 0};
  if (t < 23) { const p = ioC(t - 22); return {x: 0, y: 0, z: lerp(-9800, -12300, p), ry: 0}; }
  if (t < 27.5) return {x: 0, y: 0, z: lerp(-12300, -12480, (t - 23) / 4.5), ry: 0};
  if (t < 27.8) return {x: 0, y: 0, z: -12480, ry: 0};
  const p = ioC(P_(t, 27.8, 6.2));
  return {x: lerp(-90, 0, p), y: lerp(-120, -180, p), z: lerp(4200, 2500, p), ry: lerp(-0.03, 0, p)};
}
function view(c, X, Y, Z) {
  const dx = X - c.x, dy = Y - c.y, dz = c.z - Z, cs = Math.cos(c.ry), sn = Math.sin(c.ry);
  return {vx: dx * cs - dz * sn, vy: dy, vz: dz * cs + dx * sn};
}
function proj(v) { const s = P / v.vz; return {x: W / 2 + v.vx * s, y: H / 2 + v.vy * s, s}; }
function orbY(t) { return t >= 27.8 ? -330 : lerp(720, 0, ioC(P_(t, 0.3, 3.7))); }
function focusAt(t, c) {
  const vz = id => view(c, ...OBJ[id]).vz;
  if (t < 4.5) return view(c, 0, orbY(t), 0).vz;
  if (t < 5.9) return vz('ub');
  if (t < 8) return vz('kb');
  if (t < 13.2) return 1100;
  if (t < 18.6) return view(c, RING[0], 0, RING[1]).vz;
  if (t < 22) return vz('sh');
  if (t < 27.5) return vz('win');
  return view(c, 0, orbY(t), 0).vz;
}
const suck = t => ioC(P_(t, 30.6, 0.9));

(() => { const c = document.createElement('canvas'); c.width = 270; c.height = 480; const g = c.getContext('2d');
  const d = g.createImageData(270, 480); let s = 3;
  for (let i = 0; i < d.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = s % 256; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
  g.putImageData(d, 0, 0); $('grain').style.backgroundImage = `url(${c.toDataURL()})`; })();

// ── the world: sky, stars, mountains, fog, ground grid ──
function world(t, c, orbScreen, orbBright) {
  const g = $('sky').getContext('2d');
  g.setTransform(0.5, 0, 0, 0.5, 0, 0);
  const hz = H / 2 + (GROUND - c.y) * P / 90000;              // horizon line
  const sky = g.createLinearGradient(0, 0, 0, hz);
  sky.addColorStop(0, '#04060a'); sky.addColorStop(0.6, '#0b0b0e');
  sky.addColorStop(1, `rgb(${Math.round(40 + 40 * orbBright)},${Math.round(28 + 24 * orbBright)},${Math.round(20 + 10 * orbBright)})`);
  g.fillStyle = sky; g.fillRect(0, 0, W, hz + 2);
  for (const [sx, sy, k, tw] of STARS) {
    const x = (sx * W - c.ry * 1400 - c.x * 0.01) % (W * 1.6), y = sy * hz * 0.95;
    const a = (0.25 + 0.55 * k) * (0.6 + 0.4 * Math.sin(t * (1 + 3 * tw) + tw * 20)) * clamp(1 - orbBright * 0.4);
    g.fillStyle = `rgba(255,245,230,${a})`; g.fillRect(x, y, 2 + 2 * k, 2 + 2 * k);
  }
  // glow of the sun-orb on the sky
  if (orbScreen) {
    const gl = g.createRadialGradient(orbScreen.x, Math.min(orbScreen.y, hz), 0, orbScreen.x, Math.min(orbScreen.y, hz), 1300);
    gl.addColorStop(0, `rgba(255,190,120,${0.32 * orbBright})`); gl.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gl; g.fillRect(0, 0, W, H);
  }
  // mountain ridges (far to near)
  RIDGES.forEach(([d, hgt, col, par], k) => {
    g.beginPath();
    const base = H / 2 + (GROUND - c.y) * P / d;
    g.moveTo(-10, H);
    for (let sx = -10; sx <= W + 10; sx += 12) {
      const X = (sx - W / 2) * d / P + c.x + c.ry * d;
      const top = H / 2 + (GROUND - hgt * ridgeH(k, X) - c.y) * P / d;
      g.lineTo(sx, top);
    }
    g.lineTo(W + 10, H); g.closePath();
    g.fillStyle = col; g.fill();
    // atmospheric haze between layers
    const hzG = g.createLinearGradient(0, base - 260, 0, base + 30);
    hzG.addColorStop(0, 'rgba(0,0,0,0)'); hzG.addColorStop(1, `rgba(${60 + 50 * orbBright},${44 + 30 * orbBright},${34 + 14 * orbBright},${0.22 - k * 0.04})`);
    g.fillStyle = hzG; g.fillRect(0, base - 260, W, 290);
  });
  // ground
  const gy = H / 2 + (GROUND - c.y) * P / 15000;
  const gr = g.createLinearGradient(0, gy, 0, H);
  gr.addColorStop(0, '#0e0c0a'); gr.addColorStop(1, '#030303');
  g.fillStyle = gr; g.fillRect(0, gy, W, H - gy);
  // grid on the ground
  g.lineWidth = 2;
  const step = 500, z0 = Math.floor(c.z / step) * step;
  for (let k = 1; k < 44; k++) {
    const Z = z0 - k * step;
    const a = view(c, -7000, GROUND, Z), b = view(c, 7000, GROUND, Z);
    if (a.vz < 60 || b.vz < 60) continue;
    const pa = proj(a), pb = proj(b), d = (a.vz + b.vz) / 2;
    g.strokeStyle = `rgba(239,214,170,${0.16 * clamp(1 - d / 16000) * clamp((d - 100) / 400)})`;
    g.beginPath(); g.moveTo(pa.x, pa.y); g.lineTo(pb.x, pb.y); g.stroke();
  }
  for (let X = -6000; X <= 6000; X += 600) {
    const a = view(c, X + c.x - (c.x % 600), GROUND, c.z - 120), b = view(c, X + c.x - (c.x % 600), GROUND, c.z - 18000);
    if (a.vz < 60) continue;
    const pa = proj(a), pb = proj(b);
    const lg = g.createLinearGradient(pa.x, pa.y, pb.x, pb.y);
    lg.addColorStop(0, 'rgba(239,214,170,.14)'); lg.addColorStop(1, 'rgba(239,214,170,0)');
    g.strokeStyle = lg; g.beginPath(); g.moveTo(pa.x, pa.y); g.lineTo(pb.x, pb.y); g.stroke();
  }
  // orb reflection on the ground
  if (orbScreen && orbScreen.y < gy + 200) {
    const ry = gy + (gy - orbScreen.y) * 0.35 + 40;
    const rg = g.createRadialGradient(orbScreen.x, ry, 0, orbScreen.x, ry, 420);
    rg.addColorStop(0, `rgba(255,200,140,${0.28 * orbBright})`); rg.addColorStop(1, 'rgba(0,0,0,0)');
    g.save(); g.translate(orbScreen.x, ry); g.scale(1, 0.32); g.translate(-orbScreen.x, -ry);
    g.fillStyle = rg; g.beginPath(); g.arc(orbScreen.x, ry, 420, 0, Math.PI * 2); g.fill(); g.restore();
  }
  // drifting fog over the horizon
  for (let k = 0; k < 5; k++) {
    const fx = ((k * 380 + t * (14 + k * 5) - c.ry * 900) % 1700) - 300, fy = gy - 40 + k * 26;
    const fg = g.createRadialGradient(fx, fy, 0, fx, fy, 520);
    fg.addColorStop(0, `rgba(${120 + 60 * orbBright},${100 + 40 * orbBright},${86 + 20 * orbBright},.11)`); fg.addColorStop(1, 'rgba(0,0,0,0)');
    g.save(); g.translate(fx, fy); g.scale(1, 0.25); g.translate(-fx, -fy);
    g.fillStyle = fg; g.beginPath(); g.arc(fx, fy, 520, 0, Math.PI * 2); g.fill(); g.restore();
  }
}
// nearest ridge in front of the rising orb (intro only)
function frontRidge(t, c) {
  const g = $('fg').getContext('2d');
  g.clearRect(0, 0, W, H);
  const fade = 1 - P_(t, 4.4, 1.0);
  if (fade <= 0) return;
  const Zr = 1500, d = c.z - Zr;
  if (d < 200) return;
  g.globalAlpha = fade;
  g.beginPath(); g.moveTo(-10, H);
  for (let sx = -10; sx <= W + 10; sx += 10) {
    const X = (sx - W / 2) * d / P + c.x;
    const valley = 1 - Math.exp(-Math.pow(X / 900, 2));
    const h = 560 + 520 * valley + 90 * Math.sin(X * 0.004) + 40 * Math.sin(X * 0.013);
    g.lineTo(sx, H / 2 + (GROUND - h - c.y) * P / d);
  }
  g.lineTo(W + 10, H); g.closePath();
  const rf = g.createLinearGradient(0, H / 2, 0, H);
  rf.addColorStop(0, '#0b0a09'); rf.addColorStop(1, '#030303');
  g.fillStyle = rf; g.fill();
  g.strokeStyle = `rgba(255,200,140,${0.35 * clamp(t / 2)})`; g.lineWidth = 3; g.stroke();
  g.globalAlpha = 1;
}
function rays(g, x, y, r, a, t) {
  if (a <= 0.003) return;
  g.save(); g.translate(x, y); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 18; i++) {
    const ang = i / 18 * Math.PI * 2 + t * 0.1 + Math.sin(i * 7.3) * 0.2, w = 0.045 + 0.035 * Math.sin(i * 3.1 + t);
    const len = r * (0.7 + 0.5 * Math.abs(Math.sin(i * 1.7)));
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, len);
    gr.addColorStop(0, `rgba(255,225,180,${0.2 * a})`); gr.addColorStop(1, 'rgba(255,200,140,0)');
    g.fillStyle = gr; g.beginPath(); g.moveTo(0, 0); g.arc(0, 0, len, ang - w, ang + w); g.closePath(); g.fill();
  }
  const glow = g.createRadialGradient(0, 0, 0, 0, 0, r * 0.9);
  glow.addColorStop(0, `rgba(255,240,215,${0.5 * a})`); glow.addColorStop(0.25, `rgba(255,205,150,${0.2 * a})`); glow.addColorStop(1, 'rgba(0,0,0,0)');
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
function searchlights(g, t, a) {
  if (a <= 0.003) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [bx, ph] of [[180, 0], [900, 2.1]]) {
    const ang = -Math.PI / 2 + 0.38 * Math.sin(t * 0.9 + ph);
    const len = 2300, w = 0.075;
    const gr = g.createRadialGradient(bx, 1560, 0, bx, 1560, len);
    gr.addColorStop(0, `rgba(255,230,190,${0.22 * a})`); gr.addColorStop(1, 'rgba(255,220,180,0)');
    g.fillStyle = gr; g.beginPath(); g.moveTo(bx, 1560); g.arc(bx, 1560, len, ang - w, ang + w); g.closePath(); g.fill();
  }
  g.restore();
}

window.render = (t) => {
  const c = camera(t), focus = focusAt(t, c), sk = suck(t);
  const ov = view(c, 0, orbY(t), 0);
  const orbBright = t < 4 ? 0.25 + 0.75 * ioC(P_(t, 0.3, 3.7)) : (t >= 31.5 ? 0.3 : 1);
  const orbScreen = ov.vz > 60 ? proj(ov) : null;
  world(t, c, orbScreen, orbBright);
  frontRidge(t, c);
  for (const [id, pos] of Object.entries(OBJ)) {
    const el = $(id);
    let [X, Y, Z] = pos;
    if (id === 'orb') Y = orbY(t);
    if (id !== 'orb' && sk > 0) { X *= 1 - sk; Y *= 1 - sk; Z *= 1 - sk; }
    const v = view(c, X, Y, Z);
    let op = clamp((v.vz - 120) / 380) * clamp((16000 - v.vz) / 3500);
    const sh = SHOW[id]; if (sh) op *= P_(t, sh[0], 0.5);
    if (sk > 0 && id !== 'orb') op *= 1 - clamp((sk - 0.6) / 0.4);
    if (t >= 31.5 && id === 'orb') op = 0;
    if (t >= 27.8 && id !== 'orb') op = 0;
    if (op <= 0.001 || v.vz < 60) { el.style.display = 'none'; continue; }
    el.style.display = 'block';
    let sc = 1;
    if (id === 'orb') sc = (1 + 0.6 * oE(P_(t, 3.95, 0.5)) * (t < 4.5 ? 1 : 0)) * (1 + 0.8 * sk) * (1 + 0.03 * Math.sin(t * 6));
    if (id === 'orb2') sc = 0.45 * (1 + 0.05 * Math.sin(t * 5));
    if (id === 'sh') sc = 1 + 0.03 * Math.sin(t * 4);
    if (id !== 'orb' && sk > 0) sc *= 1 - 0.8 * sk;
    const blur = Math.min(18, Math.abs(v.vz - focus) * 0.0075);
    el.style.opacity = op;
    el.style.transform = `translate3d(${v.vx}px, ${v.vy}px, ${P - v.vz}px) scale(${sc})`;
    el.style.filter = (id === 'sh' ? 'drop-shadow(0 0 40px rgba(255,220,170,.55)) ' : '') + (blur > 0.4 ? `blur(${blur}px)` : '');
  }
  const reply = "Aaj 10 baje standup hai, 2 baje design review. Mausam 27° aur sunny ☀️ Pehle Bengaluru flights book kar lo.";
  const ws = reply.split(' ');
  $('kt').textContent = ws.slice(0, Math.round(P_(t, 6.0, 1.6) * ws.length)).join(' ');
  const fp = P_(t, 9.6, 1.8);
  $('fring').style.strokeDashoffset = 264 * (1 - 0.08 - 0.5 * fp);
  const secs = 25 * 60 - Math.floor(fp * 95);
  $('ftime').textContent = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;
  $('mprog').style.width = (30 + 25 * P_(t, 11, 2)) + '%';
  $('sweep').style.transform = `translateX(${-130 + 260 * ioC(P_(t, 24.0, 1.0))}%)`;

  // light
  const g = $('fx').getContext('2d');
  g.clearRect(0, 0, W, H);
  if (orbScreen && t < 31.5) rays(g, orbScreen.x, orbScreen.y, Math.min(2600, 1300 * orbScreen.s), orbBright * clamp((ov.vz - 150) / 500) * (1 + sk), t);
  const o2 = view(c, RING[0], 0, RING[1]);
  if (o2.vz > 60 && t > 11 && t < 30.5) { const p = proj(o2); rays(g, p.x, p.y, Math.min(1400, 700 * p.s), 0.6 * P_(t, 11, 1), t * 1.3); }
  const sv = view(c, ...OBJ.sh);
  if (sv.vz > 60 && t > 15 && t < 23) { const p = proj(sv); rays(g, p.x, p.y, Math.min(1500, 800 * p.s), 0.45 * P_(t, 15, 1), -t); }
  searchlights(g, t, P_(t, 22.6, 0.8) * (1 - P_(t, 27.2, 0.3)));
  let fl = 0, fx = W / 2, fy = H / 2;
  if (orbScreen) { fx = orbScreen.x; fy = orbScreen.y; }
  fl = Math.max(fl, Math.exp(-Math.max(0, t - 4.0) / 0.35) * (t >= 3.95 ? 1 : 0));
  const pass = 8 + (950 - 250) / 1400;
  fl = Math.max(fl, 0.9 * Math.exp(-Math.pow((t - pass) / 0.16, 2)));
  if (t >= 31.5) { fx = W / 2; fy = 790; fl = Math.max(fl, Math.exp(-(t - 31.5) / 0.5)); }
  flare(g, fx, fy, fl);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [X, Y, Z, k] of DUST) {
    const v = view(c, X * (1 - 0.5 * sk), Y, Z);
    if (v.vz < 40 || v.vz > 9000) continue;
    const p = proj(v);
    if (p.x < -200 || p.x > W + 200 || p.y < -200 || p.y > H + 200) continue;
    const near = v.vz < 700, r = near ? 18 + 60 * (1 - v.vz / 700) : Math.max(1.2, 3.2 * p.s);
    const a = (near ? 0.1 : 0.55) * clamp((9000 - v.vz) / 4000) * (0.5 + 0.5 * k);
    const gg = g.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
    gg.addColorStop(0, `rgba(255,225,185,${a})`); gg.addColorStop(near ? 0.7 : 0.4, `rgba(255,210,160,${a * 0.5})`); gg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gg; g.beginPath(); g.arc(p.x, p.y, r, 0, Math.PI * 2); g.fill();
  }
  g.restore();

  // titles
  const fade = (id, a, b, inD = 0.5, outD = 0.4, track = true) => {
    const el = $(id), pi = oE(P_(t, a, inD)), po = P_(t, b - outD, outD);
    const on = t >= a && t < b;
    el.style.opacity = on ? pi * (1 - po) : 0;
    el.style.letterSpacing = track ? (0.12 * (1 - pi)) + 'em' : '';
    el.style.transform = `translateY(${(1 - pi) * 20 - po * 20}px)`;
    el.style.filter = `blur(${(1 - pi) * 8 + po * 8}px)`;
  };
  fade('tA', 0.4, 2.3, 0.7, 0.35); fade('tB', 2.4, 4.0, 0.5, 0.25);
  fade('tC', 5.0, 8.0, 0.6, 0.35, false); fade('tC2', 6.2, 8.0, 0.6, 0.3, false);
  const words = [[8.35, 9.9, 'Your day.'], [9.95, 10.95, 'Your focus.'], [11.0, 11.65, 'Your notes.'], [11.7, 12.2, 'Your music.'],
                 [12.25, 12.75, 'Your apps.'], [12.8, 13.7, 'Your memory.']];
  const cur = words.find(([a, b]) => t >= a && t < b);
  if (cur) { $('tD').textContent = cur[2]; fade('tD', cur[0], cur[1], 0.3, 0.2); } else $('tD').style.opacity = 0;
  fade('tH', 14.6, 18.5, 0.7, 0.4, false);
  fade('tI', 19.7, 22.2, 0.6, 0.35, false); fade('tI2', 20.3, 22.2, 0.6, 0.35, false);
  fade('tE', 23.4, 25.9, 0.7, 0.3, false); fade('tF', 24.2, 25.9, 0.6, 0.3, false);
  // roast
  const rd = P_(t, 25.9, 0.15) * (1 - P_(t, 27.8, 0.2));
  $('roast').style.opacity = rd * 0.94;
  const ru = P_(t, 26.1, 0.3) * (1 - P_(t, 27.8, 0.2));
  $('rub').style.opacity = ru; $('rub').style.transform = `translateY(${(1 - oE(ru)) * 40}px)`;
  const rk = (t >= 26.9 ? 1 : 0) * (1 - P_(t, 27.8, 0.2)), slam = Math.exp(-Math.max(0, t - 26.9) / 0.12);
  $('rkb').style.opacity = rk; $('rkb').style.transform = `scale(${1 + 0.35 * slam * (t >= 26.9 ? 1 : 0)}) translate(${Math.sin(t * 90) * 14 * slam}px, 0)`;
  const sku = P_(t, 27.15, 0.3) * (1 - P_(t, 27.8, 0.2));
  $('skull').style.opacity = clamp(sku * 3); $('skull').style.transform = `scale(${2 - oE(sku)}) rotate(${10 - 20 * (1 - sku)}deg)`;
  // promises
  const lines = [[28.3, 'Free.'], [28.8, 'Open source.'], [29.3, 'Private by design.'], [29.8, 'Built for Windows.']];
  $('tG').innerHTML = lines.map(([a, s]) => { const q = oE(P_(t, a, 0.4)); return `<div style="opacity:${q};transform:translateY(${(1 - q) * 30}px);filter:blur(${(1 - q) * 10}px)">${s}</div>`; }).join('');
  $('tG').style.opacity = (t >= 28.2 ? 1 : 0) * (1 - P_(t, 30.4, 0.35));
  // logo
  const lg = t >= 31.5;
  $('logo').style.opacity = lg ? 1 : 0;
  if (lg) {
    const ps = $('lmk').querySelectorAll('path');
    ps[0].style.strokeDashoffset = 40 * (1 - ioC(P_(t, 31.5, 0.6))); ps[1].style.strokeDashoffset = 40 * (1 - ioC(P_(t, 31.7, 0.55)));
    const n = P_(t, 31.9, 0.8); $('lnm').style.opacity = n; $('lnm').style.letterSpacing = (0.6 - 0.4 * oE(n)) + 'em';
    $('lnm').style.backgroundPosition = `${100 - 100 * ioC(P_(t, 32.4, 1.0))}% 0`;
    $('lsb').style.opacity = P_(t, 32.4, 0.5);
    const l = P_(t, 32.8, 0.5); $('lpl').style.opacity = l; $('lpl').style.transform = `scale(${0.9 + 0.1 * oE(l)})`;
  }
  // flash, letterbox, grain, shake
  let f = 0;
  for (const [h, a, k] of [[4.0, 0.75, 0.12], [26.9, 0.5, 0.08], [31.5, 0.9, 0.15], [18.5, 0.25, 0.1], [22.0, 0.3, 0.1]]) f = Math.max(f, a * Math.exp(-Math.max(0, t - h) / k) * (t >= h ? 1 : 0));
  f = Math.max(f, 0.85 * Math.exp(-Math.pow((t - pass) / 0.09, 2)));
  $('flash').style.opacity = f;
  let lb = t < 4 ? 560 : lerp(560, 0, oE(P_(t, 4.0, 0.9)));
  lb = Math.max(lb, 300 * ioC(P_(t, 32.2, 1.2)));
  $('lbt').style.height = $('lbb').style.height = lb + 'px';
  const fr = Math.floor(t * 15);
  $('grain').style.transform = `translate(${(fr * 37) % 160 - 80}px, ${(fr * 61) % 160 - 80}px)`;
  let shk = 0;
  for (const h of [4.0, 8.0, 18.5, 26.9, 31.5]) if (t >= h) shk = Math.max(shk, 16 * Math.exp(-(t - h) / 0.2));
  if ((t >= 8 && t < 13.5) || (t >= 18.5 && t < 25.8) || (t >= 28 && t < 30.5)) shk = Math.max(shk, 3 * Math.exp(-((t % 0.5) / 0.1)));
  $('vp').style.transform = `translate(${Math.sin(t * 77) * shk}px, ${Math.cos(t * 59) * shk}px)`;
};
"""


# ── Score ────────────────────────────────────────────────────────────────────
rng = random.Random(34)
N = int(TOTAL * SR)


def hz(n):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    return 440 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def saws(freqs, length, cut, decay=0.0, attack=0.01, amp=0.2, detune=(-9, 9), drive=1.0):
    n = int(length * SR)
    vs = [(f * 2 ** (d / 1200), rng.random()) for f in freqs for d in detune]
    ph = [p for _, p in vs]
    inc = [f / SR for f, _ in vs]
    out, a1, a2 = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        s = 0.0
        for k in range(len(ph)):
            ph[k] = (ph[k] + inc[k]) % 1.0
            s += 2 * ph[k] - 1
        cc = cut(t)
        a1 += cc * (s - a1)
        a2 += cc * (a1 - a2)
        env = min(1, t / attack) * (math.exp(-t * decay) if decay else 1) * min(1, (length - t) / 0.1)
        x = a2 / len(ph) * 2.2 * env
        out.append(amp * (math.tanh(drive * x) / math.tanh(drive) if drive > 1 else x))
    return out


def braam(length=3.0, amp=0.55):
    b = saws([hz("A1"), hz("E2"), hz("A2"), hz("C3")], length, lambda t: 0.015 + 0.16 * (1 - math.exp(-t * 14)) * math.exp(-t * 1.6),
             attack=0.03, amp=amp, detune=(-14, 0, 14), drive=2.6)
    out, ph = [], 0.0
    for i, x in enumerate(b):
        t = i / SR
        ph += 2 * math.pi * (55 + 40 * math.exp(-t * 6)) / SR
        out.append(x + 0.5 * amp * math.sin(ph) * math.exp(-t * 1.2) * min(1, t * 200))
    return out


def taiko(amp=0.9):
    out, ph = [], 0.0
    for i in range(int(0.6 * SR)):
        t = i / SR
        ph += 2 * math.pi * (48 + 47 * math.exp(-t * 22)) / SR
        out.append(amp * math.tanh(2.0 * (math.sin(ph) * math.exp(-t * 6) + rng.uniform(-1, 1) * 0.35 * math.exp(-t * 60))))
    return out


def snare(amp=0.55):
    return [amp * (0.8 * rng.uniform(-1, 1) * math.exp(-i / SR * 14) + 0.5 * math.sin(2 * math.pi * 180 * i / SR) * math.exp(-i / SR * 24)) for i in range(int(0.35 * SR))]


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


def whoosh(length=0.6, amp=0.3):
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


def reverb(x, mix, fbs=1.0):
    out = [0.0] * len(x)
    for d, fb in ((1687, .84), (1601, .83), (2053, .85), (2251, .86), (1931, .84), (1777, .85)):
        buf = [0.0] * len(x)
        f = fb * fbs
        for i in range(len(x)):
            y = x[i] + (f * buf[i - d] if i >= d else 0)
            buf[i] = y
            out[i] += y * mix / 6
    return out


CHORDS = [["A2", "E3", "A3", "C4"], ["F2", "C3", "F3", "A3"], ["C3", "G3", "C4", "E4"], ["G2", "D3", "G3", "B3"]]
GAPS = [(7.85, 8.0), (25.85, 26.9)]


def in_gap(t):
    return any(a <= t < b for a, b in GAPS)


def make_score():
    big, drums, strings, air, fx = ([0.0] * N for _ in range(5))
    add(big, saws([hz("A1"), hz("E2")], TOTAL, lambda t: 0.004 + 0.012 * min(1, t / 6), attack=1.5, amp=0.22, detune=(-6, 6)), 0)
    for at, a, ln in ((0.3, 0.5, 3.0), (4.0, 0.75, 3.0), (18.5, 0.6, 2.5), (26.9, 0.65, 1.4), (31.5, 0.85, 2.5)):
        add(big, braam(ln, a), at)
    t = 1.0
    while t < 31.5:
        if not in_gap(t):
            add(fx, tick(0.13 if int(round(t * 4)) % 2 == 0 else 0.07), t)
        t += 0.25
    cache = {}

    def pl(f, bright=0.25):
        key = (f, bright)
        if key not in cache:
            cache[key] = saws([f], 0.16, lambda t: 0.06 + bright * math.exp(-t * 25), attack=0.004, decay=10, amp=0.16, detune=(-7, 7))
        return cache[key]

    # ostinato and pads, bar by bar (2 s bars from 4 s)
    for bar in range(14):
        t0 = 4.0 + bar * 2.0
        if t0 >= 31.5:
            break
        ch = CHORDS[bar % 4] if t0 >= 8 else CHORDS[0]
        brain = 14.5 <= t0 < 18.5
        notes = [hz(n) * (4 if brain else 2) for n in ch]
        for s in range(16):
            tt = t0 + s * 0.125
            if in_gap(tt) or tt >= 31.5:
                continue
            if brain and s % 2:
                continue
            g = 0.4 if tt < 8 else (0.55 if brain else (1.0 if tt >= 28 else 0.85))
            add(strings, pl(notes[[0, 2, 1, 3, 2, 1, 3, 2][s % 8]], 0.35 if tt >= 28 else 0.25), tt, g)
        if t0 >= 8 and not (25.8 <= t0 < 27.9):
            add(air if brain else strings, saws([hz(n) * (2 if brain else 1) for n in ch], 2.0, lambda t: 0.02 if not brain else 0.035, attack=0.3, amp=0.12, detune=(-8, 0, 8)), t0)
    # drums
    tk, sn = taiko(), snare()
    for start, end, mode in ((8.0, 14.4, "drive"), (14.5, 18.4, "half"), (18.5, 25.8, "drive"), (27.9, 31.5, "hard")):
        t, i = start, 0
        while t < end - 1e-6:
            pos = i % 8
            if mode == "half":
                if pos in (0, 4):
                    add(drums, tk, t, 0.75)
            else:
                if pos in (0, 3, 4, 6) or (mode == "hard" and pos in (1, 5, 7)):
                    add(drums, tk, t, 1.0 if pos in (0, 4) else 0.7)
                if pos in (2, 6):
                    add(drums, sn, t, 0.9)
            t += 0.25
            i += 1
    for r in range(8):
        add(drums, sn, 31.0 + r * 0.0625, 0.25 + 0.08 * r)
    for r in range(8):
        add(drums, sn, 13.4 + r * 0.125, 0.15 + 0.05 * r)
    # risers, impacts, whooshes, chimes
    for at, ln in ((1.5, 2.5), (5.6, 2.3), (16.4, 2.1), (29.2, 2.3)):
        add(fx, riser(ln, 0.3), at)
    for at, a in ((4.0, 0.9), (8.0, 1.0), (18.5, 0.8), (22.0, 0.7), (25.85, 0.6), (26.9, 0.9), (31.5, 1.0)):
        add(fx, impact(a), at)
    for k in range(13):
        add(fx, whoosh(0.5, 0.24), 8.0 + (700 + 700 * k * 0.5 + 200) / 1400 - 0.2 if k < 13 else 99)
    for at, ln in ((13.3, 1.2), (18.4, 1.3), (22.0, 1.0), (27.6, 3.0), (30.4, 1.2)):
        add(fx, whoosh(ln, 0.3), at)
    for k, at in enumerate((14.8, 15.5, 16.2, 16.9, 17.6)):
        add(fx, bell(hz(["E6", "A5", "C6", "G5", "E6"][k]), 1.6, 0.06), at)
    add(fx, bell(hz("A5")), 31.6)
    add(fx, bell(hz("E6"), amp=0.09), 31.7)
    for a, b in GAPS:
        for buf in (big, drums, strings, air):
            for i in range(int(a * SR), min(N, int(b * SR))):
                buf[i] *= 0.05
    wb, wd, ws, wa = reverb(big, 0.35), reverb([d * 0.6 for d in drums], 0.25, 0.97), reverb(strings, 0.3), reverb(air, 0.6)
    sfx_dry = [fx[i] + 0.55 * big[i] for i in range(N)]
    sfx_wet = reverb(sfx_dry, 0.3)
    sfx = [sfx_dry[i] + sfx_wet[i] for i in range(N)]
    left, right = [0.0] * N, [0.0] * N
    d1, d2 = int(0.375 * SR), int(0.5 * SR)
    for i in range(N):
        el = 0.22 * strings[i - d1] if i >= d1 else 0
        er = 0.22 * strings[i - d2] if i >= d2 else 0
        base = big[i] + drums[i] + fx[i] + wb[i] + wd[i] + ws[i] + wa[i] + air[i] * 0.6 + strings[i]
        left[i] = base + el
        right[i] = base + er
    fade = int(1.8 * SR)
    sfx_r = sfx[:]
    for ch in (left, right, sfx, sfx_r):
        for i in range(fade):
            ch[N - 1 - i] *= (i / fade) ** 1.3
        peak = max(1e-9, max(abs(x) for x in ch))
        for i in range(N):
            ch[i] = math.tanh(1.4 * ch[i] / peak) / math.tanh(1.4)
    return left, right, sfx, sfx_r


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
                               "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "8M", "-bufsize", "16M",
                               "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
        for i in range(frames):
            acc = None
            for k in range(SUB):
                tt = (i + k / SUB * 0.75) / FPS
                for attempt in range(4):              # the browser occasionally stalls; reload and retry
                    try:
                        pg.evaluate(f"window.render({tt})")
                        shot = pg.screenshot(type="jpeg", quality=95, timeout=120000)
                        break
                    except Exception as e:
                        print(f"  retry frame {i} ({e.__class__.__name__})", flush=True)
                        pg.reload()
                        pg.wait_for_load_state("networkidle")
                        pg.wait_for_timeout(1500)
                else:
                    raise RuntimeError(f"frame {i} failed")
                im = Image.open(io.BytesIO(shot)).convert("RGB")
                acc = im if acc is None else Image.blend(acc, im, 1 / (k + 1))
            buf = io.BytesIO()
            acc.save(buf, "JPEG", quality=94)
            ff.stdin.write(buf.getvalue())
            if i % 90 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        pg.evaluate("window.render(15.6)")
        pg.screenshot(path=str(OUT / "kalki_reel_epic_cover.png"))
        if errors:
            print("page errors:", errors[:3], flush=True)
        browser.close()
        ff.stdin.close()
        ff.wait()


def main():
    checks = [float(a) for a in sys.argv[1:] if not a.startswith("--")]
    silent = OUT / "kalki_reel_epic_silent.mp4"
    render_video(silent, checks)
    if "--checks-only" in sys.argv:
        return
    print("video done", flush=True)
    left, right, sl, sr = make_score()
    write_wav(TMP / "score.wav", left, right)
    write_wav(TMP / "sfx.wav", sl, sr)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(TMP / "sfx.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-20:TP=-2.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / "kalki_reel_epic_sfx.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(TMP / "score.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-13:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / "kalki_reel_epic.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(TMP / "score.wav"), "-af", "loudnorm=I=-13:TP=-1.0:LRA=11",
                    "-ar", "48000", str(OUT / "kalki_epic_score.wav")], check=True)
    print("done", TMP, flush=True)


if __name__ == "__main__":
    main()
