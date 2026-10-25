/** Workbench — workflows, code, and screen vision.
 *
 *  Functional tabs: Workflows, Code studio, Screen and vision, Skills catalog.
 *  Workflows execute defined action chains and trigger confirmations for
 *  destructive operations. Code studio provides multi-language generation
 *  and execution. Screen & vision handles desktop capture, image analysis,
 *  and document extraction. Skills catalog allows toggling capabilities. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { workflows, code, vision, desktop } from '../api/endpoints.js';
import { set } from '../state/store.js';
import { emptyState } from '../components/states.js';
import { openDialog, confirmDialog } from '../components/dialog.js';
import { ok, err, toast } from '../state/toasts.js';

/* ── Tab state ────────────────────────────────────────────────────────── */

let activeTab = 'workflows'; // 'workflows' | 'terminal' | 'workspace' | 'code' | 'vision' | 'skills'

/* ── Workflows state ──────────────────────────────────────────────────── */

const MODES = [
  { id: 'study mode', label: 'Study mode', icon: 'flow', desc: 'Silences notifications, opens your notes, starts a 50-minute focus timer.', voice: 'calm, brief' },
  { id: 'gaming mode', label: 'Gaming mode', icon: 'play', desc: 'Closes background apps, raises performance, pauses sync.', voice: 'upbeat' },
  { id: 'developer mode', label: 'Dev mode', icon: 'code', desc: 'Opens editor and terminal, checks Git status, starts local servers.', voice: 'concise' },
  { id: 'ctf mode', label: 'CTF mode', icon: 'security', desc: 'Opens tools and a notes template, starts the scoped lab workspace.', voice: 'terse' },
  { id: 'focus mode', label: 'Deep focus', icon: 'eye', desc: 'Quits distracting apps and blocks sites. Needs your confirmation.', voice: 'silent', advanced: true },
];

const customRoutines = [];
const runs = [];

function recordRun(entry) {
  runs.unshift({ ...entry, at: Date.now() });
  if (runs.length > 20) runs.pop();
  set('workbench', {});
}

async function runMode(mode) {
  const meta = MODES.find((m) => m.id === mode.id) || mode;
  if (meta?.advanced) {
    const go = await confirmDialog({
      title: `Switch to ${meta.label} mode?`,
      description: 'This changes how KALKI speaks and may adjust system volume. You can switch back at any time.',
      confirmLabel: 'Switch mode',
      danger: false,
    });
    if (!go) return;
  }
  const entry = { mode: meta.label || mode.id, id: mode.id, state: 'running', detail: 'Executing workflow steps...' };
  recordRun(entry);
  render();
  const r = await workflows.run(mode.id);
  if (r.ok) {
    entry.state = 'succeeded';
    entry.detail = r.data.result || (Array.isArray(r.data.log) ? r.data.log.join(' · ') : r.data.message) || 'Mode applied successfully';
    entry.logs = Array.isArray(r.data.log) ? r.data.log : [];
    ok(`${meta?.label || mode.id} is active`);
  } else {
    entry.state = 'failed';
    entry.detail = r.detail || r.message || 'Workflow execution failed';
    entry.logs = [];
    err(r.message || 'Workflow failed', r.detail);
  }
  render();
}

function openCreateRoutineModal() {
  let nameInput;
  let aliasInput;
  const currentActions = [
    { type: 'open_app', value: '' },
    { type: 'speak', value: '' }
  ];

  let bodyContainer;

  function renderActionsList() {
    if (!bodyContainer) return;
    bodyContainer.replaceChildren();

    const form = h('div.col.g12', null,
      h('div.col.g4', null,
        h('label.t-label', null, 'Routine Name'),
        h('input.input', {
          placeholder: 'e.g., Morning Focus or Stream Setup',
          value: nameInput?.value || '',
          ref: el => { nameInput = el; }
        })
      ),
      h('div.col.g4', null,
        h('label.t-label', null, 'Voice Trigger / Alias (optional)'),
        h('input.input', {
          placeholder: 'e.g., start morning or prep stream',
          value: aliasInput?.value || '',
          ref: el => { aliasInput = el; }
        })
      ),
      h('div.col.g8', { style: { marginTop: '6px' } },
        h('div.row.sb', null,
          h('label.t-label', null, 'Actions Chain'),
          h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            onClick: () => {
              currentActions.push({ type: 'open_app', value: '' });
              renderActionsList();
            }
          }, icon('plus', 14), ' Add step')
        ),
        ...currentActions.map((act, idx) => {
          return h('div.card.in.row.g8', { style: { padding: '8px 10px', alignItems: 'center' } },
            h('span.t-meta', { style: { width: '18px', color: 'var(--mut)', textAlign: 'center' } }, `${idx + 1}`),
            h('select.select', {
              style: { width: '130px', flex: 'none', height: '28px', fontSize: '12px' },
              onChange: (e) => {
                act.type = e.target.value;
                if (act.type === 'set_volume' && !act.value) act.value = '50';
                renderActionsList();
              }
            },
              h('option', { value: 'open_app', selected: act.type === 'open_app' }, 'Open App'),
              h('option', { value: 'open_url', selected: act.type === 'open_url' }, 'Open URL'),
              h('option', { value: 'set_volume', selected: act.type === 'set_volume' }, 'Set Volume'),
              h('option', { value: 'speak', selected: act.type === 'speak' }, 'Speak Text')
            ),
            h('input.input', {
              style: { flex: '1', height: '28px', fontSize: '12px' },
              placeholder: act.type === 'open_app' ? 'App name (e.g., code, spotify, chrome)'
                : act.type === 'open_url' ? 'URL (e.g., https://github.com)'
                : act.type === 'set_volume' ? 'Volume 0 - 100 (e.g., 50)'
                : 'Spoken phrase',
              value: act.value,
              type: act.type === 'set_volume' ? 'number' : 'text',
              min: act.type === 'set_volume' ? '0' : undefined,
              max: act.type === 'set_volume' ? '100' : undefined,
              onInput: (e) => { act.value = e.target.value; }
            }),
            currentActions.length > 1 ? h('button.btn.btn-sm.btn-ghost', {
              type: 'button',
              'aria-label': 'Remove action',
              style: { padding: '4px', color: 'var(--mut)' },
              onClick: () => {
                currentActions.splice(idx, 1);
                renderActionsList();
              }
            }, icon('trash', 14)) : null
          );
        })
      )
    );

    bodyContainer.appendChild(form);
  }

  bodyContainer = h('div', { style: { minWidth: '380px' } });
  renderActionsList();

  const { close } = openDialog({
    title: 'Create a routine',
    description: 'Chain actions into a custom automated routine for KALKI.',
    width: '32rem',
    body: bodyContainer,
    actions: [
      h('button.btn.btn-secondary', { type: 'button', onClick: () => close() }, 'Cancel'),
      h('button.btn.btn-primary', {
        type: 'button',
        onClick: async () => {
          const name = nameInput?.value?.trim();
          if (!name) {
            toast({ kind: 'warning', text: 'Please enter a routine name.' });
            nameInput?.focus();
            return;
          }
          const validActions = currentActions.filter(a => a.value && String(a.value).trim());
          if (!validActions.length) {
            toast({ kind: 'warning', text: 'Please add at least one action with a value.' });
            return;
          }
          const formatted = validActions.map(a => [
            a.type,
            a.type === 'set_volume' ? parseInt(a.value, 10) || 50 : String(a.value).trim()
          ]);
          const alias = aliasInput?.value?.trim() ? [aliasInput.value.trim()] : [];

          try {
            const r = await workflows.saveCustom(name, formatted, alias);
            if (r.ok || r.status === 200) {
              ok(`Routine "${name}" saved!`);
            } else {
              toast({ kind: 'info', text: `Routine "${name}" created locally.` });
            }
          } catch {
            toast({ kind: 'info', text: `Routine "${name}" created locally.` });
          }

          customRoutines.push({
            id: name.toLowerCase(),
            label: name,
            desc: `Custom routine with ${formatted.length} actions: ${formatted.map(f => f[0].replace('_', ' ')).join(', ')}`,
            voice: 'assistant',
            custom: true,
            actions: formatted,
            icon: 'flow'
          });

          close();
          render();
        }
      }, 'Save routine')
    ]
  });
}

/* ── Code studio state ───────────────────────────────────────────────── */

const CODE_LANGUAGES = [
  { id: 'python', label: 'Python' },
  { id: 'javascript', label: 'JavaScript' },
  { id: 'powershell', label: 'PowerShell' },
  { id: 'bash', label: 'Shell' },
  { id: 'html', label: 'HTML/CSS' },
];

const codeState = {
  lang: 'python',
  prompt: '',
  source: '',
  output: '',
  exitCode: null,
  busy: false
};

async function generateCode(prompt) {
  if (!prompt || !prompt.trim()) return;
  codeState.busy = true;
  codeState.exitCode = null;
  render();
  const r = await code.generate(prompt.trim(), codeState.lang, false);
  codeState.busy = false;
  if (r.ok) {
    codeState.source = r.data.code || '';
    codeState.output = r.data.path ? `Script saved to ${r.data.path}` : '';
    codeState.exitCode = 0;
    ok('Code generated successfully');
  } else {
    codeState.output = r.detail || r.message || 'Generation failed';
    codeState.exitCode = 1;
    err(r.message || 'Generation failed', r.detail);
  }
  render();
}

async function runCode() {
  if (!codeState.source.trim()) return;
  const go = await confirmDialog({
    title: 'Run this code on your machine?',
    description: 'KALKI executes it locally through its verification sandbox. Only run code you understand.',
    confirmLabel: 'Run script',
    danger: false,
  });
  if (!go) return;
  codeState.busy = true;
  render();
  const r = await code.run(codeState.source, codeState.lang);
  codeState.busy = false;
  if (r.ok) {
    const d = r.data;
    const std = [d.stdout, d.stderr, d.error].filter(Boolean).join('\n');
    codeState.output = std || `Finished with exit code ${d.returncode ?? d.exit ?? 0}`;
    codeState.exitCode = d.returncode ?? d.exit ?? 0;
    if (d.stderr || d.error || (codeState.exitCode !== 0)) {
      toast({ kind: 'warning', text: 'Script finished with warnings or errors.' });
    } else {
      ok('Script finished successfully');
    }
  } else {
    codeState.output = r.detail || r.message || 'Execution failed';
    codeState.exitCode = 1;
    err(r.message || 'Execution error', r.detail);
  }
  render();
}

function copyCode() {
  if (!codeState.source) return;
  navigator.clipboard.writeText(codeState.source).then(() => {
    ok('Code copied to clipboard');
  }).catch(() => {
    toast({ kind: 'warning', text: 'Clipboard copy failed' });
  });
}

function clearCode() {
  codeState.source = '';
  codeState.output = '';
  codeState.exitCode = null;
  render();
}

/* ── Screen & vision state ───────────────────────────────────────────── */

const visionState = {
  // Screen
  screenImage: null,
  screenQuestion: 'What error is on my screen?',
  screenAnswer: '',
  screenMode: '',
  screenBusy: false,

  // Image analysis
  uploadedImage: null,
  uploadedImageName: '',
  imageQuestion: '',
  imageAnswer: '',
  imageBusy: false,

  // Documents
  docName: '',
  docSize: '',
  docText: '',
  docBusy: false,
};

async function captureDesktop() {
  visionState.screenBusy = true;
  render();
  try {
    const r = await vision.capture();
    if (r.ok && r.data?.image) {
      visionState.screenImage = r.data.image;
      ok('Desktop screen captured');
    } else if (navigator?.mediaDevices?.getDisplayMedia) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const video = document.createElement('video');
        video.srcObject = stream;
        await video.play();
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        stream.getTracks().forEach(t => t.stop());
        visionState.screenImage = canvas.toDataURL('image/jpeg', 0.85);
        ok('Desktop screen captured');
      } catch (mediaErr) {
        err(r.message || 'Screen capture failed', r.detail || mediaErr.message);
      }
    } else {
      err(r.message || 'Screen capture failed', r.detail || 'Pillow capture failed');
    }
  } catch (e) {
    err('Capture failed', e.message);
  } finally {
    visionState.screenBusy = false;
    render();
  }
}

async function analyzeScreen() {
  const q = visionState.screenQuestion.trim() || 'What is on my screen?';
  visionState.screenBusy = true;
  render();
  try {
    let r;
    if (visionState.screenImage) {
      const b64 = visionState.screenImage.replace(/^data:image\/[a-z]+;base64,/, '');
      r = await vision.image(b64, q);
    } else {
      r = await vision.screen(q);
    }
    if (r.ok) {
      visionState.screenAnswer = r.data.reply || r.data.ocr || 'Screen analysis complete.';
      visionState.screenMode = r.data.mode || 'vision';
      ok('Screen analysis finished');
    } else {
      visionState.screenAnswer = r.detail || r.message || 'Vision analysis failed.';
      err(r.message || 'Analysis failed', r.detail);
    }
  } catch (e) {
    visionState.screenAnswer = e.message;
    err('Analysis failed', e.message);
  } finally {
    visionState.screenBusy = false;
    render();
  }
}

async function analyzeUploadedImage() {
  if (!visionState.uploadedImage) {
    toast({ kind: 'warning', text: 'Please select an image first.' });
    return;
  }
  const q = visionState.imageQuestion.trim() || 'Analyze and describe what is in this image.';
  visionState.imageBusy = true;
  render();
  try {
    const b64 = visionState.uploadedImage.replace(/^data:image\/[a-z]+;base64,/, '');
    const r = await vision.image(b64, q);
    if (r.ok) {
      visionState.imageAnswer = r.data.reply || 'Image analysis finished.';
      ok('Image analysis finished');
    } else {
      visionState.imageAnswer = r.detail || r.message || 'Failed to analyze image.';
      err(r.message || 'Analysis failed', r.detail);
    }
  } catch (e) {
    visionState.imageAnswer = e.message;
    err('Analysis failed', e.message);
  } finally {
    visionState.imageBusy = false;
    render();
  }
}

async function parseDocumentFile(file) {
  if (!file) return;
  visionState.docName = file.name;
  visionState.docSize = (file.size / 1024).toFixed(1) + ' KB';
  if (file.size > 1024 * 1024) {
    visionState.docSize = (file.size / (1024 * 1024)).toFixed(1) + ' MB';
  }
  visionState.docBusy = true;
  visionState.docText = '';
  render();

  try {
    const isText = /\.(txt|md|csv|json|py|js|html|css|log)$/i.test(file.name);
    if (isText) {
      const text = await file.text();
      visionState.docText = text;
      ok(`Extracted text from ${file.name}`);
    } else {
      const reader = new FileReader();
      const b64Promise = new Promise((resolve, reject) => {
        reader.onload = () => {
          const res = reader.result;
          const b64 = typeof res === 'string' ? res.replace(/^data:[^;]+;base64,/, '') : '';
          resolve(b64);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(file);
      const b64 = await b64Promise;
      const r = await vision.parseDocument(file.name, b64);
      if (r.ok) {
        visionState.docText = r.data.text || 'No text could be extracted from document.';
        ok(`Extracted text from ${file.name}`);
      } else {
        visionState.docText = `Error parsing document: ${r.detail || r.message}`;
        err(r.message || 'Document parse failed', r.detail);
      }
    }
  } catch (e) {
    visionState.docText = `Error reading file: ${e.message}`;
    err('Document read error', e.message);
  } finally {
    visionState.docBusy = false;
    render();
  }
}

/* ── Skills state ────────────────────────────────────────────────────── */

let skillsLoaded = false;
let skillsSearch = '';
let skillsCategory = 'All';

const CATALOG_SKILLS = [
  { id: 'calendar', name: 'Google Calendar', icon: 'calendar', category: 'Productivity', desc: 'Read schedules, check meetings, and create agenda reminders.', needs: ['Google credentials'], enabled: true },
  { id: 'spotify', name: 'Spotify Music', icon: 'music', category: 'Integrations', desc: 'Playback control, lo-fi study tracks, and playlist automation.', needs: ['Spotify credentials'], enabled: true },
  { id: 'github', name: 'GitHub Integration', icon: 'code', category: 'Integrations', desc: 'Check repositories, git statuses, and monitor issues/pull requests.', needs: ['GitHub token'], enabled: true },
  { id: 'search', name: 'Web Search', icon: 'search', category: 'Productivity', desc: 'Real-time web intelligence using Tavily / DuckDuckGo search.', needs: [], enabled: true },
  { id: 'vision', name: 'Desktop Vision', icon: 'eye', category: 'System & Automation', desc: 'Screenshot capture, multimodal visual reasoning, and OCR analysis.', needs: ['Groq Vision API / Pillow'], enabled: true },
  { id: 'terminal', name: 'Sandbox Terminal', icon: 'term', category: 'Developer', desc: 'Execute isolated scripts and verify command outcomes.', needs: [], enabled: true },
  { id: 'documents', name: 'Document Intelligence', icon: 'note', category: 'Productivity', desc: 'Extract and parse text from PDF, DOCX, XLSX, and TXT files.', needs: [], enabled: true },
  { id: 'cyber', name: 'Security Toolkit', icon: 'security', category: 'Security', desc: 'Hash lookup, CVE scanning, DNS enumeration, and dorking utilities.', needs: [], enabled: true },
  { id: 'notes', name: 'Notes & Reminders', icon: 'note', category: 'Productivity', desc: 'Semantic memory storage, quick capture, and temporal task scheduling.', needs: [], enabled: true },
  { id: 'voice', name: 'Adaptive Voice Profiles', icon: 'mic', category: 'System & Automation', desc: 'Context-aware speech modulation across gaming, focus, and study modes.', needs: ['TTS Engine'], enabled: true },
];

let skillsList = [...CATALOG_SKILLS];

async function toggleSkill(s) {
  s.enabled = !s.enabled;
  render();
  try {
    const { post } = await import('../api/client.js');
    const r = await post('/api/skills/toggle', { id: s.id, enabled: s.enabled });
    if (r.ok) {
      toast({ kind: 'info', text: `${s.name} ${s.enabled ? 'enabled' : 'disabled'}` });
    }
  } catch (e) {
    console.error('Failed to toggle skill:', e);
  }
}

/* ── View Rendering ──────────────────────────────────────────────────── */

let renderFn = () => set('workbench', {});
const render = () => renderFn();

export function workbenchView() {
  const main = h('div.pad');
  const aside = h('div', { style: { display: 'contents' } });
  const view = { main, aside };

  let promptIn;
  let sourceIn;
  let screenIn;
  let imageIn;
  let skillsIn;

  if (!skillsLoaded) {
    skillsLoaded = true;
    import('../api/client.js').then(({ get }) => get('/api/skills/list')).then(r => {
      if (r.ok && (r.data?.skills || Array.isArray(r.data))) {
        const remote = r.data.skills || r.data;
        remote.forEach(rem => {
          const match = skillsList.find(s => s.id === rem.id);
          if (match) {
            match.enabled = rem.enabled;
            if (rem.needs) match.needs = rem.needs;
          } else {
            skillsList.push({
              id: rem.id,
              name: rem.name || rem.id,
              icon: 'sliders',
              category: 'General',
              desc: rem.desc || 'System capability',
              needs: rem.needs || [],
              enabled: rem.enabled ?? true
            });
          }
        });
        view.render();
      }
    }).catch(() => {});
  }

  const getRunStateIcon = (modeId) => {
    const r = runs.find(run => run.id === modeId || run.mode === modeId);
    if (!r) return null;
    return h('span.chip.ok', null, `Last run ${new Date(r.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
  };

  /* ── Tab 1: Workflows Content ───────────────────────────────────────── */
  /* ── System Terminal Tab State & Renderer ────────────────────────── */
let terminalHistory = [
  'KALKI Sovereign Desktop Environment [PowerShell / Native Host]',
  'Type any system command or click quick action presets below.'
];
let terminalInputVal = '';
let terminalCwd = '';
let terminalBusy = false;

function renderTerminalTab() {
  const outputEl = h('div.term-body', { ref: el => { if (el) el.scrollTop = el.scrollHeight; } }, terminalHistory.join('\n\n'));
  
  const presets = [
    { label: 'System Info', cmd: 'systeminfo' },
    { label: 'Git Status', cmd: 'git status' },
    { label: 'Running Python', cmd: 'tasklist /FI "IMAGENAME eq python.exe"' },
    { label: 'Directory (dir)', cmd: 'dir' },
    { label: 'Network Config', cmd: 'ipconfig' },
    { label: 'Ping Loopback', cmd: 'ping 127.0.0.1 -n 3' },
  ];

  async function runCmd(cmd) {
    if (!cmd.trim() || terminalBusy) return;
    terminalBusy = true;
    terminalHistory.push(`PS > ${cmd}`);
    render();
    try {
      const res = await desktop.exec(cmd, terminalCwd);
      if (res && res.ok) {
        const out = (res.stdout || res.stderr || '[Completed with 0 output]').trim();
        terminalHistory.push(`[Exit code: ${res.exit_code} in ${res.duration_ms}ms]\n${out}`);
      } else {
        terminalHistory.push(`[Error: ${res?.error || 'Failed'}]`);
      }
    } catch (e) {
      terminalHistory.push(`[Execution failed: ${e.message}]`);
    } finally {
      terminalBusy = false;
      render();
    }
  }

  const inputEl = h('input.term-input', {
    type: 'text',
    placeholder: 'Enter PowerShell / CMD command (e.g. dir, git status, ping 127.0.0.1)...',
    value: terminalInputVal,
    onInput: (e) => terminalInputVal = e.target.value,
    onKeyDown: (e) => {
      if (e.key === 'Enter') {
        const c = terminalInputVal;
        terminalInputVal = '';
        runCmd(c);
      }
    }
  });

  return h('div.col.g12', { style: { marginTop: '16px' } },
    h('div.term-box', null,
      h('div.term-header', null,
        h('span.row.g8', null,
          h('span.dot.active', { style: { width: '8px', height: '8px', borderRadius: '50%', background: '#4cc061', display: 'inline-block' } }),
          h('b', null, 'LOCAL SYSTEM TERMINAL'),
          h('span.dim', null, '• Native PowerShell Host')
        ),
        h('div.row.g8', null,
          h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            onClick: () => { terminalHistory = ['[Terminal cleared]']; render(); }
          }, 'Clear Output')
        )
      ),
      h('div.term-presets', null,
        ...presets.map(p => h('button.term-pill', {
          type: 'button',
          onClick: () => runCmd(p.cmd)
        }, p.label))
      ),
      outputEl,
      h('div.term-input-row', null,
        h('span.term-prompt', null, 'PS >'),
        inputEl,
        h('button.btn.btn-sm.btn-primary', {
          type: 'button',
          disabled: terminalBusy,
          onClick: () => {
            const c = terminalInputVal;
            terminalInputVal = '';
            runCmd(c);
          }
        }, terminalBusy ? 'Running...' : 'Run')
      )
    )
  );
}

/* ── Workspace & Local File Studio ────────────────────────────────── */
let currentWorkspaceDir = '';
let workspaceFiles = [];
let activeFilePath = '';
let activeFileContent = '';
let wsLoading = false;

async function loadWorkspaceDir(path) {
  wsLoading = true;
  render();
  try {
    const res = await desktop.listDir(path);
    if (res && res.ok) {
      currentWorkspaceDir = res.path;
      workspaceFiles = res.items || [];
    } else {
      err(res?.error || 'Failed to list directory');
    }
  } catch (e) {
    err(e.message);
  } finally {
    wsLoading = false;
    render();
  }
}

async function openFile(file) {
  if (file.is_dir) {
    loadWorkspaceDir(file.path);
    return;
  }
  try {
    const res = await desktop.readFile(file.path);
    if (res && res.ok) {
      activeFilePath = res.path;
      activeFileContent = res.content || '';
      render();
    } else {
      err(res?.error || 'Could not open file');
    }
  } catch (e) {
    err(e.message);
  }
}

async function saveCurrentFile() {
  if (!activeFilePath) return;
  try {
    const res = await desktop.writeFile(activeFilePath, activeFileContent);
    if (res && res.ok) {
      ok(`Saved ${activeFilePath.split(/[\\/]/).pop()} (${res.bytes} bytes)`);
    } else {
      err(res?.error || 'Failed saving file');
    }
  } catch (e) {
    err(e.message);
  }
}

function renderWorkspaceTab() {
  if (!currentWorkspaceDir && !wsLoading && workspaceFiles.length === 0) {
    loadWorkspaceDir();
  }

  const treeItems = workspaceFiles.map(f =>
    h('div.ws-item', {
      class: activeFilePath === f.path ? 'active' : '',
      onClick: () => openFile(f),
      title: f.path
    },
      icon(f.is_dir ? 'flow' : 'code', 14),
      h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, f.name)
    )
  );

  return h('div.col.g12', { style: { marginTop: '16px' } },
    h('div.workspace-container', null,
      h('div.ws-tree', null,
        h('div.row.sb', { style: { padding: '4px 6px', borderBottom: '1px solid var(--line)', marginBottom: '6px' } },
          h('span.t-label', null, 'Files'),
          h('button.btn.btn-xs.btn-secondary', {
            type: 'button',
            onClick: async () => {
              const res = await desktop.openFolderDialog();
              if (res && res.ok && res.path) loadWorkspaceDir(res.path);
            }
          }, 'Open Folder')
        ),
        treeItems.length ? treeItems : h('div.dim', { style: { padding: '12px', fontSize: '11px' } }, 'No files in folder')
      ),
      h('div.ws-editor-wrap', null,
        h('div.ws-editor-head', null,
          h('span.t-mono', { style: { fontSize: '12px', color: 'var(--fil)' } },
            activeFilePath ? activeFilePath.split(/[\\/]/).pop() : 'No file selected'
          ),
          h('div.row.g8', null,
            activeFilePath ? h('button.btn.btn-sm.btn-secondary', {
              type: 'button',
              onClick: () => desktop.reveal(activeFilePath)
            }, 'Reveal in Explorer') : null,
            activeFilePath ? h('button.btn.btn-sm.btn-primary', {
              type: 'button',
              onClick: saveCurrentFile
            }, 'Save File') : null
          )
        ),
        activeFilePath
          ? h('textarea.ws-textarea', {
              value: activeFileContent,
              onInput: (e) => activeFileContent = e.target.value
            })
          : h('div.col.center', { style: { height: '100%', justifyContent: 'center', color: 'var(--mut)', fontStyle: 'italic', fontSize: '13px', padding: '40px' } },
              'Select any file from the explorer on the left to view or edit.'
            )
      )
    )
  );
}

function renderWorkflowsTab() {
    const allModes = [...MODES, ...customRoutines];

    const cards = allModes.map(m =>
      h('div.card.col.g8', null,
        h('div.row.sb', null,
          h('div.row.g8', null,
            icon(m.icon || 'flow', 18),
            h('span.nm', { style: { fontWeight: '500' } }, m.label)
          ),
          getRunStateIcon(m.id) || (m.advanced ? h('span.chip.warn', null, 'Asks first') : h('span.chip', null, 'Ready'))
        ),
        h('div.sm.t2', { style: { flex: '1', minHeight: '38px' } }, m.desc),
        h('div.row.sb', { style: { marginTop: '8px' } },
          h('span.xs.mut', null, m.voice ? `Voice: ${m.voice}` : (m.custom ? 'Custom Routine' : '')),
          h('button.btn.pri', {
            type: 'button',
            onClick: () => runMode(m)
          }, icon('play', 14), ' Run')
        )
      )
    );

    const newRoutineCard = h('div.card.col.g8', {
      style: {
        borderStyle: 'dashed',
        cursor: 'pointer',
        justifyContent: 'center',
        background: 'transparent'
      },
      onClick: openCreateRoutineModal
    },
      h('div.row.g8', null,
        icon('plus', 18),
        h('span.nm', { style: { fontWeight: '500' } }, 'Create a routine')
      ),
      h('div.sm.t2', null, 'Chain steps into an automated custom action and assign a voice trigger.'),
      h('button.btn.btn-secondary', {
        type: 'button',
        style: { alignSelf: 'flex-start', marginTop: '6px' },
        onClick: (e) => { e.stopPropagation(); openCreateRoutineModal(); }
      }, icon('plus', 14), ' New routine')
    );

    return h('div.col.g16', null,
      h('div.grid3', null, ...cards, newRoutineCard)
    );
  }

  /* ── Tab 2: Code Studio Content ─────────────────────────────────────── */
  function renderCodeStudioTab() {
    let promptInput;
    const promptSuggestions = [
      'Rename all photos in folder by date taken',
      'System hardware resource health check',
      'Fetch JSON payload from a REST endpoint',
      'Interactive command-line menu utility'
    ];

    const promptCard = h('div.card.col.g8', null,
      h('div.row.sb', null,
        h('label.t-label', null, 'Prompt & Language'),
        h('select.select', {
          style: { width: '160px', height: '28px', fontSize: '12px' },
          onChange: (e) => {
            codeState.lang = e.target.value;
            view.render();
          }
        },
          ...CODE_LANGUAGES.map(l =>
            h('option', { value: l.id, selected: codeState.lang === l.id }, l.label)
          )
        )
      ),
      h('div.field', { style: { background: 'var(--inset)', border: '1px solid var(--lst)', borderRadius: '6px', padding: '8px' } },
        h('textarea.textarea', {
          rows: 2,
          style: { background: 'transparent', border: '0', width: '100%', outline: 'none', color: 'inherit', resize: 'none' },
          placeholder: 'Write a script that...',
          value: codeState.prompt,
          ref: el => { promptInput = el; promptIn = el; },
          onInput: (e) => { codeState.prompt = e.target.value; },
          onKeydown: (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              generateCode(e.target.value);
            }
          }
        })
      ),
      h('div.row.sb', { style: { alignItems: 'center' } },
        h('div.row.g4.wrap', null,
          ...promptSuggestions.map(s =>
            h('button.chip', {
              type: 'button',
              style: { cursor: 'pointer', background: 'var(--raised)' },
              onClick: () => {
                codeState.prompt = s;
                if (promptInput) promptInput.value = s;
                view.render();
              }
            }, s)
          )
        ),
        h('button.btn.pri', {
          type: 'button',
          disabled: codeState.busy,
          onClick: () => generateCode(promptInput?.value || codeState.prompt)
        }, icon('spark', 14), codeState.busy ? ' Generating...' : ' Generate')
      )
    );

    const linesCount = codeState.source ? codeState.source.split('\n').length : 0;
    const charsCount = codeState.source.length;

    const editorCard = h('div.card.col.g8', null,
      h('div.row.sb', null,
        h('div.row.g8', null,
          h('span.chip', null, CODE_LANGUAGES.find(l => l.id === codeState.lang)?.label || codeState.lang),
          h('span.xs.mut', null, `${linesCount} lines · ${charsCount} chars`)
        ),
        h('div.row.g8', null,
          h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            disabled: !codeState.source.trim(),
            onClick: copyCode
          }, icon('copy', 14), ' Copy'),
          h('button.btn.btn-sm.btn-primary', {
            type: 'button',
            disabled: codeState.busy || !codeState.source.trim(),
            onClick: runCode
          }, icon('play', 14), ' Run'),
          h('button.btn.btn-sm.btn-ghost', {
            type: 'button',
            disabled: !codeState.source && !codeState.output,
            onClick: clearCode
          }, icon('trash', 14), ' Clear')
        )
      ),
      h('textarea.t-mono', {
        ref: el => { sourceIn = el; },
        style: {
          width: '100%',
          minHeight: '220px',
          background: 'var(--inset)',
          color: 'var(--text)',
          border: '1px solid var(--lst)',
          padding: '12px',
          borderRadius: '6px',
          resize: 'vertical',
          lineHeight: '1.5',
          fontSize: '12px',
          fontFamily: 'var(--mono)'
        },
        spellcheck: false,
        placeholder: '// Generated code will appear here, or you can paste / type code directly...',
        value: codeState.source,
        onInput: (e) => { codeState.source = e.target.value; }
      })
    );

    const consoleStatusChip = codeState.busy
      ? h('span.chip.warn', null, 'Running...')
      : (codeState.exitCode === 0
        ? h('span.chip.ok', null, 'Exit code 0')
        : (codeState.exitCode !== null
          ? h('span.chip.dng', null, `Exit code ${codeState.exitCode}`)
          : h('span.chip', null, 'Console idle')));

    const consoleCard = h('div.card.col.g8', null,
      h('div.row.sb', null,
        h('div.row.g8', null,
          icon('term', 16),
          h('h2', null, 'Execution output console')
        ),
        consoleStatusChip
      ),
      h('pre.t-mono', {
        style: {
          padding: '10px 14px',
          background: 'var(--inset)',
          border: '1px solid var(--lst)',
          borderRadius: '6px',
          overflowX: 'auto',
          maxHeight: '200px',
          minHeight: '64px',
          fontSize: '12px',
          lineHeight: '1.4'
        }
      }, codeState.output || 'No output recorded. Run the script to see stdout and stderr.')
    );

    return h('div.col.g16', null, promptCard, editorCard, consoleCard);
  }

  /* ── Tab 3: Screen & Vision Content ─────────────────────────────────── */
  function renderVisionTab() {
    let screenQuestionInput;
    let imageQuestionInput;
    let docFileInput;
    let imgFileInput;

    const screenChips = [
      'What error is on my screen?',
      'Explain this code on screen',
      'Summarize this webpage or document',
      'Extract text via OCR'
    ];

    // Screen capture card
    const screenCard = h('div.card.col.g12', null,
      h('div.row.sb', null,
        h('div.row.g8', null,
          icon('screen', 18),
          h('span.nm', { style: { fontWeight: '500' } }, 'Screen capture & desktop vision')
        ),
        h('div.row.g8', null,
          visionState.screenImage ? h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            onClick: () => { visionState.screenImage = null; view.render(); }
          }, 'Clear preview') : null,
          h('button.btn.btn-sm.btn-primary', {
            type: 'button',
            disabled: visionState.screenBusy,
            onClick: captureDesktop
          }, icon('screen', 14), visionState.screenBusy ? ' Capturing...' : ' Capture Desktop')
        )
      ),

      visionState.screenImage ? h('div.col.g8', {
        style: {
          background: 'var(--inset)',
          border: '1px solid var(--lst)',
          borderRadius: '6px',
          padding: '10px',
          alignItems: 'center'
        }
      },
        h('img', {
          src: visionState.screenImage,
          alt: 'Screen capture preview',
          style: {
            maxWidth: '100%',
            maxHeight: '260px',
            borderRadius: '4px',
            objectFit: 'contain'
          }
        }),
        h('div.xs.mut', null, 'Screenshot captured from primary display')
      ) : h('div.card.in', {
        style: {
          padding: '24px',
          textAlign: 'center',
          borderStyle: 'dashed',
          color: 'var(--mut)'
        }
      },
        icon('screen', 24),
        h('div.sm.t2', { style: { marginTop: '8px' } }, 'No screenshot captured yet'),
        h('div.xs.mut', null, 'Click "Capture Desktop" to snapshot your screen, then ask vision questions.')
      ),

      h('div.col.g8', null,
        h('label.t-label', null, 'Vision Question'),
        h('div.field', { style: { background: 'var(--inset)' } },
          h('input.input', {
            style: { background: 'transparent', border: '0', width: '100%', outline: 'none', color: 'inherit' },
            placeholder: 'What error is on my screen? Or explain what is open...',
            value: visionState.screenQuestion,
            ref: el => { screenQuestionInput = el; screenIn = el; },
            onInput: (e) => { visionState.screenQuestion = e.target.value; },
            onKeydown: (e) => {
              if (e.key === 'Enter') {
                visionState.screenQuestion = e.target.value;
                analyzeScreen();
              }
            }
          })
        ),
        h('div.row.sb', { style: { alignItems: 'center' } },
          h('div.row.g4.wrap', null,
            ...screenChips.map(c =>
              h('button.chip', {
                type: 'button',
                style: { cursor: 'pointer', background: 'var(--raised)' },
                onClick: () => {
                  visionState.screenQuestion = c;
                  if (screenQuestionInput) screenQuestionInput.value = c;
                  view.render();
                }
              }, c)
            )
          ),
          h('button.btn.pri', {
            type: 'button',
            disabled: visionState.screenBusy,
            onClick: () => {
              if (screenQuestionInput) visionState.screenQuestion = screenQuestionInput.value;
              analyzeScreen();
            }
          }, icon('eye', 14), visionState.screenBusy ? ' Analyzing...' : ' Analyze Screen')
        )
      ),

      visionState.screenAnswer ? h('div.card.in.col.g8', { style: { marginTop: '8px' } },
        h('div.row.sb', null,
          h('div.row.g8', null,
            icon('spark', 16),
            h('span.sm', { style: { fontWeight: '500' } }, 'Vision AI analysis')
          ),
          h('span.chip.ok', null, visionState.screenMode === 'ocr' ? 'OCR mode' : 'Multimodal Vision')
        ),
        h('div.sm.t2', { style: { whiteSpace: 'pre-wrap', lineHeight: '1.5' } }, visionState.screenAnswer),
        h('div.row.sb', { style: { marginTop: '6px' } },
          h('span.xs.mut', null, 'KALKI voice engine also spoke this reply'),
          h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            onClick: () => {
              navigator.clipboard.writeText(visionState.screenAnswer);
              ok('Answer copied');
            }
          }, icon('copy', 14), ' Copy answer')
        )
      ) : null
    );

    // Image analysis card
    const imageCard = h('div.card.col.g12', null,
      h('div.row.sb', null,
        h('div.row.g8', null,
          icon('attach', 18),
          h('span.nm', { style: { fontWeight: '500' } }, 'Image analysis')
        ),
        h('input', {
          type: 'file',
          accept: 'image/*',
          style: { display: 'none' },
          ref: el => { imgFileInput = el; },
          onChange: (e) => {
            const f = e.target.files?.[0];
            if (f) {
              const reader = new FileReader();
              reader.onload = () => {
                visionState.uploadedImage = reader.result;
                visionState.uploadedImageName = f.name;
                view.render();
              };
              reader.readAsDataURL(f);
            }
          }
        }),
        h('button.btn.btn-sm.btn-secondary', {
          type: 'button',
          onClick: () => imgFileInput?.click()
        }, icon('attach', 14), ' Select Image')
      ),

      h('div.card.in', {
        style: {
          padding: '16px',
          textAlign: 'center',
          borderStyle: 'dashed',
          cursor: 'pointer'
        },
        onClick: () => imgFileInput?.click(),
        onDragover: (e) => { e.preventDefault(); e.stopPropagation(); },
        onDrop: (e) => {
          e.preventDefault();
          e.stopPropagation();
          const f = e.dataTransfer.files?.[0];
          if (f && f.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = () => {
              visionState.uploadedImage = reader.result;
              visionState.uploadedImageName = f.name;
              view.render();
            };
            reader.readAsDataURL(f);
          }
        }
      },
        visionState.uploadedImage ? h('div.col.g8', { style: { alignItems: 'center' } },
          h('img', {
            src: visionState.uploadedImage,
            alt: 'Uploaded preview',
            style: { maxWidth: '100%', maxHeight: '180px', borderRadius: '4px', objectFit: 'contain' }
          }),
          h('div.row.g8', null,
            h('span.xs.mut', null, visionState.uploadedImageName),
            h('button.btn.btn-sm.btn-ghost', {
              type: 'button',
              onClick: (e) => {
                e.stopPropagation();
                visionState.uploadedImage = null;
                visionState.uploadedImageName = '';
                view.render();
              }
            }, icon('trash', 14))
          )
        ) : h('div.col.g4', null,
          h('div.sm.t2', null, 'Drop any image here or click to browse'),
          h('div.xs.mut', null, 'PNG, JPG, WebP supported for multimodal analysis')
        )
      ),

      h('div.col.g8', null,
        h('label.t-label', null, 'Question about image'),
        h('div.field', { style: { background: 'var(--inset)' } },
          h('input.input', {
            style: { background: 'transparent', border: '0', width: '100%', outline: 'none', color: 'inherit' },
            placeholder: 'What does this image show? Solve problem, read text...',
            value: visionState.imageQuestion,
            ref: el => { imageQuestionInput = el; imageIn = el; },
            onInput: (e) => { visionState.imageQuestion = e.target.value; },
            onKeydown: (e) => {
              if (e.key === 'Enter') {
                visionState.imageQuestion = e.target.value;
                analyzeUploadedImage();
              }
            }
          })
        ),
        h('div.row.sb', null,
          h('span.xs.mut', null, 'Multimodal vision model parses diagram, code, UI or errors'),
          h('button.btn.pri', {
            type: 'button',
            disabled: visionState.imageBusy || !visionState.uploadedImage,
            onClick: () => {
              if (imageQuestionInput) visionState.imageQuestion = imageQuestionInput.value;
              analyzeUploadedImage();
            }
          }, icon('eye', 14), visionState.imageBusy ? ' Analyzing...' : ' Analyze Image')
        )
      ),

      visionState.imageAnswer ? h('div.card.in.col.g8', null,
        h('div.row.sb', null,
          h('span.sm', { style: { fontWeight: '500' } }, 'Analysis response'),
          h('button.btn.btn-sm.btn-secondary', {
            type: 'button',
            onClick: () => {
              navigator.clipboard.writeText(visionState.imageAnswer);
              ok('Answer copied');
            }
          }, icon('copy', 14), ' Copy')
        ),
        h('div.sm.t2', { style: { whiteSpace: 'pre-wrap', lineHeight: '1.5' } }, visionState.imageAnswer)
      ) : null
    );

    // Documents extractor card
    const docsCard = h('div.card.col.g12', null,
      h('div.row.sb', null,
        h('div.row.g8', null,
          icon('note', 18),
          h('span.nm', { style: { fontWeight: '500' } }, 'Documents & text extraction')
        ),
        h('span.xs.mut', null, 'PDF, DOCX, TXT, MD, CSV · 32 MB max')
      ),

      h('input', {
        type: 'file',
        accept: '.pdf,.docx,.doc,.txt,.md,.csv,.json,.py',
        style: { display: 'none' },
        ref: el => { docFileInput = el; },
        onChange: (e) => {
          const f = e.target.files?.[0];
          if (f) parseDocumentFile(f);
        }
      }),

      h('div.card.in', {
        style: {
          padding: '20px',
          textAlign: 'center',
          borderStyle: 'dashed',
          cursor: 'pointer'
        },
        onClick: () => docFileInput?.click(),
        onDragover: (e) => { e.preventDefault(); e.stopPropagation(); },
        onDrop: (e) => {
          e.preventDefault();
          e.stopPropagation();
          const f = e.dataTransfer.files?.[0];
          if (f) parseDocumentFile(f);
        }
      },
        icon('note', 24),
        h('div.sm.t2', { style: { marginTop: '8px' } }, 'Drop a document here or click to browse'),
        h('div.xs.mut', null, 'KALKI parses and extracts structured text contents locally')
      ),

      visionState.docBusy ? h('div.row.g8', { style: { justifyContent: 'center', padding: '12px' } },
        icon('refresh', 16),
        h('span.sm.mut', null, `Extracting text from ${visionState.docName}...`)
      ) : null,

      visionState.docText ? h('div.col.g8', null,
        h('div.row.sb', null,
          h('div.row.g8', null,
            h('span.chip', null, visionState.docName),
            h('span.xs.mut', null, `${visionState.docSize} · ${visionState.docText.length} characters`)
          ),
          h('div.row.g8', null,
            h('button.btn.btn-sm.btn-secondary', {
              type: 'button',
              onClick: () => {
                navigator.clipboard.writeText(visionState.docText);
                ok('Extracted text copied');
              }
            }, icon('copy', 14), ' Copy text'),
            h('button.btn.btn-sm.btn-ghost', {
              type: 'button',
              onClick: () => {
                visionState.docText = '';
                visionState.docName = '';
                view.render();
              }
            }, icon('trash', 14), ' Clear')
          )
        ),
        h('pre.t-mono', {
          style: {
            padding: '12px',
            background: 'var(--inset)',
            border: '1px solid var(--lst)',
            borderRadius: '6px',
            maxHeight: '260px',
            overflowY: 'auto',
            fontSize: '12px',
            lineHeight: '1.4'
          }
        }, visionState.docText)
      ) : null
    );

    return h('div.col.g16', null, screenCard, imageCard, docsCard);
  }

  /* ── Tab 4: Skills Catalog Content ──────────────────────────────────── */
  function renderSkillsTab() {
    let searchInput;
    const categories = ['All', 'Productivity', 'System & Automation', 'Integrations', 'Security', 'Developer'];

    const filtered = skillsList.filter(s => {
      const matchCat = skillsCategory === 'All' || s.category === skillsCategory;
      if (!matchCat) return false;
      if (!skillsSearch.trim()) return true;
      const q = skillsSearch.toLowerCase().trim();
      return (
        s.name.toLowerCase().includes(q) ||
        (s.desc && s.desc.toLowerCase().includes(q)) ||
        (s.category && s.category.toLowerCase().includes(q)) ||
        (s.needs && s.needs.some(n => n.toLowerCase().includes(q)))
      );
    });

    const searchHeader = h('div.col.g8', null,
      h('div.row.sb', null,
        h('div.field', { style: { flex: '1', background: 'var(--inset)' } },
          icon('search', 16),
          h('input.input', {
            style: { background: 'transparent', border: '0', width: '100%', outline: 'none', color: 'inherit' },
            placeholder: 'Search skills by name, description, or requirements...',
            value: skillsSearch,
            ref: el => { searchInput = el; skillsIn = el; },
            onInput: (e) => {
              skillsSearch = e.target.value;
              view.render();
            }
          })
        ),
        skillsSearch ? h('button.btn.btn-secondary', {
          type: 'button',
          style: { marginLeft: '8px' },
          onClick: () => {
            skillsSearch = '';
            if (searchInput) searchInput.value = '';
            view.render();
          }
        }, 'Clear') : null
      ),
      h('div.row.g4.wrap', null,
        ...categories.map(cat =>
          h(`button.chip${skillsCategory === cat ? '.ok' : ''}`, {
            type: 'button',
            style: { cursor: 'pointer' },
            onClick: () => {
              skillsCategory = cat;
              view.render();
            }
          }, cat)
        )
      )
    );

    const skillsGrid = filtered.length ? h('div.grid2', { style: { gap: '14px' } },
      ...filtered.map(s =>
        h('div.card.col.g8', null,
          h('div.row.sb', null,
            h('div.row.g8', null,
              icon(s.icon || 'sliders', 18),
              h('span.nm', { style: { fontWeight: '500' } }, s.name)
            ),
            h('div.row.g8', null,
              h(`span.chip.${s.enabled ? 'ok' : 'warn'}`, null, s.enabled ? 'Enabled' : 'Disabled'),
              h(`i.tg${s.enabled ? '.on' : ''}`, {
                style: { cursor: 'pointer' },
                'aria-label': `Toggle ${s.name}`,
                onClick: () => toggleSkill(s)
              })
            )
          ),
          h('div.sm.t2', { style: { flex: '1' } }, s.desc),
          h('div.row.sb', { style: { marginTop: '4px', alignItems: 'center' } },
            h('span.chip', null, s.category || 'General'),
            s.needs?.length
              ? h('span.xs.mut', null, `Needs: ${s.needs.join(', ')}`)
              : h('span.xs.mut', null, 'Zero configuration')
          )
        )
      )
    ) : emptyState({
      iconName: 'search',
      title: 'No matching skills found',
      body: 'Try adjusting your search keyword or selecting a different category filter.'
    });

    return h('div.col.g16', null, searchHeader, skillsGrid);
  }

  /* ── Master Render ──────────────────────────────────────────────────── */
  view.render = () => {
    const hd = h('div.hd', null,
      h('div', null,
        h('h1', null, 'Workbench'),
        h('div.sub', null, 'Run routines, generate code, explore vision, and customize skills.')
      ),
      h('div.row.g8', null,
        h('span.chip.ok', null, 'Sandbox ready'),
        h('span.chip.warn', null, 'Host execution off')
      )
    );

    const tabDefs = [
      { id: 'workflows', label: 'Workflows' },
      { id: 'terminal', label: 'System Terminal' },
      { id: 'workspace', label: 'Workspace & Files' },
      { id: 'code', label: 'Code studio' },
      { id: 'vision', label: 'Screen and vision' },
      { id: 'skills', label: 'Skills catalog' },
    ];

    const tabs = h('div.tabs', { role: 'tablist' },
      ...tabDefs.map(t =>
        h(`button${activeTab === t.id ? '.a' : ''}`, {
          type: 'button',
          role: 'tab',
          'aria-selected': activeTab === t.id ? 'true' : 'false',
          onClick: () => {
            activeTab = t.id;
            view.render();
          }
        }, t.label)
      )
    );

    let activeContent;
    if (activeTab === 'workflows') {
      activeContent = renderWorkflowsTab();
    } else if (activeTab === 'terminal') {
      activeContent = renderTerminalTab();
    } else if (activeTab === 'workspace') {
      activeContent = renderWorkspaceTab();
    } else if (activeTab === 'code') {
      activeContent = renderCodeStudioTab();
    } else if (activeTab === 'vision') {
      activeContent = renderVisionTab();
    } else if (activeTab === 'skills') {
      activeContent = renderSkillsTab();
    }

    // Preserve focus & cursor across background ticks and live re-renders
    const activeEl = document.activeElement;
    let focusTarget = null;
    let selStart = 0;
    let selEnd = 0;
    if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
      if (activeEl === promptIn) focusTarget = 'prompt';
      else if (activeEl === sourceIn) focusTarget = 'source';
      else if (activeEl === screenIn) focusTarget = 'screen';
      else if (activeEl === imageIn) focusTarget = 'image';
      else if (activeEl === skillsIn) focusTarget = 'skills';
      selStart = activeEl.selectionStart || 0;
      selEnd = activeEl.selectionEnd || 0;
    }

    mount(main, hd, tabs, activeContent);

    if (focusTarget === 'prompt' && promptIn) {
      promptIn.focus();
      promptIn.setSelectionRange?.(selStart, selEnd);
    } else if (focusTarget === 'source' && sourceIn) {
      sourceIn.focus();
      sourceIn.setSelectionRange?.(selStart, selEnd);
    } else if (focusTarget === 'screen' && screenIn) {
      screenIn.focus();
      screenIn.setSelectionRange?.(selStart, selEnd);
    } else if (focusTarget === 'image' && imageIn) {
      imageIn.focus();
      imageIn.setSelectionRange?.(selStart, selEnd);
    } else if (focusTarget === 'skills' && skillsIn) {
      skillsIn.focus();
      skillsIn.setSelectionRange?.(selStart, selEnd);
    }

    /* ── Aside Panel: Status, Logs, and Last Runs ─────────────────────── */
    mount(aside,
      h('h1', { style: { fontSize: '16px' } }, 'Workbench Status'),

      h('div.card.col.g8', null,
        h('div.row.sb', null,
          h('h2', null, 'Last run'),
          runs.length ? h(`span.chip.${runs[0].state === 'succeeded' ? 'ok' : runs[0].state === 'failed' ? 'dng' : 'warn'}`, null, runs[0].state) : null,
        ),
        runs.length ? h('div.col.g4', null,
          h('div.row.sb', null,
            h('span.sm', { style: { fontWeight: '500' } }, runs[0].mode),
            h('span.xs.mut', null, new Date(runs[0].at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
          ),
          h('div.xs.mut', null, runs[0].detail)
        ) : h('div.xs.mut', null, 'No workflow runs yet')
      ),

      h('div.card.col.g8', null,
        h('div.row.sb', null,
          h('h2', null, 'Execution logs'),
          runs.length ? h('span.xs.mut', null, `${runs.length} runs`) : null
        ),
        runs.length ? h('div.col.g8', { style: { maxHeight: '280px', overflowY: 'auto' } },
          ...runs.map(r =>
            h('div.card.in.col.g4', { style: { padding: '8px 10px' } },
              h('div.row.sb', null,
                h('span.sm', { style: { fontWeight: '500' } }, r.mode),
                h(`span.chip.${r.state === 'succeeded' ? 'ok' : r.state === 'failed' ? 'dng' : 'warn'}`, null, r.state)
              ),
              h('div.xs.mut', null, new Date(r.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
              r.logs?.length ? h('div.col.g2', { style: { marginTop: '4px' } },
                ...r.logs.map(l => h('div.xs.t-mono', { style: { color: 'var(--t2)', fontSize: '10px' } }, `• ${l}`))
              ) : (r.detail ? h('div.xs.mut', { style: { fontSize: '11px' } }, r.detail) : null)
            )
          )
        ) : h('div.xs.mut', null, 'No execution logs recorded yet. Run a workflow mode to view logs.')
      ),

      h('div.card.col.g8', null,
        h('h2', null, 'Execution environment'),
        h('div.row.sb', null,
          h('span.sm.t2', null, 'Host execution'),
          h('span.chip.warn', null, 'Sandbox mode')
        ),
        h('div.xs.mut', null, 'Workflows run verified system routines. Dangerous actions require confirmation.')
      )
    );
  };

  renderFn = () => view.render();
  view.render();
  return view;
}
