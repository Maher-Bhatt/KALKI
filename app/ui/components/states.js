/** Empty and error states. Every one answers: what is this, why use it,
 *  what next. Never a bare "Nothing here". */

import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';

export function emptyState({ iconName = 'spark', title, body, actions = [], hint }) {
  return h('div.state', null,
    icon(iconName, 28),
    h('h2', null, title),
    body ? h('p', null, body) : null,
    actions.length ? h('div.actions', null, ...actions) : null,
    hint ? h('p.t-meta.faint', null, hint) : null,
  );
}

export function errorState({ title = "That didn't load", message, detail, onRetry, onDiagnostics }) {
  return h('div.state.state-error', null,
    icon('alert', 28),
    h('h2', null, title),
    message ? h('p', null, message) : null,
    h('div.actions', null,
      onRetry ? h('button.btn.btn-secondary', { type: 'button', onClick: onRetry }, 'Try again') : null,
      onDiagnostics ? h('button.btn.btn-ghost', { type: 'button', onClick: () => onDiagnostics(detail) }, 'View details') : null,
    ),
  );
}

export function skeletonRows(n = 4, height = '2.5rem') {
  return h('div.stack', null, ...Array.from({ length: n }, (_, i) =>
    h('div.skeleton', { style: { height, opacity: String(1 - i * 0.15) }, 'aria-hidden': 'true' })));
}

export function loadingRow(text) {
  return h('div.inline.muted.t-body-sm', { role: 'status' },
    h('span.btn-dots', null, h('i'), h('i'), h('i')),
    h('span', null, text),
  );
}
