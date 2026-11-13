/** KALKI's desktop pets: original pixel characters, drawn on a canvas.
 *
 *  This is a plain script, not a module, because the floating pet window loads its page
 *  from a file, where browsers block modules. The main app imports it for its side
 *  effect and reads window.KalkiPets, so both windows share one set of characters.
 *
 *  Each sprite is written as the left half of a 24-pixel-wide character and mirrored.
 *    .  empty     o  outline   b  body     s  shade    h  highlight   a  accent
 *    E  top of an eye          e  bottom of an eye
 *    T  shown on even frames   t  shown on odd frames (tails, wings, thrusters)
 */
(function (root) {
  'use strict';

  const SPECIES = {
    gobi: {
      name: 'Gobi', blurb: 'A calm rice ball', aura: '#fff4e2', tone: 520,
      colors: { o: '#3a3229', b: '#f6f0e2', s: '#d9cfba', h: '#fffdf7', a: '#2d4038', eye: '#2a2620', lid: '#f6f0e2' },
      rows: [
        '..........oo', '.........obb', '........obhb', '.......obhhb', '......obhhbb', '.....obbhbbb',
        '....obbbbbbb', '...obbbbbbbb', '...obbEEbbbb', '...obbeebbbb', '..obbbbbbbbo', '.obbbbbbbbbb',
        '.obbsssaaaaa', '.obbsaaaaaaa', '.obbsaaaaaaa', '..oosaaaaaaa', '....oooooooo',
      ],
    },
    kittu: {
      name: 'Kittu', blurb: 'A curious cat', aura: '#ffb0c8', tone: 680, oneTail: true,
      colors: { o: '#43291b', b: '#f6b26b', s: '#d98a43', h: '#ffe6c7', a: '#ff8fab', T: '#d98a43', eye: '#2b1a12', lid: '#f6b26b' },
      rows: [
        '..oo........', '..oao.......', '..oaao......', '..oaaooooooo', '..obbbbbbsbb', '.obhhbbbbsbb',
        '.obhbbbbbbbb', '.obbbEEbbbbb', '.obbbeebbbbb', '.obbbbbbbbba', '..obbbbbbboo', '...oobbbbbbb',
        '....oshhhhhh', '..T.oshhhhhh', '..T.obbhhhhh', '..t.obbhhhhh', '..t.obbobbbb', '....ooo.oooo',
      ],
    },
    byte: {
      name: 'Byte', blurb: 'A loyal robot pup', aura: '#7fe7dc', tone: 440, oneTail: true,
      colors: { o: '#18333b', b: '#67c9c1', s: '#17393f', h: '#b6f1e6', a: '#ffc24b', T: '#3d9a9e', eye: '#b8fff2', lid: '#17393f' },
      rows: [
        '...........a', '...........o', '....oooooooo', '...obhhbbbbb', '..obhbbbbbbb', 'ooaobsssssss',
        'oaaobsEEssss', 'oaaobseessss', 'oaaobsssssss', 'ooaobsssssoo', '..oobbbbbbbb', '...ooooooooo',
        '....obbbbbbb', '...oobhhhhaa', '..T.obhhhhhh', '..t.obbbbbbb', '....obbobbbb', '....ooo.oooo',
      ],
    },
    draco: {
      name: 'Draco', blurb: 'A small, warm dragon', aura: '#ffb27a', tone: 380,
      colors: { o: '#40190f', b: '#e8743f', s: '#c4552b', h: '#ffd79a', a: '#7ee0a0', T: '#7ee0a0', eye: '#2a0f08', lid: '#e8743f' },
      rows: [
        '....a.......', '....ao......', '....aooooooo', '...obbbbbbbb', '..obhbbbbbbb', 'TTobbbbbbbbb',
        'TTobbEEbbbbb', 'TTobbeebbbbb', 'ttobbbbbbbbb', 'tt.obbbbbboo', 'tt..oobbbbbb', '....obshhhhh',
        '...oobshhhhh', '...obbshhhhh', '....obbbhhhh', '....oabobbbb', '....ooo.oooo',
      ],
    },
    kitsu: {
      name: 'Kitsu', blurb: 'A clever two-tailed fox', aura: '#cbb0ff', tone: 600,
      colors: { o: '#2c1c4c', b: '#b48cf2', s: '#8c64d4', h: '#fff3fb', a: '#ffe08a', T: '#8c64d4', eye: '#20123c', lid: '#b48cf2' },
      rows: [
        '..o.........', '..oao.......', '..oaaoo.....', '..oaabbooooo', '..obbbbbbbbb', '.obbbbbbbbbb',
        '.obbbEEbbbbb', '.obbbeebbbbb', '.ohhhhhhhhha', '..ohhhhhhhoo', '...oohhhhhhh', 'T...obbhhhhh',
        'aT..obbhhhhh', 'at.oobbbhhhh', '.ttoobbbbbbb', '..ssobbobbbb', '....ooo.oooo',
      ],
    },
    nova: {
      name: 'Nova', blurb: 'A little hover drone', aura: '#9cf5b8', tone: 760,
      colors: { o: '#232c40', b: '#e8edf5', s: '#1c2638', h: '#ffffff', a: '#7bf0a0', T: '#7bf0a0', eye: '#7bf0a0', lid: '#1c2638' },
      rows: [
        '...........o', '...........a', '......oooooo', '....oohhbbbb', '...ohhbbbbbb', '..ohbbbbbbbb',
        '.ohbbbbbbbbb', '.obossssssss', '.obosssEEsss', '.obosssEEsss', '.obossssssss', '.obboooooooo',
        '..obbbbbbbbb', '...obbbbbbbb', '....obbbbbbb', '......oooooo', '........T..T', '.........t.t',
      ],
    },
  };

  const IDS = Object.keys(SPECIES);
  const OLD_NAMES = { cat: 'kittu', chibi: 'gobi', dog: 'byte', dragon: 'draco', drone: 'nova', fox: 'kitsu' };

  const LABELS = {
    idle: 'Ready',
    working: 'Working on it',
    waiting: 'Needs your approval',
    done: 'Done',
    listening: 'Listening',
    music: 'Enjoying the music',
    asleep: 'Resting',
  };

  /* Small pictures drawn beside the pet's head to show what it's doing. */
  const GLYPHS = {
    alert: ['.##.', '.##.', '.##.', '.##.', '....', '.##.'],
    spark: ['..#..', '.###.', '#####', '.###.', '..#..'],
    note: ['..##', '..#.', '..#.', '###.', '###.'],
    z: ['####', '..#.', '.#..', '####'],
    dot: ['##', '##'],
    wave: ['#.', '.#', '.#', '#.'],
  };

  const FX_COLORS = { alert: '#ffb347', spark: '#ffe08a', note: '#fff4e2', z: '#c7d2e0', dot: '#fff4e2', wave: '#7bf0a0' };

  const SIZE = 32;

  function normalize(id) {
    const clean = String(id || '').toLowerCase();
    const known = OLD_NAMES[clean] || clean;
    return SPECIES[known] ? known : 'gobi';
  }

  /** Which state to show. The order is the order of importance: a request for approval
   *  must never be hidden behind music or a sleeping pet. */
  function resolveState({ pending = 0, working = false, listening = false, doneRecently = false, music = false, idleMs = 0 } = {}) {
    if (pending > 0) return 'waiting';
    if (working) return 'working';
    if (listening) return 'listening';
    if (doneRecently) return 'done';
    if (music) return 'music';
    if (idleMs > 5 * 60 * 1000) return 'asleep';
    return 'idle';
  }

  function eyeFor(ch, state, tick, colors) {
    const closed = state === 'asleep' || (state === 'idle' && tick % 26 === 25);
    if (state === 'done') return ch === 'E' ? colors.eye : colors.lid; // A happy, arched eye.
    if (closed) return ch === 'E' ? colors.lid : colors.eye;
    return colors.eye;
  }

  function offsets(state, tick) {
    if (state === 'working') return { x: 0, y: tick % 4 < 2 ? 0 : -1 };
    if (state === 'waiting') return { x: 0, y: tick % 10 === 0 ? -1 : 0 };
    if (state === 'done') return { x: 0, y: [0, -1, -2, -1][tick % 4] };
    if (state === 'music') return { x: [0, 1, 0, -1][tick % 4], y: tick % 2 ? -1 : 0 };
    if (state === 'asleep') return { x: 0, y: tick % 16 < 8 ? 1 : 0 };
    return { x: 0, y: tick % 12 < 6 ? 0 : -1 };
  }

  function drawGlyph(ctx, name, x, y) {
    ctx.fillStyle = FX_COLORS[name];
    GLYPHS[name].forEach((row, dy) => {
      for (let dx = 0; dx < row.length; dx += 1) {
        if (row[dx] === '#') ctx.fillRect(x + dx, y + dy, 1, 1);
      }
    });
  }

  function drawEffect(ctx, state, tick) {
    if (state === 'waiting') {
      if (tick % 6 < 4) drawGlyph(ctx, 'alert', 27, 1);
    } else if (state === 'working') {
      for (let i = 0; i < 3; i += 1) {
        if (tick % 6 >= i * 2) drawGlyph(ctx, 'dot', 22 + i * 3, 2);
      }
    } else if (state === 'done') {
      drawGlyph(ctx, 'spark', 26, tick % 4 < 2 ? 1 : 3);
      if (tick % 4 >= 2) drawGlyph(ctx, 'spark', 1, 3);
    } else if (state === 'music') {
      drawGlyph(ctx, 'note', 26, 4 - (tick % 4));
    } else if (state === 'asleep') {
      drawGlyph(ctx, 'z', 26, 6 - (Math.floor(tick / 3) % 6));
    } else if (state === 'listening') {
      drawGlyph(ctx, 'wave', 28, 3);
      if (tick % 4 < 2) drawGlyph(ctx, 'wave', 30, 3);
    }
  }

  /** Draw one frame. A tick of 0 with still set gives a calm image for reduced motion. */
  function draw(canvas, speciesId, state, tick = 0) {
    const ctx = canvas.getContext('2d');
    const spec = SPECIES[normalize(speciesId)];
    const { colors, rows, oneTail } = spec;
    const place = offsets(state, tick);
    const top = SIZE - 1 - rows.length + place.y;
    const wagOn = state === 'asleep' ? true : (state === 'working' ? tick % 2 === 0 : tick % 4 < 2);
    ctx.clearRect(0, 0, SIZE, SIZE);
    rows.forEach((half, y) => {
      for (let i = 0; i < 24; i += 1) {
        const mirrored = i >= 12;
        let ch = mirrored ? half[23 - i] : half[i];
        if (mirrored && oneTail && (ch === 'T' || ch === 't')) continue;
        if (ch === '.') continue;
        if (ch === 'T' && !wagOn) continue;
        if (ch === 't' && wagOn) continue;
        let color;
        if (ch === 'E' || ch === 'e') color = eyeFor(ch, state, tick, colors);
        else if (ch === 'T' || ch === 't') color = colors.T || colors.a;
        else color = colors[ch];
        ctx.fillStyle = color;
        ctx.fillRect(4 + i + place.x, top + y, 1, 1);
      }
    });
    drawEffect(ctx, state, tick);
  }

  /** Animate a canvas. Timing stops while the page is hidden, and people who ask their
   *  system for less motion get a still image that still shows the status. */
  function createPlayer(canvas, { species = 'gobi', state = 'idle', fps = 6, keepRunning = false } = {}) {
    canvas.width = SIZE;
    canvas.height = SIZE;
    let tick = 0;
    let timer = null;
    const current = { species: normalize(species), state };
    const motionQuery = root.matchMedia ? root.matchMedia('(prefers-reduced-motion: reduce)') : null;
    const still = () => !!(motionQuery && motionQuery.matches) || root.document?.documentElement?.dataset?.motion === 'off';
    let onFrame = null;
    const paint = () => {
      draw(canvas, current.species, current.state, still() ? 0 : tick);
      if (onFrame) onFrame();
    };

    function stop() {
      if (timer) clearInterval(timer);
      timer = null;
    }
    function start() {
      stop();
      if ((root.document?.hidden && !keepRunning) || still()) return;
      timer = setInterval(() => { tick += 1; paint(); }, 1000 / fps);
    }
    const onVisibility = () => { paint(); start(); };
    root.document?.addEventListener('visibilitychange', onVisibility);
    motionQuery?.addEventListener?.('change', onVisibility);
    paint();
    start();

    return {
      /** Be told after every frame is drawn. The desktop pet cuts its window to match. */
      onFrame(fn) { onFrame = fn; paint(); },
      set(next) {
        if (next.species) current.species = normalize(next.species);
        if (next.state) current.state = next.state;
        paint();
      },
      destroy() {
        stop();
        root.document?.removeEventListener('visibilitychange', onVisibility);
        motionQuery?.removeEventListener?.('change', onVisibility);
      },
    };
  }

  root.KalkiPets = { SPECIES, IDS, LABELS, SIZE, normalize, resolveState, draw, createPlayer };
})(typeof window !== 'undefined' ? window : globalThis);
