/** Notes: the full list, search, tags, edit, delete with Undo, and Markdown export.
 *
 *  Today shows the latest few and opens this for everything else. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative } from '../lib/format.js';
import { notes } from '../api/endpoints.js';
import { openDialog, promptDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';

/** Delete a note, with an Undo that puts it back exactly as it was. */
export async function deleteNote(note, onChange) {
  const r = await notes.remove(note.id);
  if (!r.ok) { err(r.message || "The note couldn't be deleted", r.detail); return false; }
  const deleted = r.data?.deleted || note;
  onChange?.();
  toast({
    kind: 'info',
    text: 'Note deleted',
    action: {
      label: 'Undo',
      run: async () => {
        const back = await notes.restore(deleted);
        if (back.ok) { ok('Note restored'); onChange?.(); } else err(back.message || "The note couldn't be restored", back.detail);
      },
    },
  });
  return true;
}

export async function editNote(note, onChange) {
  const text = await promptDialog({ title: 'Edit note', label: 'Use #tags to group notes.', value: note.text, confirmLabel: 'Save' });
  if (text == null || text.trim() === note.text) return false;
  if (!text.trim()) { err("A note can't be empty. Delete it instead."); return false; }
  const r = await notes.update(note.id, text.trim());
  if (!r.ok) { err(r.message || "The note couldn't be saved", r.detail); return false; }
  ok('Note saved');
  onChange?.();
  return true;
}

function download(name, text) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = h('a', { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function exportNotes(q = '', tag = '') {
  const r = await notes.exportMarkdown(q, tag);
  if (!r.ok) { err(r.message || "The notes couldn't be exported", r.detail); return; }
  if (!r.data.count) { toast({ kind: 'info', text: 'No notes to export' }); return; }
  const stamp = new Date().toISOString().slice(0, 10);
  download(`kalki-notes-${tag ? tag + '-' : ''}${stamp}.md`, r.data.markdown);
  ok(`Exported ${r.data.count} note${r.data.count === 1 ? '' : 's'} as Markdown`);
}

/** One note row, used by Today and the full list. */
export function noteRow(n, onChange) {
  const tags = (n.tags || []).map((t) => h('span.chip.sub', null, '#' + t));
  return h('div.li.note-row', null,
    h('div.col.grow', { style: { gap: '2px', minWidth: '0' } },
      h('span.sm.note-text', null, n.text),
      h('div.row.g8.xs.mut', null, h('span', null, relative(n.ts || n.date)), ...tags)),
    h('div.row.note-actions', null,
      h('button.icon-btn', { type: 'button', 'aria-label': 'Edit note', title: 'Edit', onClick: () => editNote(n, onChange) }, icon('edit', 15)),
      h('button.icon-btn', { type: 'button', 'aria-label': 'Delete note', title: 'Delete', onClick: () => deleteNote(n, onChange) }, icon('trash', 15))));
}

/** Every note, searchable and filterable by tag. onChange runs after any edit, so the caller can refresh. */
export function openNotesDialog(onChange) {
  let q = '';
  let tag = '';
  let seq = 0;
  const list = h('div.col.notes-list', { role: 'list', 'aria-live': 'polite' });
  const tagRow = h('div.row.g8', { style: { flexWrap: 'wrap' } });
  const countEl = h('span.xs.mut');

  const search = h('input.input', {
    type: 'search', placeholder: 'Search notes', 'aria-label': 'Search notes',
    onInput: (e) => { q = e.target.value; refresh(); },
  });

  const changed = () => { refresh(); loadTags(); onChange?.(); };

  async function refresh() {
    const mine = ++seq;
    const r = await notes.search(q.trim(), tag);
    if (mine !== seq) return; // a newer search has started
    if (!r.ok) { mount(list, h('div.sm.mut', null, r.message || "Notes couldn't load.")); return; }
    countEl.textContent = `${r.items.length} note${r.items.length === 1 ? '' : 's'}`;
    mount(list, ...(r.items.length
      ? r.items.map((n) => noteRow(n, changed))
      : [h('div.sm.mut', { style: { padding: '12px 0' } }, q || tag ? 'No notes match.' : 'No notes yet. Capture one from Today, or say "note that…".')]));
  }

  async function loadTags() {
    const r = await notes.tags();
    const tags = r.ok ? r.data.tags || [] : [];
    if (tag && !tags.some((t) => t.tag === tag)) tag = '';
    mount(tagRow, ...(tags.length ? [
      h('button.chip' + (tag ? '' : '.ok'), { type: 'button', 'aria-pressed': String(!tag), onClick: () => { tag = ''; loadTags(); refresh(); } }, 'All'),
      ...tags.map((t) => h('button.chip' + (tag === t.tag ? '.ok' : ''), {
        type: 'button', 'aria-pressed': String(tag === t.tag),
        onClick: () => { tag = tag === t.tag ? '' : t.tag; loadTags(); refresh(); },
      }, `#${t.tag} · ${t.count}`)),
    ] : []));
  }

  openDialog({
    title: 'Notes',
    description: 'Search, tag with #words, edit or export.',
    width: 'min(640px, 94vw)',
    initialFocus: 'input[type=search]',
    body: h('div.col.g12', null, search, tagRow, countEl, list),
    actions: [
      h('button.btn', { type: 'button', onClick: () => exportNotes(q.trim(), tag) }, icon('download', 15), 'Export as Markdown'),
    ],
  });
  loadTags();
  refresh();
}
