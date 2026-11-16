"""KALKI launch Reel: a 20-second, 9:16 motion-graphics reel in the "code-built launch video" style.

KALKI's interface is rebuilt in HTML/SVG and animated frame by frame (orb, chat bubbles, briefing
cards, command bar, feature tiles), ending on the real app in a Windows 11 window. The music is an
original 120 BPM future-house track (chord stabs, arp, pumping bass, drums) with sound effects
synced to every pop, card and keystroke.
Run from the repo root:  python tools/marketing/make_reel_launch.py [check times in seconds...]
Writes marketing/video/reel_launch/.
"""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import array
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

SHOT = REPO / "marketing" / "store" / "screenshots" / "dark" / "3840x2160" / "03_today_briefing.png"
OUT = REPO / "marketing" / "video" / "reel_launch"
OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="kalki_launch_"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H = 30, 1080, 1920
BPM = 120
B = 60 / BPM            # 0.5 s per beat
TOTAL = 20.0
SR = 44100

MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path class="m1" d="M2.5 20 10 5.5 17.5 20"/><path class="m2" d="M9.5 20 15.2 9.6 21.5 20" opacity=".55"/></svg>')
ICON = {
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "bell": '<path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "note": '<path d="M5 4h10l4 4v12H5z"/><path d="M9 12h6M9 16h4"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
}
FEATURES = [("mic", "Talk naturally"), ("sun", "Daily briefing"), ("bell", "Smart reminders"),
            ("note", "Searchable notes"), ("shield", "Defender check-up"), ("chip", "Works offline")]
VOICE_REPLY = "Standup at 10, design review at 2, and it's 27° and sunny. Book those Bengaluru flights first."
ROAST_REPLY = "Useless? I've reminded you to drink water three times today and you're still dehydrated. 💀"
WINCAPS = ('<span><svg viewBox="0 0 10 10"><path d="M0 5h10" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9" rx="1.2" fill="none" stroke="currentColor" stroke-width=".9"/></svg></span>'
           '<span><svg viewBox="0 0 10 10"><path d="M.5 .5l9 9M9.5 .5l-9 9" stroke="currentColor" stroke-width=".9"/></svg></span>')


def words(text, em=()):
    out = []
    for w in text.split(" "):
        cls = ' class="em"' if w.strip(".,?!") in em else ""
        out.append(f'<span class="wm"><span class="wi"{cls}>{w}</span></span>')
    return " ".join(out)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#0d0c0b;color:#f5efe4;font-family:"Segoe UI Variable Text","Segoe UI",sans-serif}
#bg{position:absolute;inset:0}
.scene{position:absolute;inset:0;display:none}
.eyebrow{font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;font-weight:600;font-size:28px;letter-spacing:.34em;color:#9a9184;text-transform:uppercase}
.h{font-family:"Sitka Display","Sitka Heading","Palatino Linotype",Georgia,serif;font-weight:400;font-size:116px;line-height:1.04;letter-spacing:-.02em}
.h .em{font-style:italic;color:#efe4cf}
.wm{display:inline-block;overflow:hidden;vertical-align:top;padding:0 .02em .14em;margin-bottom:-.14em}
.wi{display:inline-block;will-change:transform}
.top{position:absolute;left:80px;right:80px;top:200px}
.center{position:absolute;left:70px;right:70px;text-align:center}
.orb{position:absolute;border-radius:50%;background:radial-gradient(circle at 38% 32%,#fffaf0 0%,#f1e6d1 42%,#c9b99c 100%);
  box-shadow:0 0 140px 40px rgba(239,228,207,.22),inset -18px -24px 60px rgba(120,100,70,.35)}
.ring{position:absolute;border-radius:50%;border:2px solid rgba(239,228,207,.5)}
.bars{position:absolute;display:flex;gap:10px;align-items:center;justify-content:center;height:90px}
.bars i{display:block;width:10px;border-radius:5px;background:#efe4cf}
.ub{position:absolute;right:80px;max-width:760px;background:#2c2a27;border:1.5px solid #3b3834;border-radius:38px 38px 12px 38px;padding:24px 34px;font-size:44px;font-weight:600;transform-origin:100% 100%}
.kb{position:absolute;left:80px;width:860px;background:#1b1a18;border:1.5px solid #34312c;border-radius:38px 38px 38px 12px;padding:28px 38px 34px;font-size:42px;line-height:1.36;transform-origin:0 100%}
.who{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:700;letter-spacing:.14em;color:#efe4cf;margin-bottom:10px}
.who svg{width:34px;height:34px}
.chip{display:inline-block;font-size:24px;font-weight:700;letter-spacing:.08em;padding:6px 16px;border-radius:999px;background:#efe4cf;color:#151413;margin-left:8px}
.cards{position:absolute;left:90px;right:90px;top:500px;perspective:1800px}
.card{position:relative;background:linear-gradient(180deg,#201e1b,#181715);border:1.5px solid #34312c;border-radius:34px;padding:30px 38px;margin-bottom:26px;
  box-shadow:0 40px 80px -36px rgba(0,0,0,.9);transform-origin:50% 0}
.card .lbl{font-size:24px;font-weight:700;letter-spacing:.2em;color:#9a9184;text-transform:uppercase;margin-bottom:12px}
.row{display:flex;align-items:center;gap:20px;font-size:36px;margin:10px 0}
.time{font-family:"Cascadia Mono",Consolas,monospace;font-size:28px;padding:6px 14px;border-radius:12px;background:#2b2926;color:#e6dfd3}
.box{width:34px;height:34px;border-radius:50%;border:2.5px solid #7d756a;flex:none;display:flex;align-items:center;justify-content:center}
.box svg{width:22px;height:22px}
.strike{position:relative}
.strike:after{content:"";position:absolute;left:0;top:54%;height:3px;background:#9a9184;width:var(--s,0%)}
.cmd{position:absolute;left:90px;right:90px;top:700px;height:130px;border-radius:65px;background:#1d1c1a;border:2px solid #3a3732;display:flex;align-items:center;gap:24px;padding:0 44px;font-size:46px;
  box-shadow:0 30px 80px -30px rgba(0,0,0,.9),0 0 0 8px rgba(239,228,207,.04)}
.cmd svg{width:54px;height:54px;color:#efe4cf;flex:none}
.caret{display:inline-block;width:4px;height:52px;background:#efe4cf;vertical-align:-8px;margin-left:3px}
.np{position:absolute;left:150px;right:150px;top:900px;border-radius:34px;background:#1b1a18;border:1.5px solid #34312c;padding:32px;display:flex;gap:30px;align-items:center}
.art{width:160px;height:160px;border-radius:22px;background:linear-gradient(135deg,#3b2f5c,#b5566b 55%,#e8a265);flex:none}
.eq{display:flex;gap:6px;align-items:flex-end;height:44px;margin-top:18px}
.eq i{display:block;width:8px;background:#efe4cf;border-radius:3px}
.prog{height:6px;border-radius:3px;background:#34312c;margin-top:18px;overflow:hidden}
.prog b{display:block;height:100%;background:#efe4cf;width:0}
.app{position:absolute;left:390px;top:1240px;width:300px;text-align:center;font-size:32px;color:#d9d1c4}
.app .tile{width:220px;height:220px;margin:0 auto 22px;border-radius:52px;background:linear-gradient(160deg,#3cd27a,#1c9e57);display:flex;align-items:center;justify-content:center;
  box-shadow:0 30px 70px -20px rgba(40,200,110,.45)}
.app .tile svg{width:120px;height:120px;color:#fff}
.stage3d{position:absolute;left:0;right:0;top:470px;height:800px;perspective:2200px}
.win{position:absolute;left:40px;width:1000px;border-radius:14px;overflow:hidden;border:1.5px solid #3a3631;background:#1b1a18;box-shadow:0 60px 120px -40px rgba(0,0,0,.95);transform-origin:50% 50%}
.win .bar{height:44px;display:flex;align-items:center;background:#23211e;border-bottom:1px solid #34312c;font-size:17px;color:#e6dfd3;padding-left:16px}
.win .bar .ttl{display:flex;align-items:center;gap:10px;flex:1}
.win .bar .ttl svg{width:20px;height:20px}
.win .bar .cap{display:flex;height:100%}
.win .bar .cap span{width:62px;display:flex;align-items:center;justify-content:center}
.win .bar .cap svg{width:13px;height:13px}
.win img{display:block;width:100%}
.shine{position:absolute;inset:0;background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.16) 50%,transparent 65%);transform:translateX(-120%)}
.grid{position:absolute;left:80px;right:80px;top:560px;display:grid;grid-template-columns:1fr 1fr;gap:28px}
.tile2{height:300px;border-radius:36px;background:linear-gradient(180deg,#201e1b,#181715);border:1.5px solid #34312c;padding:38px;display:flex;flex-direction:column;justify-content:space-between}
.tile2 svg{width:84px;height:84px;color:#efe4cf}
.tile2 div{font-size:40px;font-weight:600;line-height:1.15}
.prom{position:absolute;left:110px;right:80px;display:flex;align-items:center;gap:36px;font-family:"Sitka Display","Palatino Linotype",Georgia,serif;font-size:92px;line-height:1.05}
.prom svg{width:96px;height:96px;flex:none;color:#efe4cf}
.prom .c1{stroke-dasharray:63;stroke-dashoffset:63}
.prom .c2{stroke-dasharray:14;stroke-dashoffset:14}
.logo{position:absolute;left:0;right:0;top:620px;text-align:center}
.logo .mk{width:300px;height:300px;margin:0 auto;color:#efe4cf}
.logo .mk svg{width:100%;height:100%}
.logo .mk path{stroke-dasharray:40;stroke-dashoffset:40}
.logo .nm{font-family:"Segoe UI Variable Display","Segoe UI",sans-serif;font-weight:650;font-size:150px;letter-spacing:.2em;margin:40px 0 0 .2em}
.logo .sb{font-size:46px;color:#bfb5a6;margin-top:22px}
.logo .pl{display:inline-block;margin-top:64px;font-size:46px;font-weight:700;background:#efe4cf;color:#151413;padding:18px 50px 22px;border-radius:999px}
"""


def build_html():
    shot = SHOT.as_uri()
    bars = "".join("<i></i>" for _ in range(24))
    eq = "".join("<i></i>" for _ in range(12))
    tiles = "".join(f'<div class="tile2"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICON[i]}</svg><div>{t}</div></div>'
                    for i, t in FEATURES)
    check = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
             '<circle class="c1" cx="12" cy="12" r="10"/><path class="c2" d="M7.5 12.5l3 3 6-6.5"/></svg>')
    box = '<svg viewBox="0 0 24 24" fill="none" stroke="#151413" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
    body = f"""
<div id="bg"></div>
<div class="scene" id="s1">
  <div class="orb" id="o1"></div>
  <div class="center h" id="h1" style="top:1020px">{words("What if your PC")}<br>{words("could talk back?", em=("talk", "back"))}</div>
</div>
<div class="scene" id="s2">
  <div class="top"><div class="eyebrow e">Voice mode</div><div class="h" id="h2">{words("Just talk.", em=("talk",))}</div></div>
  <div class="ring" id="r1"></div><div class="ring" id="r2"></div><div class="ring" id="r3"></div>
  <div class="orb" id="o2"></div>
  <div class="bars" id="bars" style="left:0;right:0;top:960px">{bars}</div>
  <div class="ub" id="ub2" style="top:1120px">Hey KALKI, what's on today?</div>
  <div class="kb" id="kb2" style="top:1290px"><div class="who">{MARK}KALKI</div><span id="kt2"></span></div>
</div>
<div class="scene" id="s3">
  <div class="top"><div class="eyebrow e">Every morning</div><div class="h" id="h3">{words("Your day, briefed.", em=("briefed",))}</div></div>
  <div class="cards" id="cards">
    <div class="card"><div class="lbl">Weather · Bengaluru</div><div class="row" style="font-size:80px;font-family:'Segoe UI Variable Display','Segoe UI';font-weight:300">☀️ 27°<span style="font-size:32px;color:#9a9184;margin-left:14px">Sunny · H 30° L 21°</span></div></div>
    <div class="card"><div class="lbl">Calendar</div>
      <div class="row"><span class="time">10:00</span>Team standup</div><div class="row"><span class="time">14:00</span>Design review</div><div class="row"><span class="time">18:30</span>Gym with Kabir</div></div>
    <div class="card"><div class="lbl">Tasks · 4 open</div>
      <div class="row"><span class="box" id="tbox">{box}</span><span class="strike" id="tstrike">Finish the quarterly report</span></div>
      <div class="row"><span class="box"></span>Book flights to Bengaluru</div></div>
    <div class="card"><div class="lbl">Reminder</div><div class="row">💧 Stretch and drink water <span style="color:#9a9184;font-size:28px">· every day</span></div></div>
  </div>
</div>
<div class="scene" id="s4">
  <div class="top"><div class="eyebrow e">Hands-free</div><div class="h" id="h4">{words("Say it. Done.", em=("Done.",))}</div></div>
  <div class="cmd" id="cmd">{MARK}<span id="ct"></span><span class="caret" id="cc"></span></div>
  <div class="np" id="np"><div class="art"></div><div style="flex:1"><div style="font-size:40px;font-weight:600">Midnight Drive</div>
    <div style="font-size:30px;color:#9a9184;margin-top:4px">Lo-fi Lounge <span class="chip" style="font-size:20px">Apple Music</span></div>
    <div class="eq" id="eq">{eq}</div><div class="prog"><b id="pb"></b></div></div></div>
  <div class="app" id="app"><div class="tile"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18.5V7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H8z"/></svg></div>Opening WhatsApp…</div>
</div>
<div class="scene" id="s5">
  <div class="top"><div class="eyebrow e">Not a mockup</div><div class="h" id="h5">{words("This is KALKI.", em=("KALKI.",))}</div></div>
  <div class="stage3d"><div class="win" id="win"><div class="bar"><div class="ttl">{MARK}<span>KALKI</span></div><div class="cap">{WINCAPS}</div></div><img src="{shot}"><div class="shine" id="shine"></div></div></div>
  <div class="center" id="f5" style="top:1380px;font-size:40px;color:#bfb5a6">Real app. Real Windows. Running on your PC.</div>
</div>
<div class="scene" id="s6">
  <div class="top"><div class="eyebrow e">All in one</div><div class="h" id="h6">{words("Everything you need.", em=("need.",))}</div></div>
  <div class="grid" id="grid">{tiles}</div>
</div>
<div class="scene" id="s7">
  <div class="top"><div class="eyebrow e">Savage mode</div><div class="h" id="h7">{words("And if you're rude…", em=("rude…",))}</div></div>
  <div class="ub" id="ub7" style="top:760px">bro you're kinda useless ngl</div>
  <div class="kb" id="kb7" style="top:930px"><div class="who">{MARK}KALKI<span class="chip">SAVAGE</span></div><span id="kt7"></span></div>
  <div id="skull" style="position:absolute;left:820px;top:1330px;font-size:150px">💀</div>
</div>
<div class="scene" id="s8">
  <div class="prom" id="p1" style="top:640px">{check}<span>Free.</span></div>
  <div class="prom" id="p2" style="top:860px">{check}<span>Open source.</span></div>
  <div class="prom" id="p3" style="top:1080px">{check}<span>Your data stays<br>on your PC.</span></div>
</div>
<div class="scene" id="s9">
  <div class="logo"><div class="mk" id="lmk">{MARK}</div><div class="nm" id="lnm">KALKI</div>
    <div class="sb" id="lsb">Your AI assistant for Windows</div><div class="pl" id="lpl">Free · link in bio</div></div>
</div>
"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}<script>
const B = {B}, VREPLY = {json.dumps(VOICE_REPLY)}, RREPLY = {json.dumps(ROAST_REPLY, ensure_ascii=False)};
{JS}
</script></body></html>"""


JS = r"""
const $ = id => document.getElementById(id);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, d) => clamp((t - a) / d);
const oExpo = x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x);
const oCubic = x => 1 - Math.pow(1 - x, 3);
const ioCubic = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const oBack = (x, c = 1.7) => 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2);
const spring = x => x <= 0 ? 0 : 1 - Math.exp(-7 * x) * Math.cos(11 * x);
const beatPulse = (t, k = 0.12) => Math.exp(-((t % B) / k));
const SC = [[0, 2.1], [2, 5.1], [5, 8.1], [8, 10.1], [10, 12.1], [12, 14.1], [14, 16.1], [16, 18.1], [18, 20.1]];

function reveal(el, t, start, stagger = 0.07, dur = 0.55) {
  el.querySelectorAll('.wi').forEach((w, i) => {
    const p = oExpo(P(t, start + i * stagger, dur));
    w.style.transform = `translateY(${(1 - p) * 115}%)`;
  });
}
function exit(el, t, end, d = 0.22) {
  const p = ioCubic(P(t, end - d, d));
  el.style.opacity = 1 - p;
  el.style.transform = `translateY(${-70 * p}px) scale(${1 - 0.04 * p})`;
  el.style.filter = p > 0 ? `blur(${10 * p}px)` : 'none';
}
function pop(el, t, start, from = 0.7) {
  const p = P(t, start, 0.5);
  el.style.opacity = clamp(p * 4);
  const s = from + (1 - from) * spring(p * 1.1);
  el.style.transform = `translateY(${(1 - oExpo(p)) * 50}px) scale(${s})`;
}
function typeWords(el, text, t, a, b) {
  const ws = Array.from(text.split(' '));
  const n = Math.round(clamp((t - a) / (b - a)) * ws.length);
  el.textContent = ws.slice(0, n).join(' ');
}
function bg(t) {
  const x = 540 + 260 * Math.sin(t * 0.35), y = 760 + 300 * Math.cos(t * 0.27);
  const glow = 0.10 + (t >= 2 && t < 18 ? 0.05 * beatPulse(t, 0.18) : 0);
  $('bg').style.background = `radial-gradient(1100px 1100px at ${x}px ${y}px, rgba(239,228,207,${glow}), rgba(0,0,0,0) 70%),
    radial-gradient(900px 900px at ${1080 - x}px ${1920 - y}px, rgba(180,120,90,.07), rgba(0,0,0,0) 70%), #0d0c0b`;
}

window.render = (t) => {
  bg(t);
  SC.forEach(([a, b], i) => {
    const el = $('s' + (i + 1));
    const on = t >= a && t < b;
    el.style.display = on ? 'block' : 'none';
    if (on) { el.style.opacity = 1; el.style.transform = 'none'; el.style.filter = 'none'; if (i < 8) exit(el, t, b); }
  });

  // 1 · hook: the orb appears, the question builds word by word, then the orb flies on
  if (t < 2.1) {
    const o = $('o1');
    const g = spring(P(t, 0.05, 0.6));
    const fly = ioCubic(P(t, 1.75, 0.35));
    const size = 120 * g * (1 + 0.08 * beatPulse(t, 0.15)) * (1 + fly * 1.3);
    const cy = 720 + (640 - 720) * fly;
    o.style.width = o.style.height = size + 'px';
    o.style.left = (540 - size / 2) + 'px'; o.style.top = (cy - size / 2) + 'px';
    reveal($('h1'), t, 0.25, 0.1, 0.6);
    $('h1').style.opacity = 1 - P(t, 1.8, 0.2);
  }
  // 2 · voice: orb, rings and bars react to the beat; the conversation plays out
  if (t >= 2 && t < 5.1) {
    reveal($('h2'), t, 2.05);
    const size = 300 * (1 + 0.06 * beatPulse(t, 0.12)), cy = 640;
    const o = $('o2'); o.style.width = o.style.height = size + 'px'; o.style.left = (540 - size / 2) + 'px'; o.style.top = (cy - size / 2) + 'px';
    ['r1', 'r2', 'r3'].forEach((id, k) => {
      const ph = ((t - 2 + k * B / 3) % B) / B;
      const s = 300 + 420 * oCubic(ph);
      const r = $(id); r.style.width = r.style.height = s + 'px'; r.style.left = (540 - s / 2) + 'px'; r.style.top = (cy - s / 2) + 'px';
      r.style.opacity = 0.55 * (1 - ph);
    });
    const speaking = t > 2.95;
    $('bars').querySelectorAll('i').forEach((b, k) => {
      const n = Math.abs(Math.sin(t * 9 + k * 1.7) * Math.cos(t * 5.3 + k * 0.6));
      b.style.height = (10 + (speaking ? 70 : 26) * n * (0.5 + 0.5 * beatPulse(t, 0.2))) + 'px';
      b.style.opacity = 0.35 + 0.65 * n;
    });
    pop($('ub2'), t, 2.4);
    pop($('kb2'), t, 2.95);
    typeWords($('kt2'), VREPLY, t, 3.05, 4.5);
  }
  // 3 · briefing: cards fly in from depth on the beat; a task gets ticked
  if (t >= 5 && t < 8.1) {
    reveal($('h3'), t, 5.05);
    const cards = $('cards').querySelectorAll('.card');
    cards.forEach((c, k) => {
      const p = P(t, 5.2 + k * 0.4, 0.7);
      const e = oExpo(p);
      c.style.opacity = clamp(p * 3);
      c.style.transform = `translateY(${(1 - e) * 260}px) translateZ(${(1 - e) * -600}px) rotateX(${(1 - e) * 38 + 4}deg)`;
    });
    const tk = P(t, 7.05, 0.25);
    $('tbox').style.background = tk > 0 ? '#efe4cf' : 'transparent';
    $('tbox').style.borderColor = tk > 0 ? '#efe4cf' : '#7d756a';
    $('tbox').querySelector('svg').style.opacity = tk;
    $('tbox').style.transform = `scale(${1 + 0.35 * Math.sin(Math.PI * tk)})`;
    $('tstrike').style.setProperty('--s', (oCubic(P(t, 7.15, 0.35)) * 100) + '%');
    $('tstrike').style.color = tk > 0 ? '#8d857a' : '#ece6dc';
    $('cards').style.transform = `translateY(${-40 * P(t, 5, 3)}px)`;
  }
  // 4 · commands: "play some music" → now playing; "open WhatsApp" → app launches
  if (t >= 8 && t < 10.1) {
    reveal($('h4'), t, 8.02);
    const cmdIn = oExpo(P(t, 8.0, 0.4)); $('cmd').style.opacity = cmdIn; $('cmd').style.transform = `scale(${0.92 + 0.08 * cmdIn})`;
    const a = 'play some music', b2 = 'open WhatsApp';
    let txt = '';
    if (t < 9.0) txt = a.slice(0, Math.round(P(t, 8.12, 0.42) * a.length));
    else txt = b2.slice(0, Math.round(P(t, 9.08, 0.36) * b2.length));
    $('ct').textContent = txt;
    $('cc').style.opacity = Math.floor(t * 4) % 2 ? 1 : 0.2;
    const np = P(t, 8.7, 0.5);
    $('np').style.opacity = clamp(np * 3) * (1 - P(t, 9.5, 0.2) * 0.6);
    $('np').style.transform = `translateY(${(1 - oExpo(np)) * -80}px) scale(${0.9 + 0.1 * spring(np)})`;
    $('eq').querySelectorAll('i').forEach((b, k) => { b.style.height = (8 + 36 * Math.abs(Math.sin(t * 7 + k)) * (0.4 + 0.6 * beatPulse(t, 0.2))) + 'px'; });
    $('pb').style.width = (12 + 30 * P(t, 8.7, 1.4)) + '%';
    const ap = P(t, 9.55, 0.5);
    $('app').style.opacity = clamp(ap * 4);
    $('app').style.transform = `scale(${0.3 + 0.7 * spring(ap)})`;
  }
  // 5 · the real app swings into view in a Windows 11 window
  if (t >= 10 && t < 12.1) {
    reveal($('h5'), t, 10.6);
    const p = P(t, 10.0, 1.1), e = oExpo(p);
    const w = $('win');
    w.style.top = (60 + (1 - e) * 200) + 'px';
    w.style.transform = `rotateX(${(1 - e) * 48}deg) rotateY(${(1 - e) * -22}deg) rotateZ(${(1 - e) * 6}deg) scale(${0.62 + 0.38 * e})`;
    w.style.opacity = clamp(p * 4);
    $('shine').style.transform = `translateX(${-120 + 240 * ioCubic(P(t, 11.15, 0.6))}%)`;
    const f = P(t, 11.0, 0.5); $('f5').style.opacity = f; $('f5').style.transform = `translateY(${(1 - oExpo(f)) * 30}px)`;
  }
  // 6 · feature grid pops in on the half beats, with a highlight running through it
  if (t >= 12 && t < 14.1) {
    reveal($('h6'), t, 12.02);
    $('grid').querySelectorAll('.tile2').forEach((el, k) => {
      const p = P(t, 12.15 + k * 0.25, 0.55);
      el.style.opacity = clamp(p * 4);
      el.style.transform = `translateY(${(1 - oExpo(p)) * 120}px) scale(${0.85 + 0.15 * spring(p)})`;
      const hl = Math.exp(-Math.pow((t - (13.55 + k * 0.07)) / 0.08, 2));
      el.style.borderColor = `rgba(239,228,207,${0.18 + 0.7 * hl})`;
      el.style.boxShadow = `0 0 ${60 * hl}px rgba(239,228,207,${0.35 * hl})`;
    });
  }
  // 7 · savage mode: the roast
  if (t >= 14 && t < 16.1) {
    reveal($('h7'), t, 14.02);
    pop($('ub7'), t, 14.35);
    pop($('kb7'), t, 14.75);
    typeWords($('kt7'), RREPLY, t, 14.85, 15.6);
    const sk = P(t, 15.55, 0.4);
    $('skull').style.opacity = clamp(sk * 4);
    $('skull').style.transform = `scale(${2.2 - 1.2 * oBack(sk, 2.5)}) rotate(${(1 - sk) * -25 + 8}deg)`;
  }
  // 8 · promises, each ticked on the beat
  if (t >= 16 && t < 18.1) {
    ['p1', 'p2', 'p3'].forEach((id, k) => {
      const a = 16.0 + k * 0.5, p = P(t, a, 0.5), el = $(id);
      el.style.opacity = clamp(p * 4);
      el.style.transform = `translateX(${(1 - oExpo(p)) * 80}px)`;
      el.querySelector('.c1').style.strokeDashoffset = 63 * (1 - oCubic(P(t, a, 0.45)));
      el.querySelector('.c2').style.strokeDashoffset = 14 * (1 - oCubic(P(t, a + 0.15, 0.3)));
    });
  }
  // 9 · logo: the mark draws itself, the name settles, the call to action lands
  if (t >= 18) {
    const d1 = oCubic(P(t, 18.0, 0.55)), d2 = oCubic(P(t, 18.2, 0.5));
    const ps = $('lmk').querySelectorAll('path');
    ps[0].style.strokeDashoffset = 40 * (1 - d1); ps[1].style.strokeDashoffset = 40 * (1 - d2);
    $('lmk').style.transform = `scale(${1 + 0.06 * Math.exp(-Math.max(0, t - 18.6) / 0.15) * (t > 18.6 ? 1 : 0)})`;
    const n = P(t, 18.45, 0.6); $('lnm').style.opacity = n; $('lnm').style.letterSpacing = (0.55 - 0.35 * oExpo(n)) + 'em';
    const s = P(t, 18.85, 0.4); $('lsb').style.opacity = s; $('lsb').style.transform = `translateY(${(1 - oExpo(s)) * 24}px)`;
    const l = P(t, 19.1, 0.45); $('lpl').style.opacity = clamp(l * 3); $('lpl').style.transform = `scale(${0.8 + 0.2 * spring(l)})`;
  }
};
"""


# ── Music: an original 120 BPM future-house track, plus sound design ────────
rng = random.Random(1200)
N = int(TOTAL * SR)
S16 = B / 4


def nhz(n):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    return 440 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


CHORDS = {"Am": ["A3", "C4", "E4", "G4"], "F": ["F3", "A3", "C4", "E4"], "G": ["G3", "B3", "D4", "G4"], "Em": ["E3", "G3", "B3", "D4"]}
ROOT = {"Am": "A2", "F": "F2", "G": "G2", "Em": "E2"}
BARS = ["Am", "F", "G", "Em", "Am", "F", "F", "G", "Em", "Am"]          # 10 bars of 2 s
DROP = {1, 2, 3, 4, 6, 7, 8}


def supersaw(freqs, length, cutoff_hi, cutoff_lo, decay, attack=0.002, amp=0.18):
    n = int(length * SR)
    voices = [(f * 2 ** (c / 1200), rng.random()) for f in freqs for c in (-11, 0, 11)]
    phases = [p for _, p in voices]
    incs = [f / SR for f, _ in voices]
    out, lp, lp2 = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        s = 0.0
        for k in range(len(phases)):
            phases[k] = (phases[k] + incs[k]) % 1.0
            s += 2 * phases[k] - 1
        a = cutoff_lo + (cutoff_hi - cutoff_lo) * math.exp(-t * decay)
        lp += a * (s - lp)
        lp2 += a * (lp - lp2)
        env = min(1, t / attack) * (math.exp(-t * 3.2) if decay > 4 else 1.0)
        out.append(amp * lp2 * env / len(phases) * 3)
    return out


def sine_bass(f, length, amp=0.55):
    out, ph = [], 0.0
    for i in range(int(length * SR)):
        t = i / SR
        ph += 2 * math.pi * f / SR
        out.append(amp * math.tanh(1.8 * (math.sin(ph) + 0.3 * math.sin(2 * ph))) * min(1, t * 200) * math.exp(-t * 6))
    return out


def kick(amp=1.0):
    out, ph = [], 0.0
    for i in range(int(0.34 * SR)):
        t = i / SR
        ph += 2 * math.pi * (48 + 140 * math.exp(-t * 34)) / SR
        out.append(amp * math.tanh(1.8 * (math.sin(ph) * math.exp(-t * 8.5) + rng.uniform(-1, 1) * 0.25 * math.exp(-t * 900))))
    return out


def clap(amp=0.6):
    out, lp, prev = [], 0.0, 0.0
    for i in range(int(0.25 * SR)):
        t = i / SR
        x = rng.uniform(-1, 1)
        hp = x - prev
        prev = x
        lp += 0.55 * (hp - lp)
        env = sum(math.exp(-(t - d) * 240) for d in (0, .01, .02) if t >= d) * .8 + 0.5 * math.exp(-t * 15)
        out.append(amp * lp * env)
    return out


def hat(length=0.05, amp=0.2, decay=90):
    out, prev = [], 0.0
    for i in range(int(length * SR)):
        x = rng.uniform(-1, 1)
        out.append(amp * (x - prev) * math.exp(-i / SR * decay))
        prev = x
    return out


def snare(amp=0.4):
    return [amp * (0.7 * rng.uniform(-1, 1) * math.exp(-i / SR * 22) + 0.5 * math.sin(2 * math.pi * 210 * i / SR) * math.exp(-i / SR * 28))
            for i in range(int(0.15 * SR))]


def riser(length, amp=0.3):
    out, lp = [], 0.0
    n = int(length * SR)
    for i in range(n):
        p = i / n
        lp += (0.015 + 0.5 * p ** 2) * (rng.uniform(-1, 1) - lp)
        out.append(amp * p ** 2 * lp)
    return out


def impact(amp=0.9):
    out, lp, ph = [], 0.0, 0.0
    for i in range(int(1.2 * SR)):
        t = i / SR
        lp += 0.05 * (rng.uniform(-1, 1) - lp)
        ph += 2 * math.pi * (34 + 80 * math.exp(-t * 18)) / SR
        out.append(amp * math.tanh(1.4 * (math.sin(ph) * math.exp(-t * 3) + 1.3 * lp * math.exp(-t * 6))))
    return out


def whoosh(length=0.4, amp=0.28):
    out, lp = [], 0.0
    n = int(length * SR)
    for i in range(n):
        p = i / n
        env = math.sin(math.pi * p) ** 2
        lp += (0.02 + 0.3 * env) * (rng.uniform(-1, 1) - lp)
        out.append(amp * lp * env * 2.4)
    return out


def blip(f0=900, f1=420, length=0.09, amp=0.22):
    out, ph = [], 0.0
    for i in range(int(length * SR)):
        t = i / SR
        ph += 2 * math.pi * (f1 + (f0 - f1) * math.exp(-t * 40)) / SR
        out.append(amp * math.sin(ph) * math.exp(-t * 32))
    return out


def tick(amp=0.08):
    out, prev = [], 0.0
    for i in range(int(0.01 * SR)):
        x = rng.uniform(-1, 1)
        out.append(amp * (x - prev) * math.exp(-i / SR * 600))
        prev = x
    return out


def bell(f=880, length=2.2, amp=0.22):
    out = []
    for i in range(int(length * SR)):
        t = i / SR
        s = sum(a * math.sin(2 * math.pi * f * m * t) * math.exp(-t * d) for m, a, d in ((1, 1, 1.6), (2.0, .4, 2.4), (2.76, .25, 3.5), (5.4, .1, 6)))
        out.append(amp * s * min(1, t * 400))
    return out


def add(buf, sample, at, gain=1.0):
    s = int(at * SR)
    for i, x in enumerate(sample):
        j = s + i
        if 0 <= j < N:
            buf[j] += x * gain


def reverb(x, mix=0.25):
    out = [0.0] * len(x)
    for d, fb in ((1557, .82), (1617, .81), (1491, .83), (1422, .84), (1277, .8), (1356, .82)):
        buf = [0.0] * len(x)
        for i in range(len(x)):
            y = x[i] + (fb * buf[i - d] if i >= d else 0)
            buf[i] = y
            out[i] += y * mix / 6
    return out


def make_music():
    drums, music, bassb, fx = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
    side = [1.0] * N
    k, c, h, oh, sn = kick(), clap(), hat(), hat(0.22, 0.14, 14), snare()
    stab = {name: supersaw([nhz(n) for n in notes], 0.42, 0.55, 0.03, 9, amp=0.2) for name, notes in CHORDS.items()}
    pad = {name: supersaw([nhz(n) for n in notes], 2.1, 0.06, 0.06, 0, attack=0.25, amp=0.11) for name, notes in CHORDS.items()}
    arp_cache = {}

    def arp_note(f):
        if f not in arp_cache:
            arp_cache[f] = supersaw([f], 0.16, 0.45, 0.05, 22, amp=0.13)
        return arp_cache[f]

    for bar, ch in enumerate(BARS):
        t0 = bar * 4 * B
        drop = bar in DROP
        if bar in (0, 5, 9) or drop:
            add(music, pad[ch], t0, 0.8 if bar in (0, 5, 9) else 0.45)
        # arp: chord tones an octave up in 16ths (filtered in the intro)
        notes = [nhz(n) * 2 for n in CHORDS[ch]]
        order = [0, 1, 2, 3, 2, 1, 3, 2]
        for s in range(16):
            if bar == 9 and s > 3:
                break
            add(music, arp_note(notes[order[s % 8]]), t0 + s * S16, 0.55 if drop else 0.35)
        if drop:
            for s in (0, 3, 6, 10, 12):
                add(music, stab[ch], t0 + s * S16, 1.0 if bar < 6 else 1.15)
            for b in range(4):
                tb = t0 + b * B
                add(drums, k, tb)
                a = int(tb * SR)
                for j in range(int(0.22 * SR)):
                    if a + j < N:
                        side[a + j] = min(side[a + j], 1 - 0.7 * math.exp(-j / SR / 0.09))
                if b % 2:
                    add(drums, c, tb)
                add(drums, oh, tb + B / 2, 0.9)
                for s in range(4):
                    add(drums, h, tb + s * S16, 0.5 if s % 2 else 0.25)
                add(bassb, sine_bass(nhz(ROOT[ch]), 0.24), tb + B / 2)
                add(bassb, sine_bass(nhz(ROOT[ch]) / 2, 0.2, 0.35), tb + B / 2)
    # intro build, break build, impacts
    add(fx, riser(2.0, 0.3), 0.0)
    for r in range(8):
        add(drums, sn, 1.0 + r * 0.125, 0.15 + 0.06 * r)
    add(fx, impact(), 2.0)
    add(fx, riser(2.0, 0.34), 10.0)
    for r in range(12):
        add(drums, sn, 11.0 + r * (1 / 12), 0.12 + 0.05 * r)
    add(fx, impact(), 12.0)
    add(drums, k, 18.0)
    add(fx, impact(0.6), 18.0)
    # sound design synced to the picture
    for ts in (2, 5, 8, 10, 12, 14, 16, 18):
        add(fx, whoosh(0.36, 0.22), ts - 0.18)
    for ts, f in ((0.08, 700), (2.42, 880), (2.97, 660), (5.22, 740), (5.62, 830), (6.02, 930), (6.42, 1040),
                  (8.72, 880), (9.57, 990), (14.37, 880), (14.77, 660), (15.57, 520)):
        add(fx, blip(f, f * 0.5), ts)
    add(fx, blip(1400, 1200, 0.12, 0.2), 7.06)
    for i in range(12):
        add(fx, blip(700 + 60 * i, 500 + 60 * i, 0.07, 0.1), 12.17 + i * 0.125 if i < 6 else 99)
    for ts in (16.02, 16.52, 17.02):
        add(fx, blip(1320, 1320, 0.16, 0.16), ts)
        add(fx, blip(1760, 1760, 0.16, 0.12), ts + 0.06)
    for a, b2 in ((8.12, 8.54), (9.08, 9.44)):
        t = a
        while t < b2:
            add(fx, tick(rng.uniform(0.05, 0.1)), t)
            t += rng.uniform(0.03, 0.05)
    add(fx, whoosh(0.9, 0.3), 9.9)
    add(fx, bell(1046.5), 18.55)
    add(fx, bell(1318.5, amp=0.12), 18.6)

    wet = reverb([m for m in music], 0.3)
    left, right = [0.0] * N, [0.0] * N
    d1, d2 = int(3 * S16 * SR), int(4 * S16 * SR)
    for i in range(N):
        sc = side[i]
        m = music[i] * sc
        el = 0.25 * music[i - d1] * sc if i >= d1 else 0
        er = 0.25 * music[i - d2] * sc if i >= d2 else 0
        base = drums[i] + bassb[i] * sc + fx[i] + wet[i] * (0.6 + 0.4 * sc)
        left[i] = base + m + el
        right[i] = base + m + er
    fade = int(1.2 * SR)
    for ch in (left, right):
        for i in range(fade):
            ch[N - 1 - i] *= (i / fade) ** 1.5
        peak = max(1e-9, max(abs(x) for x in ch))
        for i in range(N):
            ch[i] = math.tanh(1.3 * ch[i] / peak) / math.tanh(1.3)
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
                           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "12M", "-bufsize", "24M",
                           "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
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
            ff.stdin.close()
            ff.wait()
            sys.exit(0)
        for i in range(frames):
            pg.evaluate(f"window.render({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=94))
            if i % 150 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        pg.evaluate("window.render(3.9)")
        pg.screenshot(path=str(OUT / "kalki_reel_launch_cover.png"))
        if errors:
            print("page errors:", errors[:3], flush=True)
        browser.close()
    ff.stdin.close()
    ff.wait()


def main():
    checks = [float(a) for a in sys.argv[1:] if not a.startswith("--")]
    silent = OUT / "kalki_reel_launch_silent.mp4"
    render_video(silent, checks)
    print("video done", flush=True)
    left, right = make_music()
    write_wav(TMP / "music.wav", left, right)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(TMP / "music.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-13:TP=-1.0:LRA=9", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / "kalki_reel_launch.mp4")], check=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(TMP / "music.wav"), "-af", "loudnorm=I=-13:TP=-1.0:LRA=9",
                    "-ar", "48000", str(OUT / "kalki_launch_track.wav")], check=True)
    print("done", TMP, flush=True)


if __name__ == "__main__":
    main()
