/** The filament: KALKI's presence mark.
 *
 *  Two nodes, and only opacity and transform ever change. A filament changes
 *  intensity — it does not spin, orbit or scan — which is both the visual rule
 *  and the cheapest thing a GPU-disabled WebView2 can draw. It lives in the
 *  rail as the brand mark, never at the centre of the screen. */

import { h } from '../lib/dom.js';

const LABEL = {
  unavailable: 'KALKI is offline',
  'mic-released': 'Microphone released',
  'mic-muted': 'Microphone muted',
  ready: 'KALKI is ready',
  attending: 'KALKI is listening for your request',
  thinking: 'KALKI is working',
  speaking: 'KALKI is speaking',
  interrupted: 'Stopped',
};

export function createPresence() {
  const core = h('span.presence-core');
  const halo = h('span.presence-halo');
  const badge = h('span.presence-badge', { hidden: true });
  // Sizing is CSS's job, not this function's: the rail gets the .presence
  // class default (--size-xl, 2.5rem) and the voice overlay gets the
  // #voice-overlay .presence override (10rem) purely from where the element
  // is mounted. An earlier version set an inline width/height here, which
  // masked a real bug — the overlay's id didn't match that CSS selector, so
  // both contexts silently rendered at the same 2.5rem size.
  const el = h('div.presence', {
    dataset: { state: 'unavailable' },
    role: 'img',
    'aria-label': LABEL.unavailable,
  }, halo, core, badge);

  return {
    el,
    /** @param {string} state @param {{ttsTrouble?:boolean}} flags */
    update(state, flags = {}) {
      if (el.dataset.state !== state) {
        el.dataset.state = state;
        el.setAttribute('aria-label', LABEL[state] || LABEL.ready);
      }
      badge.hidden = !flags.ttsTrouble;
      badge.style.background = 'var(--warning)';
    },
  };
}

export const presenceLabel = (s) => LABEL[s] || LABEL.ready;
