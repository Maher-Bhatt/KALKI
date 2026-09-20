/** Security — the advanced workspace.
 *
 *  Hidden from the rail unless the user turns it on in Settings → Advanced or
 *  has a Shodan key configured. Thirteen offensive-security endpoints shown to
 *  everyone is what makes software read as a hacking tool; gating them is the
 *  single largest change in how KALKI presents itself.
 *
 *  Nothing here lowers a backend gate. Port scans stay capped by the server's
 *  CYBER_SCAN_PORT_LIMIT and every destructive-sounding tool states its scope. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { cyber } from '../api/endpoints.js';
import { emptyState, loadingRow } from '../components/states.js';
import { ok, err } from '../state/toasts.js';

const TOOLS = [
  { id: 'surface', label: 'Attack surface', hint: 'A combined DNS, port and header brief for one host.', field: 'host', run: (v) => cyber.surface(v), scope: 'Scans the host you enter. Only run this against systems you are authorised to test.' },
  { id: 'dns', label: 'DNS records', hint: 'Resolve a domain and list its records.', field: 'domain', run: (v) => cyber.dns(v) },
  { id: 'headers', label: 'HTTP headers', hint: 'Fetch and inspect response headers for a URL.', field: 'url', run: (v) => cyber.headers(v) },
  { id: 'portscan', label: 'Port scan', hint: 'Check common ports on a host.', field: 'host', run: (v) => cyber.portscan(v), scope: 'Connects to ports on the host you enter. Authorised targets only. The server caps how many ports it will try.' },
  { id: 'subdomains', label: 'Subdomains', hint: 'Enumerate subdomains for a domain.', field: 'domain', run: (v) => cyber.subdomains(v) },
  { id: 'cve', label: 'CVE lookup', hint: 'Look up a CVE identifier.', field: 'CVE id', run: (v) => cyber.cve(v) },
  { id: 'identify', label: 'Identify hash', hint: 'Guess which algorithm produced a hash.', field: 'hash', run: (v) => cyber.identify(v) },
  { id: 'hash', label: 'Hash text', hint: 'Hash a string with SHA-256.', field: 'text', run: (v) => cyber.hash(v) },
  { id: 'encode', label: 'Encode', hint: 'Base64-encode a string.', field: 'text', run: (v) => cyber.encode(v) },
  { id: 'decode', label: 'Decode', hint: 'Base64-decode a string.', field: 'text', run: (v) => cyber.decode(v) },
  { id: 'dorks', label: 'Search dorks', hint: 'Build search queries for a target.', field: 'target', run: (v) => cyber.dorks(v) },
];

let current = TOOLS[0];
let value = '';
let result = null;
let busy = false;
let renderFn = () => {};

async function run() {
  if (!value.trim() || busy) return;
  busy = true; result = null; renderFn();
  const r = await current.run(value.trim());
  busy = false;
  if (r.ok) {
    const { ok: _drop, ...rest } = r.data;
    result = rest;
    ok(`${current.label} finished`);
  } else {
    result = null;
    err(r.message, r.detail);
  }
  renderFn();
}

/** Render a result as readable rows, with the raw payload behind a disclosure. */
function resultView(data) {
  const rows = [];
  for (const [k, v] of Object.entries(data)) {
    if (v === null || v === undefined || v === '') continue;
    const text = Array.isArray(v)
      ? (v.length ? v.map((x) => (typeof x === 'object' ? JSON.stringify(x) : String(x))).join(', ') : '—')
      : typeof v === 'object' ? JSON.stringify(v) : String(v);
    rows.push(h('div.row', null,
      h('span.t-meta.muted', { style: { minWidth: '9rem' } }, k),
      h('span.t-body-sm', { style: { flex: '1', minWidth: '0', wordBreak: 'break-word' } }, text),
    ));
  }
  return h('div.stack', null,
    rows.length ? h('div.stack', null, ...rows) : h('p.muted.t-body-sm', null, 'The tool returned no fields.'),
    h('details', null,
      h('summary.t-meta.muted', { style: { cursor: 'pointer', padding: 'var(--space-3) 0' } }, 'Raw output'),
      h('pre.pre-out', null, JSON.stringify(data, null, 2)),
    ),
  );
}

export function securityView() {
  const body = h('div.view-body.scroll');
  const view = h('section.view', { 'aria-label': 'Security' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Security'),
      h('span.spacer'),
      h('span.chip.chip-warning', null, 'Advanced'),
    ),
    body,
  );

  view.render = () => {
    const tabs = h('div.inline.wrap', { role: 'tablist', 'aria-label': 'Security tools' },
      ...TOOLS.map((t) => h('button.btn.btn-sm', {
        type: 'button', role: 'tab', class: current.id === t.id ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-ghost',
        'aria-selected': current.id === t.id ? 'true' : 'false',
        onClick: () => { current = t; result = null; renderFn(); },
      }, t.label)));

    mount(body,
      h('p.t-body-sm.muted', { style: { marginBottom: 'var(--space-6)', maxWidth: '46rem' } },
        'These tools run from your machine against the target you name. Use them on systems you own or have written permission to test.'),
      tabs,
      h('section.panel', { style: { marginTop: 'var(--space-6)' } },
        h('div.panel-head', null, h('h2', null, current.label), h('span.spacer'), h('span.t-meta.muted', null, current.hint)),
        h('div.panel-body.stack', null,
          current.scope ? h('div.toolrun.toolrun-confirm', null, h('div.toolrun-head', null, icon('alert', 16), h('span', null, current.scope))) : null,
          h('div.inline', null,
            h('input.input', {
              value, placeholder: current.field, 'aria-label': current.field,
              onInput: (e) => { value = e.target.value; },
              onKeydown: (e) => { if (e.key === 'Enter') run(); },
            }),
            h('button.btn.btn-secondary', { type: 'button', disabled: busy, onClick: run }, busy ? 'Running' : 'Run'),
          ),
          busy ? loadingRow(`Running ${current.label.toLowerCase()}`) : null,
          result ? resultView(result)
            : !busy ? emptyState({
                iconName: 'security', title: `Nothing run yet`,
                body: `Enter a ${current.field} above. Results appear here as readable fields, with the raw payload available underneath.`,
              }) : null,
        ),
      ),
    );
  };

  renderFn = view.render;
  return view;
}
