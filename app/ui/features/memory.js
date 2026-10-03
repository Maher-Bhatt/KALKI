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

export function memoryView() {
  const main = h('div.pad');
  const aside = h('div');
  
  let quickText = '';
  let quickType = 'preference';
  let quickImp = 5;

  const searchInput = h('input', {
    type: 'search',
    placeholder: 'Search memory',
    style: { border: 'none', background: 'transparent', outline: 'none', flex: '1', color: 'inherit' },
    onInput: debounce((e) => {
      set('memory', { query: e.target.value });
      view.render();
    }, 160)
  });

  const view = { main, aside };

  view.render = () => {
    const m = store.memory;
    const q = (m.query || '').trim().toLowerCase();
    searchInput.value = m.query || '';

    const filtered = (m.items || [])
      .filter((x) => !q || String(x.text).toLowerCase().includes(q))
      .sort((a, b) => (Number(b.type === 'pinned') - Number(a.type === 'pinned')) || ((b.importance ?? 5) - (a.importance ?? 5)));

    // MAIN
    const hd = h('div.hd', null, 
      h('div', null, h('h1', null, 'Memory'), h('div.sub', null, 'Facts KALKI keeps about you. Stored on this machine only.')), 
      h('button.btn.pri', { type: 'button', onClick: () => editor(null) }, h('i', {'data-i': 'plus'}), 'Add memory')
    );

    const banner = m.legacyCount ? 
      h('div.card.row.sb', { style: { marginBottom: '16px' } }, 
        h('span.sm', null, h('b', { style: { fontWeight: '500' } }, `${m.legacyCount} older memories`), ' from the previous version can be imported with full metadata.'), 
        h('div.row.g8', null, 
          h('button.btn.pri', { type: 'button', onClick: importLegacy }, `Import ${m.legacyCount} memories`), 
          h('button.btn.gh', { type: 'button', onClick: () => { set('memory', { legacyCount: 0 }); sessionStorage.setItem('kalki.legacyMemoryDone', '1'); view.render(); } }, 'Dismiss')
        )
      ) : null;

    const searchRow = h('div.row.g8', { style: { marginBottom: '16px' } }, 
      h('div.field', { style: { flex: '1' } }, h('i', {'data-i': 'search'}), searchInput), 
      h('select', { style: { appearance: 'none', background: 'transparent', border: 'none', outline: 'none', padding: '0 8px', color: 'inherit' }, className: 'btn' }, 
        h('option', { value: 'all' }, 'Type: all'), 
        ...TYPES.map(t => h('option', { value: t }, `Type: ${t}`))
      ), 
      h('select', { style: { appearance: 'none', background: 'transparent', border: 'none', outline: 'none', padding: '0 8px', color: 'inherit' }, className: 'btn' }, 
        h('option', { value: 'any' }, 'Importance: any'), 
        ...[1,2,3,4,5,6,7,8,9,10].map(i => h('option', { value: i }, `Importance: ${i}`))
      )
    );

    let listNodes = [];
    if (m.loading) {
      listNodes.push(skeletonRows(3));
    } else if (m.error) {
      listNodes.push(errorState({
        title: "Memory didn't load",
        message: m.error.kind === 'unavailable'
          ? 'The embedding backend is unavailable, so search is limited. Your memories are safe.'
          : m.error.message,
        detail: m.error.detail, onRetry: loadMemory,
      }));
    } else if (!m.items.length && !q) {
      listNodes.push(emptyState({
        iconName: 'memory',
        title: 'KALKI remembers nothing yet',
        body: 'Add the things you would otherwise repeat.',
      }));
    } else if (!filtered.length) {
      listNodes.push(emptyState({
        iconName: 'search', title: 'No memories match that',
        body: `Nothing stored contains "${m.query}". Try a shorter phrase.`,
        actions: [h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => { searchInput.value = ''; set('memory', { query: '' }); view.render(); } }, 'Clear search')],
      }));
    } else {
      filtered.forEach(x => {
        const pinned = x.type === 'pinned';
        listNodes.push(
          h('div.li', null, 
            h('span.chip', null, x.type || 'fact'), 
            h('div', { style: { flex: '1', minWidth: '0' } }, 
              h('div.sm', { style: { wordBreak: 'break-word' } }, x.text), 
              h('div.xs.mut', { style: { marginTop: '4px', display: 'flex', gap: '8px' } }, 
                h('span', { title: `Importance ${x.importance ?? 5}` }, '■'.repeat(Math.max(1, Math.round((x.importance ?? 5) / 2)))), 
                x.created_at ? h('span', null, relative(x.created_at)) : null
              )
            ), 
            h('div.row.g4', null, 
              h('button.ib', { type: 'button', title: pinned ? 'Unpin' : 'Pin', onClick: () => togglePin(x) }, h('i', {'data-i': 'pin', style: pinned ? { color: 'var(--fg)' } : undefined})), 
              h('button.ib', { type: 'button', title: 'Edit', onClick: () => editor(x) }, h('i', {'data-i': 'pen'})), 
              h('button.ib', { type: 'button', title: 'Forget', onClick: () => remove(x) }, h('i', {'data-i': 'trash'}))
            )
          )
        );
      });
    }

    const memCard = h('div.card', { id: 'mem' }, ...listNodes);

    const quickAddCard = h('div.card.in.col.g12', { style: { marginTop: '18px' } }, 
      h('h2', null, 'Add a memory'), 
      h('div.field', { style: { minHeight: '56px', alignItems: 'flex-start' } }, 
        h('textarea', {
          style: { width: '100%', background: 'transparent', border: 'none', outline: 'none', resize: 'none', color: 'inherit', fontFamily: 'inherit' },
          placeholder: 'I prefer short, direct answers...',
          value: quickText,
          onInput: (e) => { quickText = e.target.value; }
        })
      ), 
      h('div.row.g8', null, 
        h('select', { 
            className: 'btn', 
            style: { appearance: 'none', background: 'transparent' }, 
            onInput: (e) => { quickType = e.target.value; }
          },
          ...TYPES.map(t => h('option', { value: t, selected: quickType === t }, `Type: ${t}`))
        ), 
        h('span.xs.mut', null, 'Importance'), 
        h('input', { 
          type: 'range', min: '1', max: '10', value: String(quickImp), 
          style: { width: '80px' },
          onInput: (e) => { quickImp = Number(e.target.value); view.render(); } 
        }), 
        h('span.imp', { id: 'impn' }, String(quickImp)), 
        h('div.sp', { style: { flex: '1' } }), 
        h('button.btn.pri', { 
          type: 'button',
          onClick: async () => {
             if (!quickText.trim()) return;
             const r = await memory.add({ text: quickText.trim(), type: quickType, importance: quickImp });
             if (r.ok) {
               ok('Memory added');
               quickText = '';
               quickImp = 5;
               quickType = 'preference';
               loadMemory();
             } else {
               err(r.message, r.detail);
             }
          }
        }, 'Save memory')
      )
    );

    mount(main, hd, banner, searchRow, h('h2', { style: { marginBottom: '6px' } }, 'Pinned ╖ always included'), memCard, quickAddCard);

    // ASIDE
    mount(aside, 
      h('h1', { style: { fontSize: '16px' } }, 'Overview'), 
      h('div.card.col.g12', null, 
        h('div.row.sb', null, h('span.xs.mut', null, 'Total memories'), h('span.mono', null, String(m.items?.length || 0))), 
        h('div.row.sb', null, h('span.xs.mut', null, 'Pinned'), h('span.mono', null, String(m.items?.filter(x => x.type === 'pinned').length || 0))), 
        h('div.row.sb', null, h('span.xs.mut', null, 'Search mode'), h('span.chip.ok', null, m.error?.kind === 'unavailable' ? 'Text fallback' : 'Semantic'))
      ), 
      h('div.card.col.g8', null, 
        h('h2', null, 'What memory is for'), 
        h('div.sm.t2', null, 'KALKI uses memory to answer in your context. Pinned items are always included; the rest are found by meaning. Nothing leaves this machine.')
      ), 
      h('div.card.col.g8', null, 
        h('h2', null, 'If search is unavailable'), 
        h('div.sm.t2', null, 'Memory still lists and edits, and search falls back to matching text. KALKI says so on screen.')
      )
    );
  };

  return view;
}
