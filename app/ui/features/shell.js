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
import { store, applyUi, notify, subscribe } from '../state/store.js';
import { ok, err, dismiss } from '../state/toasts.js';
import { createPresence, presenceLabel } from '../components/presence.js';
import { openDialog } from '../components/dialog.js';
import { system, desktop, approvals } from '../api/endpoints.js';
import { refreshStatus } from '../state/status.js';
import { openDiagnostics } from './diagnostics.js';
import { openPalette } from './palette.js';

const DESTINATIONS = [
  { id: 'ask', label: 'Ask', icon: 'ask' },
  { id: 'today', label: 'Today', icon: 'today' },
  { id: 'memory', label: 'Memory', icon: 'memory' },
  { id: 'workbench', label: 'Workbench', icon: 'workbench' },
  { id: 'security', label: 'Antivirus & Cyber', icon: 'security' },
  { id: 'oversight', label: 'Oversight', icon: 'alert' },
];

let railPresence = null;
let overlayPresence = null;
let voiceDialog = null;

export function buildShell(root) {
  railPresence = createPresence();

  const railNav = h('nav.rail', { 'aria-label': 'Destinations' });
  const viewSlot = h('main', { class: 'on' });
  const contextEl = h('aside', { class: 'on' });
  
  const banner = h('div', { hidden: true });
  const toastsEl = h('div.toasts', { 'aria-live': 'polite', 'aria-atomic': 'false' });
  const announcer = h('div.sr-only', { role: 'status', 'aria-live': 'polite' });

  const palBtn = h('button.pal', { type: 'button', onClick: () => openPalette() }, 
    icon('search', 14), 'Search or run a command', h('kbd', null, keyLabel('mod+k')));

  const micChip = h('span.chip', { id: 'mic' }, 'Voice status unknown');
  const modeBadge = h('span.chip.desktop-badge', null, 'Browser');
  const titlebar = h('div.title.pywebview-drag-region', null,
    h('div.title-brand', null,
      h('span.dot.active', { title: 'Desktop Sovereign Engine Linked' }),
      h('span.badge-core', null, 'DESKTOP OS CORE')
    ),
    palBtn,
    h('div.title-actions', null,
      micChip,
      modeBadge,
      h('button.win-btn.pet-btn', {
        type: 'button',
        title: 'Toggle Desktop Companion Pet Mascot',
        onClick: () => desktop.togglePet().then(() => ok('Desktop Companion Pet toggled'))
      }, icon('pet', 13), 'Pet'),
      h('button.win-btn', {
        type: 'button',
        title: 'Pin Always-on-Top',
        onClick: () => desktop.togglePin().then(r => ok(r?.pinned ? 'Window Pinned on Top' : 'Window Unpinned'))
      }, icon('pin', 13))
    )
  );

  const bodyEl = h('div.body', null, railNav, viewSlot, contextEl);
  const appEl = h('div.app', null, titlebar, banner, bodyEl);

  mount(root, appEl, toastsEl, announcer);

  /* ── Rail ─────────────────────────────────────────────────────────── */
  let lastRailSig = '';

  function paintRail(force = false) {
    const routeName = store.route?.name || '';
    const listenerState = store.status?.listenerState || 'idle';
    const security = !!store.ui?.securityEnabled;
    const railSig = `${routeName}|${listenerState}|${security}`;

    if (!force && railSig === lastRailSig) return;
    lastRailSig = railSig;

    const active = document.activeElement;
    const hadFocusInRail = !!(active && railNav.contains(active));
    const activeTitle = hadFocusInRail ? active.getAttribute('title') : null;
    const activeAriaCurrent = hadFocusInRail ? active.getAttribute('aria-current') : null;
    const activeIndex = hadFocusInRail ? Array.from(railNav.querySelectorAll('button, .mark')).indexOf(active) : -1;

    const dests = [...DESTINATIONS];

    // In filament, the icon function isn't used directly for the mark, but we use the DOM we parsed.
    const markEl = h('div.mark', { title: 'KALKI — ready', dataset: { s: listenerState } }, h('b', null));

    mount(railNav,
      markEl,
      ...dests.map((d) => h('button.nav', {
        type: 'button',
        'aria-current': store.route.name === d.id ? 'page' : null,
        title: d.label,
        onClick: () => location.hash = `#/${d.id}`
      }, icon(d.icon, 16))),
      h('div.sp', null),
      h('button.nav', {
        type: 'button', title: 'Settings',
        'aria-current': store.route.name === 'settings' ? 'page' : null,
        onClick: () => location.hash = `#/settings`
      }, icon('settings', 16))
    );

    if (hadFocusInRail) {
      if (activeTitle) {
        const btn = railNav.querySelector(`button[title="${activeTitle}"]`);
        if (btn) btn.focus();
      } else if (activeAriaCurrent) {
        const btn = railNav.querySelector(`button[aria-current="${activeAriaCurrent}"]`);
        if (btn) btn.focus();
      } else if (activeIndex >= 0) {
        const items = railNav.querySelectorAll('button, .mark');
        if (items[activeIndex]) items[activeIndex].focus();
      }
    }
  }

  /* ── Approvals, available from every screen ───────────────────────── */
  let knownWaiting = 0;
  let waitingApprovals = [];

  async function loadApprovals() {
    const r = await approvals.list();
    waitingApprovals = r.ok ? (r.data.approvals || []) : [];
    notify();
  }

  async function decideApproval(id, decision) {
    const r = await approvals.decide(id, decision);
    if (r.ok) ok(decision === 'approve' ? 'Approved' : 'Denied');
    else err(r.detail || r.message);
    await loadApprovals();
    refreshStatus();
  }

  /* ── Offline / update banner ──────────────────────────────────────── */
  function paintBanner() {
    const up = store.status?.updateProgress;
    if (!store.online) {
      banner.hidden = false;
      banner.className = 'card dng';
      mount(banner, h('span', null, "KALKI's local service isn't responding."));
      return;
    }
    if (up?.active) {
      banner.hidden = false;
      banner.className = 'card warn';
      mount(banner, h('span', null, `Updating KALKI — ${up.pct || 0}%`));
      return;
    }
    if (store.status?.storeError) {
      banner.hidden = false;
      banner.className = 'card dng';
      mount(banner, h('span', null, `Your tasks, notes and memories can't be opened: ${store.status.storeError}`));
      return;
    }
    const waiting = store.status?.pendingApprovals || 0;
    if (waiting !== knownWaiting) {
      knownWaiting = waiting;
      loadApprovals();
    }
    const a = waitingApprovals[0];
    if (waiting && a && !location.hash.startsWith('#/oversight')) {
      banner.hidden = false;
      banner.className = 'card warn';
      mount(banner, h('div.row.sb', { style: { gap: '12px', alignItems: 'flex-start' } },
        h('div', { style: { flex: '1', minWidth: 0 } },
          h('strong', null, waiting === 1 ? 'KALKI needs your approval' : `KALKI needs your approval (1 of ${waiting})`),
          h('div.sm', { style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '160px', overflowY: 'auto' } }, a.description)),
        h('div.row.g8', null,
          h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => decideApproval(a.id, 'deny') }, 'Deny'),
          h('button.btn.btn-sm.btn-primary', { type: 'button', onClick: () => decideApproval(a.id, 'approve') }, 'Approve'))));
      return;
    }
    const version = store.status?.updateAvailable;
    if (version) {
      banner.hidden = false;
      banner.className = 'card';
      mount(banner, h('div.row.sb', null,
        h('span', null, `KALKI ${version} is available.`),
        h('button.btn.btn-sm.btn-primary', { type: 'button', onClick: () => system.installUpdate() }, 'Install update')));
      return;
    }
    banner.hidden = true;
  }

  function paintContext() {
    // contextEl is now handled by main.js inserting into it!
    // we don't clear it here anymore.
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
  window.addEventListener('kalki:nav-changed', () => { paintRail(true); notify(); });

  function render() {
    paintRail();
    paintBanner();
    paintToasts();
    modeBadge.textContent = window.pywebview ? 'Desktop app' : 'Browser';
    const st = store.status;
    if (st) {
      if (!st.listenerOnline) {
        micChip.className = 'chip';
        micChip.textContent = 'Voice off';
      } else if (st.listenerPaused || st.listenerMicMuted || st.listenerState === 'asleep') {
        micChip.className = 'chip';
        micChip.textContent = 'Mic off';
      } else if (st.listenerState === 'listening') {
        micChip.className = 'chip warn';
        micChip.textContent = 'Mic live';
      } else {
        micChip.className = 'chip ok';
        micChip.textContent = 'Mic ready';
      }
    }
    overlayPresence?.update?.(store.voice.state, { ttsTrouble: store.voice.ttsTrouble });
    if (voiceDialog) voiceDialog.caption.textContent = presenceLabel(store.voice.state);
  }

  render();

  return {
    railNav,
    banner,
    viewSlot,
    contextEl,
    toastsEl,
    announcer,
    presence: { el: h('div') },
    paintRail,
    render,
    openVoiceOverlay,
    toggleRail() { store.ui.railOpen = !store.ui.railOpen; applyUi(); paintRail(true); },
  };
}
