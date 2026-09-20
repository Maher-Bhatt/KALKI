/** Memory — built entirely on the semantic store.
 *
 *  The backend has two memory systems: semantic_memory (id, text, tags,
 *  importance 1-10, type, created_at) and an older flat list behind
 *  /api/memories. Showing both as products would be confusing, so the legacy
 *  list appears exactly once, as a one-time import banner, and never again.
 *
 *  type: "pinned" is not a label — semantic_memory.search() merges every
 *  pinned document into results regardless of similarity. Pinning here does
 *  the real thing. */

import { h, mount, debounce } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative } from '../lib/format.js';
import { memory } from '../api/endpoints.js';
import { store, set } from '../state/store.js';
import { emptyState, errorState, skeletonRows } from '../components/states.js';
import { openDialog, confirmDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';

const TYPES = ['fact', 'preference', 'event', 'person', 'pinned'];

export async function loadMemory() {
  set('memory', { loading: true, error: null });
  const r = await memory.list();
  if (!r.ok) { set('memory', { loading: false, error: r }); return; }
  set('memory', { loading: false, items: r.items });
  checkLegacy();
}

async function checkLegacy() {
  if (sessionStorage.getItem('kalki.legacyMemoryDone')) return;
  const legacy = await memory.legacy();
  set('memory', { legacyCount: Array.isArray(legacy) ? legacy.length : 0 });
}

async function importLegacy() {
  const legacy = await memory.legacy();
  let done = 0;
  for (const item of legacy) {
    const text = typeof item === 'string' ? item : (item.text || item.fact || '');
    if (!text) continue;
    const r = await memory.add({ text, type: 'fact', importance: 5 });
    if (r.ok) done++;
  }
  sessionStorage.setItem('kalki.legacyMemoryDone', '1');
  set('memory', { legacyCount: 0 });
  ok(`Imported ${done} older memories`);
  loadMemory();
}

function editor(existing) {
  let textEl, typeEl, impEl, impOut;
  const submit = async () => {
    const payload = {
      text: textEl.value.trim(),
      type: typeEl.value,
      importance: Number(impEl.value),
    };
    if (!payload.text) { textEl.focus(); return; }
    const r = existing ? await memory.update({ id: existing.id, ...payload }) : await memory.add(payload);
    if (r.ok) { ok(existing ? 'Memory updated' : 'Memory added'); close(); loadMemory(); }
    else err(r.message, r.detail);
  };

  const { close } = openDialog({
    title: existing ? 'Edit memory' : 'Add a memory',
    description: 'Stored on this machine only. KALKI retrieves it when it is relevant.',
    width: '32rem',
    body: h('div.stack', null,
      h('div.field', null,
        h('label', { for: 'mem-text' }, 'What should KALKI remember?'),
        h('textarea.textarea', { id: 'mem-text', rows: 3, value: existing?.text || '', ref: (el) => { textEl = el; } }),
      ),
      h('div.field', null,
        h('label', { for: 'mem-type' }, 'Type'),
        h('select.select', { id: 'mem-type', ref: (el) => { typeEl = el; } },
          ...TYPES.map((t) => h('option', { value: t, selected: (existing?.type || 'fact') === t }, t === 'pinned' ? 'pinned — always retrieved' : t))),
      ),
      h('div.field', null,
        h('label', { for: 'mem-imp' }, 'Importance'),
        h('input.slider', {
          id: 'mem-imp', type: 'range', min: '1', max: '10', value: String(existing?.importance ?? 5),
          ref: (el) => { impEl = el; },
          onInput: (e) => { impOut.textContent = e.target.value; },
        }),
        h('span.hint', { ref: (el) => { impOut = el; } }, String(existing?.importance ?? 5)),
      ),
    ),
    actions: [
      h('button.btn.btn-secondary', { type: 'button', onClick: () => close() }, 'Cancel'),
      h('button.btn.btn-primary', { type: 'button', onClick: submit }, existing ? 'Save changes' : 'Add memory'),
    ],
    initialFocus: '#mem-text',
  });
}

async function togglePin(m) {
  const next = m.type === 'pinned' ? 'fact' : 'pinned';
  const r = await memory.update({ id: m.id, text: m.text, importance: m.importance, type: next });
  if (r.ok) { ok(next === 'pinned' ? 'Pinned — KALKI will always see this' : 'Unpinned'); loadMemory(); }
  else err(r.message, r.detail);
}

async function remove(m) {
  if (!(await confirmDialog({ title: 'Forget this?', description: m.text, confirmLabel: 'Forget' }))) return;
  const snapshot = { ...m };
  const r = await memory.remove(m.id);
  if (!r.ok) return err(r.message, r.detail);
  set('memory', { items: store.memory.items.filter((x) => x.id !== m.id) });
  toast({
    kind: 'success', text: 'Memory removed',
    action: { label: 'Undo', run: async () => {
      const back = await memory.add({ text: snapshot.text, importance: snapshot.importance, type: snapshot.type });
      if (back.ok) { ok('Restored'); loadMemory(); }
    } },
  });
}

function memoryRow(m) {
  const pinned = m.type === 'pinned';
  return h('div.row', { style: pinned ? { borderLeft: '2px solid var(--filament-3)', borderRadius: '0 var(--radius-sm) var(--radius-sm) 0' } : null },
    h('div', { style: { flex: '1', minWidth: '0' } },
      h('div.t-body-sm', null, m.text),
      h('div.inline.t-meta.muted', { style: { marginTop: 'var(--space-2)' } },
        h('span.chip', null, m.type || 'fact'),
        h('span', { title: `Importance ${m.importance ?? 5} of 10`, 'aria-label': `Importance ${m.importance ?? 5} of 10` },
          '●'.repeat(Math.max(1, Math.round((m.importance ?? 5) / 3.4)))),
        m.created_at ? h('span', null, relative(m.created_at)) : null,
      ),
    ),
    h('button.icon-btn', { type: 'button', 'aria-label': pinned ? 'Unpin memory' : 'Pin memory', title: pinned ? 'Unpin' : 'Pin', onClick: () => togglePin(m) }, icon('pin', 16)),
    h('button.icon-btn', { type: 'button', 'aria-label': 'Edit memory', title: 'Edit', onClick: () => editor(m) }, icon('edit', 16)),
    h('button.icon-btn', { type: 'button', 'aria-label': 'Forget memory', title: 'Forget', onClick: () => remove(m) }, icon('trash', 16)),
  );
}

export function memoryView() {
  const body = h('div.view-body.scroll');
  const search = h('input.input', {
    type: 'search', placeholder: 'Search memories', 'aria-label': 'Search memories',
    style: { maxWidth: '18rem' },
    onInput: debounce((e) => set('memory', { query: e.target.value }), 160),
  });

  const view = h('section.view', { 'aria-label': 'Memory' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Memory'),
      h('span.spacer'),
      search,
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => editor(null) }, icon('plus', 14), 'Add'),
    ),
    body,
  );

  view.render = () => {
    const m = store.memory;
    if (m.loading) return mount(body, skeletonRows(5));
    if (m.error) {
      return mount(body, errorState({
        title: "Memory didn't load",
        message: m.error.kind === 'unavailable'
          ? 'The embedding backend is unavailable, so search is limited. Your memories are safe.'
          : m.error.message,
        detail: m.error.detail, onRetry: loadMemory,
      }));
    }

    const q = m.query.trim().toLowerCase();
    const filtered = m.items
      .filter((x) => !q || String(x.text).toLowerCase().includes(q))
      .sort((a, b) => (Number(b.type === 'pinned') - Number(a.type === 'pinned')) || ((b.importance ?? 5) - (a.importance ?? 5)));

    const banner = m.legacyCount
      ? h('div.toolrun.toolrun-confirm', { style: { marginBottom: 'var(--space-6)' } },
          h('div.toolrun-head', null,
            icon('info', 16),
            h('span', null, `${m.legacyCount} older memories are stored in the previous format.`),
            h('span.spacer'),
            h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: importLegacy }, 'Import them'),
          ))
      : null;

    if (!m.items.length) {
      return mount(body, banner, emptyState({
        iconName: 'memory',
        title: 'KALKI remembers nothing yet',
        body: 'Add the things you would otherwise repeat — how you like replies, who people are, what you are working on. Everything stays on this machine.',
        actions: [h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => editor(null) }, 'Add the first memory')],
      }));
    }

    if (!filtered.length) {
      return mount(body, banner, emptyState({
        iconName: 'search', title: 'No memories match that',
        body: `Nothing stored contains "${m.query}". Try a shorter phrase.`,
        actions: [h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => { search.value = ''; set('memory', { query: '' }); } }, 'Clear search')],
      }));
    }

    mount(body, banner,
      h('p.t-meta.muted', { style: { marginBottom: 'var(--space-5)' } },
        `${filtered.length} ${filtered.length === 1 ? 'memory' : 'memories'}${q ? ' matching' : ''}`),
      h('div.stack', null, ...filtered.map(memoryRow)));
  };

  return view;
}
