/** The KALKI pet: a small companion that shows what KALKI is doing at a glance.
 *
 *  It works like a status light with a personality. It tells you when KALKI is working,
 *  when it needs your approval and when it has finished, and nothing here pretends to
 *  be more than that. The characters live in pet_sprites.js, shared with the floating
 *  desktop window. */

import '../pet_sprites.js';
import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { openDialog } from '../components/dialog.js';
import { ok, err } from '../state/toasts.js';
import { store, subscribe } from '../state/store.js';
import { go } from './router.js';

const Pets = window.KalkiPets;
const STORAGE_KEY = 'kalki.pet.v1';
const DONE_MS = 4000;

const DEFAULTS = { enabled: true, species: 'gobi', name: 'Gobi', sound: false };

let state = loadPetState();
let audio = null;

export function loadPetState() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {};
  } catch { /* Storage may be blocked or damaged. The defaults are fine. */ }
  const merged = { ...DEFAULTS, ...saved };
  merged.species = Pets.normalize(merged.species);
  merged.name = String(merged.name || Pets.SPECIES[merged.species].name).slice(0, 24);
  return merged;
}

export function getPetState() {
  return state;
}

const changeListeners = new Set();

export function savePetState(patch = {}) {
  state = { ...state, ...patch };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* It still applies for this session. */ }
  fetch('/api/pet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ species: state.species, name: state.name, sound: state.sound, enabled: state.enabled }),
  }).catch(() => { /* The floating pet catches up the next time it can reach KALKI. */ });
  for (const fn of changeListeners) fn(state);
  return state;
}

function chirp(frequency) {
  if (!state.sound) return;
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = 'triangle';
    osc.frequency.value = frequency;
    gain.gain.setValueAtTime(0.06, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.14);
    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + 0.14);
  } catch { /* Sound is a nicety. */ }
}

/** What the rest of the app reports, turned into the pet's state. */
function currentInputs(doneUntil, lastActive) {
  const st = store.status || {};
  const playing = String(st.nowPlaying?.status || '').toLowerCase() === 'playing';
  return {
    pending: st.pendingApprovals || 0,
    working: !!store.conv?.streaming || st.listenerState === 'thinking',
    listening: st.listenerState === 'listening',
    doneRecently: Date.now() < doneUntil,
    music: playing,
    idleMs: Date.now() - lastActive,
  };
}

/** Mount the small pet in a screen. Returns a function that removes it. */
export function createPetCompanion(container) {
  const canvas = h('canvas.pet-canvas', { role: 'img' });
  const player = Pets.createPlayer(canvas, { species: state.species });
  const nameEl = h('span.pet-dock-name');
  const statusEl = h('span.pet-dock-status');
  const openBtn = h('button.pet-dock-btn', {
    type: 'button',
    title: 'Pet settings',
    onClick: () => {
      if (store.status?.pendingApprovals) go('oversight');
      else openPetSettings();
    },
  }, canvas);
  const dock = h('div.pet-dock', null, h('div.pet-dock-text', null, nameEl, statusEl), openBtn);
  container.appendChild(dock);

  let doneUntil = 0;
  let lastActive = Date.now();
  let wasStreaming = false;
  let shown = null;

  function refresh() {
    const streaming = !!store.conv?.streaming;
    if (wasStreaming && !streaming) doneUntil = Date.now() + DONE_MS;
    if (streaming) lastActive = Date.now();
    wasStreaming = streaming;

    dock.hidden = !state.enabled;
    const next = Pets.resolveState(currentInputs(doneUntil, lastActive));
    const label = Pets.LABELS[next];
    if (next !== shown) {
      if (next === 'waiting') chirp(660);
      if (next === 'done') chirp(880);
      shown = next;
    }
    dock.dataset.state = next;
    nameEl.textContent = state.name;
    statusEl.textContent = label;
    canvas.setAttribute('aria-label', `${state.name}: ${label}`);
    openBtn.title = next === 'waiting' ? 'Review what KALKI is asking' : 'Pet settings';
    player.set({ species: state.species, state: next });
  }

  const wake = () => { lastActive = Date.now(); };
  window.addEventListener('pointerdown', wake, { passive: true });
  window.addEventListener('keydown', wake, { passive: true });
  const unsubscribe = subscribe(refresh);
  changeListeners.add(refresh);
  const clock = setInterval(refresh, 1000);
  refresh();

  return () => {
    clearInterval(clock);
    unsubscribe();
    changeListeners.delete(refresh);
    window.removeEventListener('pointerdown', wake);
    window.removeEventListener('keydown', wake);
    player.destroy();
    dock.remove();
  };
}

/** Pick a pet: every character is shown moving, so the choice is the real thing. */
export function petPicker({ onChange } = {}) {
  const players = [];
  const grid = h('div.pet-picker', { role: 'radiogroup', 'aria-label': 'Choose a pet' });

  function paint() {
    players.splice(0).forEach((p) => p.destroy());
    mount(grid, ...Pets.IDS.map((id) => {
      const spec = Pets.SPECIES[id];
      const selected = state.species === id;
      const canvas = h('canvas.pet-canvas');
      players.push(Pets.createPlayer(canvas, { species: id, state: selected ? 'done' : 'idle' }));
      return h('button.pet-choice', {
        type: 'button',
        role: 'radio',
        'aria-checked': selected ? 'true' : 'false',
        onClick: () => {
          const renamed = state.name !== Pets.SPECIES[state.species].name;
          savePetState({ species: id, name: renamed ? state.name : spec.name });
          paint();
          onChange?.(state);
        },
      }, canvas, h('strong', null, spec.name), h('span', null, spec.blurb));
    }));
  }
  paint();
  return { el: grid, destroy: () => players.splice(0).forEach((p) => p.destroy()) };
}

export async function openPetSettings() {
  const picker = petPicker({ onChange: (s) => { nameInput.value = s.name; } });
  const nameInput = h('input.input', {
    type: 'text',
    maxlength: '24',
    value: state.name,
    'aria-label': 'Pet name',
    onChange: (e) => savePetState({ name: e.target.value.trim() || Pets.SPECIES[state.species].name }),
  });
  const soundBox = h('input', {
    type: 'checkbox',
    checked: state.sound,
    onChange: (e) => savePetState({ sound: e.target.checked }),
  });
  const shownBox = h('input', {
    type: 'checkbox',
    checked: state.enabled,
    onChange: (e) => savePetState({ enabled: e.target.checked }),
  });

  openDialog({
    title: 'Your pet',
    description: 'It shows when KALKI is working, needs your approval, or has finished.',
    width: '32rem',
    onClose: () => picker.destroy(),
    body: h('div.col.g16', null,
      picker.el,
      h('label.col.g4', null, h('span.sm', null, 'Name'), nameInput),
      h('label.row.g8', null, shownBox, h('span.sm', null, 'Show the pet in Ask')),
      h('label.row.g8', null, soundBox, h('span.sm', null, 'Play a soft sound when it needs you')),
    ),
  });
}

/** Show or hide the floating desktop pet. */
export async function setDesktopPet(enable, api) {
  const res = await api(enable);
  if (res && res.ok !== false) {
    ok((typeof res.running === 'boolean' ? res.running : enable) ? 'The pet is on your desktop' : 'The desktop pet is closed');
  } else {
    err(res?.error || "The desktop pet couldn't be changed");
  }
  return res;
}

export { icon as petIcon };
