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
  enabled: false,
  species: 'gobi',
  name: 'Gobi',
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

/* ── Species Character Designs & Pixel Sprites ─────────────────────── */

export const SPECIES_CONFIG = {
  gobi: {
    id: 'gobi',
    title: 'Gobi',
    desc: 'Pixel Sprite Chibi Companion (Flagship Mascot). Blushing cheeks and protective aura.',
    treat: '🍙 Pixel Riceball',
    sprite: 'assets/pets/gobi.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/gobi.png" class="pet-pixel-sprite" alt="Gobi" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  },
  kittu: {
    id: 'kittu',
    title: 'Kittu',
    desc: 'Cybernetic feline companion with reactive ears and neon whiskers.',
    treat: '🐟 Cyber Fish',
    sprite: 'assets/pets/kittu.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/kittu.png" class="pet-pixel-sprite" alt="Kittu" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  },
  byte: {
    id: 'byte',
    title: 'Byte',
    desc: 'Robo puppy with floppy cyber ears, holographic collar, and wagging tail.',
    treat: '🍖 Data Bone',
    sprite: 'assets/pets/byte.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/byte.png" class="pet-pixel-sprite" alt="Byte" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  },
  draco: {
    id: 'draco',
    title: 'Draco',
    desc: 'Cyber dragon with glowing wings, crest horns, and warm solar ember breath.',
    treat: '🔥 Solar Ember',
    sprite: 'assets/pets/draco.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/draco.png" class="pet-pixel-sprite" alt="Draco" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  },
  kitsu: {
    id: 'kitsu',
    title: 'Kitsu',
    desc: 'Twin-tailed cyber fox with mystical brow markings and keen ears.',
    treat: '🍬 Star Candy',
    sprite: 'assets/pets/kitsu.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/kitsu.png" class="pet-pixel-sprite" alt="Kitsu" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  },
  nova: {
    id: 'nova',
    title: 'Nova',
    desc: 'Levitating AI assistant drone with rotating optic ring and hover thrusters.',
    treat: '🔋 Quantum Battery',
    sprite: 'assets/pets/nova.png',
    svg(c) {
      return `
        <div class="pet-sprite-shell" style="position:relative; width:80px; height:80px; display:grid; place-items:center;">
          <div class="pet-aura" style="position:absolute; width:72px; height:72px; border-radius:50%; background:radial-gradient(circle, ${c}44 0%, transparent 70%);"></div>
          <img src="assets/pets/nova.png" class="pet-pixel-sprite" alt="Nova" style="width:72px; height:auto; image-rendering:pixelated; position:relative; z-index:2; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));" />
        </div>`;
    }
  }
};

// Aliases for backwards compatibility with any existing saved states
SPECIES_CONFIG.cat = SPECIES_CONFIG.kittu;
SPECIES_CONFIG.chibi = SPECIES_CONFIG.gobi;
SPECIES_CONFIG.dog = SPECIES_CONFIG.byte;
SPECIES_CONFIG.dragon = SPECIES_CONFIG.draco;
SPECIES_CONFIG.drone = SPECIES_CONFIG.nova;
SPECIES_CONFIG.fox = SPECIES_CONFIG.kitsu;

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
