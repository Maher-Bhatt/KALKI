/** Diagnostics drawer. Raw exception text from the server's _safe_call wrapper
 *  lives here and nowhere else — users read a mapped message, maintainers read
 *  the truth. Never renders a secret: /api/settings/get masks them server-side
 *  and this view does not request settings at all. */

import { h } from '../lib/dom.js';
import { callLog } from '../api/client.js';
import { store } from '../state/store.js';
import { openDialog } from '../components/dialog.js';

export function openDiagnostics(extraDetail) {
  const s = store.status || {};
  const safe = { ...s };
  delete safe.terminalLogs;

  openDialog({
    title: 'Diagnostics',
    description: 'Local state only. Nothing here is transmitted.',
    width: '44rem',
    body: h('div.stack', null,
      extraDetail ? h('div', null,
        h('h3.t-label', null, 'Reported error'),
        h('pre.pre-out', null, String(extraDetail)),
      ) : null,
      h('div', null,
        h('h3.t-label', null, 'Voice state'),
        h('pre.pre-out', null, JSON.stringify({
          state: store.voice.state,
          speaking: s.speaking,
          listenerPaused: s.listenerPaused,
          listenerMicMuted: s.listenerMicMuted,
          ttsProvider: s.ttsProvider,
          ttsLastError: s.ttsLastError,
          ttsProbeError: s.ttsProbeError,
          listenerCapabilityNotice: s.listenerCapabilityNotice,
        }, null, 2)),
      ),
      h('div', null,
        h('h3.t-label', null, 'Recent API calls'),
        h('pre.pre-out', null, callLog().map((c) => `${c.kind.padEnd(16)} ${String(c.status).padStart(3)}  ${String(c.ms).padStart(5)}ms  ${c.path}`).join('\n') || 'none yet'),
      ),
      h('div', null,
        h('h3.t-label', null, 'Status payload'),
        h('pre.pre-out', null, JSON.stringify(safe, null, 2)),
      ),
      Array.isArray(s.terminalLogs) && s.terminalLogs.length ? h('div', null,
        h('h3.t-label', null, 'Service log'),
        h('pre.pre-out', null, s.terminalLogs.slice(-40).join('\n')),
      ) : null,
    ),
    actions: [
      h('button.btn.btn-secondary', {
        type: 'button',
        onClick: () => navigator.clipboard?.writeText(JSON.stringify({ voice: store.voice, status: safe, calls: callLog() }, null, 2)),
      }, 'Copy report'),
    ],
  });
}
