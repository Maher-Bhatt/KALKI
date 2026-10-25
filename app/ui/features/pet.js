/** KALKI Companion Pet — Interactive AI Desk Mascot.
 *
 *  Features 5 distinct cyber companions:
 *  - Kittu (Cyber Cat)
 *  - Byte (Robo Pup)
 *  - Draco (Cyber Dragon)
 *  - Nova (Floating Drone Bot)
 *  - Kitsu (Twin-tailed Cyber Fox)
 *
 *  Reactive to KALKI chat lifecycle:
 *  - Typing -> alert / perked up
 *  - Streaming -> calculating / working (gears / bulb)
 *  - Complete -> happy celebration (hearts / stars)
 *  - Music -> jamming (notes / dancing)
 *  - Idle > 45s -> sleeping (z Z Z particles)
 *
 *  Interactive gameplay:
 *  - Petting (click pet) -> hearts + purr + XP
 *  - Feeding (treat menu) -> nom nom + happiness + XP
 *  - Play (laser ball) -> chase & fetch + level up
 *  - Customization (species, custom name, aura color, sound effects)
 *
 *  Zero external dependencies: 100% SVG, CSS keyframes, and Web Audio API. */

import { h, mount, frag } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { openDialog } from '../components/dialog.js';
import { ok } from '../state/toasts.js';

const STORAGE_KEY = 'kalki.pet.v1';

const DEFAULT_STATE = {
  enabled: true,
  species: 'cat',       // 'cat' | 'dog' | 'dragon' | 'drone' | 'fox'
  name: 'Kittu',
  color: '#fff4e2',     // Filament gold
  level: 1,
  xp: 0,
  xpNext: 100,
  happiness: 88,
  sound: true,
  perch: 'dock',        // 'dock' | 'float'
  lastFed: 0,
};

let state = loadPetState();
let activeReaction = 'idle'; // 'idle' | 'alert' | 'working' | 'happy' | 'jamming' | 'sleeping'
let idleTimer = null;
let bubbleTimer = null;
let currentMount = null;
let listenersBound = false;

/* ── State persistence ────────────────────────────────────────────────── */

export function loadPetState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_STATE, ...JSON.parse(raw) };
  } catch (e) {
    /* ignore parse errors */
  }
  return { ...DEFAULT_STATE };
}

export function savePetState(patch = {}) {
  state = { ...state, ...patch };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    /* ignore quota errors */
  }
  try {
    fetch('/api/pet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state)
    }).catch(() => {});
  } catch (e) {}
  updatePetDom();
  return state;
}

export function getPetState() {
  return state;
}

/* ── Web Audio Synthesizer (Cute 8-bit / cyber sound effects) ─────────── */

let audioCtx = null;
function getAudio() {
  if (!state.sound) return null;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  } catch (e) {
    return null;
  }
}

function playTone(freq, type = 'sine', duration = 0.1, delay = 0, gainLevel = 0.08) {
  const ctx = getAudio();
  if (!ctx) return;
  setTimeout(() => {
    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(gainLevel, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      /* ignore audio failure */
    }
  }, delay * 1000);
}

export function soundPetChirp() {
  playTone(523.25, 'triangle', 0.08, 0, 0.06);     // C5
  playTone(659.25, 'sine', 0.12, 0.07, 0.07);      // E5
  playTone(783.99, 'sine', 0.16, 0.14, 0.08);      // G5
}

export function soundPetPurr() {
  playTone(180, 'triangle', 0.12, 0, 0.05);
  playTone(190, 'triangle', 0.14, 0.08, 0.05);
  playTone(185, 'triangle', 0.16, 0.16, 0.04);
}

export function soundPetNom() {
  playTone(440, 'sine', 0.07, 0, 0.07);
  playTone(330, 'triangle', 0.09, 0.06, 0.06);
  playTone(550, 'sine', 0.1, 0.14, 0.07);
}

export function soundPetLevelUp() {
  playTone(440, 'triangle', 0.09, 0, 0.07);
  playTone(554.37, 'triangle', 0.09, 0.08, 0.07);
  playTone(659.25, 'triangle', 0.09, 0.16, 0.08);
  playTone(880, 'sine', 0.28, 0.24, 0.09);
}

/* ── Species SVG Character Designs ───────────────────────────────────── */

const SPECIES_CONFIG = {
  cat: {
    title: 'Kittu',
    desc: 'Cybernetic feline with reactive ears, twitching tail and neon whiskers.',
    treat: '🐟 Cyber Fish',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg cat-svg">
          <!-- Ears -->
          <polygon points="24,38 14,14 42,26" fill="${c}" opacity="0.85" class="pet-ear pet-ear-l" />
          <polygon points="26,34 20,20 38,28" fill="#ff76a5" opacity="0.6" />
          <polygon points="76,38 86,14 58,26" fill="${c}" opacity="0.85" class="pet-ear pet-ear-r" />
          <polygon points="74,34 80,20 62,28" fill="#ff76a5" opacity="0.6" />
          <!-- Tail -->
          <path d="M72 70 C88 64, 95 44, 88 32 C85 27, 78 30, 80 36 C84 46, 78 60, 66 65" 
                stroke="${c}" stroke-width="5" stroke-linecap="round" fill="none" class="pet-tail cat-tail" />
          <!-- Body -->
          <ellipse cx="50" cy="68" rx="28" ry="22" fill="#1e2329" stroke="${c}" stroke-width="2" />
          <!-- Head -->
          <ellipse cx="50" cy="46" rx="26" ry="22" fill="#262c33" stroke="${c}" stroke-width="2" class="pet-head" />
          <!-- Eyes -->
          <ellipse cx="38" cy="44" rx="4.5" ry="6" fill="${c}" class="pet-eye pet-eye-l" />
          <ellipse cx="62" cy="44" rx="4.5" ry="6" fill="${c}" class="pet-eye pet-eye-r" />
          <circle cx="39.5" cy="42" r="1.6" fill="#0d0f12" />
          <circle cx="63.5" cy="42" r="1.6" fill="#0d0f12" />
          <!-- Snout & Nose -->
          <polygon points="50,51 47,48 53,48" fill="#ff76a5" />
          <path d="M47 52 Q50 55 53 52" stroke="#b3bcc6" stroke-width="1.2" fill="none" />
          <!-- Whiskers -->
          <line x1="22" y1="47" x2="33" y2="48" stroke="${c}" stroke-width="1.2" opacity="0.75" />
          <line x1="20" y1="52" x2="32" y2="51" stroke="${c}" stroke-width="1.2" opacity="0.75" />
          <line x1="78" y1="47" x2="67" y2="48" stroke="${c}" stroke-width="1.2" opacity="0.75" />
          <line x1="80" y1="52" x2="68" y2="51" stroke="${c}" stroke-width="1.2" opacity="0.75" />
          <!-- Paws -->
          <ellipse cx="38" cy="84" rx="6.5" ry="4" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
          <ellipse cx="62" cy="84" rx="6.5" ry="4" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
        </svg>`;
    }
  },
  chibi: {
    title: 'Gobi',
    desc: 'Chibi Pixel Sprite companion inspired by Codex desktop pets.',
    treat: '🍙 Pixel Riceball',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg chibi-svg">
          <polygon points="25,32 30,16 42,28" fill="#5c3d22" stroke="${c}" stroke-width="2"/>
          <polygon points="75,32 70,16 58,28" fill="#5c3d22" stroke="${c}" stroke-width="2"/>
          <rect x="22" y="26" width="56" height="52" rx="14" fill="#9a7049" stroke="${c}" stroke-width="2.5"/>
          <rect x="30" y="44" width="40" height="28" rx="8" fill="#f5dec7" opacity="0.85"/>
          <ellipse cx="38" cy="48" rx="4.5" ry="6" fill="#1e1b18"/>
          <ellipse cx="62" cy="48" rx="4.5" ry="6" fill="#1e1b18"/>
          <circle cx="36.5" cy="45.5" r="1.8" fill="#ffffff"/>
          <circle cx="60.5" cy="45.5" r="1.8" fill="#ffffff"/>
          <ellipse cx="32" cy="54" rx="4" ry="2" fill="#ff7f7f" opacity="0.6"/>
          <ellipse cx="68" cy="54" rx="4" ry="2" fill="#ff7f7f" opacity="0.6"/>
          <path d="M47 52 Q50 55 53 52" fill="none" stroke="#331f0d" stroke-width="2" stroke-linecap="round"/>
          <rect x="28" y="74" width="16" height="12" rx="6" fill="#5c3d22" stroke="${c}" stroke-width="2"/>
          <rect x="56" y="74" width="16" height="12" rx="6" fill="#5c3d22" stroke="${c}" stroke-width="2"/>
        </svg>`;
    }
  },
  dog: {
    title: 'Byte',
    desc: 'Robo puppy with floppy cyber ears, holographic collar, and a wagging tail.',
    treat: '🍖 Data Bone',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg dog-svg">
          <!-- Tail -->
          <path d="M72 68 Q88 56 86 40 Q84 36 80 40 Q78 52 68 64" fill="${c}" class="pet-tail dog-tail" />
          <!-- Body -->
          <ellipse cx="50" cy="68" rx="27" ry="21" fill="#1e2329" stroke="${c}" stroke-width="2" />
          <!-- Floppy Ears -->
          <path d="M26 34 C16 34 14 58 22 62 C26 64 30 52 30 38 Z" fill="#2d343d" stroke="${c}" stroke-width="1.6" class="pet-ear dog-ear-l" />
          <path d="M74 34 C84 34 86 58 78 62 C74 64 70 52 70 38 Z" fill="#2d343d" stroke="${c}" stroke-width="1.6" class="pet-ear dog-ear-r" />
          <!-- Head -->
          <circle cx="50" cy="46" r="23" fill="#262c33" stroke="${c}" stroke-width="2" class="pet-head" />
          <!-- Eyes -->
          <ellipse cx="40" cy="44" rx="4" ry="5.5" fill="${c}" class="pet-eye pet-eye-l" />
          <ellipse cx="60" cy="44" rx="4" ry="5.5" fill="${c}" class="pet-eye pet-eye-r" />
          <circle cx="41.2" cy="42" r="1.5" fill="#0d0f12" />
          <circle cx="61.2" cy="42" r="1.5" fill="#0d0f12" />
          <!-- Nose & Tongue -->
          <ellipse cx="50" cy="50" rx="4" ry="3" fill="#0d0f12" stroke="${c}" stroke-width="1" />
          <path d="M48 53 Q50 56 52 53" stroke="${c}" stroke-width="1.2" fill="none" />
          <ellipse cx="50" cy="57" rx="2.5" ry="3.5" fill="#ff76a5" class="pet-tongue" />
          <!-- Collar -->
          <rect x="36" y="65" width="28" height="4" rx="2" fill="${c}" opacity="0.8" />
          <circle cx="50" cy="70" r="2.5" fill="#ffcc00" />
          <!-- Paws -->
          <ellipse cx="38" cy="85" rx="7" ry="4" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
          <ellipse cx="62" cy="85" rx="7" ry="4" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
        </svg>`;
    }
  },
  dragon: {
    title: 'Draco',
    desc: 'Cybernetic pocket dragon with pulsing wings, crest horns, and ember breath.',
    treat: '🔥 Solar Ember',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg dragon-svg">
          <!-- Wings -->
          <path d="M30 52 C12 36, 10 18, 28 28 C20 38, 24 46, 34 50 Z" fill="${c}" opacity="0.75" class="pet-wing pet-wing-l" />
          <path d="M70 52 C88 36, 90 18, 72 28 C80 38, 76 46, 66 50 Z" fill="${c}" opacity="0.75" class="pet-wing pet-wing-r" />
          <!-- Tail with Arrow tip -->
          <path d="M68 72 C82 72 90 60 84 48" stroke="${c}" stroke-width="3.5" fill="none" class="pet-tail dragon-tail" />
          <polygon points="84,48 80,40 90,44" fill="${c}" />
          <!-- Body -->
          <ellipse cx="50" cy="68" rx="25" ry="20" fill="#1c242c" stroke="${c}" stroke-width="2" />
          <!-- Dragon Chest Scales -->
          <path d="M44 64 Q50 67 56 64 M43 70 Q50 73 57 70" stroke="${c}" stroke-width="1.5" fill="none" opacity="0.8" />
          <!-- Horns -->
          <path d="M36 32 C30 16 20 18 24 28" stroke="${c}" stroke-width="3" stroke-linecap="round" fill="none" />
          <path d="M64 32 C70 16 80 18 76 28" stroke="${c}" stroke-width="3" stroke-linecap="round" fill="none" />
          <!-- Head -->
          <ellipse cx="50" cy="44" rx="23" ry="20" fill="#222b34" stroke="${c}" stroke-width="2" class="pet-head" />
          <!-- Eyes -->
          <polygon points="36,42 43,40 42,46 37,47" fill="${c}" class="pet-eye pet-eye-l" />
          <polygon points="64,42 57,40 58,46 63,47" fill="${c}" class="pet-eye pet-eye-r" />
          <circle cx="40" cy="43" r="1.2" fill="#0d0f12" />
          <circle cx="60" cy="43" r="1.2" fill="#0d0f12" />
          <!-- Snout with tiny spark nostrils -->
          <ellipse cx="50" cy="52" rx="10" ry="6" fill="#182028" stroke="${c}" stroke-width="1.2" />
          <circle cx="46" cy="52" r="1" fill="${c}" />
          <circle cx="54" cy="52" r="1" fill="${c}" />
        </svg>`;
    }
  },
  drone: {
    title: 'Nova',
    desc: 'Levitating AI assistant drone with rotating optic ring and hover thrusters.',
    treat: '🔋 Quantum Battery',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg drone-svg">
          <!-- Thruster Glows -->
          <ellipse cx="32" cy="74" rx="8" ry="3" fill="${c}" opacity="0.3" class="pet-thruster" />
          <ellipse cx="68" cy="74" rx="8" ry="3" fill="${c}" opacity="0.3" class="pet-thruster" />
          <!-- Antenna -->
          <line x1="50" y1="26" x2="50" y2="15" stroke="${c}" stroke-width="2" />
          <circle cx="50" cy="14" r="3" fill="${c}" class="pet-antenna-light" />
          <!-- Wing Rings / Thruster pods -->
          <ellipse cx="26" cy="52" rx="7" ry="14" fill="#1b2026" stroke="${c}" stroke-width="1.8" />
          <ellipse cx="74" cy="52" rx="7" ry="14" fill="#1b2026" stroke="${c}" stroke-width="1.8" />
          <!-- Spherical Body -->
          <circle cx="50" cy="52" r="25" fill="#242b33" stroke="${c}" stroke-width="2" class="pet-head" />
          <!-- Orbit Ring -->
          <ellipse cx="50" cy="52" rx="31" ry="9" stroke="${c}" stroke-width="1.5" stroke-dasharray="4,2" fill="none" opacity="0.75" class="drone-ring" />
          <!-- Holographic Visor -->
          <path d="M33 46 Q50 40 67 46 Q67 58 50 59 Q33 58 33 46 Z" fill="#0d1117" stroke="${c}" stroke-width="1.4" />
          <!-- Optical Sensor / Eye -->
          <circle cx="50" cy="50" r="5" fill="${c}" class="pet-eye" />
          <circle cx="50" cy="50" r="2" fill="#fff" />
          <!-- Status LED strip -->
          <rect x="42" y="66" width="16" height="2.5" rx="1.2" fill="${c}" opacity="0.8" />
        </svg>`;
    }
  },
  fox: {
    title: 'Kitsu',
    desc: 'Mystical twin-tailed cyber fox with sleek glowing brow markings and keen ears.',
    treat: '🍬 Star Candy',
    svg(c) {
      return `
        <svg viewBox="0 0 100 100" class="pet-svg fox-svg">
          <!-- Twin Tails -->
          <path d="M68 68 C86 64, 94 44, 86 28 C82 34, 76 46, 64 60" fill="${c}" opacity="0.9" class="pet-tail fox-tail-1" />
          <path d="M72 72 C92 70, 96 52, 90 38 C86 44, 80 54, 70 66" fill="#e08c33" opacity="0.65" class="pet-tail fox-tail-2" />
          <!-- Pointy Large Ears -->
          <polygon points="26,38 10,8 44,24" fill="#2d343d" stroke="${c}" stroke-width="1.8" class="pet-ear pet-ear-l" />
          <polygon points="26,32 18,16 38,24" fill="#e08c33" opacity="0.7" />
          <polygon points="74,38 90,8 56,24" fill="#2d343d" stroke="${c}" stroke-width="1.8" class="pet-ear pet-ear-r" />
          <polygon points="74,32 82,16 62,24" fill="#e08c33" opacity="0.7" />
          <!-- Body -->
          <ellipse cx="50" cy="70" rx="26" ry="20" fill="#1c2128" stroke="${c}" stroke-width="2" />
          <!-- Head / Mask -->
          <polygon points="50,65 24,40 28,30 72,30 76,40" fill="#262c33" stroke="${c}" stroke-width="2" class="pet-head" />
          <!-- White Cheeks -->
          <polygon points="50,63 26,42 36,46" fill="#f0f3f6" opacity="0.25" />
          <polygon points="50,63 74,42 64,46" fill="#f0f3f6" opacity="0.25" />
          <!-- Forehead Gem -->
          <polygon points="50,34 47,38 50,42 53,38" fill="${c}" />
          <!-- Eyes -->
          <ellipse cx="38" cy="42" rx="4" ry="3" transform="rotate(-10 38 42)" fill="${c}" class="pet-eye pet-eye-l" />
          <ellipse cx="62" cy="42" rx="4" ry="3" transform="rotate(10 62 42)" fill="${c}" class="pet-eye pet-eye-r" />
          <!-- Nose -->
          <circle cx="50" cy="62" r="2" fill="#0d0f12" />
          <!-- Paws -->
          <ellipse cx="38" cy="86" rx="6" ry="3.5" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
          <ellipse cx="62" cy="86" rx="6" ry="3.5" fill="#2d343d" stroke="${c}" stroke-width="1.2" />
        </svg>`;
    }
  }
};

/* ── Dialogue & Reactions ────────────────────────────────────────────── */

const DIALOGUES = {
  click: {
    cat: ['*purrrrrr*', 'Meow~ 💛', 'Purr-fect!', 'System: happy!'],
    dog: ['*wag wag*', 'Woof! Ready!', 'Beep-bark! 🐾', 'Good human!'],
    dragon: ['*tiny spark*', 'Rwwar! 🔥', 'Scale polish!', 'Warm flame!'],
    drone: ['Bloop-blip! ⚡', 'Core 100%!', 'Calibrated! 🤖', 'Telemetry: joy'],
    fox: ['Yip yip! ✨', 'Twin swish!', 'Mystic focus!', 'Sleek & ready!'],
  },
  feed: {
    cat: ['Chomp chomp! 🐟 Tasty bytes!', 'Nom nom nom~ Delicious!'],
    dog: ['Crunch crunch! 🍖 Best snack!', 'Gulp! Woof woof!'],
    dragon: ['Fwoosh! Solar fuel absorbed! 🔥', 'Crackling energy!'],
    drone: ['Charging capacitor... 🔋 100%!', 'Megawatts acquired!'],
    fox: ['Sweet star crunch! 🍬 Sparkling!', 'Mana replenished!'],
  },
  work: ['Calculating...', 'Crunching tokens...', 'Analyzing data...', 'Thinking hard!'],
  done: ['Boom! Answer ready! ✨', 'Done, Sir! 🎉', 'Processed cleanly!'],
  jam: ['Vibing to the beat! 🎵', 'Groovy frequencies! 🎶', 'Jam mode! 🎧'],
  sleep: ['Zzz...', 'Sleep mode...', 'Dreaming of electric sheep...'],
};

function getRandomDialogue(category) {
  const spec = state.species || 'cat';
  const list = DIALOGUES[category]?.[spec] || DIALOGUES[category] || ['Beep!'];
  return list[Math.floor(Math.random() * list.length)];
}

/* ── DOM Generation & Mount ───────────────────────────────────────────── */

let rootEl = null;
let speechBubbleEl = null;
let petSvgContainer = null;
let moodPillEl = null;
let xpBarEl = null;

export function createPetCompanion(container, options = {}) {
  currentMount = container;
  bindLifecycleListeners();

  rootEl = h('div.kalki-pet-dock', {
    dataset: { reaction: activeReaction, species: state.species },
    title: `${state.name} (Lvl ${state.level}) - Click to pet!`
  });

  if (!state.enabled) {
    rootEl.style.display = 'none';
  }

  // Speech bubble
  speechBubbleEl = h('div.pet-speech', null, 'Hello, Sir! ✨');

  // SVG character container
  petSvgContainer = h('div.pet-character-wrap', {
    onClick: handlePetClick,
    title: 'Click to pet!'
  });

  // Action bar buttons
  const feedBtn = h('button.pet-action-btn', {
    type: 'button',
    title: 'Feed treat',
    'aria-label': 'Feed treat',
    onClick: handleFeedClick
  }, icon('food', 13));

  const playBtn = h('button.pet-action-btn', {
    type: 'button',
    title: 'Play laser ball',
    'aria-label': 'Play laser ball',
    onClick: handlePlayClick
  }, icon('ball', 13));

  const configBtn = h('button.pet-action-btn', {
    type: 'button',
    title: 'Companion settings',
    'aria-label': 'Companion settings',
    onClick: openPetSettings
  }, icon('sliders', 13));

  const actionsRow = h('div.pet-actions-row', null, feedBtn, playBtn, configBtn);

  // Status & XP bar
  moodPillEl = h('span.pet-mood-pill', null, getMoodLabel());
  xpBarEl = h('div.pet-xp-meter', null, h('div.pet-xp-fill', { style: { width: `${(state.xp / state.xpNext) * 100}%` } }));

  const nameBadge = h('div.pet-badge-row', null,
    h('span.pet-name-txt', null, `${state.name} · Lvl ${state.level}`),
    moodPillEl
  );

  mount(rootEl,
    speechBubbleEl,
    petSvgContainer,
    nameBadge,
    xpBarEl,
    actionsRow
  );

  updatePetDom();
  resetIdleWatchdog();

  if (container) {
    container.appendChild(rootEl);
  }

  return {
    el: rootEl,
    setReaction: triggerPetReaction,
    feed: handleFeedClick,
    play: handlePlayClick,
    settings: openPetSettings,
    refresh: updatePetDom
  };
}

function updatePetDom() {
  if (!rootEl) return;
  rootEl.style.display = state.enabled ? 'flex' : 'none';
  rootEl.dataset.reaction = activeReaction;
  rootEl.dataset.species = state.species;
  rootEl.style.setProperty('--pet-aura', state.color || 'var(--fil)');

  const spec = SPECIES_CONFIG[state.species] || SPECIES_CONFIG.cat;
  if (petSvgContainer) {
    petSvgContainer.innerHTML = spec.svg(state.color || 'var(--fil)');
  }

  if (rootEl.querySelector('.pet-name-txt')) {
    rootEl.querySelector('.pet-name-txt').textContent = `${state.name} · Lvl ${state.level}`;
  }

  if (moodPillEl) {
    moodPillEl.textContent = getMoodLabel();
  }

  if (xpBarEl) {
    const fill = xpBarEl.querySelector('.pet-xp-fill');
    if (fill) fill.style.width = `${Math.min(100, Math.round((state.xp / state.xpNext) * 100))}%`;
  }
}

function getMoodLabel() {
  if (state.happiness >= 85) return 'Ecstatic ✨';
  if (state.happiness >= 65) return 'Happy 💛';
  if (state.happiness >= 40) return 'Content 🐾';
  return 'Tired 💤';
}

/* ── Interactive Actions ──────────────────────────────────────────────── */

export function triggerPetReaction(reaction, duration = 3000, bubbleText = null) {
  activeReaction = reaction;
  if (rootEl) rootEl.dataset.reaction = reaction;

  if (bubbleText) {
    showSpeech(bubbleText, duration);
  }

  resetIdleWatchdog();

  if (duration > 0 && reaction !== 'idle' && reaction !== 'sleeping') {
    setTimeout(() => {
      if (activeReaction === reaction) {
        activeReaction = 'idle';
        if (rootEl) rootEl.dataset.reaction = 'idle';
      }
    }, duration);
  }
}

function showSpeech(text, ms = 3000) {
  if (!speechBubbleEl) return;
  clearTimeout(bubbleTimer);
  speechBubbleEl.textContent = text;
  speechBubbleEl.classList.add('is-visible');
  bubbleTimer = setTimeout(() => {
    speechBubbleEl?.classList.remove('is-visible');
  }, ms);
}

function spawnParticle(type = 'heart', el = petSvgContainer) {
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const particle = document.createElement('div');
  particle.className = `pet-float-particle pet-particle-${type}`;
  particle.textContent = type === 'heart' ? '❤️' : (type === 'star' ? '✨' : (type === 'note' ? '🎵' : '💥'));
  particle.style.left = `${Math.random() * 40 + 20}px`;
  particle.style.top = '10px';
  el.appendChild(particle);
  setTimeout(() => particle.remove(), 1200);
}

function addXp(amount) {
  let xp = state.xp + amount;
  let level = state.level;
  let xpNext = state.xpNext;
  let leveledUp = false;

  while (xp >= xpNext) {
    xp -= xpNext;
    level += 1;
    xpNext = Math.round(xpNext * 1.35);
    leveledUp = true;
  }

  const happiness = Math.min(100, state.happiness + Math.round(amount / 2));
  savePetState({ xp, level, xpNext, happiness });

  if (leveledUp) {
    soundPetLevelUp();
    triggerPetReaction('happy', 4000, `LEVEL UP! 🌟 Lvl ${level}`);
    ok(`${state.name} leveled up to Level ${level}! 🎉`);
  }
}

function handlePetClick(e) {
  e?.stopPropagation();
  soundPetPurr();
  soundPetChirp();
  spawnParticle('heart');
  spawnParticle('star');
  addXp(3);
  triggerPetReaction('happy', 2500, getRandomDialogue('click'));
}

function handleFeedClick(e) {
  e?.stopPropagation();
  const spec = SPECIES_CONFIG[state.species] || SPECIES_CONFIG.cat;
  soundPetNom();
  spawnParticle('star');
  addXp(15);
  savePetState({ happiness: Math.min(100, state.happiness + 20), lastFed: Date.now() });
  triggerPetReaction('happy', 3000, `*Nom nom nom!* 😋 Ate ${spec.treat}!`);
}

function handlePlayClick(e) {
  e?.stopPropagation();
  triggerPetReaction('alert', 1500, 'Ball! Fetch! 🎾');
  soundPetChirp();

  // Create bouncing laser ball across chat area
  const ball = document.createElement('div');
  ball.className = 'pet-laser-ball';
  ball.textContent = '🎾';
  document.body.appendChild(ball);

  setTimeout(() => {
    soundPetChirp();
    spawnParticle('star');
    addXp(25);
    triggerPetReaction('happy', 3500, 'Caught it! Good play! 🏆 (+25 XP)');
    ball.remove();
  }, 1400);
}

function resetIdleWatchdog() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    if (activeReaction === 'idle') {
      activeReaction = 'sleeping';
      if (rootEl) rootEl.dataset.reaction = 'sleeping';
      showSpeech(getRandomDialogue('sleep'), 3000);
    }
  }, 45000); // 45 seconds idle
}

/* ── Global Event Listeners (React to user and KALKI) ─────────────────── */

function bindLifecycleListeners() {
  if (listenersBound) return;
  listenersBound = true;

  // React to typing in any textarea or input
  window.addEventListener('input', (e) => {
    if (activeReaction === 'sleeping') {
      activeReaction = 'idle';
      if (rootEl) rootEl.dataset.reaction = 'idle';
    }
    if (activeReaction === 'idle') {
      triggerPetReaction('alert', 1600);
    }
    resetIdleWatchdog();
  }, { passive: true });

  // React to user clicks & activity
  window.addEventListener('pointerdown', () => {
    if (activeReaction === 'sleeping') {
      activeReaction = 'idle';
      if (rootEl) rootEl.dataset.reaction = 'idle';
      showSpeech('Awake! ☀️', 2000);
    }
    resetIdleWatchdog();
  }, { passive: true });

  // Custom events
  window.addEventListener('kalki:stream-start', () => {
    triggerPetReaction('working', 0, getRandomDialogue('work'));
  });

  window.addEventListener('kalki:stream-end', () => {
    soundPetChirp();
    addXp(10);
    triggerPetReaction('happy', 3500, getRandomDialogue('done'));
  });

  window.addEventListener('kalki:music-play', () => {
    if (activeReaction !== 'working') {
      triggerPetReaction('jamming', 5000, getRandomDialogue('jam'));
    }
  });
}

/* ── Settings Dialog ─────────────────────────────────────────────────── */

export async function openPetSettings() {
  const current = getPetState();
  let selectedSpecies = current.species;
  let selectedColor = current.color;
  let enabledVal = current.enabled;
  let soundVal = current.sound;
  let nameInput = null;

  const colorOptions = [
    { label: 'Filament Gold', hex: '#fff4e2' },
    { label: 'Cyber Cyan', hex: '#00e5ff' },
    { label: 'Neon Purple', hex: '#c084fc' },
    { label: 'Matrix Green', hex: '#4cc061' },
    { label: 'Sunset Amber', hex: '#e08c33' },
    { label: 'Sakura Pink', hex: '#ff76a5' },
  ];

  const speciesGrid = h('div.pet-species-picker');
  
  const renderSpecies = () => {
    mount(speciesGrid, ...Object.entries(SPECIES_CONFIG).map(([id, info]) => {
      const isCur = id === selectedSpecies;
      return h('div.pet-species-card' + (isCur ? '.is-selected' : ''), {
        onClick: () => {
          selectedSpecies = id;
          renderSpecies();
        }
      },
        h('div.pet-species-preview', {
          ref: (el) => { el.innerHTML = info.svg(selectedColor); }
        }),
        h('div.pet-species-meta', null,
          h('div.t-title-2', null, info.title),
          h('div.t-meta', null, info.desc)
        )
      );
    }));
  };

  renderSpecies();

  const colorPills = h('div.row.wrap.g8', null,
    ...colorOptions.map((c) => {
      return h('button.pet-color-btn', {
        type: 'button',
        title: c.label,
        style: {
          width: '24px', height: '24px', borderRadius: '50%',
          background: c.hex,
          border: selectedColor === c.hex ? '2px solid #fff' : '1px solid var(--lst)',
          boxShadow: selectedColor === c.hex ? '0 0 8px ' + c.hex : 'none',
          cursor: 'pointer'
        },
        onClick: () => {
          selectedColor = c.hex;
          renderSpecies();
        }
      });
    })
  );

  nameInput = h('input.input', {
    type: 'text',
    value: current.name || 'Kittu',
    placeholder: 'Companion Name'
  });

  const togglePet = h('i.tg' + (enabledVal ? '.on' : ''), {
    style: { cursor: 'pointer' },
    onClick: (e) => {
      enabledVal = !enabledVal;
      e.currentTarget.classList.toggle('on', enabledVal);
    }
  });

  const toggleSound = h('i.tg' + (soundVal ? '.on' : ''), {
    style: { cursor: 'pointer' },
    onClick: (e) => {
      soundVal = !soundVal;
      e.currentTarget.classList.toggle('on', soundVal);
    }
  });

  const body = h('div.col.g16', null,
    h('div.row.sb', null,
      h('div', null,
        h('div.sm', null, 'Enable Companion Pet'),
        h('div.xs.mut', null, 'Show interactive AI desktop mascot in workspace')
      ),
      togglePet
    ),
    h('div.row.sb', null,
      h('div', null,
        h('div.sm', null, 'Companion Name'),
        h('div.xs.mut', null, 'Give your AI pet a personalized name')
      ),
      nameInput
    ),
    h('div.col.g8', null,
      h('div.sm', null, 'Species'),
      speciesGrid
    ),
    h('div.col.g8', null,
      h('div.sm', null, 'Aura & Eye Glow'),
      colorPills
    ),
    h('div.row.sb', null,
      h('div', null,
        h('div.sm', null, 'Sound Effects'),
        h('div.xs.mut', null, 'Play cute synthesized 8-bit chimes and purrs')
      ),
      toggleSound
    )
  );

  const res = await openDialog({
    title: 'Customize AI Companion Pet',
    description: 'Personalize your interactive desk pet, choose their species and aura color.',
    body,
    confirmLabel: 'Save Companion',
    cancelLabel: 'Cancel'
  });

  if (res) {
    const finalName = nameInput.value.trim() || SPECIES_CONFIG[selectedSpecies]?.title || 'Kittu';
    savePetState({
      enabled: enabledVal,
      species: selectedSpecies,
      name: finalName,
      color: selectedColor,
      sound: soundVal
    });
    ok(`Companion saved: ${finalName} (${SPECIES_CONFIG[selectedSpecies]?.title})`);
  }
}
