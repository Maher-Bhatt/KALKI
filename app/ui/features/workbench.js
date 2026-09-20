/** Workbench — workflows, code, and screen vision.
 *
 *  Advanced capability that shouldn't dominate the assistant. Workflow modes
 *  come from workflows.py; destructive modes go through the server's
 *  _queue_confirmation() path, which holds a pending action for 30 seconds —
 *  so the confirmation here shows a real countdown against a real deadline. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { workflows, code } from '../api/endpoints.js';
import { set } from '../state/store.js';
import { emptyState } from '../components/states.js';
import { confirmDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';

/** Modes defined in app/workflows.py. Confirmation-gated ones are marked so
 *  the UI warns before the server's own gate fires. */
const MODES = [
  { id: 'dev', label: 'Developer', desc: 'Crisp pair-programming voice, tuned for code sessions.' },
  { id: 'focus', label: 'Focus', desc: 'Low-distraction deep work. Quieter, slower delivery.' },
  { id: 'study', label: 'Study', desc: 'Relaxed pace for reading and revision.' },
  { id: 'gaming', label: 'Gaming', desc: 'Fast, low-latency, subdued so it stays out of the way.' },
  { id: 'ctf', label: 'CTF', desc: 'Sharp, precise delivery for security work.', advanced: true },
];

const runs = [];

function recordRun(entry) {
  runs.unshift({ ...entry, at: Date.now() });
  if (runs.length > 12) runs.pop();
  set('today', {}); // trigger a render pass
}

async function runMode(mode) {
  const meta = MODES.find((m) => m.id === mode.id);
  if (meta?.advanced) {
    const go = await confirmDialog({
      title: `Switch to ${meta.label} mode?`,
      description: 'This changes how KALKI speaks and may adjust system volume. You can switch back at any time.',
      confirmLabel: 'Switch mode', danger: false,
    });
    if (!go) return;
  }
  recordRun({ mode: mode.id, state: 'running' });
  const r = await workflows.run(mode.id);
  if (r.ok) {
    runs[0].state = 'succeeded';
    runs[0].detail = r.data.result || r.data.message || 'Mode applied';
    ok(`${meta?.label || mode.id} mode is active`);
  } else {
    runs[0].state = 'failed';
    runs[0].detail = r.detail || r.message;
    err(r.message, r.detail);
  }
  set('today', {});
}

function workflowCard(m) {
  return h('div.row', null,
    icon('flow', 18),
    h('div', { style: { flex: '1', minWidth: '0' } },
      h('div.t-body-sm', null, m.label),
      h('div.t-meta.muted', null, m.desc),
    ),
    m.advanced ? h('span.chip.chip-warning', null, 'confirms first') : null,
    h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => runMode(m) }, 'Run'),
  );
}

/* ── Code studio ─────────────────────────────────────────────────────── */

let codeState = { lang: 'python', source: '', output: '', busy: false };

async function generate(prompt) {
  codeState.busy = true;
  render();
  const r = await code.generate(prompt, codeState.lang, false);
  codeState.busy = false;
  if (r.ok) { codeState.source = r.data.code || ''; codeState.output = r.data.path ? `Saved to ${r.data.path}` : ''; ok('Code generated'); }
  else err(r.message, r.detail);
  render();
}

async function runCode() {
  if (!codeState.source.trim()) return;
  const go = await confirmDialog({
    title: 'Run this code on your machine?',
    description: 'KALKI executes it locally through its verification sandbox. Only run code you understand.',
    confirmLabel: 'Run it',
  });
  if (!go) return;
  codeState.busy = true;
  render();
  const r = await code.run(codeState.source, codeState.lang);
  codeState.busy = false;
  if (r.ok) {
    const d = r.data;
    codeState.output = [d.stdout, d.stderr, d.error].filter(Boolean).join('\n') || `Finished with exit code ${d.returncode ?? d.exit ?? 0}`;
    if (d.stderr || d.error) toast({ kind: 'warning', text: 'The script reported errors.' });
  } else {
    codeState.output = r.detail || r.message;
    err(r.message, r.detail);
  }
  render();
}

let renderFn = () => {};
const render = () => renderFn();

/* ── View ────────────────────────────────────────────────────────────── */

export function workbenchView() {
  const body = h('div.view-body.scroll');
  const view = h('section.view', { 'aria-label': 'Workbench' },
    h('header.view-head', null, h('h1', { tabindex: '-1', id: 'view-title' }, 'Workbench')),
    body,
  );

  view.render = () => {
    const grid = h('div.grid-2');

    grid.appendChild(h('section.panel', null,
      h('div.panel-head', null, h('h2', null, 'Modes')),
      h('div.panel-body', null,
        h('p.t-body-sm.muted', { style: { marginBottom: 'var(--space-5)' } },
          'A mode changes how KALKI sounds and behaves for a stretch of work. It stays until you change it.'),
        h('div.stack', null, ...MODES.map(workflowCard)),
      )));

    grid.appendChild(h('section.panel', null,
      h('div.panel-head', null, h('h2', null, 'Recent runs')),
      h('div.panel-body', null,
        runs.length
          ? h('div.stack', null, ...runs.map((r) => h('div.toolrun', { class: r.state === 'failed' ? 'toolrun toolrun-failed' : 'toolrun' },
              h('div.toolrun-head', null,
                icon(r.state === 'failed' ? 'alert' : r.state === 'running' ? 'clock' : 'check', 16),
                h('span', null, r.mode),
                h('span.spacer'),
                h('span.t-meta.muted', null, r.state),
              ),
              r.detail ? h('p.t-meta.muted', { style: { marginTop: 'var(--space-3)' } }, String(r.detail).slice(0, 220)) : null,
            )))
          : emptyState({ iconName: 'flow', title: 'No runs yet', body: 'Modes you run in this session appear here with their result.' }),
      )));

    // Code studio
    let promptEl, sourceEl;
    grid.appendChild(h('section.panel', { style: { gridColumn: '1 / -1' } },
      h('div.panel-head', null,
        h('h2', null, 'Code'),
        h('span.spacer'),
        h('select.select', {
          'aria-label': 'Language', style: { width: '9rem' },
          onChange: (e) => { codeState.lang = e.target.value; },
        }, ...['python', 'javascript', 'bash'].map((l) => h('option', { value: l, selected: codeState.lang === l }, l))),
      ),
      h('div.panel-body.stack', null,
        h('div.field', null,
          h('label', { for: 'code-prompt' }, 'Describe what the script should do'),
          h('div.inline', null,
            h('input.input', {
              id: 'code-prompt', placeholder: 'rename every .jpg in a folder to its capture date',
              ref: (el) => { promptEl = el; },
              onKeydown: (e) => { if (e.key === 'Enter' && promptEl.value.trim()) generate(promptEl.value.trim()); },
            }),
            h('button.btn.btn-secondary', {
              type: 'button', disabled: codeState.busy,
              onClick: () => promptEl.value.trim() && generate(promptEl.value.trim()),
            }, codeState.busy ? h('span.btn-dots', null, h('i'), h('i'), h('i')) : 'Generate'),
          ),
        ),
        h('div.field', null,
          h('label', { for: 'code-source' }, 'Source'),
          h('textarea.textarea.t-mono', {
            id: 'code-source', rows: 10, value: codeState.source,
            ref: (el) => { sourceEl = el; },
            onInput: (e) => { codeState.source = e.target.value; },
          }),
        ),
        h('div.inline', null,
          h('button.btn.btn-secondary', { type: 'button', disabled: codeState.busy || !codeState.source, onClick: runCode }, 'Run locally'),
          h('button.btn.btn-ghost', {
            type: 'button', disabled: !codeState.source,
            onClick: () => { navigator.clipboard?.writeText(codeState.source); ok('Code copied'); },
          }, 'Copy'),
          h('span.spacer'),
          h('span.t-meta.faint', null, 'Execution is gated by KALKI\u2019s sandbox settings.'),
        ),
        codeState.output ? h('pre.pre-out', null, codeState.output) : null,
      )));

    mount(body, grid);
  };

  renderFn = view.render;
  return view;
}
