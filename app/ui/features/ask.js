/** Ask — the assistant workspace. This is the application, not a destination.
 *
 *  Streaming lifecycle: idle → sending → streaming → complete | stopped | failed.
 *  Every state is named for the user; there is no unlabelled spinner. */

import { h, mount, autosize, stickyScroll, on, frag } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { renderMarkdown, toPlain } from '../lib/markdown.js';
import { relative, bytes, modelLabel } from '../lib/format.js';
import { streamChat } from '../api/stream.js';
import { system, vision, tasks } from '../api/endpoints.js';
import { store, set, notify } from '../state/store.js';
import { refreshStatus, loadModels } from '../state/status.js';
import * as conv from '../state/conversations.js';
import { emptyState } from '../components/states.js';
import { openDialog, promptDialog } from '../components/dialog.js';
import { toast, ok, err } from '../state/toasts.js';

const MAX_UPLOAD = 32 * 1024 * 1024; // server MAX_BODY

let pending = [];      // staged attachments
let liveRegion = null;
let announceTimer = null;
let scroller = null;

/* ── Live region: announce accumulated text on a throttle, never per token ─ */
function announce(text) {
  if (!liveRegion) return;
  clearTimeout(announceTimer);
  announceTimer = setTimeout(() => { liveRegion.textContent = toPlain(text).slice(-600); }, 400);
}

/* ── Message rendering ───────────────────────────────────────────────── */

function messageActions(msg) {
  const btn = (name, label, fn) =>
    h('button.ib', { type: 'button', 'aria-label': label, title: label, onClick: fn }, icon(name, 16));

  return h('div.row', { style: { marginTop: '8px' } },
    btn('copy', 'Copy message', (e) => {
      navigator.clipboard?.writeText(msg.content || '');
      ok('Message copied');
      e.currentTarget.blur();
    }),
    msg.role === 'assistant' ? btn('ref', 'Regenerate reply', () => regenerate(msg)) : null,
    msg.role === 'user' ? btn('pen', 'Edit and resend', () => editAndResend(msg)) : null,
    msg.role === 'assistant' ? btn('flag', 'Report this response', () => reportDialog(msg)) : null,
  );
}

function renderMessage(msg) {
  if (msg.role === 'user') {
    return h('div', { dataset: { id: msg.id } },
      h('div.who', null, 'You'),
      msg.origin === 'voice' ? h('div.msg-voice-tag', null, 'Spoken · ' + relative(msg.ts)) : null,
      msg.content,
      msg.attachments?.length
        ? h('div.row.g8', { style: { marginTop: '8px' } }, ...msg.attachments.map((a) =>
            h('span.chip', null, icon('mon', 12), `${a.name} · ${a.size ? bytes(a.size) : ''}`)))
        : null,
      messageActions(msg)
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
    rawText = rawText.replace(/\[TASK:\s*(.+?)\]/g, (m, t) => { createdTasks.push(t); return ''; });
    
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

  try {
    if (image) {
      const r = await vision.image(image.data, trimmed);
      if (r.ok) await conv.updateMessage(assistant.id, { content: r.data.reply || '(no description returned)', streaming: false, done: true });
      else await conv.updateMessage(assistant.id, { streaming: false, failed: true, error: r.message, detail: r.detail });
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
      },
      onError: async (e) => {
        await conv.updateMessage(assistant.id, { content: acc, streaming: false, failed: !acc, error: e.message, detail: e.detail });
        if (acc) toast({ kind: 'warning', text: 'The reply was cut short.' });
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
  
  const threadEl = h('div.thread', null, 
    h('div.th-h', null, 
      h('div', null, 
        h('h1', { style: { fontSize: '16px', lineHeight: '22px' }, id: 'view-title' }, 'Ask'), 
        h('div.sub', { id: 'context-meter-header' }, '')
      ), 
      h('div.row', null, 
        h('button.ib', null, icon('pin', 16)), 
        h('button.ib', null, icon('dots', 16))
      )
    ), 
    inner,
    c.el
  );

  scroller = stickyScroll(threadEl);

  const hist = h('div.hist', null, 
    h('div.field', null, icon('search', 16), 'Search conversations'), 
    h('button.btn', {style: {justifyContent: 'center', margin: '6px 0 2px'}, onClick: () => conv.newThread()}, icon('plus', 16), 'New thread'),
    h('div.g', null, 'Pinned'), 
    h('div.t.s', null, icon('pin', 16), 'Odoo session prep'), 
    h('div.g', null, 'Today'), 
    h('div.t', null, 'Draft the v2.0.0 release notes'), 
    h('div.t', null, 'Port scan results, lab router'), 
    h('div.t', null, 'Study plan for DBMS unit 3'), 
    h('div.g', null, 'Yesterday'), 
    h('div.t', null, 'CVE brief for Friday'), 
    h('div.t', null, 'Telegram bot webhook fix'), 
    h('div.t', null, 'Resume bullets rewrite'), 
    h('div.g', null, 'Earlier this week'), 
    h('div.t', null, 'Groq and Ollama latency'), 
    h('div.t', null, 'Vault migration checklist'), 
    h('div.t', null, 'Standup notes (meeting mode)'), 
    h('div.g', null, 'Archived'), 
    h('div.t.mut', null, '12 threads')
  );

  const main = h('div.ask', null, hist, threadEl, liveRegion);

  const aside = frag(
    h('div.row.sb', null, h('h1', { style: { fontSize: '16px' } }, 'Context'), icon('panel', 16)),
    h('div.col.g8', null, h('h2', null, 'Next up'), h('div.card.row', null, h('span.big', null, '14:30'), h('div', null, h('div.nm', null, 'Odoo Experience'), h('div.xs.mut', null, 'Hall B · in 2 h 04 m')))),
    h('div.col.g8', null, h('div.row.sb', null, h('h2', null, 'Tasks'), h('span.xs.mut', null, '3 open')), h('div.card', null, h('div.li', null, h('i.cb', null), h('span.sm.t2', null, 'Review session agenda')), h('div.li', null, h('i.cb', null), h('span.sm.t2', null, 'Carry venue pass, charge laptop')), h('div.li', null, h('i.cb', null), h('span.sm.t2', null, 'Publish v2.0.0 release notes')))),
    h('div.col.g8', null, h('h2', null, 'Inbox'), h('div.card.row.sb', null, h('span.sm', null, '0 unread important'), h('span.chip.ok', null, 'All clear'))),
    h('div.col.g8', null, h('h2', null, 'Now playing'), h('div.card.col.g8', null, h('div.row', null, h('div', { style: { width: '36px', height: '36px', borderRadius: '4px', background: 'var(--float)' } }), h('div', null, h('div.nm', null, 'Night Drive'), h('div.xs.mut', null, 'Instrumental · 2:41 / 4:10'))), h('div.row', { style: { justifyContent: 'center' } }, h('button.ib', null, icon('prev', 16)), h('button.ib', null, icon('play', 16)), h('button.ib', null, icon('next', 16))))),
    h('div.col.g8', null, h('div.row.sb', null, h('h2', null, 'System'), h('span.xs.mut', null, 'Live')), h('div.card.col.g8', { id: 'sys' })),
    h('div.col.g8', null, h('h2', null, 'Voice'), h('div.card.col.g8', null, h('div.row.sb', null, h('span.xs.mut', null, 'Wake words'), h('span.chip.ok', null, 'Mic ready')), h('span.mono.xs.t2', null, 'hey kalki · ok kalki'), h('div.row.sb', null, h('span.xs.mut', null, 'Speech'), h('span.xs.t2', null, 'en-GB-Ryan · 212 ms'))))
  );

  main.render = () => {
    const t = conv.active();
    const msgs = t?.messages || [];
    if (!msgs.length) {
      mount(inner, emptyState({
        iconName: 'ask',
        title: 'Ask KALKI anything',
        body: 'Type below, attach a file, or speak. KALKI answers from your configured model and can act on your tasks, memory and system.',
        hint: 'Ctrl K opens the command palette',
      }));
    } else {
      const want = msgs.map((m) => m.id).join('|');
      if (inner.dataset.sig !== want) {
        inner.dataset.sig = want;
        mount(inner, ...msgs.map(renderMessage));
        scroller.toBottom(true);
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

  main.focusComposer = () => c.ta.focus();
  return { main, aside };
}

export { send as sendMessage };
