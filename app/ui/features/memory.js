/** Memory â€” built entirely on the semantic store.
 *
 *  Organizes memories by topic (Preferences, Projects, Work, Personal, Music, Tech),
 *  with instant keyword & topic search, topic filter chips, importance rating,
 *  pinning, and deletion with confirmation. */

import { h, mount, debounce } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative } from '../lib/format.js';
import { memory } from '../api/endpoints.js';
import { store, set } from '../state/store.js';
import { emptyState, errorState, skeletonRows } from '../components/states.js';
import { openDialog, confirmDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';

export const TYPES = ['fact', 'preference', 'event', 'person', 'pinned'];
export const STANDARD_TOPICS = ['All', 'Preferences', 'Projects', 'Work', 'Personal', 'Music', 'Tech'];

export function extractTopic(item) {
  if (!item) return 'General';

  // 1. Direct topic property or metadata
  if (item.topic && typeof item.topic === 'string' && item.topic.trim()) {
    return normalizeTopic(item.topic);
  }
  if (item.metadata?.topic && typeof item.metadata.topic === 'string' && item.metadata.topic.trim()) {
    return normalizeTopic(item.metadata.topic);
  }

  // 2. Check tags array
  const tags = Array.isArray(item.tags) ? item.tags.map((t) => String(t).trim().toLowerCase()) : [];
  for (const t of tags) {
    if (t === 'pref' || t === 'preference' || t === 'preferences') return 'Preferences';
    if (t === 'proj' || t === 'project' || t === 'projects') return 'Projects';
    if (t === 'work' || t === 'job' || t === 'career' || t === 'client' || t === 'office' || t === 'business') return 'Work';
    if (t === 'person' || t === 'personal' || t === 'life' || t === 'home' || t === 'health' || t === 'family') return 'Personal';
    if (t === 'music' || t === 'audio' || t === 'spotify' || t === 'song') return 'Music';
    if (t === 'tech' || t === 'technology' || t === 'code' || t === 'dev' || t === 'coding' || t === 'software') return 'Tech';
  }

  // 3. Check memory type
  const type = String(item.type || '').toLowerCase();
  if (type === 'preference') return 'Preferences';
  if (type === 'project') return 'Projects';
  if (type === 'person') return 'Personal';

  // 4. Content / heuristic analysis of text
  const text = String(item.text || '').toLowerCase();
  if (/\b(music|spotify|song|album|artist|track|playlist|guitar|piano|beats|audio|band)\b/i.test(text)) {
    return 'Music';
  }
  if (/\b(python|javascript|typescript|api|server|docker|linux|database|model|ai|llm|terminal|cpu|ram|backend|frontend|framework|deploy)\b/i.test(text)) {
    return 'Tech';
  }
  if (/\b(office|meeting|client|company|boss|deadline|colleague|job|salary|corp|contract|invoice)\b/i.test(text)) {
    return 'Work';
  }
  if (/\b(project|repo|repository|codebase|app|build|milestone|sprint|release|v2|refactor|git)\b/i.test(text)) {
    return 'Projects';
  }
  if (/\b(family|friend|wife|husband|mom|dad|kid|child|birthday|anniversary|home|doctor|personal|health|hobby)\b/i.test(text)) {
    return 'Personal';
  }
  if (/\b(prefer|preference|favourite|favorite|dislike|hate|love|always want|never use|call me|my style|pronoun)\b/i.test(text)) {
    return 'Preferences';
  }

  // If there are other custom tags, use the first tag capitalized
  if (tags.length > 0 && tags[0]) {
    return tags[0].charAt(0).toUpperCase() + tags[0].slice(1);
  }

  return 'General';
}

function normalizeTopic(raw) {
  const s = String(raw).trim();
  const lower = s.toLowerCase();
  if (lower.includes('pref')) return 'Preferences';
  if (lower.includes('proj')) return 'Projects';
  if (lower.includes('work') || lower.includes('job')) return 'Work';
  if (lower.includes('person')) return 'Personal';
  if (lower.includes('music') || lower.includes('audio')) return 'Music';
  if (lower.includes('tech') || lower.includes('code')) return 'Tech';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export async function loadMemory() {
  set('memory', { loading: true, error: null });
  const r = await memory.list();
  if (!r.ok) { set('memory', { loading: false, error: r }); return; }
  set('memory', { loading: false, items: r.items || [] });
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
  let textEl, typeEl, impEl, impOut, topicEl;
  const existingTopic = existing ? extractTopic(existing) : 'Preferences';
  const EDIT_TOPICS = ['Preferences', 'Projects', 'Work', 'Personal', 'Music', 'Tech', 'General'];

  const submit = async () => {
    const selectedTopic = topicEl ? topicEl.value : 'General';
    const payload = {
      text: textEl.value.trim(),
      tags: [selectedTopic.toLowerCase()],
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
        h('label', { for: 'mem-topic' }, 'Topic'),
        h('select.select', { id: 'mem-topic', ref: (el) => { topicEl = el; } },
          ...EDIT_TOPICS.map((t) => h('option', { value: t, selected: existingTopic.toLowerCase() === t.toLowerCase() }, t))),
      ),
      h('div.field', null,
        h('label', { for: 'mem-type' }, 'Type'),
        h('select.select', { id: 'mem-type', ref: (el) => { typeEl = el; } },
          ...TYPES.map((t) => h('option', { value: t, selected: (existing?.type || 'fact') === t }, t === 'pinned' ? 'pinned â€” always retrieved' : t))),
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
  const r = await memory.update({ id: m.id, text: m.text, tags: m.tags, importance: m.importance, type: next });
  if (r.ok) { ok(next === 'pinned' ? 'Pinned â€” KALKI will always retrieve this' : 'Unpinned'); loadMemory(); }
  else err(r.message, r.detail);
}

async function remove(m) {
  const preview = m.text.length > 70 ? m.text.slice(0, 70) + 'â€¦' : m.text;
  if (!(await confirmDialog({
    title: 'Delete memory?',
    description: `Are you sure you want KALKI to forget: "${preview}"?`,
    confirmLabel: 'Delete'
  }))) return;

  const snapshot = { ...m };
  const r = await memory.remove(m.id);
  if (!r.ok) return err(r.message, r.detail);
  set('memory', { items: store.memory.items.filter((x) => x.id !== m.id) });
  toast({
    kind: 'success', text: 'Memory deleted',
    action: {
      label: 'Undo', run: async () => {
        const back = await memory.add({
          text: snapshot.text,
          importance: snapshot.importance,
          type: snapshot.type,
          tags: snapshot.tags,
        });
        if (back.ok) { ok('Memory restored'); loadMemory(); }
      }
    },
  });
}

export function memoryView() {
  const main = h('div.pad');
  const aside = h('div');

  let quickText = '';
  let quickTopic = 'Preferences';
  let quickType = 'preference';
  let quickImp = 5;

  const quickTa = h('textarea', {
    style: { width: '100%', background: 'transparent', border: 'none', outline: 'none', resize: 'none', color: 'inherit', fontFamily: 'inherit' },
    placeholder: 'I prefer concise answers with code snippets...',
    onInput: (e) => { quickText = e.target.value; },
  });

  const searchInput = h('input', {
    type: 'search',
    placeholder: 'Filter memories instantly by keyword or topicâ€¦',
    style: { border: 'none', background: 'transparent', outline: 'none', flex: '1', color: 'inherit', fontSize: '13px' },
    onInput: debounce((e) => {
      set('memory', { query: e.target.value });
      view.render();
    }, 60)
  });

  const view = { main, aside };

  view.render = () => {
    const m = store.memory;
    const q = (m.query || '').trim().toLowerCase();
    const activeTopic = m.activeTopic || 'All';
    searchInput.value = m.query || '';

    const allItems = m.items || [];

    // Calculate dynamic topic counts
    const topicCounts = { All: allItems.length };
    for (const item of allItems) {
      const top = extractTopic(item);
      topicCounts[top] = (topicCounts[top] || 0) + 1;
    }

    // Standard topics + any extra detected topics
    const extraTopics = Object.keys(topicCounts).filter((t) => !STANDARD_TOPICS.includes(t) && t !== 'General');
    if (topicCounts['General'] && !extraTopics.includes('General')) extraTopics.push('General');
    const visibleTopics = [...STANDARD_TOPICS, ...extraTopics];

    // Filter by topic chip and keyword query
    const filtered = allItems
      .filter((x) => {
        const itemTopic = extractTopic(x);

        // Filter by topic chip
        if (activeTopic !== 'All' && itemTopic.toLowerCase() !== activeTopic.toLowerCase()) {
          return false;
        }

        // Filter by instant search query
        if (!q) return true;
        const textMatch = String(x.text || '').toLowerCase().includes(q);
        const topicMatch = itemTopic.toLowerCase().includes(q);
        const tagMatch = Array.isArray(x.tags) && x.tags.some((t) => String(t).toLowerCase().includes(q));
        const typeMatch = String(x.type || '').toLowerCase().includes(q);
        return textMatch || topicMatch || tagMatch || typeMatch;
      })
      .sort((a, b) => (Number(b.type === 'pinned') - Number(a.type === 'pinned')) || ((b.importance ?? 5) - (a.importance ?? 5)));

    // MAIN
    const hd = h('div.hd', null,
      h('div', null,
        h('h1', null, 'Memory'),
        h('div.sub', null, 'Knowledge & facts KALKI keeps about you. Stored locally.')
      ),
      h('button.btn.pri', { type: 'button', onClick: () => editor(null) }, h('i', { 'data-i': 'plus' }), 'Add memory')
    );

    const banner = m.legacyCount ?
      h('div.card.row.sb', { style: { marginBottom: '16px' } },
        h('span.sm', null, h('b', { style: { fontWeight: '500' } }, `${m.legacyCount} older memories`), ' from the previous version can be imported with full metadata.'),
        h('div.row.g8', null,
          h('button.btn.pri', { type: 'button', onClick: importLegacy }, `Import ${m.legacyCount} memories`),
          h('button.btn.gh', { type: 'button', onClick: () => { set('memory', { legacyCount: 0 }); sessionStorage.setItem('kalki.legacyMemoryDone', '1'); view.render(); } }, 'Dismiss')
        )
      ) : null;

    // Search bar
    const searchRow = h('div.row.g8', { style: { marginBottom: '12px' } },
      h('div.field', { style: { flex: '1', padding: '6px 12px' } },
        h('i', { 'data-i': 'search' }),
        searchInput
      ),
      q ? h('button.btn.gh', {
        type: 'button',
        title: 'Clear search',
        onClick: () => {
          searchInput.value = '';
          set('memory', { query: '' });
          view.render();
        }
      }, 'Clear') : null
    );

    // Topic Filter Chips
    const topicChips = h('div.row.g8', {
      style: {
        marginBottom: '16px',
        flexWrap: 'wrap',
        gap: '6px',
        alignItems: 'center'
      }
    },
      ...visibleTopics.map((topic) => {
        const isSelected = activeTopic.toLowerCase() === topic.toLowerCase();
        const count = topicCounts[topic] ?? 0;
        return h('button.chip' + (isSelected ? '.ok' : ''), {
          type: 'button',
          style: {
            cursor: 'pointer',
            padding: '4px 10px',
            borderRadius: '14px',
            fontWeight: isSelected ? '600' : '400',
            background: isSelected ? 'rgba(76, 192, 97, 0.16)' : 'var(--raised)',
            borderColor: isSelected ? 'rgba(76, 192, 97, 0.4)' : 'var(--line)',
            color: isSelected ? 'var(--text)' : 'var(--t2)',
            transition: 'all 0.12s ease'
          },
          onClick: () => {
            set('memory', { activeTopic: topic });
            view.render();
          }
        },
          topic,
          h('span.xs.mut', { style: { marginLeft: '4px', opacity: '0.75' } }, `(${count})`)
        );
      })
    );

    let listNodes = [];
    if (m.loading) {
      listNodes.push(skeletonRows(3));
    } else if (m.error) {
      listNodes.push(errorState({
        title: "Memory didn't load",
        message: m.error.kind === 'unavailable'
          ? 'The embedding backend is unavailable, so semantic search is limited. Your memories are safe.'
          : m.error.message,
        detail: m.error.detail, onRetry: loadMemory,
      }));
    } else if (!m.items.length && !q) {
      listNodes.push(emptyState({
        iconName: 'memory',
        title: 'KALKI remembers nothing yet',
        body: 'Add preferences, work context, and personal facts you want KALKI to retain.',
      }));
    } else if (!filtered.length) {
      listNodes.push(emptyState({
        iconName: 'search',
        title: 'No memories match that filter',
        body: `Nothing matches topic "${activeTopic}"${q ? ` and search "${m.query}"` : ''}.`,
        actions: [h('button.btn.btn-sm.btn-ghost', {
          type: 'button',
          onClick: () => {
            searchInput.value = '';
            set('memory', { query: '', activeTopic: 'All' });
            view.render();
          }
        }, 'Reset filters')],
      }));
    } else {
      filtered.forEach((x) => {
        const pinned = x.type === 'pinned';
        const itemTopic = extractTopic(x);
        const imp = x.importance ?? 5;
        const stars = Math.max(1, Math.min(5, Math.round(imp / 2)));

        listNodes.push(
          h('div.li', {
            style: {
              display: 'flex',
              alignItems: 'flex-start',
              padding: '12px 14px',
              gap: '12px',
              borderBottom: '1px solid var(--lst, rgba(255,255,255,0.06))'
            }
          },
            // Topic badge & Pinned badge
            h('div.col.g4', { style: { flexShrink: '0', alignItems: 'flex-start', minWidth: '85px' } },
              h('span.chip', { style: { fontSize: '11px', textTransform: 'capitalize' } }, itemTopic),
              pinned ? h('span.chip.ok', { style: { fontSize: '10px', padding: '1px 5px' } }, h('i', { 'data-i': 'pin' }), 'Pinned') : null
            ),
            // Memory text & details
            h('div', { style: { flex: '1', minWidth: '0' } },
              h('div.sm', { style: { wordBreak: 'break-word', fontSize: '13.5px', lineHeight: '1.5', color: 'var(--text)' } }, x.text),
              h('div.row.g12', { style: { marginTop: '6px', alignItems: 'center', flexWrap: 'wrap' } },
                // Importance indicator (stars and meter)
                h('div.row.g4', { style: { alignItems: 'center' }, title: `Importance: ${imp}/10` },
                  h('span', { style: { color: 'var(--warnt, #e08c33)', fontSize: '12px', letterSpacing: '1px' } },
                    'â˜…'.repeat(stars) + 'â˜†'.repeat(5 - stars)
                  ),
                  h('div.meter', { style: { width: '36px', height: '4px', margin: '0 4px' } },
                    h('i', { style: { width: `${imp * 10}%` } })
                  ),
                  h('span.xs.mut', null, `${imp}/10`)
                ),
                // Timestamp / relative date
                x.created_at ? h('span.xs.mut', null, relative(x.created_at)) : null,
                // Tags
                (x.tags && x.tags.length) ? h('span.xs.mut', null, x.tags.map((t) => `#${t}`).join(' ')) : null
              )
            ),
            // Actions
            h('div.row.g4', { style: { flexShrink: '0' } },
              h('button.ib', {
                type: 'button',
                title: pinned ? 'Unpin from prompt' : 'Pin â€” always included in prompt',
                onClick: () => togglePin(x)
              }, h('i', { 'data-i': 'pin', style: pinned ? { color: 'var(--okt, #4cc061)' } : undefined })),
              h('button.ib', {
                type: 'button',
                title: 'Edit memory',
                onClick: () => editor(x)
              }, h('i', { 'data-i': 'pen' })),
              h('button.ib', {
                type: 'button',
                title: 'Delete memory',
                onClick: () => remove(x)
              }, h('i', { 'data-i': 'trash', style: { color: 'var(--dng)' } }))
            )
          )
        );
      });
    }

    const memCard = h('div.card', { id: 'mem', style: { padding: '0', overflow: 'hidden' } }, ...listNodes);

    // Quick Add Memory Card
    const EDIT_TOPICS = ['Preferences', 'Projects', 'Work', 'Personal', 'Music', 'Tech', 'General'];
    const quickAddCard = h('div.card.in.col.g12', { style: { marginBottom: '18px' } },
      h('div.row.sb', null,
        h('h2', null, 'Quick add memory'),
        h('span.xs.mut', null, 'Saved to semantic store')
      ),
      h('div.field', { style: { minHeight: '56px', alignItems: 'flex-start' } },
        quickTa
      ),
      h('div.row.g8', { style: { flexWrap: 'wrap', alignItems: 'center' } },
        h('select', {
          className: 'btn',
          style: { appearance: 'none', background: 'transparent' },
          onInput: (e) => { quickTopic = e.target.value; }
        },
          ...EDIT_TOPICS.map((t) => h('option', { value: t, selected: quickTopic === t }, `Topic: ${t}`))
        ),
        h('select', {
          className: 'btn',
          style: { appearance: 'none', background: 'transparent' },
          onInput: (e) => { quickType = e.target.value; }
        },
          ...TYPES.map((t) => h('option', { value: t, selected: quickType === t }, `Type: ${t}`))
        ),
        h('span.xs.mut', null, 'Importance'),
        h('input', {
          type: 'range', min: '1', max: '10', value: String(quickImp),
          style: { width: '80px' },
          onInput: (e) => {
            quickImp = Number(e.target.value);
            const badge = quickAddCard.querySelector('#impn');
            if (badge) badge.textContent = String(quickImp);
          }
        }),
        h('span.imp', { id: 'impn' }, String(quickImp)),
        h('div.sp', { style: { flex: '1' } }),
        h('button.btn.pri', {
          type: 'button',
          onClick: async () => {
            if (!quickText.trim()) return;
            const r = await memory.add({
              text: quickText.trim(),
              tags: [quickTopic.toLowerCase()],
              type: quickType,
              importance: quickImp
            });
            if (r.ok) {
              ok('Memory added');
              quickText = '';
              if (quickTa) quickTa.value = '';
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

    const wasSearchFocused = document.activeElement === searchInput;
    const wasQuickFocused = document.activeElement === quickTa;
    const searchPos = searchInput.selectionStart;
    const quickPos = quickTa?.selectionStart || 0;

    mount(main, hd, banner, quickAddCard, searchRow, topicChips, memCard);

    if (wasSearchFocused) {
      searchInput.focus();
      try { searchInput.selectionStart = searchInput.selectionEnd = searchPos; } catch {}
    }
    if (wasQuickFocused && quickTa) {
      quickTa.focus();
      try { quickTa.selectionStart = quickTa.selectionEnd = quickPos; } catch {}
    }

    // ASIDE
    const totalMem = allItems.length;
    const pinnedCount = allItems.filter((x) => x.type === 'pinned').length;

    mount(aside,
      h('h1', { style: { fontSize: '16px' } }, 'Overview'),
      h('div.card.col.g12', null,
        h('div.row.sb', null, h('span.xs.mut', null, 'Total memories'), h('span.mono', null, String(totalMem))),
        h('div.row.sb', null, h('span.xs.mut', null, 'Pinned items'), h('span.mono', null, String(pinnedCount))),
        h('div.row.sb', null, h('span.xs.mut', null, 'Active topic'), h('span.chip', null, activeTopic)),
        h('div.row.sb', null, h('span.xs.mut', null, 'Search mode'), h('span.chip.ok', null, m.error?.kind === 'unavailable' ? 'Text fallback' : 'Semantic'))
      ),
      h('div.card.col.g8', null,
        h('h2', null, 'Topic Organization'),
        h('div.sm.t2', null, 'Memories are categorized by topic: Preferences, Projects, Work, Personal, Music, and Tech. KALKI uses relevant topics when crafting answers.')
      ),
      h('div.card.col.g8', null,
        h('h2', null, 'Pinned vs Semantic'),
        h('div.sm.t2', null, 'Pinned memories are always injected into KALKIâ€™s system context. Other memories are retrieved dynamically by similarity to your conversation.')
      )
    );
  };

  return view;
}

