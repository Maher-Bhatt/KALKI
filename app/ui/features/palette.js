/** Command palette — one of KALKI's core interaction systems.
 *
 *  Built on native <dialog>.showModal(), so the document outside is inert and
 *  no focus trap is hand-written. The text input holds DOM focus throughout;
 *  the result list is a listbox driven by aria-activedescendant, which is what
 *  lets arrow keys move the selection without stealing focus from the input.
 *
 *  Every entry runs a real action. Nothing here is a placeholder. */

import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { label as keyLabel } from '../lib/keys.js';
import { modelLabel } from '../lib/format.js';
import { store, set } from '../state/store.js';
import { system, tasks, notes, voice } from '../api/endpoints.js';
import * as conv from '../state/conversations.js';
import { loadModels, refreshStatus } from '../state/status.js';
import { go } from './router.js';
import { ok, err } from '../state/toasts.js';
import { promptDialog } from '../components/dialog.js';
import { openDiagnostics } from './diagnostics.js';

let dlg = null;
let input = null;
let resultsEl = null;
let items = [];
let cursor = 0;
let lastTrigger = null;

const navCommands = () => {
  const base = [
    { group: 'Go to', label: 'Ask', icon: 'ask', shortcut: 'mod+1', run: () => go('ask') },
    { group: 'Go to', label: 'Today', icon: 'today', shortcut: 'mod+2', run: () => go('today') },
    { group: 'Go to', label: 'Memory', icon: 'memory', shortcut: 'mod+3', run: () => go('memory') },
    { group: 'Go to', label: 'Workbench', icon: 'workbench', shortcut: 'mod+4', run: () => go('workbench') },
  ];
  if (store.ui.securityEnabled) base.push({ group: 'Go to', label: 'Security', icon: 'security', run: () => go('security') });
  base.push({ group: 'Go to', label: 'Settings', icon: 'settings', shortcut: 'mod+,', run: () => go('settings') });
  return base;
};

const actionCommands = () => [
  { group: 'Run', label: 'New conversation', icon: 'plus', shortcut: 'mod+n', run: () => { conv.newThread(); go('ask'); } },
  {
    group: 'Run', label: 'Add a task', icon: 'check',
    run: async () => {
      const t = await promptDialog({ title: 'New task', label: 'What needs doing?', confirmLabel: 'Add task' });
      if (!t) return;
      const r = await tasks.add(t);
      r.ok ? ok('Task added') : err(r.message, r.detail);
    },
  },
  {
    group: 'Run', label: 'Write a note', icon: 'note',
    run: async () => {
      const t = await promptDialog({ title: 'New note', label: 'Anything worth keeping', confirmLabel: 'Save note' });
      if (!t) return;
      const r = await notes.add(t);
      r.ok ? ok('Note saved') : err(r.message, r.detail);
    },
  },
  {
    group: 'Run', label: store.status?.listenerPaused ? 'Reclaim the microphone' : 'Release the microphone', icon: 'mic',
    run: async () => {
      const r = store.status?.listenerPaused ? await voice.resume() : await voice.pause();
      if (r.ok) { ok(store.status?.listenerPaused ? 'Microphone reclaimed' : 'Microphone released'); refreshStatus(); }
      else err(r.message, r.detail);
    },
  },
  { group: 'Run', label: 'Wake KALKI', icon: 'spark', run: async () => { const r = await system.wake(''); r.ok ? refreshStatus() : err(r.message, r.detail); } },
  { group: 'Run', label: 'Stop speaking', icon: 'stop', run: async () => { await system.stop(); refreshStatus(); } },
  { group: 'Run', label: 'Open diagnostics', icon: 'info', run: () => setTimeout(openDiagnostics, 60) },
  {
    group: 'Run', label: `Switch theme to ${store.ui.theme === 'dark' ? 'light' : 'dark'}`, icon: 'spark',
    run: () => { store.ui.theme = store.ui.theme === 'dark' ? 'light' : 'dark'; import('../state/store.js').then((m) => m.applyUi()); },
  },
];

const modelCommands = () => store.models.available.map((m) => ({
  group: 'Run', label: `Use ${modelLabel(m)}`, icon: 'spark', context: m === store.models.current ? 'current' : '',
  run: async () => {
    const r = await system.setModel(m);
    r.ok ? (set('models', { current: r.data.model || m }), ok(`Model set to ${modelLabel(m)}`)) : err(r.message, r.detail);
  },
}));

const conversationCommands = (q) => conv.searchThreads(q).map((t) => ({
  group: 'Ask KALKI', label: t.title, icon: 'ask',
  context: t.pinned ? 'pinned' : '',
  run: () => { conv.openThread(t.id); go('ask'); },
}));

const memoryCommands = (q) => store.memory.items
  .filter((m) => !q || String(m.text).toLowerCase().includes(q.toLowerCase()))
  .slice(0, 6)
  .map((m) => ({ group: 'Ask KALKI', label: m.text, icon: 'memory', context: m.type, run: () => go('memory') }));

const settingsCommands = (q) => [
  'general', 'appearance', 'voice', 'models', 'memory', 'integrations',
  'privacy', 'security', 'performance', 'shortcuts', 'backup', 'advanced', 'about',
].filter((s) => !q || s.includes(q.toLowerCase()))
  .map((s) => ({ group: 'Go to', label: `Settings — ${s}`, icon: 'settings', run: () => go('settings', { section: s }) }));

/** Prefixes: `>` actions, `@` memory, `#` tasks/notes, `/` settings. */
function build(raw) {
  const q = raw.trim();
  if (q.startsWith('>')) return filter(actionCommands(), q.slice(1));
  if (q.startsWith('@')) return memoryCommands(q.slice(1));
  if (q.startsWith('/')) return settingsCommands(q.slice(1));
  if (q.startsWith('#')) return filter(actionCommands().filter((c) => /task|note/i.test(c.label)), q.slice(1));

  if (!q) {
    return [...conversationCommands('').slice(0, 4), ...navCommands(), ...actionCommands().slice(0, 4)];
  }
  return [
    ...conversationCommands(q).slice(0, 5),
    ...filter(navCommands(), q),
    ...filter(actionCommands(), q),
    ...filter(modelCommands(), q).slice(0, 5),
    ...memoryCommands(q).slice(0, 4),
    ...settingsCommands(q).slice(0, 4),
  ].slice(0, 24);
}

function filter(list, q) {
  const s = q.trim().toLowerCase();
  if (!s) return list;
  return list.filter((c) => c.label.toLowerCase().includes(s));
}

function paint() {
  items = build(input.value);
  cursor = Math.min(cursor, Math.max(0, items.length - 1));
  resultsEl.replaceChildren();

  if (!items.length) {
    resultsEl.appendChild(h('div.palette-group', null, `Nothing matches "${input.value.trim()}"`));
    resultsEl.appendChild(h('div.palette-item', { style: { cursor: 'default' } },
      h('span.label.muted', null, 'Press Enter to ask KALKI this instead')));
    return;
  }

  let group = null;
  items.forEach((cmd, i) => {
    if (cmd.group !== group) {
      group = cmd.group;
      resultsEl.appendChild(h('div.palette-group', { role: 'presentation' }, group));
    }
    resultsEl.appendChild(h('div.palette-item', {
      id: `pal-${i}`, role: 'option', 'aria-selected': i === cursor ? 'true' : 'false',
      onMouseenter: () => { cursor = i; syncSelection(); },
      onClick: () => execute(i),
    },
      icon(cmd.icon || 'chevron', 16),
      h('span.label', null, cmd.label),
      cmd.context ? h('span.ctx', null, cmd.context) : null,
      cmd.shortcut ? h('span.kbd', null, keyLabel(cmd.shortcut)) : null,
    ));
  });
  syncSelection();
}

function syncSelection() {
  const rows = resultsEl.querySelectorAll('.palette-item[role="option"]');
  rows.forEach((el, i) => el.setAttribute('aria-selected', i === cursor ? 'true' : 'false'));
  input.setAttribute('aria-activedescendant', rows[cursor]?.id || '');
  rows[cursor]?.scrollIntoView({ block: 'nearest' });
}

async function execute(index) {
  const cmd = items[index];
  const raw = input.value.trim();
  close();
  if (cmd) { await cmd.run(); return; }
  // No match: treat the text as a question rather than dropping it.
  if (raw) {
    const { sendMessage } = await import('./ask.js');
    go('ask');
    setTimeout(() => sendMessage(raw), 60);
  }
}

function close() {
  if (dlg?.open) dlg.close();
}

export function openPalette(prefill = '') {
  if (dlg?.open) { input.focus(); input.select(); return; }
  lastTrigger = document.activeElement;
  loadModels();

  input = h('input.palette-input', {
    type: 'text', role: 'combobox', 'aria-expanded': 'true', 'aria-controls': 'palette-results',
    'aria-autocomplete': 'list', 'aria-label': 'Search commands, conversations and settings',
    autocomplete: 'off', spellcheck: 'false', value: prefill,
    placeholder: 'Search or run a command…',
    onInput: () => { cursor = 0; paint(); },
    onKeydown: (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); cursor = Math.min(cursor + 1, Math.max(0, items.length - 1)); syncSelection(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); cursor = Math.max(cursor - 1, 0); syncSelection(); }
      else if (e.key === 'Home') { e.preventDefault(); cursor = 0; syncSelection(); }
      else if (e.key === 'End') { e.preventDefault(); cursor = items.length - 1; syncSelection(); }
      else if (e.key === 'Enter') { e.preventDefault(); execute(cursor); }
      else if (e.key === 'Tab' && items[cursor]) { e.preventDefault(); input.value = items[cursor].label; cursor = 0; paint(); }
    },
  });

  resultsEl = h('div.palette-results', { id: 'palette-results', role: 'listbox', 'aria-label': 'Results' });

  dlg = h('dialog', { id: 'palette', class: 'jarvis-hud theme-dark', 'aria-label': 'Command palette' },
    input,
    resultsEl,
    h('div.palette-foot', null,
      h('span', null, h('span.kbd', null, '↑'), ' ', h('span.kbd', null, '↓'), ' move'),
      h('span', null, h('span.kbd', null, '↵'), ' run'),
      h('span', null, h('span.kbd', null, 'esc'), ' close'),
      h('span.spacer', { style: { flex: '1' } }),
      h('span', null, '> actions  @ memory  / settings'),
    ),
  );

  dlg.addEventListener('close', () => {
    dlg.remove();
    dlg = null;
    if (lastTrigger instanceof HTMLElement && document.contains(lastTrigger)) lastTrigger.focus();
  });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) close(); });

  document.body.appendChild(dlg);
  dlg.showModal();
  paint();
  input.focus();
  input.select();
}

export { close as closePalette };

