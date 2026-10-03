/** Today — the context surface. Tasks, reminders, notes, agenda, mail, focus.
 *
 *  Every one of these endpoints existed in server.py with no interface at all
 *  before this rebuild. "Not configured" is a designed state here, never an
 *  error: an unconnected integration offers a way to connect it. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative, dateTime, clock } from '../lib/format.js';
import { tasks, reminders, notes, calendar, spotify, system } from '../api/endpoints.js';
import { store, set } from '../state/store.js';
import { emptyState, errorState, skeletonRows } from '../components/states.js';
import { promptDialog, confirmDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';
import { go } from './router.js';

let focusTimer = null;

export async function loadToday() {
  set('today', { loading: true });
  const [t, r, n, b] = await Promise.all([
    tasks.list(), 
    reminders.list(), 
    notes.list(6),
    system.briefing().catch(() => ({ ok: false }))
  ]);
  
  let briefingData = null;
  if (b.ok) {
    briefingData = b.data?.text || b.data || b.text;
  }

  set('today', {
    loading: false,
    tasks: t.ok ? t.items : [],
    tasksError: t.ok ? null : t,
    reminders: r.ok ? r.items : [],
    notes: n.ok ? n.items : [],
    briefing: briefingData,
  });
  loadAgenda();
}

async function loadAgenda() {
  const s = store.status;
  if (s && s.gcalConfigured === false) { set('today', { events: [], calendarConfigured: false }); return; }
  const r = await calendar.today();
  set('today', { calendarConfigured: true, events: r.ok ? (r.data.events || []) : [], agendaError: r.ok ? null : r });
}

/* ── Tasks ───────────────────────────────────────────────────────────── */

async function addTask() {
  const text = await promptDialog({ title: 'New task', label: 'What needs doing?', confirmLabel: 'Add task' });
  if (!text) return;
  const r = await tasks.add(text);
  if (r.ok) { ok('Task added'); loadToday(); } else err(r.message, r.detail);
}

async function completeTask(t) {
  const r = await tasks.complete(t.id);
  if (!r.ok) return err(r.message, r.detail);
  set('today', { tasks: store.today.tasks.filter((x) => x.id !== t.id) });
  toast({ kind: 'success', text: `Completed "${t.text}"` });
}

async function deleteTask(t) {
  if (!(await confirmDialog({ title: 'Delete this task?', description: t.text, confirmLabel: 'Delete' }))) return;
  const r = await tasks.remove(t.id);
  if (r.ok) { set('today', { tasks: store.today.tasks.filter((x) => x.id !== t.id) }); ok('Task deleted'); }
  else err(r.message, r.detail);
}

function taskRow(t) {
  return h('div.row', null,
    h('button.icon-btn', { type: 'button', 'aria-label': `Complete ${t.text}`, title: 'Complete', onClick: () => completeTask(t) }, icon('check', 16)),
    h('span', { style: { flex: '1', minWidth: '0' } }, t.text),
    t.added ? h('span.t-meta.muted', null, relative(t.added)) : null,
    h('button.icon-btn', { type: 'button', 'aria-label': `Delete ${t.text}`, title: 'Delete', onClick: () => deleteTask(t) }, icon('trash', 16)),
  );
}

/* ── Reminders ───────────────────────────────────────────────────────── */

async function addReminder() {
  const text = await promptDialog({ title: 'New reminder', label: 'Remind me to…', confirmLabel: 'Next' });
  if (!text) return;
  const due = await promptDialog({ title: 'When?', label: 'Say it however you like — "in 20 minutes", "tomorrow at 9"', confirmLabel: 'Add reminder' });
  if (!due) return;
  const r = await reminders.add(text, due);
  if (r.ok) { ok('Reminder set'); loadToday(); } else err(r.message, r.detail);
}

function groupReminders(rems) {
  const groups = {};
  for (const r of rems) {
    const time = dateTime(r.due) || r.due || 'Sometime';
    if (!groups[time]) groups[time] = [];
    groups[time].push(r);
  }
  return groups;
}

/* ── Notes ───────────────────────────────────────────────────────────── */

async function addNote(text) {
  if (!text) return;
  const r = await notes.add(text);
  if (r.ok) { ok('Note saved'); loadToday(); } else err(r.message, r.detail);
}

/* ── Focus ───────────────────────────────────────────────────────────── */

export async function syncFocus() {
  const r = await system.focus();
  if (!r.ok) return;
  set('today', { focus: r.data });
  
  clearInterval(focusTimer);
  if (r.data.active) {
    focusTimer = setInterval(async () => {
      const fr = await system.focus();
      if (fr.ok && fr.data.active) {
        const el = document.getElementById('focus-clock');
        if (el) el.textContent = clock(fr.data.remainingSec);
        store.today.focus = fr.data;
      } else {
        clearInterval(focusTimer);
        syncFocus();
      }
    }, 1000);
  }
}

/* ── View ────────────────────────────────────────────────────────────── */

function section(title, actionLabel, onAction, body) {
  return h('section.panel', null,
    h('div.panel-head', null,
      h('h2', null, title),
      h('span.spacer'),
      onAction ? h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: onAction }, icon('plus', 14), actionLabel) : null,
    ),
    h('div.panel-body', null, body),
  );
}

export function todayView() {
  const body = h('div.view-body.scroll');
  const view = h('section.view', { 'aria-label': 'Today' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Today'),
      h('span.spacer'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: loadToday }, icon('refresh', 14), 'Refresh'),
    ),
    body,
  );

  view.render = () => {
    const d = store.today;
    body.innerHTML = '';
    
    // Briefing Card
    if (d.briefing) {
      body.appendChild(h('section.panel', { style: { marginBottom: 'var(--space-6)', background: 'var(--surface-float)' } },
        h('div.panel-body', null, 
          h('div.inline', { style: { marginBottom: 'var(--space-4)', color: 'var(--text-muted)' } }, icon('spark', 16), h('strong', null, 'Morning Briefing')),
          h('div.t-body-sm', { style: { whiteSpace: 'pre-wrap' } }, typeof d.briefing === 'string' ? d.briefing : JSON.stringify(d.briefing))
        )
      ));
    }

    const grid = h('div.grid-2');

    // Tasks
    grid.appendChild(section('Tasks', 'Add', addTask,
      d.loading ? skeletonRows(3)
        : d.tasksError ? errorState({ title: "Tasks didn't load", message: d.tasksError.message, detail: d.tasksError.detail, onRetry: loadToday })
        : d.tasks.length ? h('div.stack', null, ...d.tasks.map(taskRow))
        : emptyState({
            iconName: 'check', title: 'No open tasks',
            body: 'Tasks you add here are the same ones KALKI creates when you ask it to remember something out loud.',
            actions: [h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: addTask }, 'Add a task')],
          })));

    // Reminders
    const rGroups = groupReminders(d.reminders || []);
    const rEls = [];
    for (const [time, items] of Object.entries(rGroups)) {
      rEls.push(h('div.t-label.muted', { style: { marginTop: 'var(--space-3)' } }, time));
      for (const r of items) {
        rEls.push(h('div.row', null,
          icon('clock', 16),
          h('span', { style: { flex: '1', minWidth: '0' } }, r.text)
        ));
      }
    }

    grid.appendChild(section('Reminders', 'Add', addReminder,
      d.loading ? skeletonRows(2)
        : d.reminders.length ? h('div.stack', null, ...rEls)
        : emptyState({
            iconName: 'clock', title: 'Nothing scheduled',
            body: 'KALKI speaks reminders when they fall due, whether or not this window is open.',
            actions: [h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: addReminder }, 'Set a reminder')],
          })));

    // Agenda
    grid.appendChild(section('Agenda', null, null,
      d.calendarConfigured === false
        ? emptyState({
            iconName: 'calendar', title: 'Google Calendar isn\u2019t connected',
            body: 'Connect it and KALKI will read your day out loud and answer questions about it.',
            actions: [h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => go('settings', { section: 'integrations' }) }, 'Connect')],
          })
        : d.agendaError ? errorState({ title: "Calendar didn't load", message: d.agendaError.message, detail: d.agendaError.detail, onRetry: loadAgenda })
        : d.events.length
          ? h('div.stack', null, ...d.events.map((e) => h('div.row', null,
              icon('calendar', 16),
              h('span', { style: { flex: '1', minWidth: '0' } }, e.summary || e.title || 'Event'),
              h('span.t-meta.muted', null, e.start || e.when || ''))))
          : emptyState({ iconName: 'calendar', title: 'Nothing on the calendar today', body: 'A clear day. KALKI will speak anything that appears.' })));

    // Notes
    grid.appendChild(section('Notes', null, null,
      h('div.stack', null,
        h('form.row', { 
            style: { borderBottom: '1px solid var(--line-subtle)', paddingBottom: 'var(--space-4)' },
            onSubmit: async (e) => {
              e.preventDefault();
              const input = e.target.elements.note;
              const text = input.value.trim();
              if (text) {
                input.value = '';
                await addNote(text);
              }
            }
          },
          h('input.t-body-sm', { name: 'note', placeholder: 'Quick capture...', style: { flex: '1', border: 'none', background: 'var(--surface-inset)', padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-sm)', color: 'var(--text)', outline: 'none' } }),
          h('button.btn.btn-sm.btn-secondary', { type: 'submit' }, 'Save')
        ),
        d.notes.length
          ? h('div.stack', { style: { paddingTop: 'var(--space-2)' } }, ...d.notes.map((n) => h('div.row', null,
              icon('note', 16),
              h('span', { style: { flex: '1', minWidth: '0' } }, n.text || String(n)),
              h('span.t-meta.muted', null, relative(n.date || n.added)))))
          : emptyState({
              iconName: 'note', title: 'No notes yet',
              body: 'Quick captures you or KALKI jot down. Searchable from the command palette.',
            })
      )));

    // Focus
    const f = d.focus;
    grid.appendChild(section('Focus', null, null,
      h('div.stack', null,
        h('div.inline', null,
          h('span.t-display.num', { id: 'focus-clock' }, f?.active ? clock(f.remainingSec) : `${f?.minutes || 25}:00`),
          h('span.spacer'),
          f?.active
            ? h('span.chip.chip-success', null, 'Running')
            : h('button.btn.btn-sm.btn-secondary', {
                type: 'button',
                onClick: async () => { await system.command('start a focus session'); setTimeout(syncFocus, 600); },
              }, 'Start ' + (f?.minutes || 25) + ' minutes'),
        ),
        h('p.t-body-sm.muted', null, 'A focus session quiets KALKI\u2019s voice and notifications until it ends.'),
      )));

    // Now playing — only when Spotify is actually linked
    if (store.status?.spotifyConfigured) {
      const np = store.status.nowPlaying;
      grid.appendChild(section('Music', null, null,
        h('div.stack', null,
          h('p.t-body-sm', null, np ? (np.title || np.name || String(np)) : 'Nothing playing right now.'),
          h('div.inline', null,
            h('button.icon-btn', { type: 'button', 'aria-label': 'Play', title: 'Play', onClick: () => spotify.play() }, icon('play', 16)),
            h('button.icon-btn', { type: 'button', 'aria-label': 'Pause', title: 'Pause', onClick: () => spotify.pause() }, icon('pause', 16)),
            h('button.icon-btn', { type: 'button', 'aria-label': 'Next track', title: 'Next', onClick: () => spotify.next() }, icon('next', 16)),
          ),
        )));
    }

    body.appendChild(grid);
  };

  return view;
}
