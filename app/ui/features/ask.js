/** Ask — the assistant workspace. This is the application, not a destination.
 *
 *  Streaming lifecycle: idle → sending → streaming → complete | stopped | failed.
 *  Every state is named for the user; there is no unlabelled spinner. */

import { h, mount, autosize, stickyScroll, on } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { renderMarkdown, toPlain } from '../lib/markdown.js';
import { relative, bytes, modelLabel } from '../lib/format.js';
import { streamChat } from '../api/stream.js';
import { system, vision } from '../api/endpoints.js';
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
    h('button.icon-btn', { type: 'button', 'aria-label': label, title: label, onClick: fn }, icon(name, 16));

  return h('div.msg-actions', null,
    btn('copy', 'Copy message', (e) => {
      navigator.clipboard?.writeText(msg.content || '');
      ok('Message copied');
      e.currentTarget.blur();
    }),
    msg.role === 'assistant' ? btn('refresh', 'Regenerate reply', () => regenerate(msg)) : null,
    msg.role === 'user' ? btn('edit', 'Edit and resend', () => editAndResend(msg)) : null,
    msg.role === 'assistant' ? btn('flag', 'Report this response', () => reportDialog(msg)) : null,
  );
}

function renderMessage(msg) {
  if (msg.role === 'user') {
    return h('div.msg.msg-user', { dataset: { id: msg.id } },
      msg.origin === 'voice' ? h('div.msg-voice-tag', null, 'Spoken · ' + relative(msg.ts)) : null,
      h('div.msg-body', null,
        h('p', null, msg.content),
        msg.attachments?.length
          ? h('div.attachments', null, ...msg.attachments.map((a) =>
              h('span.attachment', null, icon('attach', 12), h('span', null, a.name))))
          : null,
      ),
      messageActions(msg),
    );
  }

  const body = h('div.msg-body');
  if (msg.failed) {
    mount(body, h('div.msg-error', null,
      h('div', null, msg.error || "KALKI couldn't answer that."),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', style: { marginTop: 'var(--space-4)' }, onClick: () => regenerate(msg) }, 'Try again'),
    ));
  } else if (!msg.content && msg.streaming) {
    mount(body, h('div.msg-status', { role: 'status' },
      h('span.btn-dots', null, h('i'), h('i'), h('i')),
      h('span', null, 'Reaching the model'),
    ));
  } else {
    mount(body, renderMarkdown(msg.content || '', { streaming: !!msg.streaming, onCopy: () => ok('Code copied') }));
    if (msg.streaming) body.appendChild(h('span.caret', { 'aria-hidden': 'true' }));
  }

  return h('div.msg.msg-assistant', { dataset: { id: msg.id } },
    h('span.msg-mark', { 'aria-hidden': 'true' }),
    h('div', null,
      msg.origin === 'voice' ? h('div.msg-voice-tag', null, 'Spoken · ' + relative(msg.ts)) : null,
      body,
      msg.stopped ? h('p.t-meta.faint', { style: { marginTop: 'var(--space-3)' } }, 'Stopped before finishing.') : null,
      msg.model && !msg.streaming ? h('p.t-meta.faint', { style: { marginTop: 'var(--space-3)' } }, modelLabel(msg.model)) : null,
      !msg.streaming && !msg.failed ? messageActions(msg) : null,
    ),
  );
}

/* ── Streaming ───────────────────────────────────────────────────────── */

async function send(text, attachments = []) {
  if (store.conv.streaming) return;
  const trimmed = text.trim();
  if (!trimmed && !attachments.length) return;

  await conv.addMessage({ role: 'user', content: trimmed, attachments: attachments.map((a) => ({ name: a.name, size: a.size })) });

  // Images go to the vision endpoint; documents are extracted then prefixed.
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

/** Patch just the streaming message's body — re-rendering the whole thread on
 *  every token would be the single most expensive thing this app could do. */
function patchStreaming(id, text) {
  const node = document.querySelector(`.msg[data-id="${id}"] .msg-body`);
  if (!node) { notify(); return; }
  mount(node, renderMarkdown(text, { streaming: true }));
  node.appendChild(h('span.caret', { 'aria-hidden': 'true' }));
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
      h('span.attachment', null,
        a.preview ? h('img', { src: a.preview, alt: '' }) : icon('attach', 12),
        h('span', null, a.name),
        h('span.faint', null, bytes(a.size)),
        h('button.icon-btn', {
          type: 'button', 'aria-label': `Remove ${a.name}`,
          onClick: () => { pending.splice(i, 1); refreshAttachments(); },
        }, icon('close', 12)),
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

  attachRow = h('div.attachments', { hidden: true });

  const micBtn = h('button.icon-btn', {
    type: 'button', 'aria-label': 'Voice', title: 'Voice (Ctrl+Shift+V)',
    onClick: () => window.dispatchEvent(new CustomEvent('kalki:voice-toggle')),
  }, icon('mic', 18));

  const sendBtn = h('button.icon-btn.icon-btn-lg.btn-send', {
    type: 'button', 'aria-label': 'Send message', title: 'Send',
    onClick: () => (store.conv.streaming ? stopStreaming() : submit()),
  }, icon('send', 18));

  const box = h('div.composer', null,
    attachRow,
    h('div.composer-fields', null,
      ta,
      h('div.composer-controls', null,
        h('button.icon-btn', {
          type: 'button', 'aria-label': 'Attach a file or image', title: 'Attach',
          onClick: () => fileInput.click(),
        }, icon('attach', 18)),
        h('button.icon-btn', {
          type: 'button', 'aria-label': 'Ask about my screen', title: 'Ask about my screen',
          onClick: askScreen,
        }, icon('screen', 18)),
        micBtn,
        sendBtn,
      ),
    ),
    h('div.composer-foot', null,
      h('button.btn.btn-sm.btn-ghost', {
        type: 'button', id: 'model-chip', 'aria-label': 'Change model',
        onClick: openModelPicker,
      }, modelLabel(store.models.current) || 'auto'),
      h('span.spacer'),
      h('span', { id: 'context-meter', title: 'KALKI keeps the most recent turns as context' }, ''),
    ),
    fileInput,
  );

  // Drag-and-drop lands on the composer only. The attach button is the
  // required single-pointer equivalent (WCAG 2.5.7).
  on(box, 'dragover', (e) => { e.preventDefault(); box.classList.add('is-dragover'); });
  on(box, 'dragleave', () => box.classList.remove('is-dragover'));
  on(box, 'drop', (e) => {
    e.preventDefault();
    box.classList.remove('is-dragover');
    if (e.dataTransfer?.files?.length) stageFiles(e.dataTransfer.files, refreshAttachments);
  });

  autosize(ta);
  return { el: h('div.composer-wrap', null, h('div.composer-inner', null, box)), ta, sendBtn, micBtn };
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
  const threadEl = h('div.thread.scroll', { id: 'thread' });
  const inner = h('div.thread-inner');
  threadEl.appendChild(inner);
  liveRegion = h('div.sr-only', { role: 'status', 'aria-live': 'polite', 'aria-atomic': 'false' });
  const c = composer();
  scroller = stickyScroll(threadEl);

  const view = h('section.view', { 'aria-label': 'Ask KALKI' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Ask'),
      h('span.spacer'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => conv.newThread() }, icon('plus', 16), 'New'),
    ),
    threadEl, liveRegion, c.el,
  );

  view.render = () => {
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
      // Only rebuild rows whose identity changed; streaming is patched in place.
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

    const chip = view.querySelector('#model-chip');
    if (chip) chip.textContent = modelLabel(store.models.current) || 'auto';

    const meter = view.querySelector('#context-meter');
    if (meter) {
      meter.textContent = store.conv.contextTurns
        ? `${store.conv.contextTurns} of ${store.conv.maxTurns} turns in context`
        : `${store.conv.maxTurns} turns of context`;
    }

    c.sendBtn.classList.toggle('is-stop', store.conv.streaming);
    c.sendBtn.setAttribute('aria-label', store.conv.streaming ? 'Stop generating' : 'Send message');
    mount(c.sendBtn, icon(store.conv.streaming ? 'stop' : 'send', 18));

    const vs = store.voice.state;
    c.micBtn.classList.toggle('is-active', vs === 'attending' || vs === 'speaking');
  };

  view.focusComposer = () => c.ta.focus();
  return view;
}

export { send as sendMessage };
