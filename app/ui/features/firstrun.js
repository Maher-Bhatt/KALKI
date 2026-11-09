/** First run, inside the main app: your name, an AI, and what KALKI will and won't do.
 *
 *  Each step can be skipped. KALKI works for tasks, notes and reminders without an AI,
 *  and everything here can be changed in Settings later. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { settings as api } from '../api/endpoints.js';
import { err } from '../state/toasts.js';
import { petPicker, getPetState } from './pet.js';

const DONE_KEY = 'kalki.firstRun.v1';
const PLACEHOLDER_NAME = 'YourName';

const PROVIDERS = [
  { key: 'GEMINI_API_KEY', label: 'Google Gemini', note: 'Has a free tier. Keys from aistudio.google.com' },
  { key: 'GROQ_API_KEY', label: 'Groq', note: 'Has a free tier. Keys from console.groq.com' },
  { key: 'OPENAI_API_KEY', label: 'OpenAI', note: 'Paid. Keys from platform.openai.com' },
  { key: 'ANTHROPIC_API_KEY', label: 'Anthropic', note: 'Paid. Keys from console.anthropic.com' },
];

function alreadyDone() {
  try {
    return localStorage.getItem(DONE_KEY) === '1';
  } catch {
    return false;
  }
}

function remember() {
  try {
    localStorage.setItem(DONE_KEY, '1');
  } catch { /* It shows once more next time. Nothing is lost. */ }
}

const isSet = (value) => {
  const text = String(value || '').trim();
  return !!text && !/^your[_-]|^xxx|placeholder/i.test(text);
};

/** Show the steps if this looks like a new install. Someone who has already entered a
 *  name or a key isn't new, even if this browser profile has no record of it. */
export async function maybeShowFirstRun() {
  if (alreadyDone()) return false;
  const r = await api.get();
  if (!r.ok) return false;
  const values = r.data.keys || r.data.values || r.data;
  const name = String(values.OWNER_NAME || '').trim();
  const hasName = !!name && name !== PLACEHOLDER_NAME;
  const hasKey = PROVIDERS.some((p) => isSet(values[p.key]));
  if (hasName || hasKey) {
    remember();
    return false;
  }
  showFirstRun();
  return true;
}

export function showFirstRun() {
  const answers = { name: '', provider: PROVIDERS[0].key, key: '' };
  const root = h('div.first-run', { role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Set up KALKI' });
  const card = h('div.first-card');
  root.appendChild(card);
  document.body.appendChild(root);

  let picker = null;
  let step = 0;

  function finish() {
    remember();
    picker?.destroy();
    root.remove();
  }

  async function saveAndNext(patch) {
    if (Object.keys(patch).length) {
      const r = await api.save(patch);
      if (!r.ok) {
        err("That couldn't be saved", r.detail || r.message);
        return;
      }
    }
    step += 1;
    paint();
  }

  const progress = () => h('div.first-steps', { 'aria-hidden': 'true' },
    ...[0, 1, 2].map((i) => h('i' + (i <= step ? '.on' : ''))));

  const label = () => h('div.sub', null, `Step ${step + 1} of 3`);

  function nameStep() {
    const input = h('input.input', {
      type: 'text', maxlength: '100', autocomplete: 'given-name', value: answers.name,
      placeholder: 'Your name',
      onInput: (e) => { answers.name = e.target.value; },
    });
    const next = () => saveAndNext(answers.name.trim() ? { OWNER_NAME: answers.name.trim() } : {});
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') next(); });
    setTimeout(() => input.focus(), 30);
    return [
      h('h1', { id: 'view-title' }, 'Welcome to KALKI'),
      h('p', null, 'Your personal assistant on this PC. What should it call you?'),
      h('label.first-field', null, 'Name', input),
      h('div.first-foot', null,
        h('span.grow'),
        h('button.btn.gh', { type: 'button', onClick: finish }, 'Skip setup'),
        h('button.btn.pri', { type: 'button', onClick: next }, 'Continue')),
    ];
  }

  function aiStep() {
    const noteEl = h('div.xs.mut');
    const showNote = () => { noteEl.textContent = PROVIDERS.find((p) => p.key === answers.provider).note; };
    const select = h('select.input', {
      'aria-label': 'AI provider',
      onChange: (e) => { answers.provider = e.target.value; showNote(); },
    }, ...PROVIDERS.map((p) => h('option', { value: p.key, selected: p.key === answers.provider }, p.label)));
    showNote();
    const keyInput = h('input.input', {
      type: 'password', autocomplete: 'off', spellcheck: 'false', placeholder: 'Paste your key',
      onInput: (e) => { answers.key = e.target.value; },
    });
    return [
      h('h1', { id: 'view-title' }, 'Connect an AI'),
      h('p', null, "KALKI needs an AI service to answer questions. Your key is encrypted and stored only on this PC. Tasks, notes and reminders work without one."),
      h('label.first-field', null, 'Service', select),
      noteEl,
      h('label.first-field', null, 'Key', keyInput),
      h('div.first-foot', null,
        h('button.btn.gh', { type: 'button', onClick: () => { step -= 1; paint(); } }, 'Back'),
        h('span.grow'),
        h('button.btn.gh', { type: 'button', onClick: () => saveAndNext({}) }, 'Do this later'),
        h('button.btn.pri', {
          type: 'button',
          onClick: () => saveAndNext(answers.key.trim() ? { [answers.provider]: answers.key.trim() } : {}),
        }, 'Continue')),
    ];
  }

  function promiseStep() {
    picker?.destroy();
    picker = petPicker({ onChange: (s) => { startBtn.textContent = `Start with ${s.name}`; } });
    const startBtn = h('button.btn.pri', { type: 'button', onClick: finish }, `Start with ${getPetState().name}`);
    const promise = (iconName, title, body) => h('div.first-promise', null, icon(iconName, 16),
      h('div', null, h('strong', null, title), h('div.sm.mut', null, body)));
    return [
      h('h1', { id: 'view-title' }, 'One last thing'),
      h('div', null,
        promise('security', 'You stay in charge', 'KALKI shows you exactly what it wants to do and waits for your approval before anything that matters.'),
        promise('vault', 'Your data stays here', "Chats, notes and memories are kept on this PC. Your questions, and what's needed to answer them, go to the AI service you chose.")),
      h('div.col.g8', null, h('h2', null, 'Pick a companion'), h('div.sm.mut', null, 'It shows when KALKI is working or needs you. You can turn it off in Settings.'), picker.el),
      h('div.first-foot', null,
        h('button.btn.gh', { type: 'button', onClick: () => { step -= 1; paint(); } }, 'Back'),
        h('span.grow'),
        startBtn),
    ];
  }

  function paint() {
    const body = [nameStep, aiStep, promiseStep][step]();
    mount(card, progress(), label(), ...body);
  }

  paint();
}
