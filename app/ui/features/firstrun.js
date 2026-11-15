/** Onboarding: the first thing a new KALKI user sees, inside the app.
 *
 *  Seven short steps with a step list on the left. Every key has a numbered guide with
 *  a button to the right page, a format check, and a real test. Each step saves as you
 *  go, everything can be skipped, and you can leave and come back where you were.
 *  Finishing writes setup_complete.marker on the server, so it never shows twice. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { settings as api, voice } from '../api/endpoints.js';
import { ok, err, toast } from '../state/toasts.js';
import { toggleSwitch } from '../components/states.js';
import { brandMark, mountainArt } from '../components/brand.js';
import { petPicker, getPetState } from './pet.js';

const DONE_KEY = 'kalki.firstRun.v1';
const STEP_KEY = 'kalki.onboarding.step';
const PLACEHOLDER_NAME = 'YourName';

const STEPS = [
  ['welcome', 'Welcome'],
  ['you', 'About you'],
  ['brain', 'AI brain'],
  ['voice', 'Voice'],
  ['connect', 'Connect apps'],
  ['day', 'Your day'],
  ['ready', 'Ready'],
];

/* ── What each AI service needs, step by step ─────────────────────────── */

const PROVIDERS = [
  {
    id: 'gemini', key: 'GEMINI_API_KEY', name: 'Google Gemini', badge: 'Free · recommended',
    blurb: 'Smart and free for everyday use. Needs a Google account.',
    url: 'https://aistudio.google.com/apikey', prefix: /^AIza[\w-]{20,}$/,
    steps: ['Open Google AI Studio and sign in with your Google account.', 'Click "Create API key".', 'Copy the key. It starts with "AIza".', 'Paste it below and press Save and test.'],
  },
  {
    id: 'groq', key: 'GROQ_API_KEY', name: 'Groq', badge: 'Free · fastest',
    blurb: 'Very fast replies, free tier with daily limits.',
    url: 'https://console.groq.com/keys', prefix: /^gsk_\w{20,}$/,
    steps: ['Open the Groq console and sign in (Google or email).', 'Click "Create API Key" and name it KALKI.', 'Copy the key right away. It starts with "gsk_" and is only shown once.', 'Paste it below and press Save and test.'],
  },
  {
    id: 'openai', key: 'OPENAI_API_KEY', name: 'OpenAI', badge: 'Paid',
    blurb: 'GPT models. Needs prepaid credit on your OpenAI account.',
    url: 'https://platform.openai.com/api-keys', prefix: /^sk-[\w-]{20,}$/,
    steps: ['Open the OpenAI API keys page and sign in.', 'Add credit under Billing if you have none.', 'Click "Create new secret key" and copy it. It starts with "sk-".', 'Paste it below and press Save and test.'],
  },
  {
    id: 'anthropic', key: 'ANTHROPIC_API_KEY', name: 'Anthropic Claude', badge: 'Paid',
    blurb: 'Claude models. Needs credit on your Anthropic account.',
    url: 'https://console.anthropic.com/settings/keys', prefix: /^sk-ant-[\w-]{20,}$/,
    steps: ['Open the Anthropic console and sign in.', 'Add credit under Billing if you have none.', 'Click "Create Key" and copy it. It starts with "sk-ant-".', 'Paste it below and press Save and test.'],
  },
  {
    id: 'ollama', key: null, name: 'Ollama (offline)', badge: 'Free · private',
    blurb: 'Runs on this PC with no account and no key. Needs a reasonably strong PC.',
    url: 'https://ollama.com/download',
    steps: ['Download and install Ollama.', 'Open a terminal and run:  ollama pull llama3.2', 'Come back here and press Check for Ollama.'],
  },
];

const VOICES = [
  ['en-US-AndrewMultilingualNeural', 'Andrew · natural, warm'],
  ['en-IN-PrabhatNeural', 'Prabhat · Indian English'],
  ['en-GB-RyanNeural', 'Ryan · British'],
  ['en-US-GuyNeural', 'Guy · confident'],
  ['en-US-JennyNeural', 'Jenny · warm'],
  ['en-US-AriaNeural', 'Aria · bright'],
];

/* ── Small helpers ────────────────────────────────────────────────────── */

function alreadyDone() {
  try { return localStorage.getItem(DONE_KEY) === '1'; } catch { return false; }
}

function remember() {
  try { localStorage.setItem(DONE_KEY, '1'); localStorage.removeItem(STEP_KEY); } catch { /* shows once more, nothing lost */ }
}

function openLink(url) {
  window.open(url, '_blank', 'noreferrer');
}

const isSet = (value) => {
  const text = String(value || '').trim();
  return !!text && !/^your[_-]|^xxx|placeholder|^paste_/i.test(text);
};

function guide(steps) {
  return h('ol.ob-guide', null, ...steps.map((s) => h('li', null, s)));
}

function field(label, input, hint) {
  return h('label.ob-field', null, h('span', null, label), input, hint ? h('span.ob-hint', null, hint) : null);
}

function secretInput(placeholder) {
  return h('input.input', { type: 'password', autocomplete: 'off', spellcheck: 'false', placeholder });
}

/** Show the onboarding on a new install. A user who already has a name or key set isn't
 *  new, even without the marker (older versions), so they're marked done quietly. */
export async function maybeShowFirstRun() {
  const state = await api.setupState();
  if (state.ok && state.data.complete) {
    remember();
    return false;
  }
  if (alreadyDone() && !state.ok) return false;
  const r = await api.get();
  if (!r.ok) return false;
  const values = r.data.settings || {};
  const status = r.data.secretStatus || {};
  const name = String(values.OWNER_NAME || '').trim();
  const hasName = !!name && name !== PLACEHOLDER_NAME;
  const hasKey = PROVIDERS.some((p) => p.key && (status[p.key] === true || isSet(values[p.key])));
  if (hasName && hasKey) {
    remember();
    api.setupComplete();
    return false;
  }
  showFirstRun({ values, status });
  return true;
}

/* ── The onboarding ───────────────────────────────────────────────────── */

export function showFirstRun({ values = {}, status = {} } = {}) {
  const saved = { ...values };
  const secrets = { ...status };
  const done = new Set();
  let step = 0;
  try { step = Math.min(STEPS.length - 1, Math.max(0, Number(localStorage.getItem(STEP_KEY)) || 0)); } catch { /* start at 0 */ }

  const root = h('div.ob', { role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'ob-title' });
  const rail = h('div.ob-rail');
  const panel = h('div.ob-panel');
  root.append(rail, panel);
  document.body.appendChild(root);
  document.documentElement.classList.add('ob-open');

  let picker = null;

  async function save(patch, quiet = false) {
    const r = await api.save(patch);
    if (!r.ok) { err("That couldn't be saved", r.detail || r.message); return false; }
    Object.assign(saved, patch);
    if (!quiet) ok('Saved');
    return true;
  }

  function go(next) {
    step = Math.max(0, Math.min(STEPS.length - 1, next));
    try { localStorage.setItem(STEP_KEY, String(step)); } catch { /* fine */ }
    paint();
    panel.scrollTop = 0;
  }

  async function finish() {
    await api.setupComplete();
    remember();
    picker?.destroy();
    root.remove();
    document.documentElement.classList.remove('ob-open');
    location.hash = '#/ask';
    toast({ kind: 'success', text: `You're all set${saved.OWNER_NAME ? `, ${saved.OWNER_NAME}` : ''}. Try saying "brief me".` });
  }

  function later() {
    remember();
    picker?.destroy();
    root.remove();
    document.documentElement.classList.remove('ob-open');
    toast({ kind: 'info', text: 'You can finish setting up any time in Settings.' });
  }

  /* Left: brand, steps, reassurance */
  function paintRail() {
    mount(rail,
      h('div.ob-brand', null, brandMark(22), h('strong', null, 'KALKI')),
      h('ol.ob-steps', null, ...STEPS.map(([id, label], i) => h('li', {
        class: i === step ? 'is-current' : (done.has(id) || i < step ? 'is-done' : ''),
        'aria-current': i === step ? 'step' : null,
      }, h('button', { type: 'button', onClick: () => go(i), disabled: i > step + 1 && !done.has(STEPS[i - 1][0]) },
        h('span.ob-dot', null, done.has(id) || i < step ? icon('check', 12) : String(i + 1)), label)))),
      h('div.ob-rail-foot', null, icon('vault', 14),
        h('span', null, 'Keys are encrypted on this PC. Everything can be changed later in Settings.')));
  }

  function foot({ back = true, skip = null, nextLabel = 'Continue', onNext = null, nextDisabled = false } = {}) {
    return h('div.ob-foot', null,
      back && step > 0 ? h('button.btn.gh', { type: 'button', onClick: () => go(step - 1) }, 'Back') : null,
      h('span.grow'),
      skip ? h('button.btn.gh', { type: 'button', onClick: skip }, 'Skip for now') : null,
      h('button.btn.pri', {
        type: 'button', disabled: nextDisabled,
        onClick: async () => { if (onNext && (await onNext()) === false) return; done.add(STEPS[step][0]); go(step + 1); },
      }, nextLabel, icon('chevron', 14)));
  }

  /* 1. Welcome */
  function welcome() {
    return [
      h('div.ob-hero', null, mountainArt()),
      h('h1.ob-title', { id: 'ob-title' }, 'Welcome to KALKI'),
      h('p.ob-lead', null, 'Your personal assistant for this PC. It talks, listens, plans your day, plays your music and keeps your PC safe. Setting up takes about three minutes.'),
      h('div.ob-points', null,
        point('ask', 'Ask anything', 'Chat or talk, with answers from the AI you choose.'),
        point('today', 'Plans your day', 'Briefing, reminders, focus sessions and notes.'),
        point('security', 'You stay in charge', 'Anything that matters waits for your approval.')),
      h('div.ob-foot', null,
        h('button.btn.gh', { type: 'button', onClick: later }, "I'll set it up later"),
        h('span.grow'),
        h('button.btn.pri.ob-big', { type: 'button', onClick: () => { done.add('welcome'); go(1); } }, "Let's begin", icon('chevron', 14))),
    ];
  }

  function point(iconName, title, body) {
    return h('div.ob-point', null, h('span.ob-point-icon', null, icon(iconName, 16)),
      h('div', null, h('strong', null, title), h('div.sm.mut', null, body)));
  }

  /* 2. About you */
  function you() {
    const name = h('input.input', { value: isSet(saved.OWNER_NAME) && saved.OWNER_NAME !== PLACEHOLDER_NAME ? saved.OWNER_NAME : '', maxLength: 100, placeholder: 'Your first name', autocomplete: 'given-name' });
    const title = h('input.input', { value: saved.OWNER_TITLE ?? '', maxLength: 50, placeholder: 'For example: boss, or leave empty' });
    let useLocation = !!saved.USE_DEVICE_LOCATION;
    const locNote = h('span.ob-hint', null, 'Windows finds this PC with GPS or nearby Wi-Fi, never your IP address. Used only for the weather.');
    const locToggle = toggleSwitch({
      checked: useLocation, label: "Use this PC's location",
      onClick: async () => {
        useLocation = !useLocation;
        await save({ USE_DEVICE_LOCATION: useLocation }, true);
        if (useLocation) {
          locNote.textContent = 'Asking Windows…';
          const r = await api.deviceLocation(true);
          locNote.textContent = r.ok && r.data.ok
            ? `Found: ${[r.data.city, r.data.country].filter(Boolean).join(', ') || 'this PC'}, within about ${r.data.accuracy_m} m.`
            : (r.data?.reason || r.message || "Windows couldn't find this PC. Turn on location in Windows Settings > Privacy & security > Location.");
        }
        paint();
      },
    });
    setTimeout(() => name.focus(), 30);
    return [
      h('h1.ob-title', { id: 'ob-title' }, 'About you'),
      h('p.ob-lead', null, 'So KALKI greets you properly and gives you the right weather.'),
      field('What should KALKI call you?', name),
      field('How should it address you out loud?', title, 'KALKI says this in replies, like "Good morning, boss."'),
      h('div.ob-row', null, h('div', null, h('strong', null, "Use this PC's location"), locNote), locToggle),
      foot({ onNext: () => save({ OWNER_NAME: name.value.trim() || PLACEHOLDER_NAME, OWNER_TITLE: title.value.trim() }, true) }),
    ];
  }

  /* 3. AI brain */
  let chosen = 'gemini';
  let tested = null; // { ok, text }
  function brain() {
    const p = PROVIDERS.find((x) => x.id === chosen);
    const cards = h('div.ob-cards', { role: 'radiogroup', 'aria-label': 'AI service' }, ...PROVIDERS.map((x) => h('button.ob-card', {
      type: 'button', role: 'radio', 'aria-checked': String(x.id === chosen),
      class: x.id === chosen ? 'is-on' : '',
      onClick: () => { chosen = x.id; tested = null; paint(); },
    }, h('div.ob-card-top', null, h('strong', null, x.name),
      x.key && secrets[x.key] ? h('span.chip.ok', null, 'Key saved') : h('span.chip', null, x.badge)),
    h('span.sm.mut', null, x.blurb))));

    const result = h('div.ob-result', { role: 'status' });
    if (tested) {
      result.className = 'ob-result ' + (tested.ok ? 'is-ok' : 'is-bad');
      result.textContent = tested.text;
    }

    let detail;
    if (p.key) {
      const key = secretInput(secrets[p.key] ? 'A key is saved. Paste a new one to replace it.' : `Paste your ${p.name} key`);
      const formatHint = h('span.ob-hint');
      key.addEventListener('input', () => {
        const v = key.value.trim();
        formatHint.textContent = v && p.prefix && !p.prefix.test(v) ? "That doesn't look like a " + p.name + ' key. Check you copied all of it.' : '';
      });
      const testBtn = h('button.btn.pri', {
        type: 'button',
        onClick: async () => {
          const v = key.value.trim();
          if (!v && !secrets[p.key]) { key.focus(); return; }
          testBtn.disabled = true;
          testBtn.textContent = 'Testing…';
          if (v) {
            if (!(await save({ [p.key]: v }, true))) { testBtn.disabled = false; testBtn.textContent = 'Save and test'; return; }
            secrets[p.key] = true;
          }
          const r = await api.testAi();
          tested = r.ok && r.data?.ok
            ? { ok: true, text: `It works. KALKI says: "${String(r.data.reply).slice(0, 160)}"` }
            : { ok: false, text: `That didn't work: ${r.data?.error || r.message || 'no answer'}. Check the key, or try another service.` };
          if (tested.ok) done.add('brain');
          paint();
        },
      }, 'Save and test');
      detail = [guide(p.steps),
        h('div.row.g8', null, h('button.btn', { type: 'button', onClick: () => openLink(p.url) }, icon('link', 14), `Open ${new URL(p.url).hostname}`)),
        field('Your key', key), formatHint,
        h('div.row.g8', null, testBtn), result];
    } else {
      const check = h('button.btn.pri', {
        type: 'button',
        onClick: async () => {
          check.disabled = true;
          const r = await api.findOllama();
          const models = r.ok ? r.data.models || [] : [];
          tested = r.ok && r.data.running
            ? (models.length ? { ok: true, text: `Ollama is running with ${models.length} model${models.length === 1 ? '' : 's'}. KALKI will use it.` }
              : { ok: false, text: 'Ollama is running but has no models yet. Run: ollama pull llama3.2' })
            : { ok: false, text: "Ollama isn't running on this PC yet. Install it, then start it." };
          if (tested.ok) done.add('brain');
          paint();
        },
      }, 'Check for Ollama');
      detail = [guide(p.steps),
        h('div.row.g8', null, h('button.btn', { type: 'button', onClick: () => openLink(p.url) }, icon('link', 14), 'Download Ollama'), check), result];
    }

    return [
      h('h1.ob-title', { id: 'ob-title' }, 'Give KALKI a brain'),
      h('p.ob-lead', null, 'KALKI uses an AI service to understand you and answer. Pick one; you can add more later. Not sure? Google Gemini is free and works well.'),
      cards,
      h('div.ob-detail', null, ...detail),
      foot({
        skip: () => { go(step + 1); },
        nextLabel: tested?.ok ? 'Continue' : 'Continue anyway',
      }),
      tested?.ok ? null : h('p.ob-hint', null, 'Without an AI, KALKI still handles tasks, notes, reminders, music and your PC, but can’t answer questions.'),
    ];
  }

  /* 4. Voice */
  function voiceStep() {
    const current = saved.TTS_VOICE || VOICES[0][0];
    const list = h('div.ob-voices', null, ...VOICES.map(([id, label]) => h('button.ob-voice', {
      type: 'button', class: id === current ? 'is-on' : '', 'aria-pressed': String(id === current),
      onClick: async () => {
        await save({ TTS_VOICE: id }, true);
        const r = await voice.testTts(`Hi${saved.OWNER_NAME && saved.OWNER_NAME !== PLACEHOLDER_NAME ? ' ' + saved.OWNER_NAME : ''}, I'm KALKI. This is how I sound.`);
        if (!r.ok || r.data?.ok === false) err("KALKI couldn't speak", r.data?.lastError || r.message);
        paint();
      },
    }, icon('volume', 14), h('span', null, label))));
    const mode = saved.LISTEN_MODE || 'always';
    const listen = (value, title, body) => h('button.ob-card', {
      type: 'button', role: 'radio', 'aria-checked': String(mode === value), class: mode === value ? 'is-on' : '',
      onClick: async () => { await save({ LISTEN_MODE: value }, true); paint(); },
    }, h('strong', null, title), h('span.sm.mut', null, body));
    return [
      h('h1.ob-title', { id: 'ob-title' }, 'How KALKI sounds and listens'),
      h('p.ob-lead', null, 'Tap a voice to hear it. Make sure your speakers are on.'),
      list,
      h('h2.ob-sub', null, 'Listening'),
      h('div.ob-cards.two', { role: 'radiogroup', 'aria-label': 'Listening mode' },
        listen('always', 'Say "Hey KALKI"', 'Always listening for the wake word. Hands-free.'),
        listen('push', 'Press to talk', 'The microphone stays off until you press the mic button.')),
      h('div.ob-row', null, h('div', null, h('strong', null, 'Savage mode'),
        h('span.ob-hint', null, 'Blunt, witty and free to swear. Insults get roasted back in your language.')),
      toggleSwitch({ checked: !!saved.ROAST_MODE, label: 'Savage mode', onClick: async () => { await save({ ROAST_MODE: !saved.ROAST_MODE }, true); paint(); } })),
      foot(),
    ];
  }

  /* 5. Connect apps */
  let openConnector = null;
  function connect() {
    const item = (id, title, body, isOn, content) => h('div.ob-acc' + (openConnector === id ? '.is-open' : ''), null,
      h('button.ob-acc-head', { type: 'button', 'aria-expanded': String(openConnector === id), onClick: () => { openConnector = openConnector === id ? null : id; paint(); } },
        h('div', null, h('strong', null, title), h('div.sm.mut', null, body)),
        isOn ? h('span.chip.ok', null, 'Connected') : h('span.chip', null, 'Optional'),
        icon('chevronD', 14)),
      openConnector === id ? h('div.ob-acc-body', null, ...content()) : null);

    const saveButton = (label, inputs, makePatch) => h('button.btn.pri', {
      type: 'button',
      onClick: async () => {
        const patch = makePatch();
        if (!Object.values(patch).some((v) => String(v).trim())) { inputs[0]?.focus(); return; }
        if (await save(patch)) {
          Object.keys(patch).forEach((k) => { secrets[k] = true; });
          openConnector = null;
          paint();
        }
      },
    }, label);

    return [
      h('h1.ob-title', { id: 'ob-title' }, 'Connect your apps'),
      h('p.ob-lead', null, 'All optional. Each one makes KALKI more useful; skip any you don’t use.'),
      item('calendar', 'Google Calendar', 'Your events in the briefing; "what’s on today?"', false, () => [
        guide(['Press Start Google setup. A guided window opens.', 'Sign in with Google and allow calendar access.', 'Come back here when it says it’s done.']),
        h('button.btn.pri', { type: 'button', onClick: async () => { const r = await api.setupTool('google'); r.ok ? ok('Google setup opened') : err(r.message, r.detail); } }, 'Start Google setup')]),
      item('music', 'Music', 'Spotify, Apple Music or YouTube Music', false, () => [
        h('p.sm', null, 'Apple Music and YouTube Music work without setup. KALKI uses Spotify if you connect it.'),
        guide(['Press Start Spotify setup. A guided window opens.', 'Sign in to Spotify and allow access.', 'Come back here when it says it’s done.']),
        h('button.btn', { type: 'button', onClick: async () => { const r = await api.setupTool('spotify'); r.ok ? ok('Spotify setup opened') : err(r.message, r.detail); } }, 'Start Spotify setup')]),
      item('mail', 'Email (Gmail)', 'Unread and important mail in your briefing', !!secrets.EMAIL_APP_PASSWORD, () => {
        const address = h('input.input', { type: 'email', placeholder: 'you@gmail.com', value: saved.EMAIL_ADDRESS || '' });
        const pass = secretInput('16-letter app password');
        return [guide([
          'Gmail needs 2-Step Verification turned on in your Google account.',
          'Open App passwords, type "KALKI" as the name and press Create.',
          'Copy the 16-letter password Google shows, and paste it below with your address.',
        ]),
        h('button.btn', { type: 'button', onClick: () => openLink('https://myaccount.google.com/apppasswords') }, icon('link', 14), 'Open App passwords'),
        field('Email address', address), field('App password', pass, 'Not your normal password. Other mail services: set the server in Settings > Integrations.'),
        saveButton('Save email', [address, pass], () => ({ EMAIL_ADDRESS: address.value.trim(), ...(pass.value.trim() ? { EMAIL_APP_PASSWORD: pass.value.replace(/\s+/g, '') } : {}) }))];
      }),
      item('telegram', 'Telegram', 'Message KALKI from your phone', !!secrets.TELEGRAM_BOT_TOKEN, () => {
        const token = secretInput('Bot token from @BotFather');
        const user = h('input.input', { inputMode: 'numeric', placeholder: 'Your numeric user ID', value: saved.TELEGRAM_USER_ID || '' });
        return [guide([
          'In Telegram, open @BotFather and send /newbot.',
          'Pick a name and a username ending in "bot". Copy the token it gives you.',
          'Open @userinfobot and copy your numeric ID, so only you can use the bot.',
        ]),
        h('button.btn', { type: 'button', onClick: () => openLink('https://t.me/BotFather') }, icon('link', 14), 'Open @BotFather'),
        field('Bot token', token), field('Your user ID', user),
        saveButton('Save Telegram', [token, user], () => ({ ...(token.value.trim() ? { TELEGRAM_BOT_TOKEN: token.value.trim() } : {}), TELEGRAM_USER_ID: user.value.replace(/\D/g, '') }))];
      }),
      item('github', 'GitHub', 'Pull requests and issues waiting for you', !!secrets.GITHUB_TOKEN, () => {
        const token = secretInput('Personal access token');
        return [guide([
          'Open GitHub token settings and choose "Generate new token (classic)".',
          'Tick only the "notifications" scope and generate it.',
          'Copy the token (it starts with "ghp_") and paste it here.',
        ]),
        h('button.btn', { type: 'button', onClick: () => openLink('https://github.com/settings/tokens') }, icon('link', 14), 'Open GitHub tokens'),
        field('Token', token),
        saveButton('Save GitHub', [token], () => ({ GITHUB_TOKEN: token.value.trim() }))];
      }),
      foot({ skip: () => go(step + 1) }),
    ];
  }

  /* 6. Your day */
  function day() {
    picker?.destroy();
    picker = petPicker({});
    const toggle = (key, title, body, fallback) => h('div.ob-row', null,
      h('div', null, h('strong', null, title), h('span.ob-hint', null, body)),
      toggleSwitch({ checked: saved[key] ?? fallback, label: title, onClick: async () => { await save({ [key]: !(saved[key] ?? fallback) }, true); paint(); } }));
    return [
      h('h1.ob-title', { id: 'ob-title' }, 'Your day with KALKI'),
      h('p.ob-lead', null, 'A few habits that make KALKI feel like yours.'),
      toggle('AUTO_START', 'Start with Windows', 'KALKI is ready when you sign in.', true),
      toggle('BRIEFING_ON_START', 'Morning briefing', 'The first time your PC starts each day, KALKI reads your calendar, reminders, tasks and weather.', true),
      toggle('SCREEN_TIME_ENABLED', 'Screen time', 'Minutes per app, kept only on this PC. Window titles are never stored.', false),
      h('h2.ob-sub', null, 'Pick a companion'),
      h('p.sm.mut', null, 'It shows when KALKI is working or needs you. You can turn it off in Settings.'),
      picker.el,
      foot(),
    ];
  }

  /* 7. Ready */
  function ready() {
    const hasAi = PROVIDERS.some((p) => p.key && secrets[p.key]) || done.has('brain');
    const row = (isOn, title, body, target) => h('div.ob-check' + (isOn ? '.is-on' : ''), null,
      h('span.ob-dot', null, isOn ? icon('check', 12) : '–'),
      h('div.grow', null, h('strong', null, title), h('div.sm.mut', null, body)),
      !isOn && target !== undefined ? h('button.btn.gh', { type: 'button', onClick: () => go(target) }, 'Set up') : null);
    return [
      h('h1.ob-title', { id: 'ob-title' }, `You're ready${saved.OWNER_NAME && saved.OWNER_NAME !== PLACEHOLDER_NAME ? ', ' + saved.OWNER_NAME : ''}`),
      h('p.ob-lead', null, 'Here’s what’s set up. Anything missing can be added later in Settings.'),
      h('div.ob-checks', null,
        row(isSet(saved.OWNER_NAME) && saved.OWNER_NAME !== PLACEHOLDER_NAME, 'Your name', 'KALKI knows what to call you.', 1),
        row(hasAi, 'AI brain', hasAi ? 'KALKI can answer questions.' : 'Needed for questions and chat.', 2),
        row(!!saved.USE_DEVICE_LOCATION, 'Weather for where you are', 'Uses this PC’s location.', 1),
        row(!!(secrets.EMAIL_APP_PASSWORD || secrets.TELEGRAM_BOT_TOKEN || secrets.GITHUB_TOKEN), 'Connected apps', 'Email, Telegram, GitHub, Calendar.', 4)),
      h('div.ob-points', null,
        point('mic', 'Say "Hey KALKI"', 'Or press the mic. Try "brief me" or "play some music".'),
        point('security', 'Nothing happens behind your back', 'KALKI shows exactly what it wants to do and waits for you.'),
        point('vault', 'Your data stays here', 'Chats, notes and memories are kept on this PC.')),
      h('div.ob-foot', null,
        h('button.btn.gh', { type: 'button', onClick: () => go(step - 1) }, 'Back'),
        h('span.grow'),
        h('button.btn.pri.ob-big', { type: 'button', onClick: finish }, `Start KALKI with ${getPetState().name}`)),
    ];
  }

  function paint() {
    paintRail();
    const view = [welcome, you, brain, voiceStep, connect, day, ready][step];
    mount(panel,
      h('div.ob-progress', { 'aria-hidden': 'true' }, h('i', { style: { width: `${((step + 1) / STEPS.length) * 100}%` } })),
      h('div.ob-step-label', null, `Step ${step + 1} of ${STEPS.length}`),
      h('div.ob-content', { class: `ob-${STEPS[step][0]}` }, ...view()));
  }

  root.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
      e.preventDefault();
      panel.querySelector('.ob-foot .btn.pri')?.click();
    }
  });

  paint();
}
