import { store, notify } from './store.js';

let seq = 0;

/** @param {{kind?:'info'|'success'|'error'|'warning', text:string, detail?:string, action?:{label:string,run:Function}}} t */
export function toast(t) {
  const item = { id: ++seq, kind: 'info', ...t };
  store.toasts = [...store.toasts, item].slice(-3);
  notify();
  if (item.kind !== 'error') setTimeout(() => dismiss(item.id), 5000);
  return item.id;
}

export function dismiss(id) {
  store.toasts = store.toasts.filter((t) => t.id !== id);
  notify();
}

export const ok = (text, extra) => toast({ kind: 'success', text, ...extra });
export const err = (text, detail, extra) => toast({ kind: 'error', text, detail, ...extra });
