/** The single owner of GET /api/status.
 *
 *  This matters: `wakeRequested` is a one-shot flag the server clears on read,
 *  so exactly one poller may read it or wake events get lost. Everything else
 *  subscribes to the store rather than polling itself.
 *
 *  Polling policy replaces the old fixed 1.5s timer: 2s while a turn is in
 *  flight, 10s idle, fully suspended while the document is hidden, and an
 *  immediate revalidate on focus. */

import { system } from '../api/endpoints.js';
import { health } from '../api/client.js';
import { store, set, notify } from './store.js';

const ACTIVE_MS = 2000;
const IDLE_MS = 10000;
const OFFLINE_MS = 5000;

let timer = null;
let inflight = null;
let attending = 0;
let onVoiceExchange = null;
let lastSeq = -1;

export function onExchange(fn) { onVoiceExchange = fn; }

/** Derive the voice state from signals the backend actually reports.
 *  There is deliberately no `listening` state: listener.py does not report
 *  whether the microphone is capturing, and animating an unverified state
 *  would be a lie. */
function deriveVoice(s) {
  const now = Date.now();
  if (!s) return 'unavailable';
  if (store.conv.streaming) return 'thinking';
  if (s.speaking) return 'speaking';
  if (attending && now - attending < 4000) return 'attending';
  if (s.listenerPaused) return 'mic-released';
  if (s.listenerMicMuted) return 'mic-muted';
  return 'ready';
}

function ttsTrouble(s) {
  return Boolean(s && (s.ttsProbeError || s.ttsLastError));
}

async function tick() {
  if (inflight) return;
  inflight = system.status(document.hidden);
  const r = await inflight;
  inflight = null;

  if (!r.ok) {
    if (store.online) { store.online = false; notify(); }
    // Confirm with the cheap public probe before shouting about it.
    health().then((alive) => { if (alive !== store.online) { store.online = alive; notify(); } });
    return schedule();
  }

  if (!store.online) { store.online = true; notify(); }
  const s = r.data;
  if (s.wakeRequested) attending = Date.now();

  if (typeof s.conversationSeq === 'number') {
    if (lastSeq === -1) lastSeq = s.conversationSeq;
    else if (s.conversationSeq > lastSeq) {
      lastSeq = s.conversationSeq;
      if (s.recentExchange && onVoiceExchange) onVoiceExchange(s.recentExchange);
    }
  }

  store.status = s;
  store.voice.state = deriveVoice(s);
  store.voice.ttsTrouble = ttsTrouble(s);
  if (s.model && s.model !== store.models.current) store.models.current = s.model;
  notify();
  schedule();
}

function interval() {
  if (document.hidden) return 30000;
  if (!store.online) return OFFLINE_MS;
  if (store.conv.streaming || store.voice.sessionOpen) return ACTIVE_MS;
  if (store.status?.speaking) return ACTIVE_MS;
  if (attending && Date.now() - attending < 6000) return ACTIVE_MS;
  return IDLE_MS;
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(tick, interval());
}

export function startStatus() {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { clearTimeout(timer); tick(); }
  });
  window.addEventListener('focus', () => tick());
  tick();
}

/** Pull forward the next poll — used right after an action that changes state. */
export function refreshStatus() {
  clearTimeout(timer);
  tick();
}

export async function loadModels(force = false) {
  if (store.models.available.length && !force) return;
  set('models', { loading: true });
  const r = await system.models();
  set('models', { loading: false, available: r.ok ? (r.data.models || []) : [] });
}
