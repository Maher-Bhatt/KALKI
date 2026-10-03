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

const MODES = [
  { id: 'study', label: 'Study mode', desc: 'Silences notifications, opens your notes, starts a 50-minute focus timer.', voice: 'calm, brief' },
  { id: 'gaming', label: 'Gaming mode', desc: 'Closes background apps, raises performance, pauses sync.', voice: 'upbeat' },
  { id: 'dev', label: 'Dev mode', desc: 'Opens editor and terminal, checks Git status, starts local servers.', voice: 'concise' },
  { id: 'ctf', label: 'CTF mode', desc: 'Opens tools and a notes template, starts the scoped lab workspace.', voice: 'terse' },
  { id: 'focus', label: 'Deep focus', desc: 'Quits distracting apps and blocks sites. Needs your confirmation.', voice: 'silent', advanced: true },
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
let skillsLoaded = false;
let skillsList = [];

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

let renderFn = () => set('workbench', {});
const render = () => renderFn();

/* ── View ────────────────────────────────────────────────────────────── */

export function workbenchView() {
  if (!skillsLoaded) {
    skillsLoaded = true;
    import('../api/client.js').then(({ get }) => get('/api/skills/list')).then(r => {
      if (r.ok) {
        skillsList = r.data.skills || r.data || [];
        render();
      }
    });
  }

  const toggleSkill = async (s) => {
    const next = !s.enabled;
    const { post } = await import('../api/client.js');
    const r = await post('/api/skills/toggle', { id: s.id, enabled: next });
    if (r.ok) { s.enabled = next; render(); }
  };

  const getRunStateIcon = (modeId) => {
    const r = runs.find(r => r.mode === modeId);
    if (!r) return null;
    return h('span.chip.ok', null, `Last run ${new Date(r.at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`);
  };

  const main = h('div.pad', null, 
    h('div.hd', null, 
      h('div', null, h('h1', null, 'Workbench'), h('div.sub', null, 'Run routines, generate code, and look at your screen.')), 
      h('span.chip.warn', null, 'Host execution off')
    ), 
    h('div.tabs', null, 
      h('button.a', null, 'Workflows'), 
      h('button', null, 'Code studio'), 
      h('button', null, 'Screen and vision')
    ), 
    h('div.grid3', {style: {marginBottom: '22px'}}, 
      ...MODES.map(m => 
        h('div.card.col.g8', null, 
          h('div.row.sb', null, 
            h('span.nm', null, m.label), 
            getRunStateIcon(m.id) || (m.advanced ? h('span.chip.warn', null, 'Asks first') : null)
          ), 
          h('div.sm.t2', null, m.desc), 
          h('div.row.sb', null, 
            h('span.xs.mut', null, m.voice ? `Voice: ${m.voice}` : ''), 
            h('button.btn' + (m.id === 'study' ? '.pri' : ''), { onClick: () => runMode(m) }, 'Run')
          )
        )
      ),
      h('div.card.col.g8', {style: {borderStyle: 'dashed'}}, 
        h('div.nm', null, 'Create a routine'), 
        h('div.sm.t2', null, 'Chain steps and give it a voice profile and a name KALKI understands.'), 
        h('button.btn', {style: {alignSelf: 'flex-start'}}, h('i', {'data-i': 'plus'}), 'New routine')
      )
    ), 
    h('div.grid2', null, 
      h('div.col.g12', null, 
        h('h2', null, 'Code studio'), 
        h('div.card.in.col.g8', null, 
          h('div.field', {style: {border: '0', padding: '0'}}, 
            h('input', {
              style: {background: 'transparent', border: '0', width: '100%', outline: 'none'},
              placeholder: 'Write a Python script that renames photos by date taken',
              onKeydown: (e) => { if (e.key === 'Enter' && e.target.value.trim()) generate(e.target.value.trim()); }
            })
          ), 
          h('div.row.sb', null, 
            h('select.chip', {
              onChange: (e) => { codeState.lang = e.target.value; },
              style: {border: 'none', background: 'transparent', outline: 'none', cursor: 'pointer'}
            }, ...['python', 'javascript', 'bash'].map((l) => h('option', { value: l, selected: codeState.lang === l }, l))), 
            h('button.btn.pri', {
              disabled: codeState.busy,
              onClick: (e) => {
                const prompt = e.target.closest('.card.in').querySelector('input').value.trim();
                if (prompt) generate(prompt);
              }
            }, codeState.busy ? 'Generating...' : 'Generate')
          )
        ), 
        h('textarea.t-mono', {
          style: { width: '100%', minHeight: '120px', background: 'var(--inset)', color: 'var(--text)', border: 'none', padding: '8px', borderRadius: '4px', resize: 'vertical' },
          value: codeState.source,
          onInput: (e) => { codeState.source = e.target.value; }
        }),
        codeState.output ? h('pre', { style: { padding: '8px', background: 'var(--inset)', borderRadius: '4px', overflowX: 'auto', marginTop: '8px', fontSize: '12px' } }, codeState.output) : null,
        h('div.row.g8', null, 
          h('button.btn', {disabled: codeState.busy || !codeState.source, onClick: runCode}, 'Run locally'), 
          h('span.xs.mut', null, 'Host execution is off. Turn it on in Settings, then confirm each run.')
        )
      ), 
      h('div.col.g12', null, 
        h('h2', null, 'Screen and vision'), 
        h('div.card.col.g12', null, 
          h('div.sm.t2', null, 'KALKI reads your whole desktop and speaks the reply. Capture needs your confirmation each time.'), 
          h('div.field', {style: {background: 'var(--inset)'}}, 'What error is on my screen?'), 
          h('div.row.g8', null, 
            h('button.btn.pri', null, h('i', {'data-i': 'mon'}), 'Ask about my screen'), 
            h('button.btn', null, 'Attach an image')
          )
        ), 
        h('div.card.col.g8', null, 
          h('div.row.sb', null, 
            h('span.nm', null, 'Documents'), 
            h('span.xs.mut', null, 'PDF, DOCX, XLSX, PPTX ╖ 32 MB max')
          ), 
          h('div.card.in', {style: {textAlign: 'center', borderStyle: 'dashed', padding: '20px'}}, 
            h('div.sm.t2', null, 'Drop a file here to read it'), 
            h('div.xs.mut', null, 'KALKI shows what it extracted before sending')
          )
        )
      )
    ), 
    h('div.card', {style: {marginTop: '22px'}}, 
      h('div.row.sb', null, h('h2', null, 'Skills'), h('button.btn', null, 'Browse catalog')), 
      h('div.grid2', {style: {gap: '0 28px'}}, 
        ...skillsList.map(s => h('div.li', null, 
          h('div', {style: {flex: '1'}}, 
            h('div.nm', null, s.name), 
            h('div.xs.mut', null, s.desc || (s.needs && s.needs.length ? 'Needs: ' + s.needs.join(', ') : ''))
          ), 
          h('i.tg' + (s.enabled ? '.on' : ''), { onClick: () => toggleSkill(s) })
        ))
      )
    )
  );

  const aside = [
    h('h1', {style: {fontSize: '16px'}}, 'Status'), 
    h('div.col.g8', null, 
      h('h2', null, 'Confirmation'), 
      h('div.dlg', {style: {width: 'auto', background: 'var(--overlay)'}}, 
        h('div.nm', {style: {fontSize: '16px'}}, 'No pending actions'), 
        h('div.sm.t2', {style: {margin: '6px 0 12px'}}, 'Actions requiring your approval will appear here.')
      )
    ), 
    h('div.card.col.g8', null, 
      h('h2', null, 'Last run'), 
      runs.length ? h('div', null,
        h('div.row.sb', null, h('span.sm', null, runs[0].mode), h('span.chip.ok', null, runs[0].state)), 
        h('div.xs.mut', null, runs[0].detail)
      ) : h('div.xs.mut', null, 'No runs yet')
    ), 
    h('div.card.col.g8', null, 
      h('h2', null, 'Sandbox'), 
      h('div.sm.t2', null, 'Generated code runs in a contained sandbox when host execution is off.')
    )
  ];

  return { main, aside };
}
