/** The application shell: title strip, navigation rail, work area, context
 *  panel, toasts and the voice overlay.
 *
 *  The rail holds at most five destinations. Depth lives in the command
 *  palette, not in a wall of icons. The presence mark sits at the top of the
 *  rail and is both the KALKI logotype and the state indicator — it never
 *  occupies the centre of the screen. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { duration, modelLabel } from '../lib/format.js';
import { label as keyLabel } from '../lib/keys.js';
import { store, applyUi, notify } from '../state/store.js';
import { dismiss } from '../state/toasts.js';
import { createPresence, presenceLabel } from '../components/presence.js';
import { openDialog } from '../components/dialog.js';
import { system } from '../api/endpoints.js';
import { refreshStatus } from '../state/status.js';
import { openDiagnostics } from './diagnostics.js';
import { openPalette } from './palette.js';

const DESTINATIONS = [
  { id: 'ask', label: 'Ask', icon: 'ask' },
  { id: 'today', label: 'Today', icon: 'today' },
  { id: 'memory', label: 'Memory', icon: 'memory' },
  { id: 'workbench', label: 'Workbench', icon: 'workbench' },
  { id: 'oversight', label: 'Oversight', icon: 'alert' },
];

let railPresence = null;
let overlayPresence = null;
let voiceDialog = null;

export function buildShell(root) {
  railPresence = createPresence();

  const railNav = h('nav.rail', { 'aria-label': 'Main' });
  const banner = h('div', { hidden: true });
  const workEl = h('div.work');
  const viewSlot = h('div', { style: { display: 'contents' } });
  const contextEl = h('aside.context', { 'aria-label': 'Context' });
  const toastsEl = h('div.toasts', { 'aria-live': 'polite', 'aria-atomic': 'false' });
  const announcer = h('div.sr-only', { role: 'status', 'aria-live': 'polite' });

  workEl.append(viewSlot, contextEl);

  const titlebar = h('header.titlebar', null,
    h('span.wordmark', null, 'KALKI'),
    h('span.spacer'),
    h('button.palette-hint.no-drag', {
      type: 'button', onClick: () => openPalette(),
      'aria-label': 'Open the command palette',
    }, icon('search', 14), h('span', null, 'Search'), h('span.kbd', null, keyLabel('mod+k'))),
  );

  mount(root, titlebar, h('div.shell', null, banner, railNav, workEl), toastsEl, announcer);

  /* ── Rail ─────────────────────────────────────────────────────────── */
  function paintRail() {
    const dests = [...DESTINATIONS];
    if (store.ui.securityEnabled) dests.push({ id: 'security', label: 'Security', icon: 'security' });

    mount(railNav,
      railPresence.el,
      ...dests.map((d) => h('a.rail-item', {
        href: `#/${d.id}`,
        'aria-current': store.route.name === d.id ? 'page' : null,
        title: d.label,
      }, icon(d.icon, 20), h('span', null, d.label))),
      h('span.spacer'),
      h('button.rail-item', {
        type: 'button', title: 'System',
        'aria-label': 'System status',
        onClick: openSystemPopover,
      }, icon('info', 20), h('span', null, 'System')),
      h('a.rail-item', {
        href: '#/settings',
        'aria-current': store.route.name === 'settings' ? 'page' : null,
        title: 'Settings',
      }, icon('settings', 20), h('span', null, 'Settings')),
    );
    railNav.classList.toggle('is-open', store.ui.railOpen);
  }

  railNav.addEventListener('mouseenter', () => { railNav.classList.add('is-open'); });
  railNav.addEventListener('mouseleave', () => { if (!store.ui.railOpen) railNav.classList.remove('is-open'); });
  railNav.addEventListener('focusin', () => railNav.classList.add('is-open'));
  railNav.addEventListener('focusout', (e) => {
    if (!store.ui.railOpen && !railNav.contains(e.relatedTarget)) railNav.classList.remove('is-open');
  });

  /* ── Offline / update banner ──────────────────────────────────────── */
  function paintBanner() {
    const up = store.status?.updateProgress;
    if (!store.online) {
      banner.hidden = false;
      banner.className = 'banner';
      mount(banner,
        icon('offline', 16),
        h('span', null, "KALKI's local service isn't responding."),
        h('span.spacer'),
        h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => refreshStatus() }, 'Retry'),
        h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => openDiagnostics() }, 'Details'),
      );
      return;
    }
    if (up?.active) {
      banner.hidden = false;
      banner.className = 'banner banner-warning';
      mount(banner,
        icon('download', 16),
        h('span', null, `Updating KALKI — ${up.pct || 0}%`),
        h('span.spacer'),
        h('div.meter', { style: { width: '10rem' } }, h('i', { style: { width: `${up.pct || 0}%` } })),
      );
      return;
    }
    banner.hidden = true;
  }

  /* ── Context panel ────────────────────────────────────────────────── */
  function paintContext() {
    const s = store.status;
    const show = store.route.name === 'ask';
    workEl.classList.toggle('has-context', show);
    if (!show) { contextEl.replaceChildren(); return; }

    const t = store.conv.threads.filter((x) => !x.archived).slice(0, 6);

    mount(contextEl,
      h('div.context-group', null,
        h('h2', null, 'Conversations'),
        t.length
          ? h('div.conv-list', null, ...t.map((x) => h('button.row.conv-item', {
              type: 'button',
              class: x.id === store.conv.activeId ? 'row conv-item is-selected' : 'row conv-item',
              onClick: () => { location.hash = '#/ask'; import('../state/conversations.js').then((m) => m.openThread(x.id)); },
            }, h('span.title', null, x.title))))
          : h('p.t-meta.faint', null, 'Nothing yet. Ask something below.'),
      ),
      s ? h('div.context-group', null,
        h('h2', null, 'Right now'),
        h('div.context-line', null, icon('spark', 14), h('span', null, modelLabel(s.model)),
          h('span.spacer'),
          h('span.dot', { class: s.groqConfigured || s.ollamaOnline ? 'dot dot-success' : 'dot dot-danger' })),
        h('div.context-line', null, icon('mic', 14), h('span', null, presenceLabel(store.voice.state))),
        typeof s.unreadImportant === 'number' && s.unreadImportant > 0
          ? h('div.context-line', null, icon('mail', 14), h('span', null, `${s.unreadImportant} important unread`))
          : null,
        Array.isArray(s.todayEvents) && s.todayEvents.length
          ? h('div.context-line', null, icon('calendar', 14), h('span', null, `${s.todayEvents.length} events today`))
          : null,
        s.ollamaOnline && !s.groqConfigured
          ? h('div.context-line', null, icon('offline', 14), h('span', null, 'Running on a local model'))
          : null,
      ) : null,
    );
  }

  /* ── Toasts ───────────────────────────────────────────────────────── */
  function paintToasts() {
    mount(toastsEl, ...store.toasts.map((t) => h('div.toast', { class: `toast toast-${t.kind}`, role: t.kind === 'error' ? 'alert' : 'status' },
      h('div', { style: { flex: '1' } },
        h('div', null, t.text),
        t.detail && store.ui.debug ? h('div.t-meta.faint', { style: { marginTop: 'var(--space-2)' } }, String(t.detail).slice(0, 160)) : null,
      ),
      t.action ? h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => { t.action.run(); dismiss(t.id); } }, t.action.label) : null,
      t.detail ? h('button.icon-btn', { type: 'button', 'aria-label': 'View details', title: 'Details', onClick: () => openDiagnostics(t.detail) }, icon('info', 14)) : null,
      h('button.icon-btn', { type: 'button', 'aria-label': 'Dismiss', onClick: () => dismiss(t.id) }, icon('close', 14)),
    )));
  }

  /* ── Voice overlay ────────────────────────────────────────────────── */
  function openVoiceOverlay() {
    if (voiceDialog) return;
    overlayPresence = createPresence();
    store.voice.sessionOpen = true;
    refreshStatus();

    const caption = h('p.t-title-2', null, presenceLabel(store.voice.state));
    const hint = h('p.t-body-sm.muted', null, 'Say "Hey KALKI", or close this and keep typing.');

    const { close } = openDialog({
      title: 'Voice',
      width: '24rem',
      body: h('div', { id: 'voice-overlay', style: { textAlign: 'center' } },
        overlayPresence.el, caption, hint,
      ),
      actions: [
        h('button.btn.btn-secondary', { type: 'button', onClick: async () => { await system.stop(); refreshStatus(); } }, 'Stop speaking'),
        h('button.btn.btn-primary', { type: 'button', onClick: async () => { const r = await system.wake(''); if (r.ok) refreshStatus(); } }, 'Wake KALKI'),
      ],
      onClose: () => { voiceDialog = null; overlayPresence = null; store.voice.sessionOpen = false; },
    });
    voiceDialog = { close, caption };
  }

  window.addEventListener('kalki:voice-toggle', () => (voiceDialog ? voiceDialog.close() : openVoiceOverlay()));
  window.addEventListener('kalki:nav-changed', () => { paintRail(); notify(); });

  /* ── System popover ───────────────────────────────────────────────── */
  function openSystemPopover() {
    const s = store.status || {};
    const meter = (label, value) => h('div.stack', { style: { gap: 'var(--space-2)' } },
      h('div.inline.t-meta.muted', null, h('span', null, label), h('span.spacer'), h('span.num', null, `${Math.round(value || 0)}%`)),
      h('div.meter', { class: value > 92 ? 'meter is-crit' : value > 80 ? 'meter is-warn' : 'meter' }, h('i', { style: { width: `${Math.min(100, value || 0)}%` } })),
    );
    openDialog({
      title: 'This machine',
      description: 'KALKI runs locally. These are the numbers it sees.',
      width: '24rem',
      body: h('div.stack', null,
        meter('Processor', s.cpu), meter('Memory', s.ram), meter('Disk', s.disk),
        typeof s.batteryPct === 'number' ? meter(`Battery${s.batteryPlugged ? ' (charging)' : ''}`, s.batteryPct) : null,
        h('hr.divider'),
        h('div.context-line', null, h('span.muted', null, 'Uptime'), h('span.spacer'), h('span.num', null, duration(s.uptimeSec || 0))),
        h('div.context-line', null, h('span.muted', null, 'Model'), h('span.spacer'), h('span', null, modelLabel(s.model))),
        h('div.context-line', null, h('span.muted', null, 'Offline model'), h('span.spacer'), h('span', null, s.ollamaOnline ? 'available' : 'not running')),
      ),
      actions: [h('button.btn.btn-secondary', { type: 'button', onClick: () => setTimeout(openDiagnostics, 60) }, 'Diagnostics')],
    });
  }

  /* ── Public surface ───────────────────────────────────────────────── */
  return {
    viewSlot, announcer,
    paintRail,
    render() {
      paintRail();
      paintBanner();
      paintContext();
      paintToasts();
      railPresence.update(store.voice.state, { ttsTrouble: store.voice.ttsTrouble });
      overlayPresence?.update(store.voice.state, { ttsTrouble: store.voice.ttsTrouble });
      if (voiceDialog) voiceDialog.caption.textContent = presenceLabel(store.voice.state);
    },
    openVoiceOverlay,
    toggleRail() { store.ui.railOpen = !store.ui.railOpen; applyUi(); paintRail(); },
  };
}
