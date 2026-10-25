/** Ask — the assistant workspace. This is the application, not a destination.
 *
 *  Streaming lifecycle: idle → sending → streaming → complete | stopped | failed.
 *  Every state is named for the user; there is no unlabelled spinner. */

import { h, mount, autosize, stickyScroll, on, frag } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { renderMarkdown, toPlain } from '../lib/markdown.js';
import { relative, bytes, modelLabel } from '../lib/format.js';
import { streamChat } from '../api/stream.js';
import { system, vision, tasks, media, voice } from '../api/endpoints.js';
import { store, set, notify } from '../state/store.js';
import { refreshStatus, loadModels } from '../state/status.js';
import * as conv from '../state/conversations.js';
import { openDialog, promptDialog, confirmDialog } from '../components/dialog.js';
import { toast, ok, err } from '../state/toasts.js';
import { createPetCompanion, triggerPetReaction, openPetSettings } from './pet.js';

const MAX_UPLOAD = 32 * 1024 * 1024; // server MAX_BODY

let pending = [];      // staged attachments
let liveRegion = null;
let announceTimer = null;
let scroller = null;
let activeReadingMsgId = null;

/* ── Live region: announce accumulated text on a throttle, never per token ─ */
function announce(text) {
  if (!liveRegion) return;
  clearTimeout(announceTimer);
  announceTimer = setTimeout(() => { liveRegion.textContent = toPlain(text).slice(-600); }, 400);
}

function getGreeting() {
  const hr = new Date().getHours();
  if (hr < 12) return 'Good morning, Sir';
  if (hr < 18) return 'Good afternoon, Sir';
  return 'Good evening, Sir';
}

export function exportChatMarkdown(thread) {
  if (!thread || !thread.messages?.length) {
    ok('No messages to export');
    return;
  }
  const dateStr = new Date(thread.updatedAt || Date.now()).toLocaleString();
  let md = `# ${thread.title || 'Conversation'}\n\n`;
  md += `*Exported from KALKI Assistant on ${dateStr}*\n\n---\n\n`;
  for (const m of thread.messages) {
    const role = m.role === 'user' ? '👤 User' : '🤖 KALKI';
    const time = m.ts ? new Date(m.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    md += `### ${role} ${time ? `· ${time}` : ''}\n\n`;
    md += `${m.content || ''}\n\n`;
    if (m.attachments?.length) {
      md += `*Attachments: ${m.attachments.map(a => a.name).join(', ')}*\n\n`;
    }
  }
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${(thread.title || 'kalki_conversation').replace(/[^a-z0-9_-]/gi, '_')}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  ok('Conversation exported as Markdown');
}

/* ── Message rendering ───────────────────────────────────────────────── */

function messageActions(msg) {
  const btn = (name, label, fn) =>
    h('button.ib', { type: 'button', 'aria-label': label, title: label, onClick: fn }, icon(name, 15));

  const copyBtn = h('button.ib.btn-copy-msg', {
    type: 'button',
    'aria-label': 'Copy message',
    title: 'Copy message',
    onClick: (e) => {
      navigator.clipboard?.writeText(msg.content || '');
      ok('Message copied');
      copyBtn.classList.add('is-copied');
      setTimeout(() => copyBtn.classList.remove('is-copied'), 2000);
      e.currentTarget.blur();
    }
  }, icon('copy', 14), h('span.xs', null, 'Copy'));

  const actions = [copyBtn];

  if (msg.role === 'assistant') {
    const isPlaying = activeReadingMsgId === msg.id;
    const ttsBtn = h('button.ib.btn-tts-speaker' + (isPlaying ? '.is-playing' : ''), {
      type: 'button',
      'aria-label': isPlaying ? 'Stop reading' : 'Read aloud with KALKI voice',
      title: isPlaying ? 'Stop reading' : 'Read aloud with KALKI neural voice',
      onClick: async (e) => {
        e.stopPropagation();
        if (activeReadingMsgId === msg.id) {
          activeReadingMsgId = null;
          ttsBtn.classList.remove('is-playing');
          await system.stop();
          ok('Playback stopped');
        } else {
          activeReadingMsgId = msg.id;
          ttsBtn.classList.add('is-playing');
          ok('Reading aloud with neural voice...');
          const plain = toPlain(msg.content || '');
          const r = await voice.testTts(plain.slice(0, 4000));
          if (!r.ok) {
            ttsBtn.classList.remove('is-playing');
            activeReadingMsgId = null;
          }
        }
      }
    }, icon(isPlaying ? 'volumeOff' : 'volume', 14), h('span.xs', null, isPlaying ? 'Stop' : 'Read'));

    actions.push(ttsBtn);
    actions.push(btn('ref', 'Regenerate reply', () => regenerate(msg)));
    actions.push(btn('flag', 'Report this response', () => reportDialog(msg)));
  }

  if (msg.role === 'user') {
    actions.push(btn('pen', 'Edit and resend', () => editAndResend(msg)));
  }

  return h('div.row.g6', { style: { marginTop: '8px' } }, ...actions);
}

function renderMessage(msg) {
  if (msg.role === 'user') {
    return h('div.umsg', { dataset: { id: msg.id } },
      h('div.umsg-inner', null,
        h('div.umsg-head', null,
          h('span.who', null, 'You'),
          msg.ts ? h('span.xs.mut', null, relative(msg.ts)) : null,
          msg.origin === 'voice' ? h('span.chip', null, icon('mic', 10), 'Spoken') : null
        ),
        h('div.umsg-body', null, msg.content),
        msg.attachments?.length
          ? h('div.row.wrap.g8', { style: { marginTop: '8px' } }, ...msg.attachments.map((a) =>
              h('span.chip', null, icon('mon', 12), `${a.name} · ${a.size ? bytes(a.size) : ''}`)))
          : null
      ),
      h('div.umsg-actions', null,
        h('button.ib', {
          type: 'button',
          title: 'Copy text',
          onClick: () => { navigator.clipboard?.writeText(msg.content || ''); ok('Message copied'); }
        }, icon('copy', 14)),
        h('button.ib', {
          type: 'button',
          title: 'Edit and resend',
          onClick: () => editAndResend(msg)
        }, icon('edit', 14))
      )
    );
  }

  const body = h('div.kmsg-body');
  if (msg.failed) {
    mount(body, h('div.msg-error', null,
      h('div', null, msg.error || "KALKI couldn't answer that."),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', style: { marginTop: 'var(--space-4)' }, onClick: () => regenerate(msg) }, 'Try again'),
    ));
  } else if (!msg.content && msg.streaming) {
    mount(body, h('div.stream', null, h('i')));
  } else {
    let rawText = msg.content || '';
    const createdTasks = [];
    let executedSystemAction = null;
    rawText = rawText.replace(/\[TASK:\s*(.+?)\]/g, (m, t) => { createdTasks.push(t); return ''; });
    rawText = rawText.replace(/(?:TOOL CALL:\s*)?system_control\(\s*\{[^}]*["']lock["'][^}]*\}\s*\)/gi, () => {
      executedSystemAction = 'Workstation Locked (Attitude Enforcement Protocol)';
      return '';
    });
    rawText = rawText.replace(/\[ACTION:\s*lock\]/gi, () => {
      executedSystemAction = 'Workstation Locked (Attitude Enforcement Protocol)';
      return '';
    });
    
    const rendered = renderMarkdown(rawText, { streaming: !!msg.streaming, onCopy: () => ok('Code copied') });
    
    rendered.querySelectorAll('.code-block').forEach(block => {
      const head = block.querySelector('header span');
      if (head && head.textContent === 'json') {
        const code = block.querySelector('code').textContent;
        const card = h('div.card', { style: { margin: '12px 0' } },
          h('div.row.sb', null, h('span.row.g8.t2.nm', null, icon('check', 16), 'Tool data')),
          h('details', null,
            h('summary', { style: { cursor: 'pointer', fontSize: '12px', color: 'var(--mut)' } }, 'View JSON'),
            h('pre', { style: { fontSize: '12px', color: 'var(--mut)', overflowX: 'auto', marginTop: '4px' } }, code)
          )
        );
        block.replaceWith(card);
      }
    });

    if (msg.streaming) {
      rendered.querySelectorAll('p.dim.t-mono').forEach(p => {
        if (p.textContent.includes('{"') || p.textContent.includes('[\n')) {
          const card = h('div.card', { style: { margin: '12px 0' } },
            h('div.row.sb', null, h('span.row.g8.t2.nm', null, icon('cpu', 16), 'Receiving data...'))
          );
          p.replaceWith(card);
        }
      });
    }

    mount(body, rendered);
    if (msg.streaming) {
      body.appendChild(h('span.cur', { 'aria-hidden': 'true' }));
      body.appendChild(h('div.stream', null, h('i')));
    }

    if (executedSystemAction) {
      body.appendChild(
        h('div.note', { style: { marginTop: '8px', borderLeft: '3px solid #f87171', background: 'rgba(248, 113, 113, 0.08)' } },
          icon('security', 16, { style: { color: '#f87171' } }),
          h('b', { style: { color: '#f87171' } }, 'System Security Action:'),
          h('span.t2', { style: { flex: '1', marginLeft: '6px' } }, executedSystemAction)
        )
      );
    }

    for (const t of createdTasks) {
      body.appendChild(
        h('div.note', null,
          icon('check', 16, { style: { color: 'var(--okt)' } }),
          h('b', null, 'Task created'),
          h('span.t2', { style: { flex: '1', marginLeft: '4px' } }, t),
          h('button.btn.gh', {
            style: { height: '22px' },
            type: 'button',
            onClick: async (e) => {
              const btn = e.currentTarget;
              btn.disabled = true;
              const r = await tasks.remove(t);
              if (r.ok) btn.textContent = 'Undone';
              else { btn.disabled = false; toast({ kind: 'error', text: 'Could not undo task' }); }
            }
          }, 'Undo')
        )
      );
    }
  }

  let chipText = msg.model ? modelLabel(msg.model) : '';
  if (msg.streaming) chipText += ' · streaming';
  else if (msg.done) chipText += ' · 1.1 s';

  return h('div.kmsg', { dataset: { id: msg.id } },
    h('div.who', null, 
      h('span.dot'), 
      'KALKI', 
      chipText ? h('span.chip', null, chipText) : null
    ),
    msg.origin === 'voice' ? h('div.msg-voice-tag', null, 'Spoken · ' + relative(msg.ts)) : null,
    body,
    msg.stopped ? h('p.t-meta.faint', { style: { marginTop: 'var(--space-3)' } }, 'Stopped before finishing.') : null,
    !msg.streaming && !msg.failed ? messageActions(msg) : null,
  );
}

/* ── Streaming ───────────────────────────────────────────────────────── */

async function send(text, attachments = []) {
  if (store.conv.streaming) return;
  const trimmed = text.trim();
  if (!trimmed && !attachments.length) return;

  await conv.addMessage({ role: 'user', content: trimmed, attachments: attachments.map((a) => ({ name: a.name, size: a.size })) });

  const image = attachments.find((a) => a.kind === 'image');
  const docs = attachments.filter((a) => a.kind === 'doc');

  const assistant = await conv.addMessage({ role: 'assistant', content: '', streaming: true });
  const ctl = new AbortController();
  set('conv', { streaming: true, abort: ctl });
  refreshStatus();
  window.dispatchEvent(new CustomEvent('kalki:stream-start'));

  try {
    if (image) {
      const r = await vision.image(image.data, trimmed);
      if (r.ok) await conv.updateMessage(assistant.id, { content: r.data.reply || '(no description returned)', streaming: false, done: true });
      else await conv.updateMessage(assistant.id, { streaming: false, failed: true, error: r.message, detail: r.detail });
      window.dispatchEvent(new CustomEvent('kalki:stream-end'));
      return;
    }

    let prefix = '';
    for (const d of docs) {
      const r = await vision.parseDocument(d.name, d.data);
      if (r.ok && (r.data.text || r.data.content)) prefix += `\n\n[${d.name}]\n${r.data.text || r.data.content}`;
      else toast({ kind: 'warning', text: `Couldn't read ${d.name}`, detail: r.detail });
    }

    const wire = conv.wireMessages();
    if (prefix) wire[wire.length - 1] = { role: 'user', content: `${trimmed}\n${prefix}`.slice(0, 120000) };

    let acc = '';
    await streamChat(wire, {
      signal: ctl.signal,
      onToken: (t) => {
        acc += t;
        patchStreaming(assistant.id, acc);
        announce(acc);
      },
      onDone: async (info) => {
        const tasksToCreate = [];
        acc.replace(/\[TASK:\s*(.+?)\]/g, (m, t) => { tasksToCreate.push(t); return ''; });
        for (const t of tasksToCreate) {
          await tasks.add(t);
        }

        await conv.updateMessage(assistant.id, {
          content: acc, streaming: false, done: true,
          model: info.model || store.models.current, stopped: !!info.stopped,
        });
        announce(acc);
        window.dispatchEvent(new CustomEvent('kalki:stream-end'));
      },
      onError: async (e) => {
        await conv.updateMessage(assistant.id, { content: acc, streaming: false, failed: !acc, error: e.message, detail: e.detail });
        if (acc) toast({ kind: 'warning', text: 'The reply was cut short.' });
        window.dispatchEvent(new CustomEvent('kalki:stream-end'));
      },
    });
  } finally {
    set('conv', { streaming: false, abort: null });
    refreshStatus();
  }
}

function patchStreaming(id, text) {
  const kmsg = document.querySelector(`.kmsg[data-id="${id}"]`);
  if (!kmsg) { notify(); return; }
  const node = kmsg.querySelector('.kmsg-body');
  if (!node) return;
  mount(node, renderMarkdown(text, { streaming: true }));
  node.appendChild(h('span.cur', { 'aria-hidden': 'true' }));
  node.appendChild(h('div.stream', null, h('i')));
  scroller?.toBottom();
}

export function stopStreaming() {
  store.conv.abort?.abort('user');
  system.stop();
}

async function regenerate(msg) {
  const t = conv.active();
  if (!t) return;
  const i = t.messages.findIndex((m) => m.id === msg.id);
  const priorUser = [...t.messages.slice(0, i)].reverse().find((m) => m.role === 'user');
  if (!priorUser) return;
  await conv.dropMessagesFrom(priorUser.id);
  await send(priorUser.content, []);
}

async function editAndResend(msg) {
  const next = await promptDialog({ title: 'Edit and resend', label: 'Message', value: msg.content, confirmLabel: 'Resend' });
  if (!next) return;
  await conv.dropMessagesFrom(msg.id);
  await send(next, []);
}

function reportDialog(msg) {
  let reason = 'other';
  let details;
  const reasons = [
    ['harmful', 'Harmful or dangerous'], ['hateful', 'Hateful'], ['sexual', 'Sexual content'],
    ['privacy', 'Privacy concern'], ['misleading', 'Misleading or wrong'], ['other', 'Something else'],
  ];
  const submit = async () => {
    const r = await system.report({ response: msg.content, reason, details: details.value, prompt: '' });
    if (r.ok) ok('Report sent to your local log'); else err(r.message, r.detail);
    close();
  };
  const { close } = openDialog({
    title: 'Report this response',
    description: 'Saved to your local diagnostics log. Nothing leaves this machine.',
    width: '30rem',
    body: h('div.stack', null,
      h('div.field', null,
        h('label', { for: 'report-reason' }, 'What was wrong?'),
        h('select.select', { id: 'report-reason', onChange: (e) => { reason = e.target.value; } },
          ...reasons.map(([v, label]) => h('option', { value: v }, label))),
      ),
      h('div.field', null,
        h('label', { for: 'report-detail' }, 'Anything to add? (optional)'),
        h('textarea.textarea', { id: 'report-detail', rows: 3, ref: (el) => { details = el; } }),
      ),
    ),
    actions: [
      h('button.btn.btn-secondary', { type: 'button', onClick: () => close() }, 'Cancel'),
      h('button.btn.btn-primary', { type: 'button', onClick: submit }, 'Send report'),
    ],
  });
}

/* ── Attachments ─────────────────────────────────────────────────────── */

const IMAGE_RE = /^image\//;

async function stageFiles(fileList, refresh) {
  for (const file of Array.from(fileList)) {
    if (file.size > MAX_UPLOAD) { err(`${file.name} is too large — 32 MB is the limit.`); continue; }
    const kind = IMAGE_RE.test(file.type) ? 'image' : 'doc';
    const data = await new Promise((res) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result).split(',')[1] || '');
      r.onerror = () => res('');
      r.readAsDataURL(file);
    });
    if (!data) { err(`Couldn't read ${file.name}`); continue; }
    pending.push({ name: file.name, size: file.size, kind, data, preview: kind === 'image' ? `data:${file.type};base64,${data}` : null });
  }
  refresh();
}

/* ── Composer ────────────────────────────────────────────────────────── */

function composer() {
  let ta, attachRow, fileInput;

  const refreshAttachments = () => {
    mount(attachRow, ...pending.map((a, i) =>
      h('span.chip', null,
        a.preview ? h('img', { src: a.preview, alt: '', style: { width: '12px' } }) : icon('mon', 12),
        `${a.name} · ${bytes(a.size)}`,
        h('i', {
          'data-i': 'x', style: { width: '11px', cursor: 'pointer' },
          onClick: () => { pending.splice(i, 1); refreshAttachments(); },
        })
      )));
    attachRow.hidden = pending.length === 0;
  };

  const submit = () => {
    const text = ta.value;
    const files = pending;
    ta.value = '';
    pending = [];
    refreshAttachments();
    ta.style.height = 'auto';
    send(text, files);
  };

  ta = h('textarea', {
    id: 'composer-input', rows: 1, placeholder: 'Ask KALKI', 'aria-label': 'Ask KALKI',
    style: { width: '100%', border: 'none', background: 'transparent', resize: 'none', outline: 'none' },
    onKeydown: (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); store.conv.streaming ? stopStreaming() : submit(); }
    },
    onPaste: (e) => {
      const files = Array.from(e.clipboardData?.files || []);
      if (files.length) { e.preventDefault(); stageFiles(files, refreshAttachments); }
    },
  });

  fileInput = h('input', {
    type: 'file', multiple: true, hidden: true, id: 'composer-file',
    onChange: (e) => { stageFiles(e.target.files, refreshAttachments); e.target.value = ''; },
  });

  attachRow = h('div.row.g8', { style: { marginBottom: '8px' }, hidden: true });

  const micBtn = h('button.ib', {
    type: 'button', 'aria-label': 'Voice', title: 'Voice (Ctrl+Shift+V)',
    onClick: () => window.dispatchEvent(new CustomEvent('kalki:voice-toggle')),
  }, icon('mic', 16));

  const sendBtn = h('button.btn.pri', {
    type: 'button', 'aria-label': 'Send message', title: 'Send',
    style: { width: '28px', padding: '0', justifyContent: 'center' },
    onClick: () => (store.conv.streaming ? stopStreaming() : submit()),
  }, icon('up', 16));

  const box = h('div.comp', null,
    h('div.card', null,
      attachRow,
      h('div', { style: { fontSize: '14px' } }, ta),
      h('div.row.sb', { style: { marginTop: '10px' } },
        h('div.row.g4', null,
          h('button.ib', {
            type: 'button', 'aria-label': 'Attach a file or image', title: 'Attach',
            onClick: () => fileInput.click(),
          }, icon('clip', 16)),
          h('button.ib', {
            type: 'button', 'aria-label': 'Ask about my screen', title: 'Ask about my screen',
            onClick: askScreen,
          }, icon('mon', 16)),
          micBtn,
          h('button.btn.gh', {
            type: 'button', id: 'model-chip', 'aria-label': 'Change model',
            onClick: openModelPicker,
          }, modelLabel(store.models.current) || 'auto', icon('chev', 16))
        ),
        h('div.row.g8', null,
          h('span.xs.mut', { id: 'context-meter-comp' }, ''),
          sendBtn
        )
      )
    ),
    h('div.xs', { style: { color: 'var(--faint)', marginTop: '8px' } }, 'Enter to send · Shift+Enter for a new line · Esc stops a reply · drop files to attach'),
    fileInput,
  );

  on(box, 'dragover', (e) => { e.preventDefault(); box.classList.add('is-dragover'); });
  on(box, 'dragleave', () => box.classList.remove('is-dragover'));
  on(box, 'drop', (e) => {
    e.preventDefault();
    box.classList.remove('is-dragover');
    if (e.dataTransfer?.files?.length) stageFiles(e.dataTransfer.files, refreshAttachments);
  });

  autosize(ta);
  return { el: box, ta, sendBtn, micBtn };
}

async function askScreen() {
  const q = await promptDialog({
    title: 'Ask about your screen',
    label: 'KALKI will capture your whole desktop and read it aloud. What should it look for?',
    value: 'What is on screen?',
    confirmLabel: 'Capture',
  });
  if (!q) return;
  await conv.addMessage({ role: 'user', content: `[screen] ${q}` });
  const m = await conv.addMessage({ role: 'assistant', content: '', streaming: true });
  const r = await vision.screen(q);
  if (r.ok) await conv.updateMessage(m.id, { content: r.data.reply || '(nothing returned)', streaming: false, done: true });
  else await conv.updateMessage(m.id, { streaming: false, failed: true, error: r.message, detail: r.detail });
}

function openModelPicker() {
  loadModels(true);
  const list = h('div.stack');
  const paint = () => mount(list, ...(store.models.available.length
    ? store.models.available.map((m) => h('button.row.conv-item', {
        type: 'button',
        onClick: async () => {
          const r = await system.setModel(m);
          if (r.ok) { set('models', { current: r.data.model || m }); ok(`Model set to ${modelLabel(m)}`); }
          else err(r.message, r.detail);
          close();
        },
      },
      h('span.title', null, modelLabel(m)),
      m === store.models.current ? icon('check', 16) : null,
    ))
    : [h('p.muted.t-body-sm', null, 'No models are available. Add a provider key in Settings → Models, or start Ollama for offline use.')]));
  paint();
  // /api/models is refetched on open; repaint once the list lands.
  const repaint = setTimeout(paint, 700);
  const { close } = openDialog({
    title: 'Model',
    description: 'KALKI routes to the first available provider when set to auto.',
    width: '24rem',
    body: list,
    onClose: () => clearTimeout(repaint),
  });
}

/* ── View ────────────────────────────────────────────────────────────── */

export function askView() {
  const inner = h('div.msgs');
  liveRegion = h('div.sr-only', { role: 'status', 'aria-live': 'polite', 'aria-atomic': 'false' });
  const c = composer();

  const suggestionPills = [
    { text: "What's on my schedule today?", icon: 'calendar' },
    { text: 'Summarize recent notes', icon: 'note' },
    { text: 'System health check', icon: 'cpu' },
    { text: 'Start focus session', icon: 'clock' },
    { text: 'Interact with AI companion', icon: 'pet', action: () => triggerPetReaction('happy', 3000, 'Ready to assist, Sir! ✨') },
  ];

  const pillsContainer = h('div.welcome-pills', null,
    ...suggestionPills.map((p) =>
      h('button.suggestion-pill', {
        type: 'button',
        onClick: () => {
          if (p.action) {
            p.action();
            return;
          }
          c.ta.value = p.text;
          c.ta.value = '';
          c.ta.style.height = 'auto';
          send(p.text, []);
        },
      }, icon(p.icon, 14), p.text)
    )
  );

  const composerSlot = h('div.welcome-comp-slot');
  if (!conv.active()?.messages?.length) {
    composerSlot.appendChild(c.el);
  }

  const welcomeWrap = h('div.welcome-stage', null,
    h('div.welcome-inner', null,
      h('div.welcome-head', null,
        h('div.welcome-icon', null, icon('ask', 30)),
        h('h2.welcome-title', null, `${getGreeting()} — Ask KALKI`),
        h('p.welcome-desc', null, 'Type below, attach a file, or speak. KALKI answers with neural intelligence and pairs with your live AI desk companion.'),
      ),
      composerSlot,
      pillsContainer,
    )
  );

  const headerTitleEl = h('h1', {
    style: { fontSize: '16px', lineHeight: '22px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' },
    id: 'view-title',
    title: 'Click to rename conversation',
    onClick: async () => {
      const cur = conv.active();
      if (!cur) return;
      const next = await promptDialog({
        title: 'Rename conversation',
        label: 'Conversation title',
        defaultValue: cur.title || 'Conversation',
        confirmLabel: 'Save title',
      });
      if (next && next.trim()) {
        await conv.setThread(cur.id, { title: next.trim() });
        ok('Renamed conversation');
        renderHist();
        main.render();
      }
    }
  }, 'Ask');

  const headerExportBtn = h('button.ib', {
    type: 'button',
    title: 'Export conversation as Markdown',
    'aria-label': 'Export Markdown',
    onClick: () => {
      const cur = conv.active();
      exportChatMarkdown(cur);
    }
  }, icon('export', 15));

  const headerClearBtn = h('button.ib', {
    type: 'button',
    title: 'Clear active conversation messages',
    'aria-label': 'Clear messages',
    onClick: async () => {
      const cur = conv.active();
      if (!cur || !cur.messages?.length) {
        ok('Conversation is already empty');
        return;
      }
      const confirmed = await confirmDialog({
        title: 'Clear conversation messages?',
        description: `Permanently clear all ${cur.messages.length} messages in "${cur.title || 'this conversation'}"? The conversation thread itself will remain.`,
        confirmLabel: 'Clear messages',
        danger: true,
      });
      if (confirmed) {
        await conv.setThread(cur.id, { messages: [] });
        ok('Messages cleared');
        main.render();
      }
    }
  }, icon('trash', 15));

  const headerPetBtn = h('button.ib', {
    type: 'button',
    title: 'AI Companion Pet settings',
    'aria-label': 'Companion Pet',
    onClick: () => openPetSettings()
  }, icon('pet', 15));

  const headerPinBtn = h('button.ib', {
    type: 'button',
    title: 'Pin / unpin conversation',
    'aria-label': 'Pin conversation',
    onClick: async () => {
      const cur = conv.active();
      if (!cur) return;
      await conv.setThread(cur.id, { pinned: !cur.pinned });
      headerPinBtn.classList.toggle('is-active', !!cur.pinned);
      renderHist();
      ok(cur.pinned ? 'Pinned conversation' : 'Unpinned conversation');
    }
  }, icon('pin', 15));

  const headerDotsBtn = h('button.ib', {
    type: 'button',
    title: 'Conversation options',
    'aria-label': 'Conversation options',
    onClick: async () => {
      const cur = conv.active();
      if (!cur) return;
      const choice = await promptDialog({
        title: 'Manage Conversation',
        label: 'Enter new title, or type "export" / "delete":',
        defaultValue: cur.title || 'New conversation',
        confirmLabel: 'Apply',
      });
      if (!choice) return;
      const trimmed = choice.trim();
      if (trimmed.toLowerCase() === 'delete') {
        await conv.removeThread(cur.id);
        ok('Conversation deleted');
        renderHist();
        main.render();
      } else if (trimmed.toLowerCase() === 'export') {
        exportChatMarkdown(cur);
      } else if (trimmed) {
        await conv.setThread(cur.id, { title: trimmed });
        ok('Renamed conversation');
        renderHist();
        main.render();
      }
    }
  }, icon('dots', 15));

  const threadEl = h('div.thread', null, 
    h('div.th-h', null, 
      h('div', null, 
        headerTitleEl, 
        h('div.sub', { id: 'context-meter-header' }, '')
      ), 
      h('div.row.g4', null,
        headerExportBtn,
        headerClearBtn,
        headerPetBtn,
        headerPinBtn, 
        headerDotsBtn
      )
    ), 
    welcomeWrap,
    inner,
    c.el
  );

  // Mount interactive Companion Pet in Ask thread
  createPetCompanion(threadEl);

  scroller = stickyScroll(inner);

  // ── Dynamic thread list ───────────────────────────────────────────────
  let histSearchQuery = '';
  const histList = h('div');
  const searchInput = h('input', {
    type: 'search',
    placeholder: 'Search conversations',
    style: { border: 'none', background: 'transparent', flex: '1', outline: 'none', color: 'inherit', fontSize: '13px' },
    onInput: (e) => { histSearchQuery = e.target.value; renderHist(); },
  });

  function renderHist() {
    const threads = conv.searchThreads(histSearchQuery);
    const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
    const yestStart  = new Date(todayStart.getTime() - 86400000);
    const weekStart  = new Date(todayStart.getTime() - 6 * 86400000);

    const pinned = threads.filter(t => t.pinned);
    const todayT = threads.filter(t => !t.pinned && t.updatedAt >= todayStart.getTime());
    const yestT  = threads.filter(t => !t.pinned && t.updatedAt >= yestStart.getTime() && t.updatedAt < todayStart.getTime());
    const weekT  = threads.filter(t => !t.pinned && t.updatedAt >= weekStart.getTime() && t.updatedAt < yestStart.getTime());
    const olderT = threads.filter(t => !t.pinned && t.updatedAt < weekStart.getTime());

    const activeId = conv.active()?.id;
    const row = (t) => {
      const el = h('div.t', { onClick: () => conv.switchThread(t.id), title: t.title || 'Untitled' });
      if (t.id === activeId) el.classList.add('s');
      if (t.pinned) el.append(icon('pin', 12));
      const lbl = h('span', null, t.title || 'Untitled');
      lbl.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0';
      el.append(lbl);

      const pinBtn = h('button.act-btn', {
        type: 'button',
        'aria-label': t.pinned ? 'Unpin conversation' : 'Pin conversation',
        title: t.pinned ? 'Unpin' : 'Pin',
        onClick: async (e) => {
          e.stopPropagation();
          await conv.setThread(t.id, { pinned: !t.pinned });
          renderHist();
        },
      }, icon('pin', 13));
      if (t.pinned) pinBtn.classList.add('is-active');

      const delBtn = h('button.act-btn.dng', {
        type: 'button',
        'aria-label': 'Delete conversation',
        title: 'Delete',
        onClick: async (e) => {
          e.stopPropagation();
          await conv.removeThread(t.id);
          ok('Conversation deleted');
          renderHist();
          main.render();
          renderAside();
        },
      }, icon('close', 14));

      el.append(h('div.hist-actions', null, pinBtn, delBtn));
      return el;
    };

    const nodes = [];
    if (pinned.length)  { nodes.push(h('div.g', null, 'Pinned'));            pinned.forEach(t => nodes.push(row(t))); }
    if (todayT.length)  { nodes.push(h('div.g', null, 'Today'));             todayT.forEach(t => nodes.push(row(t))); }
    if (yestT.length)   { nodes.push(h('div.g', null, 'Yesterday'));         yestT.forEach(t => nodes.push(row(t))); }
    if (weekT.length)   { nodes.push(h('div.g', null, 'Earlier this week')); weekT.forEach(t => nodes.push(row(t))); }
    if (olderT.length)  { nodes.push(h('div.g', null, 'Older'));             olderT.forEach(t => nodes.push(row(t))); }
    if (!threads.length) nodes.push(h('div.t.mut', null, histSearchQuery ? 'No results' : 'No conversations yet'));

    mount(histList, ...nodes);
  }

  const handleClearAll = async () => {
    const unpinned = store.conv.threads.filter((t) => !t.pinned);
    if (!unpinned.length) {
      ok('No unpinned conversations to clear');
      return;
    }
    const confirmed = await confirmDialog({
      title: 'Clear all conversations?',
      description: `Permanently delete ${unpinned.length} unpinned conversation${unpinned.length > 1 ? 's' : ''}? Pinned conversations will remain.`,
      confirmLabel: 'Clear all',
      danger: true,
    });
    if (confirmed) {
      await conv.clearAllThreads();
      ok('Conversations cleared');
      renderHist();
      main.render();
    }
  };

  const clearAllBtn = h('button.btn.gh', {
    type: 'button',
    title: 'Clear all unpinned conversations',
    'aria-label': 'Clear all conversations',
    style: { fontSize: '11px', padding: '0 8px', whiteSpace: 'nowrap' },
    onClick: handleClearAll,
  }, icon('trash', 14), 'Clear all');

  const hist = h('div.hist', null,
    h('div.field', null, icon('search', 16), searchInput),
    h('div.row.g6', { style: { margin: '6px 0 2px' } },
      h('button.btn', {
        style: { flex: '1', justifyContent: 'center' },
        onClick: async () => {
          await conv.newThread();
          renderHist();
          main.render();
          renderAside();
          setTimeout(() => c.ta.focus(), 50);
        }
      }, icon('plus', 16), 'New thread'),
      clearAllBtn,
    ),
    histList
  );

  const main = h('div.ask', null, hist, threadEl, liveRegion);

  // ── Dynamic aside panel ───────────────────────────────────────────────
  const asideNextUp    = h('div.card.row', null, h('div.xs.mut', null, '—'));
  const asideTasksList = h('div.card');
  const asideTaskCount = h('span.xs.mut', null, '—');
  const asideInboxTxt  = h('span.sm', null, '—');
  const asideInboxChip = h('span.chip', null, '—');
  const asideVoiceWake = h('span.mono.xs.t2', null, '—');
  const asideVoiceTTS  = h('span.xs.t2', null, '—');
  const asideVoiceChip = h('span.chip', null, '—');
  const asideSys       = h('div.card.col.g8', { id: 'sys' });

  function renderAside() {
    const st = store.status;
    const td = store.today;

    // Next up
    const evts = td.events || [];
    if (evts.length) {
      const e = evts[0];
      mount(asideNextUp,
        h('span.big', null, e.start || e.when || ''),
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('div.nm', null, e.summary || e.title || 'Event'),
          h('div.xs.mut', null, e.location || '')
        )
      );
    } else {
      mount(asideNextUp, h('div.xs.mut', null,
        td.calendarConfigured === false ? 'Calendar not connected' : 'Nothing scheduled'
      ));
    }

    // Tasks
    const openTasks = (td.tasks || []).filter(t => !t.done);
    asideTaskCount.textContent = `${openTasks.length} open`;
    mount(asideTasksList,
      openTasks.length
        ? frag(...openTasks.slice(0, 4).map(t => h('div.li', null, h('i.cb', null), h('span.sm.t2', { style: { flex: 1 } }, t.text))))
        : h('div.li', null, h('span.sm.mut', null, 'No open tasks'))
    );

    // Inbox
    const unread = st?.unreadImportant ?? 0;
    asideInboxTxt.textContent = `${unread} unread important`;
    mount(asideInboxChip, unread === 0 ? 'All clear' : `${unread} to read`);
    asideInboxChip.className = 'chip ' + (unread === 0 ? 'ok' : 'warn');

    // Voice
    asideVoiceWake.textContent = st?.wakeWords || 'hey kalki';
    asideVoiceTTS.textContent  = st?.ttsVoice  || '—';
    const micReady = store.voice?.state === 'attending' || store.voice?.state === 'idle';
    mount(asideVoiceChip, micReady ? 'Mic ready' : (store.voice?.state || '—'));
    asideVoiceChip.className = 'chip ' + (micReady ? 'ok' : '');

    // System
    if (st) {
      const uh = Math.floor((st.uptimeSec || 0) / 3600);
      const um = Math.floor(((st.uptimeSec || 0) % 3600) / 60);
      mount(asideSys,
        h('div.row.sb', null, h('span.xs.mut', null, 'CPU'),    h('span.mono.xs', null, `${st.cpu ?? '—'}%`)),
        h('div.row.sb', null, h('span.xs.mut', null, 'RAM'),    h('span.mono.xs', null, `${st.ram ?? '—'}%`)),
        h('div.row.sb', null, h('span.xs.mut', null, 'Model'),  h('span.mono.xs', null, st.model || '—')),
        h('div.row.sb', null, h('span.xs.mut', null, 'Uptime'), h('span.mono.xs', null, uh ? `${uh} h ${um} m` : `${um} m`))
      );
    }

    renderHist();
  }

  const aside = frag(
    h('div.row.sb', null, h('h1', { style: { fontSize: '16px' } }, 'Context'), icon('panel', 16)),
    h('div.col.g8', null, h('h2', null, 'Next up'), asideNextUp),
    h('div.col.g8', null, h('div.row.sb', null, h('h2', null, 'Tasks'), asideTaskCount), asideTasksList),
    h('div.col.g8', null, h('h2', null, 'Inbox'), h('div.card.row.sb', null, asideInboxTxt, asideInboxChip)),
    h('div.col.g8', null, h('h2', null, 'Now playing'), h('div.card.col.g8', { id: 'music-panel' },
      h('div.xs.mut', { style: { textAlign: 'center', padding: '8px' } }, 'Loading…')
    )),
    h('div.col.g8', null, h('div.row.sb', null, h('h2', null, 'System'), h('span.xs.mut', null, 'Live')), asideSys),
    h('div.col.g8', null, h('h2', null, 'Voice'),
      h('div.card.col.g8', null,
        h('div.row.sb', null, h('span.xs.mut', null, 'Wake words'), asideVoiceChip),
        asideVoiceWake,
        h('div.row.sb', null, h('span.xs.mut', null, 'Speech'), asideVoiceTTS)
      )
    )
  );

  main.render = () => {
    const t = conv.active();
    const msgs = t?.messages || [];
    if (!msgs.length) {
      inner.hidden = true;
      welcomeWrap.hidden = false;
      threadEl.classList.add('is-empty');
      if (composerSlot.firstElementChild !== c.el) {
        const wasFocused = document.activeElement === c.ta;
        composerSlot.appendChild(c.el);
        if (wasFocused) c.ta.focus();
      }
    } else {
      welcomeWrap.hidden = true;
      inner.hidden = false;
      threadEl.classList.remove('is-empty');
      if (threadEl.lastElementChild !== c.el) {
        const wasFocused = document.activeElement === c.ta;
        threadEl.appendChild(c.el);
        if (wasFocused) c.ta.focus();
      }
      const want = msgs.map((m) => m.id).join('|');
      if (inner.dataset.sig !== want) {
        inner.dataset.sig = want;
        mount(inner, ...msgs.map(renderMessage));
        scroller?.toBottom(true);
      } else {
        const streaming = msgs.find((m) => m.streaming);
        if (!streaming) mount(inner, ...msgs.map(renderMessage));
      }
    }

    const chip = main.querySelector('#model-chip');
    if (chip) {
      mount(chip, modelLabel(store.models.current) || 'auto', icon('chev', 16));
    }

    const ctx = store.conv.contextTurns
        ? `${store.conv.contextTurns} of ${store.conv.maxTurns} turns in context`
        : `${store.conv.maxTurns} turns of context`;

    const meter1 = main.querySelector('#context-meter-header');
    if (meter1) meter1.textContent = `Updated 14:02 · ${ctx}`;

    const meter2 = main.querySelector('#context-meter-comp');
    if (meter2) meter2.textContent = ctx;

    c.sendBtn.classList.toggle('is-stop', store.conv.streaming);
    c.sendBtn.setAttribute('aria-label', store.conv.streaming ? 'Stop generating' : 'Send message');
    mount(c.sendBtn, icon(store.conv.streaming ? 'stop' : 'up', 16));

    const vs = store.voice.state;
    c.micBtn.classList.toggle('is-active', vs === 'attending' || vs === 'speaking');
  };

  let mediaTimer = null;
  let consecutiveErrors = 0;
  let prevStatus = 'NoMedia';
  let fastPollUntil = 0;
  let lastInteraction = Date.now();

  const onActivity = () => { lastInteraction = Date.now(); };
  window.addEventListener('pointerdown', onActivity, { passive: true });
  window.addEventListener('keydown', onActivity, { passive: true });
  window.addEventListener('wheel', onActivity, { passive: true });

  const onVisibilityChange = () => {
    if (!document.hidden && document.contains(main) && consecutiveErrors < 3) {
      clearTimeout(mediaTimer);
      mediaTimer = null;
      updateMedia();
    }
  };
  document.addEventListener('visibilitychange', onVisibilityChange);

  let inFlightMedia = false;
  async function updateMedia() {
    if (inFlightMedia) return;
    inFlightMedia = true;
    clearTimeout(mediaTimer);
    mediaTimer = null;

    let r = null;
    let fetchOk = false;
    try {
      r = await media.now();
      fetchOk = !!(r && r.ok);
    } catch (_) {
      fetchOk = false;
    }

    const el = document.getElementById('music-panel');

    if (!fetchOk) {
      consecutiveErrors++;
      if (consecutiveErrors >= 3) {
        if (el) {
          el.replaceChildren(
            h('div.col.g8', { style: { alignItems: 'center', padding: '8px', textAlign: 'center' } },
              h('div.xs.mut', null, 'Music integration unavailable'),
              h('button.btn.btn-sm', {
                type: 'button',
                onClick: () => {
                  consecutiveErrors = 0;
                  if (el) el.innerHTML = '<div class="xs mut" style="text-align:center;padding:8px">Loading…</div>';
                  updateMedia();
                },
              }, 'Retry')
            )
          );
        }
        return;
      }
    } else {
      consecutiveErrors = 0;
    }

    if (el && fetchOk) {
      const d = r.data || r;
      if (!d || d.status === 'NoMedia') {
        prevStatus = 'NoMedia';
        el.replaceChildren(
          h('div.xs.mut', { style: { textAlign: 'center', padding: '8px' } }, 'Nothing playing')
        );
      } else {
        if (prevStatus === 'NoMedia' && d.status === 'Playing') {
          fastPollUntil = Date.now() + 10000;
        }
        prevStatus = d.status || 'NoMedia';
        if (d.status === 'Playing') {
          window.dispatchEvent(new CustomEvent('kalki:music-play'));
        }

        const playIcon = d.status === 'Playing' ? 'pause' : 'play';
        const title = d.title || 'Unknown';
        const artist = d.artist || 'Unknown';

        const artEl = d.thumbnail
          ? h('img.music-cover', {
              src: d.thumbnail,
              alt: title,
              onError: (e) => {
                const p = e.target.parentElement;
                if (p) {
                  const fallback = h('div.music-cover-fallback', null, icon('music', 20));
                  p.replaceChild(fallback, e.target);
                }
              },
              style: {
                width: '44px',
                height: '44px',
                borderRadius: '8px',
                objectFit: 'cover',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                border: '1px solid var(--line)',
                flexShrink: '0',
                background: 'var(--raised)',
              },
            })
          : h('div.music-cover-fallback', {
              style: {
                width: '44px',
                height: '44px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, var(--float) 0%, var(--raised) 100%)',
                border: '1px solid var(--line)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: '0',
                color: 'var(--fil)',
              },
            }, icon('music', 20));

        const sourceEl = d.source
          ? h('span.chip', {
              style: {
                fontSize: '10px',
                padding: '1px 6px',
                lineHeight: '1.4',
                flexShrink: '0',
                maxWidth: '85px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              },
              title: d.source,
            }, d.source)
          : null;

        const dur = Number(d.duration) || 0;
        const pos = Math.max(0, Number(d.position) || 0);
        const pct = dur > 0 ? Math.min(100, Math.max(0, (pos / dur) * 100)) : 0;
        const fmt = (sec) => {
          if (!sec || isNaN(sec) || sec < 0) return '0:00';
          const m = Math.floor(sec / 60);
          const s = Math.floor(sec % 60);
          return `${m}:${s < 10 ? '0' : ''}${s}`;
        };

        const progressEl = dur > 0
          ? h('div.col.g4', null,
              h('div.meter', { title: `${fmt(pos)} / ${fmt(dur)}` },
                h('i', { style: { width: `${pct}%`, transition: 'width 0.3s ease' } })
              ),
              h('div.row.sb.xs.mut.mono', null,
                h('span', null, fmt(pos)),
                h('span', null, fmt(dur))
              )
            )
          : h('div.meter', null, h('i', { style: { width: '0%', transition: 'width 0.3s ease' } }));

        el.replaceChildren(
          h('div.row.sb', { style: { alignItems: 'center', gap: '8px' } },
            h('div.row.g10', { style: { flex: '1', minWidth: '0', alignItems: 'center' } },
              artEl,
              h('div', { style: { flex: '1', minWidth: '0', overflow: 'hidden' } },
                h('div.nm', {
                  style: {
                    fontWeight: '700',
                    fontSize: '13px',
                    lineHeight: '1.3',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    color: 'var(--text)',
                  },
                  title: title,
                }, title),
                h('div.xs.mut', {
                  style: {
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    fontSize: '11px',
                    color: 'var(--mut)',
                    marginTop: '2px',
                  },
                  title: artist,
                }, artist)
              )
            ),
            sourceEl
          ),
          progressEl,
          h('div.row', { style: { justifyContent: 'center', gap: '8px' } },
            h('button.ib', {
              type: 'button',
              'aria-label': 'Previous track',
              title: 'Previous track',
              onClick: () => media.prev().then(updateMedia),
            }, icon('prev', 16)),
            h('button.ib', {
              type: 'button',
              'aria-label': d.status === 'Playing' ? 'Pause' : 'Play',
              title: d.status === 'Playing' ? 'Pause' : 'Play',
              onClick: () => (d.status === 'Playing' ? media.pause() : media.play()).then(updateMedia),
            }, icon(playIcon, 16)),
            h('button.ib', {
              type: 'button',
              'aria-label': 'Next track',
              title: 'Next track',
              onClick: () => media.next().then(updateMedia),
            }, icon('next', 16))
          )
        );
      }
    }

    inFlightMedia = false;
    if (document.contains(main)) {
      const now = Date.now();
      let delay = 3000;
      if (document.hidden || (now - lastInteraction > 60000)) {
        delay = 15000;
      } else if (now < fastPollUntil) {
        delay = 1000;
      } else {
        delay = 3000;
      }
      mediaTimer = setTimeout(updateMedia, delay);
    }
  }

  const origRender = main.render;
  const view = { main, aside };
  view.render = () => {
    origRender();
    renderAside();
    if (!mediaTimer && !inFlightMedia && consecutiveErrors < 3) updateMedia();
  };
  main.render = view.render;

  view.cleanup = () => {
    clearTimeout(mediaTimer);
    mediaTimer = null;
    window.removeEventListener('pointerdown', onActivity);
    window.removeEventListener('keydown', onActivity);
    window.removeEventListener('wheel', onActivity);
    document.removeEventListener('visibilitychange', onVisibilityChange);
  };
  main.cleanup = view.cleanup;

  view.focusComposer = () => c.ta.focus();
  view.render();
  return view;
}

export { send as sendMessage };
