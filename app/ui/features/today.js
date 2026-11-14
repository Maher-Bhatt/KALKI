/** Today — the context surface. Tasks, reminders, notes, agenda, mail, focus.
 *
 *  Your day in order of urgency, integrating Google Calendar, Morning Briefing,
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
  // The briefing checks live sources, so it loads on its own and never holds up the rest.
  loadBriefing();
  const [t, r, n, c] = await Promise.all([
    tasks.list(),
    reminders.list(),
    notes.list(6),
    calendar.today().catch((err) => ({ ok: false, error: err }))
  ]);

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
    events: rawEvents,
    calendarConfigured: isGcalConnected,
    agendaError: c.ok ? null : c,
  });
  } finally {
    loadTodayInFlight = false;
  }
}

const SNOOZE_KEY = 'kalki.briefingSnoozedOn';

function briefingSnoozed() {
  try { return localStorage.getItem(SNOOZE_KEY) === new Date().toDateString(); } catch { return false; }
}

export async function loadBriefing() {
  set('today', { briefingLoading: true });
  const b = await system.briefing().catch((e) => ({ ok: false, message: e?.message }));
  set('today', {
    briefingLoading: false,
    briefing: b.ok ? (b.data?.briefing || null) : null,
    briefingError: b.ok ? null : (b.message || "The briefing couldn't load."),
  });
}

const STATUS_CHIP = {
  empty: ['', 'Nothing today'],
  unavailable: ['.sub', 'Not set up'],
  failed: ['.warn', "Couldn't load"],
  timeout: ['.warn', 'Too slow'],
};

function briefingCardView(d, rerender) {
  if (briefingSnoozed()) return null;
  const sections = d.briefing?.sections || [];
  let body;
  if (d.briefingLoading && !d.briefing) {
    body = h('div.sm.mut', null, 'Putting your briefing together…');
  } else if (d.briefingError) {
    body = h('div.sm.mut', null, d.briefingError);
  } else if (!sections.length) {
    body = h('div.sm.mut', null, 'The briefing has nothing to cover. Choose its sections in Settings.');
  } else {
    body = h('div.col.g8', null, ...sections.map((sec) => {
      const [cls, label] = STATUS_CHIP[sec.status] || ['', ''];
      return h('div.briefing-row', null,
        h('div.row.g8', null, h('strong.sm', null, sec.title), label ? h('span.chip' + cls, null, label) : null),
        h('div.sm' + (sec.status === 'ok' ? '' : '.mut'), null, sec.text));
    }));
  }
  return h('div.card', { style: { marginBottom: '16px' } },
    h('div.row.sb', null,
      h('h2', null, 'Your briefing'),
      h('button.btn.gh', { type: 'button', 'aria-label': 'Refresh the briefing', onClick: () => loadBriefing() },
        h('i', { 'data-i': 'refresh' }), d.briefingLoading ? 'Refreshing…' : 'Refresh')),
    h('div', { style: { marginTop: '10px', lineHeight: '1.6' } }, body),
    h('div.row.g8', { style: { marginTop: '14px' } },
      h('button.btn.pri', {
        type: 'button',
        disabled: !d.briefing,
        onClick: async () => {
          const r = await system.command('read my briefing');
          if (!r.ok) err(r.message, r.detail);
        }
      }, h('i', { 'data-i': 'play' }), 'Read aloud'),
      h('button.btn', {
        type: 'button',
        onClick: () => {
          try { localStorage.setItem(SNOOZE_KEY, new Date().toDateString()); } catch { /* private mode */ }
          toast({ kind: 'info', text: "Briefing hidden until tomorrow" });
          rerender();
        }
      }, 'Hide until tomorrow'),
      h('button.btn.gh', { type: 'button', onClick: () => go('settings', { section: 'briefing' }) }, 'Choose sections')
    ));
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
        h('div.nm', null, h('strong', null, '3. Morning briefing')),
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
  const due = await promptDialog({ title: 'When?', label: 'Say it however you like: "in 20 minutes", "tomorrow at 9am", "every weekday at 8am"', confirmLabel: 'Add reminder' });
  if (!due) return;
  const r = await reminders.add(text, due);
  if (r.ok) { ok(r.data?.when ? `Reminder set for ${r.data.when}` : 'Reminder set'); loadToday(); } else err(r.message, r.detail);
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
    'aria-label': 'Add a task',
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
    'aria-label': 'Add a note',
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
        h('h1', { id: 'view-title', tabindex: '-1' }, (() => { const hr = new Date().getHours(); return hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening'; })()),
        h('div.sub', null, new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))
      ),
      h('div.row.g8', null,
        h('button.btn', { type: 'button', title: 'Refresh Today', onClick: async () => { await loadToday(); ok('Up to date'); } }, h('i', { 'data-i': 'refresh' }), 'Refresh'),
        h('button.btn', { type: 'button', onClick: async () => { const text = await promptDialog({ title: 'New note', label: 'Note', confirmLabel: 'Save' }); if (text) addNote(text); } }, h('i', { 'data-i': 'plus' }), 'Quick note')
      )
    );

    const f = d.focus;

    // What needs you right now comes first, and only appears when something does.
    const dueNow = (d.reminders || []).filter((r) => r.due && new Date(r.due).getTime() <= Date.now());
    const nowItems = [];
    for (const r of dueNow.slice(0, 3)) {
      nowItems.push(h('div.today-alert', null, h('i', { 'data-i': 'flag' }),
        h('div.grow', null, h('strong', null, r.text), h('div.xs.mut', null, 'Reminder due'))));
    }
    const nowBlock = nowItems.length ? h('div.today-now', null, ...nowItems) : null;

    const briefingCard = briefingCardView(d, () => view.render());

    // Agenda Section
    let agendaContent;
    if (d.calendarConfigured === false) {
      agendaContent = h('div.li', null, h('span.mut', { style: { flex: '1' } }, 'Connect a calendar to see your day here.'));
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
      agendaContent = h('div.li', null, h('div', { style: { flex: '1' } }, h('div.nm', null, 'Nothing on the calendar today')));
    }

    const agendaCard = h('div.card', null,
      h('h2', null, 'Agenda'),
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
          const repeatWord = { daily: 'Every day', weekdays: 'Every weekday', weekly: 'Every week' }[r.repeat] || '';
          remsEl.push(h('div.li', null, h('i.mut', { 'data-i': 'flag' }),
            h('span', { style: { flex: '1', minWidth: 0 } }, r.text, repeatWord ? h('span.xs.mut', null, ` · ${repeatWord}`) : null),
            h('button.btn.gh', {
              type: 'button',
              'aria-label': `Delete reminder: ${r.text}`,
              onClick: async () => {
                const res = await reminders.remove(r.id);
                if (res.ok && res.data?.ok !== false) { ok('Reminder deleted'); loadToday(); } else err("That reminder couldn't be deleted");
              },
            }, 'Delete')));
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
          ? h('button.btn.pri', { type: 'button', onClick: () => ok(`${clock(f.remainingSec)} left`) }, 'Running')
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

    // One row for every account that isn't connected yet, instead of a card for each.
    const liveStatus = store.status;
    const missing = [
      d.calendarConfigured === false ? 'calendar' : null,
      liveStatus && !liveStatus.mailConfigured ? 'email' : null,
      liveStatus && !liveStatus.githubConfigured ? 'GitHub' : null,
    ].filter(Boolean);
    const connectRow = missing.length ? h('div.connect-row', null, h('i', { 'data-i': 'link' }),
      h('div.grow', null, h('strong', null, 'Connect your accounts'),
        h('div.xs.mut', null, `Add your ${missing.join(', ').replace(/, ([^,]*)$/, ' and $1')} to see them here.`)),
      d.calendarConfigured === false ? h('button.btn.gh', { type: 'button', onClick: openGoogleCalendarGuide }, 'Calendar help') : null,
      h('button.btn', { type: 'button', onClick: () => go('settings', { section: 'integrations' }) }, 'Connect')
    ) : null;
    const unreadRow = liveStatus?.mailConfigured && liveStatus.unreadImportant
      ? h('div.today-alert', null, h('i', { 'data-i': 'mail' }), h('div.grow', null, h('strong', null, `${liveStatus.unreadImportant} important unread`)))
      : null;

    const wasTaskFocused = document.activeElement === taskInput;
    const wasNoteFocused = document.activeElement === noteInput;
    mount(main, hd, nowBlock, unreadRow, briefingCard, h('div.grid2', null, agendaCard, tasksCard, remsCard, focusCard, notesCard), connectRow);
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

    mount(aside, frag(
      h('h2', null, 'This PC'),
      dashboardCard,
      musicSection
    ));
  };

  // Clear the 1-second focus polling interval when this view is unmounted.
  view.cleanup = () => {
    clearInterval(focusTimer);
    focusTimer = null;
  };

  return view;
}
