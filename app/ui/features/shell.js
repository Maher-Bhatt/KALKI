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

  const railNav = h('nav.rail', { 'aria-label': 'Destinations' });
  const viewSlot = h('main', { class: 'on' });
  const contextEl = h('aside', { class: 'on' });
  
  const banner = h('div', { hidden: true });
  const toastsEl = h('div.toasts', { 'aria-live': 'polite', 'aria-atomic': 'false' });
  const announcer = h('div.sr-only', { role: 'status', 'aria-live': 'polite' });

  const palBtn = h('button.pal', { type: 'button', onClick: () => openPalette() }, 
    icon('search', 14), 'Search or run a command', h('kbd', null, keyLabel('mod+k')));

  const micChip = h('span.chip.ok', { id: 'mic' }, 'Mic ready');
  const titlebar = h('div.title', null,
    h('span', null, 'KALKI'),
    palBtn,
    h('div.row.g8', { title: 'Privacy indicators are always visible' },
      micChip,
      h('span.chip', null, 'Screen not shared'),
      h('span.chip', null, 'Local-first')
    )
  );

  const bodyEl = h('div.body', null, railNav, viewSlot, contextEl);
  const appEl = h('div.app', null, titlebar, banner, bodyEl);

  mount(root, appEl, toastsEl, announcer);

  /* ── Rail ─────────────────────────────────────────────────────────── */
  function paintRail() {
    const dests = [...DESTINATIONS];
    if (store.ui.securityEnabled) dests.push({ id: 'security', label: 'Security', icon: 'security' });

    // In filament, the icon function isn't used directly for the mark, but we use the DOM we parsed.
    const markEl = h('div.mark', { title: 'KALKI — ready', dataset: { s: store.status?.listenerState || 'idle' } }, h('b', null));

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
    banner.hidden = true;
  }

  function paintContext() {
    // contextEl is now handled by main.js inserting into it!
    // we don't clear it here anymore.
  }

  subscribe((state, prev) => {
    if (state.route.name !== prev.route.name || state.ui.securityEnabled !== prev.ui.securityEnabled || state.status?.listenerState !== prev.status?.listenerState) paintRail();
    if (state.online !== prev.online || state.status?.updateProgress !== prev.status?.updateProgress) paintBanner();
    
    if (state.status?.listenerState !== prev.status?.listenerState) {
        const s = state.status?.listenerState || 'idle';
        if (s === 'listening') {
            micChip.className = 'chip warn';
            micChip.textContent = 'Mic live';
        } else if (s === 'asleep') {
            micChip.className = 'chip';
            micChip.textContent = 'Mic off';
        } else {
            micChip.className = 'chip ok';
            micChip.textContent = 'Mic ready';
        }
    }
  });
  
  paintRail();
  paintBanner();
  
  return {
    railNav,
    banner,
    viewSlot,
    contextEl,
    toastsEl,
    announcer,
    presence: { el: h('div') } // dummy presence since we put mark in rail directly
  };
}
