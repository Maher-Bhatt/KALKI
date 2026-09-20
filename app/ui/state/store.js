/** One observable store. Features read via selectors and write via actions;
 *  nothing calls fetch from a component. Re-renders are coalesced to one per
 *  frame so a burst of updates costs a single paint. */

const listeners = new Set();
let dirty = false;

export const store = {
  route: { name: 'ask', params: {} },
  status: null,
  online: true,
  voice: { state: 'unavailable', since: 0, sessionOpen: false },
  models: { available: [], current: '', loading: false },
  conv: { activeId: null, threads: [], streaming: false, abort: null, contextTurns: 0, maxTurns: 10 },
  memory: { items: [], query: '', filter: 'all', loading: false, error: null, legacyCount: 0 },
  today: { tasks: [], reminders: [], events: [], notes: [], mail: null, focus: null, loading: false },
  settings: { values: {}, secretStatus: {}, meta: {}, loading: false, saving: false },
  ui: {
    railOpen: false, contextOpen: true, theme: 'dark', motion: 'auto',
    density: 'comfortable', securityEnabled: false, debug: false,
  },
  toasts: [],
};

const UI_KEY = 'kalki.ui.v1';

export function loadUi() {
  try {
    const raw = localStorage.getItem(UI_KEY);
    if (raw) Object.assign(store.ui, JSON.parse(raw));
  } catch { /* first run, or storage blocked — defaults are fine */ }
  applyUi();
}

export function applyUi() {
  const r = document.documentElement;
  r.dataset.theme = store.ui.theme;
  r.dataset.density = store.ui.density;
  if (store.ui.motion === 'off') r.dataset.motion = 'off'; else delete r.dataset.motion;
  try { localStorage.setItem(UI_KEY, JSON.stringify(store.ui)); } catch { /* non-fatal */ }
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function notify() {
  if (dirty) return;
  dirty = true;
  requestAnimationFrame(() => {
    dirty = false;
    for (const fn of listeners) {
      try { fn(store); } catch (e) { console.error('[kalki] render failed', e); }
    }
  });
}

/** Shallow-merge a slice and schedule a render. */
export function set(slice, patch) {
  Object.assign(store[slice], patch);
  notify();
}
