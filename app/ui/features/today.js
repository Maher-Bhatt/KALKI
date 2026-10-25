/** Today — the context surface. Tasks, reminders, notes, agenda, mail, focus.
 *
 *  Executive daily briefing dashboard integrating Google Calendar, Morning Briefing,
 *  tasks, reminders, quick notes, focus session, and universal media playback. */

import { h, mount, frag } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { relative, dateTime, clock } from '../lib/format.js';
import { tasks, reminders, notes, calendar, spotify, system, media, settings } from '../api/endpoints.js';
import { store, set } from '../state/store.js';
import { emptyState, errorState, skeletonRows } from '../components/states.js';
import { promptDialog, confirmDialog, openDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';
import { go } from './router.js';

let focusTimer = null;
let loadTodayInFlight = false;

export async function loadToday() {
  if (loadTodayInFlight) return;
  loadTodayInFlight = true;
  try {
    set('today', { loading: true });
  const [t, r, n, b, c] = await Promise.all([
    tasks.list(),
    reminders.list(),
    notes.list(6),
    system.briefing().catch(() => ({ ok: false })),
    calendar.today().catch((err) => ({ ok: false, error: err }))
  ]);

  let briefingData = null;
  if (b.ok) {
    briefingData = b.data?.text || b.data || b.text;
  }

  const s = store.status;
  const isGcalConnected = (s && s.gcalConfigured === false)
    ? false
    : Boolean(c.ok && !c.data?.error && !(typeof c.data?.summary === 'string' && c.data.summary.includes('not configured')));

  const rawEvents = c.ok && Array.isArray(c.data?.events) ? c.data.events : [];

  set('today', {
    loading: false,
    tasks: t.ok ? t.items : [],
    tasksError: t.ok ? null : t,
    reminders: r.ok ? r.items : [],
    notes: n.ok ? n.items : [],
    briefing: store.today?.snoozedBriefing ? null : briefingData,
    events: rawEvents,
    calendarConfigured: isGcalConnected,
    agendaError: c.ok ? null : c,
  });
  } finally {
    loadTodayInFlight = false;
  }
}

export async function loadAgenda() {
  const s = store.status;
  if (s && s.gcalConfigured === false) {
    set('today', { events: [], calendarConfigured: false });
    return;
  }
  const r = await calendar.today().catch((err) => ({ ok: false, error: err }));
  const isConnected = (s && s.gcalConfigured === false)
    ? false
    : Boolean(r.ok && !r.data?.error && !(typeof r.data?.summary === 'string' && r.data.summary.includes('not configured')));

  set('today', {
    calendarConfigured: isConnected,
    events: r.ok && Array.isArray(r.data?.events) ? r.data.events : [],
    agendaError: r.ok ? null : r,
  });
}

/* ── Calendar formatting & connection ─────────────────────────────────── */

export function formatEventTime(startVal, endVal) {
  if (!startVal) return 'All day';

  const sStr = typeof startVal === 'string' ? startVal.trim() : '';
  const eStr = typeof endVal === 'string' ? endVal.trim() : '';

  // Google Calendar all-day events use YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(sStr) || (!sStr.includes('T') && sStr.length === 10)) {
    return 'All day';
  }

  try {
    const sDate = new Date(startVal);
    if (isNaN(sDate.getTime())) {
      return (endVal && typeof endVal === 'string') ? `${sStr} - ${eStr}` : (sStr || String(startVal));
    }

    const sFormatted = sDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });

    if (endVal) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(eStr) || (!eStr.includes('T') && eStr.length === 10)) {
        return 'All day';
      }
      const eDate = new Date(endVal);
      if (!isNaN(eDate.getTime())) {
        const eFormatted = eDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
        return `${sFormatted} - ${eFormatted}`;
      }
    }
    return sFormatted;
  } catch {
    return String(startVal);
  }
}

export async function connectGoogleCalendar() {
  try {
    ok('Opening Google Calendar authentication in your browser...');
    const r = await calendar.connect().catch(() => null);
    if (r && r.ok) {
      ok('Authorization window opened. Complete login in browser.');
      setTimeout(loadAgenda, 4000);
    } else {
      const r2 = await settings.setupTool('google');
      if (r2.ok) {
        ok('Setup opened in a new browser window');
        setTimeout(loadAgenda, 4000);
      } else {
        err(r2.message, r2.detail);
      }
    }
  } catch {
    go('settings', { section: 'integrations' });
  }
}

export function openGoogleCalendarGuide() {
  const { close } = openDialog({
    title: 'Google Calendar Setup Guide',
    description: 'Sync your daily agenda and meetings into KALKI.',
    width: '34rem',
    body: h('div.col.g12', { style: { lineHeight: '1.5', fontSize: '13px' } },
      h('div.card', { style: { background: 'var(--inset)', border: '1px solid var(--line)', padding: '12px' } },
        h('div.nm', null, h('strong', null, '1. Google Cloud Credentials')),
        h('div.xs.mut', { style: { marginTop: '4px' } }, 'Enable Google Calendar API in Google Cloud Console and place google_credentials.json into your KALKI data directory.')
      ),
      h('div.card', { style: { background: 'var(--inset)', border: '1px solid var(--line)', padding: '12px' } },
        h('div.nm', null, h('strong', null, '2. 1-Click Browser Login')),
        h('div.xs.mut', { style: { marginTop: '4px' } }, 'Click "Connect Account" below to launch the OAuth consent screen. Sign in to your Google Account.')
      ),
      h('div.card', { style: { background: 'var(--inset)', border: '1px solid var(--line)', padding: '12px' } },
        h('div.nm', null, h('strong', null, '3. Executive Briefing Integration')),
        h('div.xs.mut', { style: { marginTop: '4px' } }, 'KALKI synchronizes today’s appointments, surfaces Google Meet links, and includes your schedule in morning voice briefings.')
      )
    ),
    actions: [
      h('button.btn', { type: 'button', onClick: () => close() }, 'Dismiss'),
      h('button.btn.pri', {
        type: 'button',
        onClick: () => {
          close();
          connectGoogleCalendar();
        }
      }, h('i', { 'data-i': 'link' }), 'Connect Account')
    ]
  });
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

  let taskDraft = '';
  let noteDraft = '';

  const taskInput = h('input', {
    placeholder: 'Add a task, press Enter',
    style: { border: 'none', background: 'transparent', flex: '1', outline: 'none', color: 'inherit' },
    onInput: (e) => { taskDraft = e.target.value; },
  });

  const taskForm = h('form', {
    onSubmit: async (e) => {
      e.preventDefault();
      const val = (taskInput.value || taskDraft).trim();
      if (val) {
        taskInput.value = '';
        taskDraft = '';
        await addTask(val);
      }
    }
  }, h('div.field', { style: { margin: '10px 0 4px', display: 'flex' } }, taskInput));

  const noteInput = h('input', {
    placeholder: 'Capture a thought or search notes',
    style: { border: 'none', background: 'transparent', flex: '1', outline: 'none', color: 'inherit' },
    onInput: (e) => { noteDraft = e.target.value; },
  });

  const noteForm = h('form', {
    onSubmit: async (e) => {
      e.preventDefault();
      const val = (noteInput.value || noteDraft).trim();
      if (val) {
        noteInput.value = '';
        noteDraft = '';
        await addNote(val);
      }
    }
  }, h('div.field', { style: { margin: '10px 0 4px', display: 'flex', alignItems: 'center', gap: '8px' } }, h('i', { 'data-i': 'search' }), noteInput));

  view.render = () => {
    const d = store.today;

    // --- MAIN ---

    const hd = h('div.hd', null,
      h('div', null,
        h('h1', null, (() => { const hr = new Date().getHours(); return hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening'; })()),
        h('div.sub', null, new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) + ' · Executive Daily Briefing')
      ),
      h('div.row.g8', null,
        h('button.btn', { type: 'button', title: 'Refresh briefing and agenda', onClick: async () => { ok('Refreshing briefing…'); await loadToday(); } }, h('i', { 'data-i': 'refresh' }), 'Refresh'),
        h('button.btn', { type: 'button', onClick: async () => { const text = await promptDialog({ title: 'New note', label: 'Quick capture thought…', confirmLabel: 'Save' }); if (text) addNote(text); } }, h('i', { 'data-i': 'plus' }), 'Quick note'),
        h('button.btn.pri', { type: 'button', onClick: async () => { await system.command('start a focus session'); setTimeout(syncFocus, 600); } }, h('i', { 'data-i': 'play' }), 'Start focus session')
      )
    );

    // Executive KPI Summary Strip
    const f = d.focus;
    const statStrip = h('div', {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        marginBottom: '16px'
      }
    },
      h('div.card.col.g4', { style: { padding: '10px 14px' } },
        h('div.xs.mut', null, 'Agenda Today'),
        h('div.row.sb', { style: { alignItems: 'baseline' } },
          h('strong', { style: { fontSize: '18px' } }, d.calendarConfigured === false ? 'Unlinked' : String(d.events?.length || 0)),
          h('span.xs.t2', null, d.calendarConfigured === false ? 'Google' : 'events')
        )
      ),
      h('div.card.col.g4', { style: { padding: '10px 14px' } },
        h('div.xs.mut', null, 'Open Actions'),
        h('div.row.sb', { style: { alignItems: 'baseline' } },
          h('strong', { style: { fontSize: '18px' } }, String(d.tasks?.length || 0)),
          h('span.xs.t2', null, 'tasks')
        )
      ),
      h('div.card.col.g4', { style: { padding: '10px 14px' } },
        h('div.xs.mut', null, 'Scheduled Reminders'),
        h('div.row.sb', { style: { alignItems: 'baseline' } },
          h('strong', { style: { fontSize: '18px' } }, String(d.reminders?.length || 0)),
          h('span.xs.t2', null, 'alerts')
        )
      ),
      h('div.card.col.g4', { style: { padding: '10px 14px' } },
        h('div.xs.mut', null, 'Focus Session'),
        h('div.row.sb', { style: { alignItems: 'baseline' } },
          h('strong', { style: { fontSize: '18px' } }, f?.active ? clock(f.remainingSec) : `${f?.minutes || 25}:00`),
          h('span.chip' + (f?.active ? '.ok' : ''), { style: { fontSize: '10px', padding: '1px 5px' } }, f?.active ? 'Active' : 'Ready')
        )
      )
    );

    // Morning Briefing Card
    const briefingCard = (d.briefing && !d.snoozedBriefing) ? h('div.card', {
      style: {
        marginBottom: '16px',
        borderLeft: '4px solid var(--fil, #e08c33)',
        background: 'linear-gradient(90deg, rgba(224, 140, 51, 0.05) 0%, transparent 100%)'
      }
    },
      h('div.row.sb', null,
        h('span.row.g8', null,
          h('h2', null, 'Morning briefing'),
          h('span.chip.ok', null, 'Executive summary')
        ),
        h('span.xs.mut', null, 'Prepared 08:00 · KALKI voice synthesis ready')
      ),
      h('div', { style: { marginTop: '10px', lineHeight: '1.6', color: 'var(--text)' } },
        typeof d.briefing === 'string' ? h('div.sm', null, d.briefing) : h('div.sm', null, JSON.stringify(d.briefing))
      ),
      h('div.row.g8', { style: { marginTop: '14px' } },
        h('button.btn.pri', {
          type: 'button',
          onClick: async () => {
            ok('Reading morning briefing aloud…');
            const r = await system.command('read morning briefing');
            if (!r.ok) err(r.message, r.detail);
          }
        }, h('i', { 'data-i': 'play' }), 'Read aloud'),
        h('button.btn', {
          type: 'button',
          onClick: () => {
            store.today.snoozedBriefing = true;
            set('today', { briefing: null, snoozedBriefing: true });
            toast({ kind: 'info', text: 'Morning briefing snoozed until tomorrow' });
            view.render();
          }
        }, 'Snooze until tomorrow'),
        h('button.btn.gh', {
          type: 'button',
          onClick: () => go('settings', { section: 'routines' })
        }, 'Change briefing time')
      )
    ) : null;

    // Agenda Section
    let agendaContent;
    if (d.calendarConfigured === false) {
      agendaContent = h('div.card', {
        style: {
          background: 'linear-gradient(135deg, rgba(66, 133, 244, 0.08), rgba(219, 68, 55, 0.04), rgba(244, 180, 0, 0.04), rgba(15, 157, 88, 0.08))',
          border: '1px solid rgba(66, 133, 244, 0.25)',
          padding: '16px',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }
      },
        h('div.row.sb', null,
          h('div.row.g8', { style: { alignItems: 'center' } },
            h('div', {
              style: {
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(66, 133, 244, 0.15)',
                display: 'grid',
                placeItems: 'center',
                color: '#4285f4'
              }
            }, h('i', { 'data-i': 'calendar' })),
            h('div', null,
              h('strong', { style: { fontSize: '14px', display: 'block' } }, 'Connect Google Calendar'),
              h('div.xs.mut', null, 'Sync agenda, appointments, and Google Meet links')
            )
          ),
          h('span.chip.warn', null, 'Not connected')
        ),
        h('div.sm', { style: { color: 'var(--t2)', lineHeight: '1.4' } },
          'Connect your Google Calendar account to see today\u2019s schedule, join video calls in one click, and receive proactive morning agenda briefings.'
        ),
        h('div.row.g8', null,
          h('button.btn.pri', {
            type: 'button',
            onClick: connectGoogleCalendar
          }, h('i', { 'data-i': 'link' }), 'Connect Account'),
          h('button.btn.gh', {
            type: 'button',
            onClick: openGoogleCalendarGuide
          }, 'Setup guide'),
          h('button.btn.gh', {
            type: 'button',
            onClick: () => go('settings', { section: 'integrations' })
          }, 'Settings')
        )
      );
    } else if (d.agendaError) {
      agendaContent = h('div.li', null, h('div.nm', null, "Calendar didn't load: " + (d.agendaError.message || 'unknown error')));
    } else if (d.events && d.events.length) {
      agendaContent = frag(...d.events.map((e) => {
        const rawStart = e.start?.dateTime || e.start?.date || e.start;
        const rawEnd = e.end?.dateTime || e.end?.date || e.end;
        const timeBadge = formatEventTime(rawStart, rawEnd);
        const summary = e.summary || e.title || 'Untitled event';

        // Extract Google Meet or conference link
        const meetUrl = e.hangoutLink
          || e.conferenceData?.entryPoints?.find((ep) => ep.uri)?.uri
          || (typeof e.location === 'string' && /https?:\/\/(meet\.google\.com|teams\.microsoft\.com|zoom\.us)/i.test(e.location) ? e.location : null);

        const locationText = (typeof e.location === 'string' && e.location.trim() && e.location !== meetUrl) ? e.location.trim() : null;

        const organizer = typeof e.organizer === 'object' && e.organizer
          ? (e.organizer.displayName || e.organizer.email || '')
          : (typeof e.organizer === 'string' ? e.organizer : '');

        const description = typeof e.description === 'string' ? e.description.trim() : '';

        return h('div.li', { style: { alignItems: 'flex-start', padding: '10px 0', gap: '10px', borderBottom: '1px solid var(--lst, rgba(255,255,255,0.06))' } },
          h('span.chip', { style: { flexShrink: '0', marginTop: '1px' } }, timeBadge),
          h('div', { style: { flex: '1', minWidth: '0' } },
            h('div.nm', null, h('strong', { style: { fontWeight: '600', fontSize: '13px' } }, summary)),
            locationText ? h('div.xs.mut.row.g4', { style: { marginTop: '3px', alignItems: 'center' } },
              h('i', { 'data-i': 'flag' }),
              locationText
            ) : null,
            (organizer || description) ? h('div.xs.mut', {
              style: { marginTop: '3px', lineHeight: '1.4', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
              title: description || organizer
            }, organizer ? `Organizer: ${organizer}${description ? ' · ' + description : ''}` : description) : null
          ),
          meetUrl ? h('a.btn.btn-sm.pri', {
            href: meetUrl,
            target: '_blank',
            rel: 'noopener noreferrer',
            style: { flexShrink: '0', display: 'inline-flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }
          }, h('i', { 'data-i': 'link' }), 'Join Meet') : null
        );
      }));
    } else {
      agendaContent = h('div.li', null, h('div', { style: { flex: '1' } }, h('div.nm', null, 'Nothing on the calendar today'), h('div.xs.mut', null, 'Your daily schedule is clear')));
    }

    const agendaCard = h('div.card', null,
      h('div.row.sb', null,
        h('h2', null, 'Agenda'),
        d.calendarConfigured === false
          ? h('span.chip.warn', null, 'Not connected')
          : h('span.chip.ok', null, 'Google Calendar')
      ),
      agendaContent
    );

    // Tasks
    const taskContent = d.loading ? skeletonRows(3)
      : d.tasksError ? errorState({ title: "Tasks didn't load", message: d.tasksError.message, detail: d.tasksError.detail, onRetry: loadToday })
      : d.tasks && d.tasks.length ? frag(...d.tasks.map((t) => h('div.li', null, h('i.cb', { onClick: () => completeTask(t) }), h('span', { style: { flex: '1' } }, t.text), t.added ? h('span.xs.mut', null, relative(t.added)) : null, h('button.btn.gh', { type: 'button', style: { height: '22px' }, onClick: () => deleteTask(t) }, 'Delete'))))
      : h('div.li', null, h('span', { style: { flex: '1' } }, 'No open tasks'));

    const tasksCard = h('div.card', null,
      h('div.row.sb', null, h('h2', null, 'Tasks'), h('span.xs.mut', null, (d.tasks?.length || 0) + ' open')),
      taskForm,
      taskContent
    );

    // Reminders
    let remsEl = [];
    if (d.loading) { remsEl = [skeletonRows(2)]; }
    else if (d.reminders && d.reminders.length) {
      const rGroups = groupReminders(d.reminders);
      for (const [time, items] of Object.entries(rGroups)) {
        remsEl.push(h('div.xs.mut', { style: { margin: '10px 0 2px' } }, time));
        for (const r of items) {
          remsEl.push(h('div.li', null, h('i.mut', { 'data-i': 'flag' }), h('span', { style: { flex: '1' } }, r.text), h('span.mono.xs.t2', null, '')));
        }
      }
    } else {
      remsEl.push(h('div.li', null, h('span', { style: { flex: '1' } }, 'Nothing scheduled')));
    }

    const remsCard = h('div.card', null,
      h('div.row.sb', null, h('h2', null, 'Reminders'), h('span.xs.mut', null, 'Say it naturally: "tomorrow 9am"')),
      frag(...remsEl),
      h('button.btn.gh', { type: 'button', style: { marginTop: '8px' }, onClick: addReminder }, 'Add reminder')
    );

    // Notes
    const notesContent = d.notes && d.notes.length
      ? frag(...d.notes.map((n) => h('div.li.col', { style: { alignItems: 'flex-start', gap: '2px' } }, h('span.xs.mut', null, relative(n.date || n.added)), h('span.sm', null, n.text || String(n)))))
      : h('div.li', null, h('span.sm', null, 'No notes yet'));

    const notesCard = h('div.card', null,
      h('div.row.sb', null, h('h2', null, 'Notes'), h('span.xs.mut', null, (d.notes?.length || 0) + ' this week')),
      noteForm,
      notesContent
    );

    // Focus
    const focusCard = h('div.card.col.g12', null,
      h('div.row.sb', null, h('h2', null, 'Focus session'), h('span.chip', null, (f?.minutes || 25) + ' min')),
      h('div.big', { style: { fontSize: '34px' }, id: 'focus-clock' }, f?.active ? clock(f.remainingSec) : `${f?.minutes || 25}:00`),
      h('div.meter', null, h('i', { style: { width: f?.active && f.minutes ? `${100 - (f.remainingSec / (f.minutes * 60) * 100)}%` : '0%' } })),
      h('div.row.g8', null,
        f?.active
          ? h('button.btn.pri', { type: 'button', onClick: () => ok(`Focus session running: ${clock(f.remainingSec)} remaining`) }, 'Running')
          : h('button.btn.pri', { type: 'button', onClick: async () => { await system.command('start a focus session'); setTimeout(syncFocus, 600); } }, 'Start session'),
        h('button.btn.gh', {
          type: 'button',
          onClick: async () => {
            await system.command('stop focus session');
            clearInterval(focusTimer);
            set('today', { focus: { active: false, remainingSec: 0, minutes: 25 } });
            ok('Focus session ended');
            view.render();
          }
        }, 'End session')
      )
    );

    // Inbox
    const inboxCard = h('div.card.col.g12', null,
      h('div.row.sb', null, h('h2', null, 'Inbox and code'), h('span.chip.ok', null, 'Synced just now')),
      h('div.row.sb', null, h('span', null, 'Important mail'), h('span.mono', null, '0 unread')),
      h('div.rule', null),
      h('div.row.sb', null, h('span', null, 'GitHub notifications'), h('span.mono', null, '0 new')),
      h('div.xs.mut', null, 'Checked every 60 s · uses the server\'s poll hint'),
      h('div.row.sb', null, h('span.t2', null, 'WhatsApp'), h('span.chip', null, 'Connect in Settings'))
    );

    const wasTaskFocused = document.activeElement === taskInput;
    const wasNoteFocused = document.activeElement === noteInput;
    mount(main, hd, statStrip, briefingCard, h('div.grid2', null, agendaCard, tasksCard, remsCard, notesCard, focusCard, inboxCard));
    if (wasTaskFocused && taskInput) {
      taskInput.focus();
      taskInput.selectionStart = taskInput.selectionEnd = taskInput.value.length;
    }
    if (wasNoteFocused && noteInput) {
      noteInput.focus();
      noteInput.selectionStart = noteInput.selectionEnd = noteInput.value.length;
    }

    // --- ASIDE ---

    const st = store.status;
    const uptimeSec = st?.uptimeSec || 0;
    const uh = Math.floor(uptimeSec / 3600);
    const um = Math.floor((uptimeSec % 3600) / 60);
    const uptimeStr = uh ? `${uh} h ${um} m` : `${um} m`;
    const cpu = st?.cpu ?? '—';
    const ram = st?.ram ?? '—';
    const memCount = store.memory?.items?.length || 0;

    const dashboardCard = h('div.card.col.g12', null,
      h('div.row.sb', null, h('span.xs.mut', null, 'CPU'),      h('span.mono', null, `${cpu}%`)),
      h('div.row.sb', null, h('span.xs.mut', null, 'RAM'),      h('span.mono', null, `${ram}%`)),
      h('div.meter', null, h('i', { style: { width: `${typeof ram === 'number' ? ram : 0}%` } })),
      h('div.row.sb', null, h('span.xs.mut', null, 'Memories'), h('span.mono', null, `${memCount}`)),
      h('div.row.sb', null, h('span.xs.mut', null, 'Uptime'),   h('span.mono', null, uptimeStr))
    );

    // Music — universal (any SMTC source: Spotify / Apple Music / YT Music)
    const musicCard = h('div.card.col.g8', { id: 'today-music-panel' },
      h('div.xs.mut', { style: { textAlign: 'center', padding: '4px' } }, 'Loading…')
    );

    (async () => {
      try {
        const r = await media.now();
        if (!document.contains(musicCard)) return;
        const res = r.ok ? (r.data || r) : { status: 'NoMedia' };
        if (!res || res.status === 'NoMedia') {
          mount(musicCard, h('div.xs.mut', { style: { textAlign: 'center', padding: '4px' } }, 'Nothing playing'));
        } else {
          const playIcon = res.status === 'Playing' ? 'pause' : 'play';
          mount(musicCard,
            h('div.row', null,
              h('div', { style: { width: '32px', height: '32px', borderRadius: '4px', background: 'var(--float)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: '0' } }, h('i', { 'data-i': 'music' })),
              h('div', { style: { flex: 1, minWidth: 0 } },
                h('div.nm', { style: { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, res.title || 'Unknown'),
                h('div.xs.mut', null, res.artist || 'Unknown')
              )
            ),
            h('div.row', { style: { justifyContent: 'center', gap: '4px' } },
              h('button.ib', { type: 'button', onClick: () => media.prev() }, h('i', { 'data-i': 'prev' })),
              h('button.ib', { type: 'button', onClick: () => (res.status === 'Playing' ? media.pause() : media.play()) }, h('i', { 'data-i': playIcon })),
              h('button.ib', { type: 'button', onClick: () => media.next() }, h('i', { 'data-i': 'next' }))
            )
          );
        }
      } catch { /* non-fatal */ }
    })();

    const musicSection = h('div.col.g8', null, h('h2', null, 'Music'), musicCard);

    const clipboardCard = h('div.col.g8', null,
      h('h2', null, 'Clipboard'),
      h('div.card.col.g8', null,
        h('div.sm', null, 'KALKI noticed a long block of text. Analyse it?'),
        h('div.row.g8', null,
          h('button.btn.pri', {
            type: 'button',
            onClick: async () => {
              let clip = '';
              try { clip = await navigator.clipboard?.readText(); } catch { /* ignore */ }
              go('ask');
              if (clip && clip.trim()) {
                setTimeout(() => {
                  const composerTa = document.querySelector('textarea.composer-ta');
                  if (composerTa) {
                    composerTa.value = `Please analyse this text:\n\n${clip.trim()}`;
                    composerTa.focus();
                  }
                }, 100);
              }
            }
          }, 'Yes, analyse'),
          h('button.btn.gh', {
            type: 'button',
            onClick: () => {
              sessionStorage.setItem('kalki.ignoreClipboard', '1');
              ok('Clipboard suggestion dismissed');
              clipboardCard.style.display = 'none';
            }
          }, 'Ignore')
        )
      )
    );
    if (sessionStorage.getItem('kalki.ignoreClipboard') === '1') {
      clipboardCard.style.display = 'none';
    }

    mount(aside, frag(
      h('h1', { style: { fontSize: '16px' } }, 'Dashboard'),
      dashboardCard,
      musicSection,
      clipboardCard
    ));
  };

  // Clear the 1-second focus polling interval when this view is unmounted.
  view.cleanup = () => {
    clearInterval(focusTimer);
    focusTimer = null;
  };

  return view;
}
