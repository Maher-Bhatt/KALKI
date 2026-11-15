/** Voice mode: a real back-and-forth conversation, like talking to a person.
 *
 *  KALKI listens through the app, notices when you stop talking, turns your words into
 *  text (Groq Whisper when you have a Groq key), answers through the same chat as typing,
 *  and speaks the reply sentence by sentence as it arrives. Then it listens again. Start
 *  talking while it speaks and it stops to listen (barge-in). Everything said shows as a
 *  transcript and is saved to your conversations.
 *
 *  While voice mode is open the background listener is paused, so only one thing listens. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { store } from '../state/store.js';
import { voice } from '../api/endpoints.js';
import { streamChat } from '../api/stream.js';
import { wireMessages } from '../state/conversations.js';
import { refreshStatus } from '../state/status.js';
import { err } from '../state/toasts.js';
import { go } from './router.js';

const SUGGESTIONS = ['What should I focus on today?', 'Play some music', 'Remind me to stretch in 30 minutes', 'Tell me something interesting'];

const STATUS = {
  starting: ['Starting…', 'Getting the microphone ready.'],
  listening: ['Listening', 'Go ahead, I’m listening.'],
  hearing: ['Listening', 'Keep going…'],
  thinking: ['Thinking', ''],
  speaking: ['Speaking', 'Talk any time to interrupt.'],
  muted: ['Microphone off', 'Press the microphone to talk again.'],
  error: ['Voice can’t start', ''],
};

/* ── Tuning ─────────────────────────────────────────────────────────────── */
const SILENCE_END_MS = 900;     // this much quiet after speech ends your turn
const MIN_SPEECH_MS = 350;      // shorter blips are ignored
const MAX_TURN_MS = 30000;
const PREROLL_FRAMES = 4;       // keep the start of the first word
const TARGET_RATE = 16000;

let layer = null;
let el = null;
let returnFocus = null;
let session = null;

export function voiceModeOpen() {
  return !!layer;
}

/* ── Audio helpers ──────────────────────────────────────────────────────── */

function rms(frame) {
  let sum = 0;
  for (let i = 0; i < frame.length; i += 1) sum += frame[i] * frame[i];
  return Math.sqrt(sum / frame.length);
}

function toWavBase64(frames, rate) {
  const total = frames.reduce((n, f) => n + f.length, 0);
  const merged = new Float32Array(total);
  let at = 0;
  for (const f of frames) { merged.set(f, at); at += f.length; }
  const ratio = rate / TARGET_RATE;
  const outLen = Math.floor(merged.length / ratio);
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(merged.length, Math.floor((i + 1) * ratio));
    let s = 0;
    for (let j = start; j < end; j += 1) s += merged[j];
    const v = Math.max(-1, Math.min(1, s / Math.max(1, end - start)));
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const v = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i += 1) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, TARGET_RATE, true); v.setUint32(28, TARGET_RATE * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, 'data'); v.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  const bytes = new Uint8Array(buf);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

/** Split finished sentences off the front of streaming text. */
function takeSentences(buffer) {
  const out = [];
  const re = /[^.!?\n।]+[.!?।]+["')\]]*\s+|[^\n]+\n+/g;
  let last = 0;
  let m;
  while ((m = re.exec(buffer))) {
    const s = m[0].trim();
    if (s.split(/\s+/).length >= 2 || s.length > 12) { out.push(s); last = re.lastIndex; }
  }
  return [out, buffer.slice(last)];
}

function speakable(text) {
  return String(text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[*_#>`~]/g, '')
    .replace(/\[(.*?)\]\(.*?\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

/* ── The conversation ───────────────────────────────────────────────────── */

function createSession() {
  const s = {
    state: 'starting', muted: false, transcript: [], partial: '',
    stream: null, ctx: null, node: null, src: null,
    recording: false, frames: [], preroll: [], speechMs: 0, quietMs: 0, startedAt: 0,
    noise: 0.008, level: 0, loudFrames: 0,
    queue: [], playing: null, chatAbort: null, turn: 0, listenerWasPaused: false, error: '',
  };

  s.set = (state, error = '') => { s.state = state; s.error = error; paint(); };

  /** Back to waiting: listening, muted, or still showing why the microphone can't start. */
  s.idle = () => (s.stream ? s.set(s.muted ? 'muted' : 'listening') : s.set('error', s.error));

  s.start = async () => {
    s.listenerWasPaused = !!store.status?.listenerPaused;
    if (!s.listenerWasPaused) voice.pause().catch(() => {});
    try {
      s.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
    } catch (e) {
      const why = e?.name === 'NotAllowedError'
        ? 'Microphone access was blocked. Allow it in Windows Settings > Privacy & security > Microphone (including "Let desktop apps access your microphone"), then try again.'
        : e?.name === 'NotFoundError' ? 'No microphone was found. Plug one in and try again.' : `The microphone couldn't start (${e?.message || e}).`;
      s.set('error', why);
      return;
    }
    s.ctx = new (window.AudioContext || window.webkitAudioContext)();
    s.src = s.ctx.createMediaStreamSource(s.stream);
    s.node = s.ctx.createScriptProcessor(4096, 1, 1);
    s.node.onaudioprocess = (ev) => s.onFrame(new Float32Array(ev.inputBuffer.getChannelData(0)));
    s.src.connect(s.node);
    s.node.connect(s.ctx.destination);
    s.set('listening');
  };

  s.onFrame = (frame) => {
    const level = rms(frame);
    const ms = (frame.length / s.ctx.sampleRate) * 1000;
    s.level = level;
    paintLevel(level);
    if (s.muted || s.state === 'error') return;

    if (!s.recording) {
      s.preroll.push(frame);
      if (s.preroll.length > PREROLL_FRAMES) s.preroll.shift();
      // Learn the room's background level while nobody is talking.
      if (s.state === 'listening') s.noise = s.noise * 0.95 + Math.min(level, 0.05) * 0.05;
    }

    const speakingNow = s.state === 'speaking';
    const threshold = speakingNow ? Math.max(0.045, s.noise * 6) : Math.max(0.018, s.noise * 3.2);

    if (!s.recording) {
      if (s.state !== 'listening' && !speakingNow) return;
      s.loudFrames = level > threshold ? s.loudFrames + 1 : 0;
      if (s.loudFrames >= (speakingNow ? 3 : 2)) {
        if (speakingNow) s.interrupt();
        s.recording = true;
        s.frames = [...s.preroll];
        s.speechMs = 0;
        s.quietMs = 0;
        s.startedAt = performance.now();
        s.set('hearing');
      }
      return;
    }

    s.frames.push(frame);
    if (level > threshold * 0.7) { s.speechMs += ms; s.quietMs = 0; } else { s.quietMs += ms; }
    if (s.quietMs >= SILENCE_END_MS || performance.now() - s.startedAt > MAX_TURN_MS) {
      const frames = s.frames;
      s.recording = false;
      s.frames = [];
      s.loudFrames = 0;
      if (s.speechMs < MIN_SPEECH_MS) { s.set('listening'); return; }
      s.finishTurn(toWavBase64(frames, s.ctx.sampleRate));
    }
  };

  s.finishTurn = async (wav) => {
    const turn = ++s.turn;
    s.set('thinking');
    const r = await voice.transcribe(wav);
    if (turn !== s.turn) return;
    const text = r.ok && r.data?.ok ? String(r.data.text || '').trim() : '';
    if (!text) {
      if (!(r.ok && r.data?.ok)) err("KALKI couldn't understand that", r.data?.error || r.message);
      s.set('listening');
      return;
    }
    s.ask(text);
  };

  s.ask = (text) => {
    const turn = ++s.turn;
    s.transcript.push({ role: 'user', text });
    s.transcript.push({ role: 'assistant', text: '' });
    const reply = s.transcript[s.transcript.length - 1];
    s.set('thinking');
    let pending = '';
    const controller = new AbortController();
    s.chatAbort = controller;
    const history = wireMessages().slice(-8);
    streamChat([...history, { role: 'user', content: text }], {
      clientSpeech: true,
      signal: controller.signal,
      extra: { voiceMode: true, source: 'voice-mode' },
      onToken: (token) => {
        if (turn !== s.turn) return;
        reply.text += token;
        pending += token;
        const [sentences, rest] = takeSentences(pending);
        pending = rest;
        sentences.forEach((x) => s.say(x, turn));
        paintTranscript();
      },
      onDone: (meta) => {
        if (turn !== s.turn) return;
        if (!reply.text && meta?.text) reply.text = meta.text;
        if (pending.trim()) s.say(pending.trim(), turn);
        pending = '';
        s.chatAbort = null;
        if (!s.queue.length && !s.playing) s.idle();
        paintTranscript();
        setTimeout(refreshStatus, 400);
      },
      onError: (e) => {
        if (turn !== s.turn) return;
        reply.text = reply.text || `Sorry, I couldn't answer that. ${e?.message || ''}`.trim();
        s.say(reply.text, turn);
        paintTranscript();
      },
    });
  };

  /** Fetch speech for one sentence now, play it in order. */
  s.say = (text, turn) => {
    const clean = speakable(text);
    if (!clean) return;
    const item = { text: clean, turn, audio: voice.speak(clean) };
    s.queue.push(item);
    if (!s.playing) s.playNext();
  };

  s.playNext = async () => {
    const item = s.queue.shift();
    if (!item) {
      s.playing = null;
      if (!s.chatAbort && !s.recording) s.idle();
      return;
    }
    if (item.turn !== s.turn) { s.playNext(); return; }
    s.playing = item;
    if (s.state !== 'hearing') s.set('speaking');
    const r = await item.audio;
    if (s.playing !== item) return;
    if (r.ok && r.data?.ok) {
      const audio = new Audio(`data:${r.data.mime || 'audio/mpeg'};base64,${r.data.audio}`);
      item.el = audio;
      audio.onended = () => { if (s.playing === item) s.playNext(); };
      audio.onerror = () => { if (s.playing === item) s.playNext(); };
      audio.play().catch(() => s.playNext());
    } else if ('speechSynthesis' in window) {
      // The natural voice service failed: Windows' own voice says it instead.
      const u = new SpeechSynthesisUtterance(item.text);
      item.utter = u;
      u.onend = () => { if (s.playing === item) s.playNext(); };
      u.onerror = () => { if (s.playing === item) s.playNext(); };
      speechSynthesis.speak(u);
    } else {
      s.playNext();
    }
  };

  /** Stop talking right now (you started speaking, or pressed stop). */
  s.interrupt = () => {
    s.turn += 1;
    s.chatAbort?.abort();
    s.chatAbort = null;
    s.queue = [];
    if (s.playing?.el) { s.playing.el.pause(); s.playing.el.src = ''; }
    if (s.playing?.utter) speechSynthesis.cancel();
    s.playing = null;
  };

  s.toggleMute = () => {
    s.muted = !s.muted;
    if (s.muted) { s.recording = false; s.frames = []; }
    s.stream?.getAudioTracks().forEach((t) => { t.enabled = !s.muted; });
    s.set(s.muted ? 'muted' : (s.playing ? 'speaking' : 'listening'));
  };

  s.stop = () => {
    s.interrupt();
    try { s.node?.disconnect(); s.src?.disconnect(); } catch { /* already gone */ }
    s.stream?.getTracks().forEach((t) => t.stop());
    s.ctx?.close().catch(() => {});
    if (!s.listenerWasPaused) voice.resume().catch(() => {});
  };

  return s;
}

/* ── Screen ─────────────────────────────────────────────────────────────── */

function firstName() {
  const name = String(store.status?.owner || '').trim();
  return name && name !== 'YourName' ? name.split(/\s+/)[0] : '';
}

function paintLevel(level) {
  if (!el) return;
  const scale = 1 + Math.min(0.45, level * 7);
  el.orb.style.setProperty('--lv', scale.toFixed(3));
}

function paintTranscript() {
  if (!el || !session) return;
  const items = session.transcript.slice(-12);
  mount(el.transcript, ...(items.length ? items.map((m) => h('div.vm-line.' + (m.role === 'user' ? 'is-you' : 'is-kalki'), null,
    h('span.vm-who', null, m.role === 'user' ? 'You' : 'KALKI'),
    h('p', null, m.text || '…'))) : [h('p.vm-empty', null, `Hi${firstName() ? ' ' + firstName() : ''}. Just start talking.`)]));
  el.transcript.scrollTop = el.transcript.scrollHeight;
}

function paint() {
  if (!el || !session) return;
  const [title, sub] = STATUS[session.state] || STATUS.listening;
  layer.dataset.state = session.state;
  el.title.textContent = title;
  el.sub.textContent = session.state === 'error' ? session.error : sub;
  mount(el.mic, icon(session.muted ? 'micOff' : 'mic', 22));
  el.mic.setAttribute('aria-label', session.muted ? 'Turn the microphone on' : 'Turn the microphone off');
  el.mic.title = session.muted ? 'Microphone on' : 'Microphone off';
  el.stopTalk.hidden = session.state !== 'speaking';
  el.retry.hidden = session.state !== 'error';
  paintTranscript();
}

/** Kept for the shell, which calls this when KALKI's status changes. */
export function paintVoiceMode() {
  paint();
}

export function openVoiceMode(container) {
  if (layer) return;
  returnFocus = document.activeElement;
  store.voice.sessionOpen = true;

  const orb = h('div.vm-orb', { 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const title = h('h1.vm-title', { id: 'voice-title', tabindex: '-1' });
  const sub = h('p.vm-sub', { role: 'status', 'aria-live': 'polite' });
  const transcript = h('div.vm-transcript', { 'aria-live': 'polite' });
  const mic = h('button.vm-round.vm-mic', { type: 'button', onClick: () => session?.toggleMute() });
  const stopTalk = h('button.btn.vm-stop', { type: 'button', hidden: true, onClick: () => { session?.interrupt(); session?.set('listening'); } }, icon('stop', 14), 'Stop talking');
  const retry = h('button.btn.pri', { type: 'button', hidden: true, onClick: () => { session?.stop(); session = createSession(); session.start(); } }, 'Try again');

  const close = () => closeVoiceMode();
  const typeInstead = () => {
    close();
    go('ask');
    setTimeout(() => document.querySelector('.comp textarea')?.focus(), 80);
  };

  layer = h('section.vm', { role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'voice-title' },
    h('header.vm-top', null,
      h('span.vm-chip', null, icon('mic', 13), 'Voice mode'),
      h('button.vm-round.sm', { type: 'button', 'aria-label': 'Close voice mode', title: 'Close (Esc)', onClick: close }, icon('close', 16))),
    h('div.vm-stage', null, orb, title, sub, stopTalk, retry),
    transcript,
    h('div.vm-suggest', null, ...SUGGESTIONS.map((text) => h('button.vm-pill', {
      type: 'button', onClick: () => { session?.interrupt(); session?.ask(text); },
    }, text))),
    h('footer.vm-controls', null,
      h('button.vm-round', { type: 'button', 'aria-label': 'Type instead', title: 'Type instead', onClick: typeInstead }, icon('edit', 18)),
      mic,
      h('button.vm-round.vm-end', { type: 'button', 'aria-label': 'End voice mode', title: 'End', onClick: close }, icon('close', 18))));
  layer.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    if (e.key === ' ' && e.target === layer) { e.preventDefault(); session?.toggleMute(); }
  });

  el = { orb, title, sub, transcript, mic, stopTalk, retry };
  container.appendChild(layer);
  session = createSession();
  paint();
  title.focus();
  session.start();
}

export function closeVoiceMode() {
  if (!layer) return;
  session?.stop();
  session = null;
  layer.remove();
  layer = null;
  el = null;
  store.voice.sessionOpen = false;
  refreshStatus();
  if (returnFocus instanceof HTMLElement && document.contains(returnFocus)) returnFocus.focus();
}

