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
import { system, desktop } from '../api/endpoints.js';
import { refreshStatus } from '../state/status.js';
import { openDiagnostics } from './diagnostics.js';
import { openPalette } from './palette.js';
import { openMenu } from '../components/menu.js';
import { go } from './router.js';
import { approvalCard } from '../components/approval.js';
import { syncApprovals, waitingApprovals } from '../state/approvals.js';
import { brand } from '../components/brand.js';
import { openVoiceMode, closeVoiceMode, voiceModeOpen, paintVoiceMode } from './voice.js';

const DESTINATIONS = [
  { id: 'ask', label: 'Ask', icon: 'ask' },
  { id: 'today', label: 'Today', icon: 'today' },
  { id: 'memory', label: 'Memory', icon: 'memory' },
  { id: 'workbench', label: 'Workbench', icon: 'workbench' },
  { id: 'security', label: 'Security', icon: 'security' },
];

const LOCAL_MODEL = /llama|qwen|phi|gemma|mistral|ollama|deepseek|local/i;

function initials(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return 'K';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function ownerName() {
  const name = String(store.status?.owner || '').trim();
  return name && name !== 'YourName' ? name : '';
}


export function buildShell(root) {
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

  const railBtn = h('button.ib.rail-toggle', {
    type: 'button',
    'aria-label': 'Show or hide navigation',
    title: `Show or hide navigation (${keyLabel('mod+b')})`,
    onClick: () => shellApi.toggleRail(),
  }, icon('panel', 16));

  const modelPill = h('button.pill', {
    type: 'button',
    title: 'Choose the AI model',
    onClick: () => go('settings', { section: 'models' }),
  });
  const bellCount = h('span.bell-count', { hidden: true });
  const bellBtn = h('button.ib.bell', {
    type: 'button',
    'aria-label': 'Activity and approvals',
    title: 'Activity and approvals',
    onClick: () => go('oversight'),
  }, icon('alert', 17), bellCount);

  const titlebar = h('div.title.pywebview-drag-region', null,
    h('button.ib', { type: 'button', 'aria-label': 'Back', title: 'Back', onClick: () => history.back() }, h('span.nav-arrow', { 'aria-hidden': 'true' }, '‹')),
    h('button.ib', { type: 'button', 'aria-label': 'Forward', title: 'Forward', onClick: () => history.forward() }, h('span.nav-arrow', { 'aria-hidden': 'true' }, '›')),
    palBtn,
    h('span.title-space'),
    modelPill,
    statusBtn,
    bellBtn,
  );

  const railHead = h('div.rail-head.pywebview-drag-region', null, brand(), railBtn);
  const railFoot = h('div.rail-foot');
  const sidebar = h('div.sidebar', null, railHead, railNav, railFoot);
  const bodyEl = h('div.body', null, viewSlot, contextEl);
  const stage = h('div.stage', null, titlebar, banner, bodyEl);
  const appEl = h('div.app', null, sidebar, stage);

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
    sidebar.dataset.open = String(open);

    const place = (id, label, iconName, count = 0) => h('button.nav', {
      type: 'button',
      dataset: { place: id },
      title: open ? null : label,
      'aria-label': count ? `${label}, ${count} waiting` : label,
      'aria-current': routeName === id ? 'page' : null,
      onClick: () => go(id),
    }, icon(iconName, 17), h('span.nav-label', null, label), count ? h('span.nav-count', null, String(count)) : null);

    mount(railNav,
      ...DESTINATIONS.map((d) => place(d.id, d.label, d.icon)),
      place('settings', 'Settings', 'settings'),
    );
    paintFoot();

    if (focusedPlace) railNav.querySelector(`[data-place="${focusedPlace}"]`)?.focus();
  }

  /* ── Bottom of the sidebar: the model, this PC and you ─────────────── */
  let lastFootSig = '';
  function paintFoot() {
    const st = store.status || {};
    const model = store.models?.current || st.model || 'auto';
    const where = model === 'auto' ? 'Picks the best for each question' : (LOCAL_MODEL.test(model) ? 'On this PC' : 'Cloud');
    const name = ownerName();
    const sig = `${model}|${where}|${name}|${st.cpu}|${store.online}|${store.ui.railLabels}`;
    if (sig === lastFootSig) return;
    lastFootSig = sig;
    mount(railFoot,
      h('button.foot-card', { type: 'button', title: 'Choose the AI model', onClick: () => go('settings', { section: 'models' }) },
        h('span.foot-label', null, 'Model'),
        h('span.foot-value', null, h('span.status-dot', { dataset: { tone: store.online ? 'ok' : 'off' } }), h('span.foot-text', null, modelLabel(model) || 'Auto')),
        h('span.foot-sub', null, where)),
      h('button.foot-card', { type: 'button', title: 'Open Today', onClick: () => go('today') },
        h('span.foot-label', null, 'This PC'),
        h('span.foot-value', null, icon('cpu', 14), h('span.foot-text', null, typeof st.cpu === 'number' ? `CPU ${Math.round(st.cpu)}% · RAM ${Math.round(st.ram || 0)}%` : 'Not measured yet'))),
      h('button.profile', { type: 'button', title: 'Your profile', onClick: () => go('settings', { section: 'general' }) },
        h('span.avatar', null, initials(name || 'KALKI')),
        h('span.profile-text', null, h('strong', null, name || 'Set your name'), h('span', null, 'Profile and settings'))),
    );
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
      { label: `Voice mode · ${voiceLine()}`, icon: 'mic', hint: keyLabel('mod+shift+v'), run: () => window.dispatchEvent(new CustomEvent('kalki:voice-toggle')) },
      { label: 'Show or hide the desktop pet', icon: 'pet', run: togglePet },
      isDesktop ? { label: 'Keep KALKI on top', icon: 'pin', run: togglePin } : null,
      { label: 'Activity', icon: 'alert', run: () => go('oversight') },
      'rule',
      { label: 'Diagnostics', icon: 'info', hint: keyLabel('mod+shift+d'), run: () => openDiagnostics() },
      { label: 'Settings', icon: 'settings', run: () => go('settings') },
    ]);
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
    syncApprovals();
    const waitingList = waitingApprovals();
    const a = waitingList[0];
    const route = store.route?.name;
    // Ask shows approvals in the conversation, and Activity lists them.
    if (a && route !== 'oversight' && route !== 'ask') {
      banner.hidden = false;
      banner.className = 'notice notice-approval'; delete banner.dataset.tone;
      if (banner.dataset.approval !== String(a.id)) {
        banner.dataset.approval = String(a.id);
        mount(banner, approvalCard(a, { position: 1, total: waitingList.length }));
      }
      return;
    }
    delete banner.dataset.approval;
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
    openVoiceMode(stage);
  }

  window.addEventListener('kalki:voice-toggle', () => (voiceModeOpen() ? closeVoiceMode() : openVoiceOverlay()));
  window.addEventListener('kalki:nav-changed', () => { paintRail(true); notify(); });

  function render() {
    paintRail();
    paintBanner();
    paintToasts();
    const now = overallStatus();
    statusDot.dataset.tone = now.tone;
    statusText.textContent = now.text;
    statusBtn.title = now.detail;
    const model = store.models?.current || store.status?.model || 'auto';
    mount(modelPill, h('span.status-dot', { dataset: { tone: store.online ? 'ok' : 'off' } }),
      model === 'auto' ? 'Auto' : `${LOCAL_MODEL.test(model) ? 'Local' : 'Cloud'} · ${modelLabel(model)}`, icon('chevronD', 12));
    const waiting = store.status?.pendingApprovals || 0;
    bellCount.hidden = !waiting;
    bellCount.textContent = String(waiting);
    bellBtn.setAttribute('aria-label', waiting ? `Activity, ${waiting} waiting for approval` : 'Activity and approvals');
    paintFoot();
    if (voiceModeOpen()) paintVoiceMode();
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
