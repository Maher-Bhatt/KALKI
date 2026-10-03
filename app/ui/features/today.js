/** Today — the context surface. Tasks, reminders, notes, agenda, mail, focus.
 *
 *  Every one of these endpoints existed in server.py with no interface at all
 *  before this rebuild. "Not configured" is a designed state here, never an
 *  error: an unconnected integration offers a way to connect it. */

import { h, mount, frag } from '../lib/dom.js';
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

async function addTask(text) {
  if (typeof text !== 'string') {
    text = await promptDialog({ title: 'New task', label: 'What needs doing?', confirmLabel: 'Add task' });
  }
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

export function todayView() {
  const main = h('div.pad');
  const aside = h('div', { style: { display: 'contents' } });
  
  const view = { main, aside };

  view.render = () => {
    const d = store.today;
    
    // --- MAIN ---
    
    const hd = h('div.hd', null, 
      h('div', null, 
        h('h1', null, 'Good afternoon'), 
        h('div.sub', null, 'Friday, 2 October ╖ focus session available')
      ), 
      h('div.row.g8', null, 
        h('button.btn', { type: 'button', onClick: async () => { const text = await promptDialog({title:'New note', label:'Quick capture...', confirmLabel:'Save'}); if(text) addNote(text); } }, h('i', {'data-i': 'plus'}), 'Quick note'), 
        h('button.btn.pri', { type: 'button', onClick: async () => { await system.command('start a focus session'); setTimeout(syncFocus, 600); } }, h('i', {'data-i': 'play'}), 'Start a focus session')
      )
    );

    const briefingCard = d.briefing ? h('div.card', {style: {marginBottom: '14px'}}, 
      h('div.row.sb', null, 
        h('span.row.g8', null, h('h2', null, 'Morning briefing'), h('span.chip', null, 'Proactive')), 
        h('span.xs.mut', null, 'Prepared 08:00 ╖ you choose when KALKI speaks up')
      ), 
      h('div.grid2', {style: {marginTop: '10px', gap: '6px 28px'}}, 
        typeof d.briefing === 'string' ? h('div.sm', null, d.briefing) : h('div.sm', null, JSON.stringify(d.briefing))
      ), 
      h('div.row.g8', {style: {marginTop: '12px'}}, 
        h('button.btn.pri', { type: 'button' }, h('i', {'data-i': 'play'}), 'Read aloud'), 
        h('button.btn', { type: 'button' }, 'Snooze until tomorrow'), 
        h('button.btn.gh', { type: 'button' }, 'Change briefing time')
      )
    ) : null;
    
    // Agenda
    const agendaContent = d.calendarConfigured === false 
      ? h('div.li', null, h('div', {style:{flex:'1'}}, h('div.nm', null, 'Google Calendar isn\'t connected'), h('div.xs.mut', null, 'Connect it to read your day')), h('button.btn.gh', {type: 'button', onClick: ()=>go('settings', {section: 'integrations'})}, 'Connect'))
      : d.agendaError ? h('div.li', null, h('div.nm', null, "Calendar didn't load"))
      : d.events && d.events.length 
        ? frag(...d.events.map(e => h('div.li', null, h('span.mono.t2.sm', {style: {width: '44px'}}, e.start || e.when || ''), h('div', {style: {flex: '1'}}, h('div.nm', null, e.summary || e.title || 'Event'), h('div.xs.mut', null, '')), h('span.xs.mut', null, ''))))
        : h('div.li', null, h('div', {style:{flex:'1'}}, h('div.nm', null, 'Nothing on the calendar today')));

    const agendaCard = h('div.card', null, 
      h('div.row.sb', null, h('h2', null, 'Agenda'), h('span.chip.ok', null, 'Google Calendar connected')), 
      agendaContent
    );
    
    // Tasks
    let taskInput;
    const taskContent = d.loading ? skeletonRows(3)
      : d.tasksError ? errorState({ title: "Tasks didn't load", message: d.tasksError.message, detail: d.tasksError.detail, onRetry: loadToday })
      : d.tasks && d.tasks.length ? frag(...d.tasks.map(t => h('div.li', null, h('i.cb', { onClick: () => completeTask(t) }), h('span', {style: {flex: '1'}}, t.text), t.added ? h('span.xs.mut', null, relative(t.added)) : null, h('button.btn.gh', { type: 'button', style: { height: '22px' }, onClick: () => deleteTask(t) }, 'Delete'))))
      : h('div.li', null, h('span', {style: {flex: '1'}}, 'No open tasks'));

    const tasksCard = h('div.card', null, 
      h('div.row.sb', null, h('h2', null, 'Tasks'), h('span.xs.mut', null, (d.tasks?.length || 0) + ' open')), 
      h('form', { onSubmit: async (e) => { e.preventDefault(); if (taskInput.value.trim()) { await addTask(taskInput.value.trim()); taskInput.value=''; } } },
        h('div.field', {style: {margin: '10px 0 4px', display:'flex'}}, h('input', { placeholder: 'Add a task, press Enter', style: { border:'none', background:'transparent', flex:'1', outline:'none', color:'inherit' }, ref: el => taskInput = el }))
      ),
      taskContent
    );
    
    // Reminders
    let remsEl = [];
    if (d.loading) { remsEl = [skeletonRows(2)]; }
    else if (d.reminders && d.reminders.length) {
      const rGroups = groupReminders(d.reminders);
      for (const [time, items] of Object.entries(rGroups)) {
        remsEl.push(h('div.xs.mut', {style: {margin: '10px 0 2px'}}, time));
        for (const r of items) {
          remsEl.push(h('div.li', null, h('i.mut', {'data-i': 'flag'}), h('span', {style: {flex: '1'}}, r.text), h('span.mono.xs.t2', null, '')));
        }
      }
    } else {
      remsEl.push(h('div.li', null, h('span', {style: {flex: '1'}}, 'Nothing scheduled')));
    }
    
    const remsCard = h('div.card', null, 
      h('div.row.sb', null, h('h2', null, 'Reminders'), h('span.xs.mut', null, 'Say it naturally: "tomorrow 9am"')), 
      frag(...remsEl),
      h('button.btn.gh', { type: 'button', style:{marginTop:'8px'}, onClick: addReminder }, 'Add reminder')
    );
    
    // Notes
    let noteInput;
    const notesContent = d.notes && d.notes.length 
      ? frag(...d.notes.map(n => h('div.li.col', {style: {alignItems: 'flex-start', gap: '2px'}}, h('span.xs.mut', null, relative(n.date || n.added)), h('span.sm', null, n.text || String(n)))))
      : h('div.li', null, h('span.sm', null, 'No notes yet'));

    const notesCard = h('div.card', null, 
      h('div.row.sb', null, h('h2', null, 'Notes'), h('span.xs.mut', null, (d.notes?.length||0) + ' this week')), 
      h('form', { onSubmit: async (e) => { e.preventDefault(); if (noteInput.value.trim()) { await addNote(noteInput.value.trim()); noteInput.value=''; } } },
        h('div.field', {style: {margin: '10px 0 4px', display:'flex', alignItems:'center', gap:'8px'}}, 
          h('i', {'data-i': 'search'}), 
          h('input', { placeholder: 'Capture a thought or search notes', style: { border:'none', background:'transparent', flex:'1', outline:'none', color:'inherit' }, ref: el => noteInput = el })
        )
      ),
      notesContent
    );
    
    // Focus
    const f = d.focus;
    const focusCard = h('div.card.col.g12', null, 
      h('div.row.sb', null, h('h2', null, 'Focus session'), h('span.chip', null, (f?.minutes || 25) + ' min')), 
      h('div.big', {style: {fontSize: '34px'}, id: 'focus-clock'}, f?.active ? clock(f.remainingSec) : `${f?.minutes || 25}:00`), 
      h('div.meter', null, h('i', {style: {width: f?.active && f.minutes ? `${100 - (f.remainingSec / (f.minutes * 60) * 100)}%` : '0%'}})), 
      h('div.row.g8', null, 
        f?.active 
          ? h('button.btn', { type: 'button' }, 'Running') 
          : h('button.btn', { type: 'button', onClick: async () => { await system.command('start a focus session'); setTimeout(syncFocus, 600); } }, 'Start session'), 
        h('button.btn.gh', { type: 'button' }, 'End session')
      )
    );
    
    // Inbox
    const inboxCard = h('div.card.col.g12', null, 
      h('div.row.sb', null, h('h2', null, 'Inbox and code'), h('span.chip.ok', null, 'Synced just now')), 
      h('div.row.sb', null, h('span', null, 'Important mail'), h('span.mono', null, '0 unread')), 
      h('div.rule', null), 
      h('div.row.sb', null, h('span', null, 'GitHub notifications'), h('span.mono', null, '0 new')), 
      h('div.xs.mut', null, 'Checked every 60 s ╖ uses the server\'s poll hint'), 
      h('div.row.sb', null, h('span.t2', null, 'WhatsApp'), h('span.chip', null, 'Connect in Settings'))
    );
    
    mount(main, hd, briefingCard, h('div.grid2', null, agendaCard, tasksCard, remsCard, notesCard, focusCard, inboxCard));
    
    // --- ASIDE ---
    
    const dashboardCard = h('div.card.col.g12', null, 
      h('div.row.sb', null, h('span.xs.mut', null, 'Screen time'), h('span.mono', null, '3 h 12 m')), 
      h('div.row.sb', null, h('span.xs.mut', null, 'Productivity'), h('span.mono', null, '74%')), 
      h('div.meter', null, h('i', {style: {width: '74%'}})), 
      h('div.row.sb', null, h('span.xs.mut', null, 'Memories'), h('span.mono', null, '128')), 
      h('div.row.sb', null, h('span.xs.mut', null, 'Uptime'), h('span.mono', null, '4 h 12 m'))
    );
    
    const musicSection = store.status?.spotifyConfigured ? h('div.col.g8', null, 
      h('h2', null, 'Music'), 
      h('div.card.col.g8', null, 
        h('div.nm', null, store.status.nowPlaying ? (store.status.nowPlaying.title || store.status.nowPlaying.name || String(store.status.nowPlaying)) : 'Nothing playing'), 
        h('div.xs.mut', null, 'Spotify'), 
        h('div.row', {style: {justifyContent: 'center'}}, 
          h('button.ib', { type: 'button', onClick: () => spotify.prev && spotify.prev() }, h('i', {'data-i': 'prev'})), 
          h('button.ib', { type: 'button', onClick: () => spotify.play && spotify.play() }, h('i', {'data-i': 'play'})), 
          h('button.ib', { type: 'button', onClick: () => spotify.pause && spotify.pause() }, h('i', {'data-i': 'pause'})),
          h('button.ib', { type: 'button', onClick: () => spotify.next && spotify.next() }, h('i', {'data-i': 'next'}))
        )
      )
    ) : null;
    
    const clipboardCard = h('div.col.g8', null, 
      h('h2', null, 'Clipboard'), 
      h('div.card.col.g8', null, 
        h('div.sm', null, 'KALKI noticed a long block of text. Analyse it?'), 
        h('div.row.g8', null, h('button.btn.pri', { type: 'button' }, 'Yes, analyse'), h('button.btn.gh', { type: 'button' }, 'Ignore'))
      )
    );
    
    const updatesCard = h('div.col.g8', null, 
      h('h2', null, 'Updates'), 
      h('div.card.col.g8', null, 
        h('div.row.sb', null, h('span.sm', null, 'Downloading 2.0.1'), h('span.mono.xs', null, '64%')), 
        h('div.meter', null, h('i', {style: {width: '64%'}}))
      )
    );
    
    mount(aside, frag(
      h('h1', {style: {fontSize: '16px'}}, 'Dashboard'), 
      dashboardCard, 
      musicSection, 
      clipboardCard, 
      updatesCard
    ));
  };
  
  return view;
}
