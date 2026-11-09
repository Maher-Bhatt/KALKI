/** The application shell: top bar, navigation rail, work area, context panel, toasts
 *  and the voice overlay.
 *
 *  The rail names every place in words and can be collapsed. The top bar holds only
 *  search and one status button, and everything else that used to sit there is in that
 *  button's menu. */

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
import { openMenu } from '../components/menu.js';
import { go } from './router.js';

const DESTINATIONS = [
  { id: 'ask', label: 'Ask', icon: 'ask' },
  { id: 'today', label: 'Today', icon: 'today' },
  { id: 'memory', label: 'Library', icon: 'memory' },
  { id: 'workbench', label: 'Studio', icon: 'workbench' },
  { id: 'security', label: 'Security', icon: 'security' },
  { id: 'oversight', label: 'Activity', icon: 'alert' },
];

let railPresence = null;
let overlayPresence = null;
let voiceDialog = null;

export function buildShell(root) {
  railPresence = createPresence();
  let shellApi = null;

  const railNav = h('nav.rail', { 'aria-label': 'Destinations' });
  const viewSlot = h('main', { class: 'on' });
  const contextEl = h('aside', { class: 'on' });
  
  const banner = h('div', { hidden: true });
  const toastsEl = h('div.toasts', { 'aria-live': 'polite', 'aria-atomic': 'false' });
  const announcer = h('div.sr-only', { role: 'status', 'aria-live': 'polite' });

  const palBtn = h('button.pal', { type: 'button', onClick: () => openPalette() }, 
    icon('search', 14), 'Search or run a command', h('kbd', null, keyLabel('mod+k')));

  const statusDot = h('span.status-dot');
  const statusText = h('span');
  const statusBtn = h('button.status-btn', {
    type: 'button',
    'aria-haspopup': 'menu',
    'aria-expanded': 'false',
    onClick: () => openStatusMenu(),
  }, statusDot, statusText, icon('chevronD', 12));

  const railBtn = h('button.ib', {
    type: 'button',
    'aria-label': 'Show or hide navigation',
    title: `Show or hide navigation (${keyLabel('mod+b')})`,
    onClick: () => shellApi.toggleRail(),
  }, icon('panel', 16));

  const titlebar = h('div.title.pywebview-drag-region', null,
    railBtn,
    h('div.title-brand', null, 'KALKI'),
    palBtn,
    statusBtn,
  );

  const bodyEl = h('div.body', null, railNav, viewSlot, contextEl);
  const appEl = h('div.app', null, titlebar, banner, bodyEl);

  mount(root, appEl, toastsEl, announcer);

  /* ── Rail ─────────────────────────────────────────────────────────── */
  let lastRailSig = '';

  function paintRail(force = false) {
    const routeName = store.route?.name || '';
    const listenerState = store.status?.listenerState || 'idle';
    const open = store.ui.railLabels !== false;
    const waiting = store.status?.pendingApprovals || 0;
    const railSig = `${routeName}|${listenerState}|${open}|${waiting}`;

    if (!force && railSig === lastRailSig) return;
    lastRailSig = railSig;

    const active = document.activeElement;
    const focusedPlace = active && railNav.contains(active) ? active.dataset.place : null;
    railNav.dataset.open = String(open);

    const place = (id, label, iconName, count = 0) => h('button.nav', {
      type: 'button',
      dataset: { place: id },
      title: open ? null : label,
      'aria-label': count ? `${label}, ${count} waiting` : label,
      'aria-current': routeName === id ? 'page' : null,
      onClick: () => go(id),
    }, icon(iconName, 17), h('span.nav-label', null, label), count ? h('span.nav-count', null, String(count)) : null);

    mount(railNav,
      ...DESTINATIONS.map((d) => place(d.id, d.label, d.icon, d.id === 'oversight' ? waiting : 0)),
      h('div.sp', null),
      place('settings', 'Settings', 'settings'),
    );

    if (focusedPlace) railNav.querySelector(`[data-place="${focusedPlace}"]`)?.focus();
  }

  /* ── The status button ────────────────────────────────────────────── */
  function overallStatus() {
    const st = store.status;
    if (!store.online) return { tone: 'dng', text: 'Offline', detail: "KALKI's local service isn't responding." };
    if (st?.storeError) return { tone: 'dng', text: 'Problem', detail: "Your tasks, notes and memories can't be opened." };
    const waiting = st?.pendingApprovals || 0;
    if (waiting) return { tone: 'warn', text: waiting === 1 ? '1 approval' : `${waiting} approvals`, detail: 'KALKI is waiting for your decision.' };
    if (store.conv?.streaming || st?.listenerState === 'thinking') return { tone: 'ok', text: 'Working', detail: 'KALKI is working on your request.' };
    return { tone: 'ok', text: 'Ready', detail: 'Everything is running.' };
  }

  function voiceLine() {
    const st = store.status;
    if (!st?.listenerOnline) return 'Voice is off';
    if (st.listenerPaused || st.listenerMicMuted || st.listenerState === 'asleep') return 'Microphone is off';
    if (st.listenerState === 'listening') return 'Microphone is listening';
    return 'Microphone is ready';
  }

  async function togglePet() {
    const r = await desktop.togglePet();
    if (r && r.ok === false) err(r.error || "The desktop pet couldn't be changed");
    else ok((r?.data?.running ?? r?.running) === false ? 'The desktop pet is closed' : 'The pet is on your desktop');
  }

  async function togglePin() {
    const r = await desktop.togglePin();
    ok(r?.pinned ? 'KALKI stays on top' : 'KALKI no longer stays on top');
  }

  function openStatusMenu() {
    const now = overallStatus();
    const isDesktop = !!window.pywebview;
    openMenu(statusBtn, [
      { info: now.text, detail: now.detail },
      (store.status?.pendingApprovals || 0) > 0 ? { label: 'Review approvals', icon: 'alert', run: () => go('oversight') } : null,
      'rule',
      { label: voiceLine(), icon: 'mic', hint: keyLabel('mod+shift+v'), run: () => window.dispatchEvent(new CustomEvent('kalki:voice-toggle')) },
      { label: 'Show or hide the desktop pet', icon: 'pet', run: togglePet },
      isDesktop ? { label: 'Keep KALKI on top', icon: 'pin', run: togglePin } : null,
      'rule',
      { label: 'Diagnostics', icon: 'info', hint: keyLabel('mod+shift+d'), run: () => openDiagnostics() },
      { label: 'Settings', icon: 'settings', run: () => go('settings') },
    ]);
  }

  /* ── Approvals, available from every screen ───────────────────────── */
  let knownWaiting = 0;
  let waitingApprovals = [];

  async function loadApprovals() {
    const r = await approvals.list();
    waitingApprovals = r.ok ? (r.data.approvals || []) : [];
    notify();
  }

  function outcomeText(decision, data) {
    if (decision !== 'approve') return 'Denied';
    const result = Array.isArray(data?.result) ? data.result[1] : data?.result;
    return result ? String(result).slice(0, 160) : 'Approved';
  }

  async function decideApproval(id, decision) {
    const r = await approvals.decide(id, decision);
    if (r.ok) ok(outcomeText(decision, r.data));
    else err(r.detail || r.message);
    await loadApprovals();
    refreshStatus();
  }

  /* ── Offline / update banner ──────────────────────────────────────── */
  function paintBanner() {
    const up = store.status?.updateProgress;
    if (!store.online) {
      banner.hidden = false;
      banner.className = 'notice'; banner.dataset.tone = 'dng';
      mount(banner, h('span', null, "KALKI's local service isn't responding."));
      return;
    }
    if (up?.active) {
      banner.hidden = false;
      banner.className = 'notice'; banner.dataset.tone = 'warn';
      mount(banner, h('span', null, `Updating KALKI — ${up.pct || 0}%`));
      return;
    }
    if (store.status?.storeError) {
      banner.hidden = false;
      banner.className = 'notice'; banner.dataset.tone = 'dng';
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
      banner.className = 'notice'; banner.dataset.tone = 'warn';
      mount(banner, h('div.row.sb', { style: { gap: '12px', alignItems: 'flex-start', flex: '1', minWidth: 0 } },
        h('div.notice-body', null,
          h('strong', null, waiting === 1 ? 'KALKI needs your approval' : `KALKI needs your approval (1 of ${waiting})`),
          h('div.sm.notice-detail', null, a.description)),
        h('div.row.g8', null,
          h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => decideApproval(a.id, 'deny') }, 'Deny'),
          h('button.btn.btn-sm.btn-primary', { type: 'button', onClick: () => decideApproval(a.id, 'approve') }, 'Approve'))));
      return;
    }
    const version = store.status?.updateAvailable;
    if (version) {
      banner.hidden = false;
      banner.className = 'notice'; delete banner.dataset.tone;
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
    const now = overallStatus();
    statusDot.dataset.tone = now.tone;
    statusText.textContent = now.text;
    statusBtn.title = now.detail;
    overlayPresence?.update?.(store.voice.state, { ttsTrouble: store.voice.ttsTrouble });
    if (voiceDialog) voiceDialog.caption.textContent = presenceLabel(store.voice.state);
  }

  render();

  shellApi = {
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
    toggleRail() { store.ui.railLabels = store.ui.railLabels === false; applyUi(); paintRail(true); },
  };
  return shellApi;
}
