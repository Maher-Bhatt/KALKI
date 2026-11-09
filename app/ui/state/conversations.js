/** Conversations live on the server, so the app, voice and Telegram share them.
 *
 *  Saves send only what changed. The server adds or updates messages and never
 *  removes them on a save, so this window can't erase a voice reply it hasn't seen.
 *  Older chats still in this browser's IndexedDB are moved across on load, and each
 *  one is deleted locally only after the server confirms it was saved. */

import { idb } from '../lib/idb.js';
import { titleFrom } from '../lib/format.js';
import { store, set, notify } from './store.js';
import { threadsApi } from '../api/endpoints.js';
import { toast } from './toasts.js';

const newId = () => `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;

export function blank() {
  const now = Date.now();
  return { id: newId(), title: 'New conversation', createdAt: now, updatedAt: now, pinned: false, archived: false, messages: [], model: '' };
}

async function moveBrowserThreads() {
  if (!idb.available) return;
  let failed = 0;
  try {
    for (const t of await idb.all()) {
      const empty = !t.messages || t.messages.length === 0;
      if (empty && !t.pinned) { await idb.del(t.id); continue; }
      const messages = (t.messages || []).map((m, i) => ({ ...m, id: m.id || `legacy_${i}` }));
      const r = await threadsApi.save({ ...t, messages });
      if (r.ok) await idb.del(t.id);
      else failed += 1;
    }
  } catch (e) { console.warn('[kalki] browser conversations unavailable', e); }
  if (failed) toast({ kind: 'warning', text: `${failed} older conversations couldn't be moved yet. They're kept, and KALKI will try again.` });
}

/** A reply cut off by a crash is no longer streaming once the app restarts. */
const settled = (t) => ({ ...t, messages: t.messages.map((m) => (m.streaming ? { ...m, streaming: false } : m)) });

export async function loadThreads() {
  await moveBrowserThreads();
  const r = await threadsApi.list();
  if (!r.ok) {
    toast({ kind: 'error', text: "Your conversations couldn't be loaded.", detail: r.detail });
    return;
  }
  store.conv.threads = r.data.threads.map(settled).filter((t) => t.pinned || t.messages.length > 0);
  notify();
}

export function active() {
  return store.conv.threads.find((t) => t.id === store.conv.activeId) || null;
}

let saveWarned = false;

async function persist(thread, changed = []) {
  thread.updatedAt = Date.now();
  const i = store.conv.threads.findIndex((t) => t.id === thread.id);
  if (i === -1) store.conv.threads.unshift(thread);
  else store.conv.threads[i] = thread;
  store.conv.threads.sort((a, b) => (b.pinned - a.pinned) || (b.updatedAt - a.updatedAt));
  recount();
  notify();
  const r = await threadsApi.save({ ...thread, messages: changed });
  if (r.ok) saveWarned = false;
  else if (!saveWarned) {
    saveWarned = true;
    toast({ kind: 'error', text: "This conversation isn't being saved.", detail: r.detail });
  }
}

export async function ensureActive() {
  let t = active();
  if (!t) {
    t = blank();
    store.conv.activeId = t.id;
    if (!store.conv.threads.some((x) => x.id === t.id)) {
      store.conv.threads.unshift(t);
    }
    recount();
    notify();
  }
  return t;
}

export async function openThread(id) {
  store.conv.activeId = id;
  recount();
  notify();
}

export const switchThread = openThread;

export async function newThread() {
  const cur = active();
  if (cur && (!cur.messages || cur.messages.length === 0)) {
    return cur;
  }
  const t = blank();
  store.conv.activeId = t.id;
  if (!store.conv.threads.some((x) => x.id === t.id)) {
    store.conv.threads.unshift(t);
  }
  recount();
  notify();
  return t;
}

export async function addMessage(msg) {
  const t = await ensureActive();
  const entry = { id: `m_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`, ts: Date.now(), ...msg };
  t.messages.push(entry);
  if (t.messages.length <= 2 && msg.role === 'user') t.title = titleFrom(msg.content);
  await persist(t, [entry]);
  return entry;
}

export async function updateMessage(id, patch) {
  const t = active();
  if (!t) return;
  const m = t.messages.find((x) => x.id === id);
  if (!m) return;
  Object.assign(m, patch);
  await persist(t, [m]);
}

export async function dropMessagesFrom(id) {
  const t = active();
  if (!t) return;
  const i = t.messages.findIndex((m) => m.id === id);
  if (i >= 0) {
    t.messages.splice(i);
    await threadsApi.truncate(t.id, id);
    await persist(t);
  }
}

export async function setThread(id, patch) {
  const t = store.conv.threads.find((x) => x.id === id);
  if (!t) return;
  Object.assign(t, patch);
  await persist(t);
}

export async function removeThread(id) {
  store.conv.threads = store.conv.threads.filter((t) => t.id !== id);
  if (store.conv.activeId === id) {
    store.conv.activeId = store.conv.threads[0]?.id || null;
    if (typeof location !== 'undefined' && location.hash.startsWith('#/ask')) {
      location.hash = store.conv.activeId ? `#/ask/${store.conv.activeId}` : '#/ask';
    }
  }
  recount();
  notify();
  const r = await threadsApi.remove(id);
  if (!r.ok) toast({ kind: 'error', text: "That conversation couldn't be deleted.", detail: r.detail });
}

export async function clearAllThreads() {
  const pinned = store.conv.threads.filter((t) => t.pinned);
  store.conv.threads = pinned;
  store.conv.activeId = pinned[0]?.id || null;
  if (typeof location !== 'undefined' && location.hash.startsWith('#/ask')) {
    location.hash = store.conv.activeId ? `#/ask/${store.conv.activeId}` : '#/ask';
  }
  recount();
  notify();
  const r = await threadsApi.clear();
  if (!r.ok) toast({ kind: 'error', text: "Your conversations couldn't be cleared.", detail: r.detail });
}

/** Voice and Telegram turns are saved by the server, and /api/status says when there's
 *  a new one. Merge rather than replace: a reply may be streaming in this window. */
export async function appendVoiceExchange(ex) {
  const r = await threadsApi.list();
  if (!r.ok) return;
  for (const incoming of r.data.threads) {
    const local = store.conv.threads.find((t) => t.id === incoming.id);
    if (!local) {
      store.conv.threads.push(settled(incoming));
      continue;
    }
    const known = new Set(local.messages.map((m) => m.id));
    local.messages.push(...incoming.messages.filter((m) => !known.has(m.id)));
    local.updatedAt = Math.max(local.updatedAt, incoming.updatedAt);
  }
  store.conv.threads.sort((a, b) => (b.pinned - a.pinned) || (b.updatedAt - a.updatedAt));
  // Nothing typed yet in this window, so show where the conversation is happening.
  const cur = active();
  if (ex?.threadId && (!cur || cur.messages.length === 0)) store.conv.activeId = ex.threadId;
  recount();
  notify();
}

/** How many turns of this thread get sent to the model. */
export function recount() {
  const t = active();
  const exchanges = t ? Math.floor(t.messages.filter((m) => m.role === 'user' || m.role === 'assistant').length / 2) : 0;
  set('conv', { contextTurns: Math.min(exchanges, store.conv.maxTurns) });
}

/** Messages sent to /api/chat: this thread's recent turns. */
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
  // Only surface threads that have messages, or are pinned, or is the currently open active thread
  const pool = store.conv.threads.filter((t) => !t.archived && (t.pinned || t.id === store.conv.activeId || (t.messages && t.messages.length > 0)));
  if (!s) return pool.slice(0, 30);
  return pool.filter((t) =>
    (t.title || '').toLowerCase().includes(s) || t.messages.some((m) => String(m.content || '').toLowerCase().includes(s)),
  ).slice(0, 30);
}
