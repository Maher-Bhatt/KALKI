/** Conversation organisation lives in the frontend.
 *
 *  The backend has no conversation database: history.json is a single flat
 *  list capped at MAX_HISTORY (20 entries = 10 exchanges) and listener.py
 *  appends to it out of process while the window is closed. So IndexedDB owns
 *  threads — title, pin, archive, search, timestamps — and history.json stays
 *  what it actually is: the model's rolling context window, shown honestly on
 *  the composer rather than hidden. */

import { idb } from '../lib/idb.js';
import { titleFrom } from '../lib/format.js';
import { store, set, notify } from './store.js';

const newId = () => `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;

export function blank() {
  const now = Date.now();
  return { id: newId(), title: 'New conversation', createdAt: now, updatedAt: now, pinned: false, archived: false, messages: [], model: '' };
}

export async function loadThreads() {
  if (!idb.available) return;
  try {
    const all = await idb.all();
    store.conv.threads = all.sort((a, b) => (b.pinned - a.pinned) || (b.updatedAt - a.updatedAt));
    notify();
  } catch (e) { console.warn('[kalki] conversation store unavailable', e); }
}

export function active() {
  return store.conv.threads.find((t) => t.id === store.conv.activeId) || null;
}

async function persist(thread) {
  thread.updatedAt = Date.now();
  const i = store.conv.threads.findIndex((t) => t.id === thread.id);
  if (i === -1) store.conv.threads.unshift(thread);
  else store.conv.threads[i] = thread;
  store.conv.threads.sort((a, b) => (b.pinned - a.pinned) || (b.updatedAt - a.updatedAt));
  recount();
  notify();
  if (idb.available) { try { await idb.put({ ...thread }); } catch { /* memory-only session */ } }
}

export async function ensureActive() {
  let t = active();
  if (!t) { t = blank(); store.conv.activeId = t.id; await persist(t); }
  return t;
}

export async function openThread(id) {
  store.conv.activeId = id;
  recount();
  notify();
}

export async function newThread() {
  const t = blank();
  store.conv.activeId = t.id;
  await persist(t);
  return t;
}

export async function addMessage(msg) {
  const t = await ensureActive();
  const entry = { id: `m_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`, ts: Date.now(), ...msg };
  t.messages.push(entry);
  if (t.messages.length <= 2 && msg.role === 'user') t.title = titleFrom(msg.content);
  await persist(t);
  return entry;
}

export async function updateMessage(id, patch) {
  const t = active();
  if (!t) return;
  const m = t.messages.find((x) => x.id === id);
  if (!m) return;
  Object.assign(m, patch);
  await persist(t);
}

export async function dropMessagesFrom(id) {
  const t = active();
  if (!t) return;
  const i = t.messages.findIndex((m) => m.id === id);
  if (i >= 0) { t.messages.splice(i); await persist(t); }
}

export async function setThread(id, patch) {
  const t = store.conv.threads.find((x) => x.id === id);
  if (!t) return;
  Object.assign(t, patch);
  await persist(t);
}

export async function removeThread(id) {
  store.conv.threads = store.conv.threads.filter((t) => t.id !== id);
  if (store.conv.activeId === id) store.conv.activeId = store.conv.threads[0]?.id || null;
  notify();
  if (idb.available) { try { await idb.del(id); } catch { /* non-fatal */ } }
}

/** Voice turns arrive from listener.py via /api/status polling. Append them so
 *  a conversation held with the window closed does not silently disappear. */
export async function appendVoiceExchange(ex) {
  const t = await ensureActive();
  const seen = t.messages.some((m) => m.voiceSeq === ex.seq);
  if (seen) return;
  t.messages.push(
    { id: `v${ex.seq}u`, role: 'user', content: ex.user || '', ts: (ex.ts || Date.now() / 1000) * 1000, origin: 'voice', voiceSeq: ex.seq },
    { id: `v${ex.seq}a`, role: 'assistant', content: ex.reply || '', ts: (ex.ts || Date.now() / 1000) * 1000, origin: 'voice', voiceSeq: ex.seq, done: true },
  );
  if (t.messages.length <= 2) t.title = titleFrom(ex.user);
  await persist(t);
}

/** How many turns of this thread the backend will actually carry.
 *  MAX_HISTORY is 20 entries, i.e. 10 exchanges. */
export function recount() {
  const t = active();
  const exchanges = t ? Math.floor(t.messages.filter((m) => m.role === 'user' || m.role === 'assistant').length / 2) : 0;
  set('conv', { contextTurns: Math.min(exchanges, store.conv.maxTurns) });
}

/** Messages sent to /api/chat. The server prepends its own history, so we send
 *  only this thread's recent turns and let it truncate. */
export function wireMessages() {
  const t = active();
  if (!t) return [];
  return t.messages
    .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.content && !m.failed)
    .slice(-store.conv.maxTurns * 2)
    .map((m) => ({ role: m.role, content: m.content }));
}

export function searchThreads(q) {
  const s = q.trim().toLowerCase();
  if (!s) return store.conv.threads.filter((t) => !t.archived).slice(0, 12);
  return store.conv.threads.filter((t) =>
    t.title.toLowerCase().includes(s) || t.messages.some((m) => String(m.content).toLowerCase().includes(s)),
  ).slice(0, 20);
}
