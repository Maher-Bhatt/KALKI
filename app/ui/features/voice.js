/** Voice mode: a calm full screen for talking to KALKI.
 *
 *  Everything on it is read from KALKI's real state: the listener's state, the microphone
 *  level, the last thing heard, and the actions KALKI recorded. When the voice listener
 *  isn't running, it says so instead of pretending to listen. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative } from '../lib/format.js';
import { store } from '../state/store.js';
import { system, activity } from '../api/endpoints.js';
import { refreshStatus } from '../state/status.js';
import { ok, err } from '../state/toasts.js';
import { go } from './router.js';

const STATES = [
  { id: 'ready', label: 'Ready' },
  { id: 'attending', label: 'Listening' },
  { id: 'thinking', label: 'Thinking' },
  { id: 'speaking', label: 'Speaking' },
];

const HEADLINES = {
  attending: "I'm listening…",
  thinking: 'Thinking…',
  speaking: 'Speaking…',
  ready: 'Say "Hey KALKI"',
  interrupted: 'Stopped',
  'mic-muted': 'The microphone is muted',
  'mic-released': 'The microphone is off',
  unavailable: 'Voice is off',
};

const SUGGESTIONS = [
  'What is on my schedule today?',
  'Remind me to stretch in 30 minutes',
  'How is my PC doing?',
  'Start a focus session',
];

let layer = null;
let parts = null;
let recent = [];
let returnFocus = null;

export function voiceModeOpen() {
  return !!layer;
}

function firstName() {
  const name = String(store.status?.owner || '').trim();
  return name && name !== 'YourName' ? name.split(/\s+/)[0] : '';
}

async function loadRecent() {
  const r = await activity.list();
  const items = r.ok ? (r.data.activities || r.data.items || []) : [];
  recent = items.slice(0, 4);
  if (layer) paintVoiceMode();
}

export function openVoiceMode(container) {
  if (layer) return;
  returnFocus = document.activeElement;
  store.voice.sessionOpen = true;
  refreshStatus();

  const bars = h('div.voice-wave', { 'aria-hidden': 'true' },
    ...Array.from({ length: 48 }, (_, i) => h('i', { ref: (el) => { el.style.setProperty('--i', String(i)); el.style.setProperty('--h', String((0.25 + 0.75 * Math.sin(Math.PI * i / 47)) * (0.45 + 0.55 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.45))))); } })));
  const headline = h('h1.voice-headline', { id: 'voice-title', tabindex: '-1' });
  const sub = h('p.voice-sub');
  const heard = h('div.voice-heard');
  const chips = h('div.voice-states', { role: 'list', 'aria-label': 'Voice states' });
  const mainBtn = h('button.voice-main', { type: 'button' });
  const recentList = h('div.voice-list');

  const close = () => closeVoiceMode();
  const typeInstead = () => {
    close();
    go('ask');
    setTimeout(() => document.querySelector('.comp textarea')?.focus(), 80);
  };

  layer = h('section.voice-mode', { role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'voice-title' },
    h('div.voice-center', null,
      h('span.voice-chip', null, icon('mic', 13), 'Voice mode'),
      bars,
      headline,
      sub,
      heard,
      chips,
      h('div.voice-controls', null,
        h('button.voice-round', { type: 'button', 'aria-label': 'Type instead', title: 'Type instead', onClick: typeInstead }, icon('edit', 18)),
        mainBtn,
        h('button.voice-round', { type: 'button', 'aria-label': 'Close voice mode', title: 'Close (Esc)', onClick: close }, icon('close', 18)),
      ),
    ),
    h('div.voice-side', null,
      h('section.voice-panel', null, h('h2', null, icon('clock', 15), 'Recent actions'), recentList),
      h('section.voice-panel', null, h('h2', null, icon('spark', 15), 'Try saying'),
        h('div.voice-list', null, ...SUGGESTIONS.map((text) =>
          h('button.voice-suggestion', {
            type: 'button',
            title: 'Run this now',
            onClick: async () => {
              const r = await system.command(text);
              if (r.ok) ok(r.data?.reply || 'Done');
              else err(r.message, r.detail);
            },
          }, `“${text}”`)))),
    ),
  );
  layer.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.preventDefault(); close(); } });

  parts = { bars, headline, sub, heard, chips, mainBtn, recentList };
  container.appendChild(layer);
  paintVoiceMode();
  loadRecent();
  headline.focus();
}

export function closeVoiceMode() {
  if (!layer) return;
  layer.remove();
  layer = null;
  parts = null;
  store.voice.sessionOpen = false;
  if (returnFocus instanceof HTMLElement && document.contains(returnFocus)) returnFocus.focus();
}

export function paintVoiceMode() {
  if (!layer || !parts) return;
  const st = store.status || {};
  const state = store.voice.state || 'unavailable';
  const online = !!st.listenerOnline;
  layer.dataset.state = state;
  parts.bars.style.setProperty('--lv', String(Math.max(0.35, Math.min(1, 0.35 + (Number(st.micLevel) || 0)))));

  parts.headline.textContent = HEADLINES[state] || HEADLINES.ready;
  const name = firstName();
  parts.sub.textContent = !online
    ? 'The voice listener isn\'t running. Turn on voice in Settings, or type instead.'
    : state === 'attending' ? `Go ahead${name ? `, ${name}` : ''}.` : 'Speak naturally, or press the button to start.';

  const last = st.recentExchange?.user;
  parts.heard.hidden = !last;
  if (last) mount(parts.heard, icon('mic', 14), h('span', null, `“${last}”`));

  mount(parts.chips, ...STATES.map((s) => h('span.voice-state', {
    role: 'listitem',
    'aria-current': s.id === state ? 'true' : null,
  }, h('i'), s.label)));

  const talking = state === 'attending' || state === 'thinking' || state === 'speaking';
  parts.mainBtn.disabled = !online;
  parts.mainBtn.setAttribute('aria-label', talking ? 'Stop' : 'Start listening');
  parts.mainBtn.title = talking ? 'Stop' : 'Start listening';
  mount(parts.mainBtn, icon(talking ? 'stop' : 'mic', 24));
  parts.mainBtn.onclick = async () => {
    const r = talking ? await system.stop() : await system.wake('');
    if (!r.ok) err(r.message, r.detail);
    refreshStatus();
  };

  mount(parts.recentList, ...(recent.length
    ? recent.map((a) => h('div.voice-recent', null,
      h('span', null, String(a.text || a.description || a.action || 'Action')),
      a.time || a.ts ? h('span.voice-time', null, relative(a.time || a.ts)) : null))
    : [h('p.voice-empty', null, 'Nothing yet. What KALKI does will show here.')]));
}
