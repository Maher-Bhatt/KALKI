/** Typed adapters over the KALKI HTTP API.
 *
 *  This is the adapter layer: the backend is inconsistent in places
 *  (/api/dashboard nests under data, /api/cyber/* spreads module output into
 *  the top level, /api/mail/inbox returns the module shape unwrapped). Every
 *  inconsistency is normalised here so no feature module ever branches on it.
 *  Route names and payload shapes below were read from app/server.py. */

import { get, post } from './client.js';

const list = (r, key) => (r.ok ? (r.data[key] || []) : []);

/* ── System ───────────────────────────────────────────────────────── */
export const system = {
  status: (hidden) => get(hidden ? '/api/status?hidden=1' : '/api/status', { timeout: 8000 }),
  dashboard: () => get('/api/dashboard'),
  metrics: () => get('/api/metrics'),
  focus: () => get('/api/focus'),
  models: () => get('/api/models'),
  setModel: (model) => post('/api/model', { model }),
  stop: () => post('/api/stop', {}),
  wake: (cmd = '') => post('/api/wake', { cmd }),
  support: () => get('/api/support'),
  clipboardResponse: (phrase) => get(`/api/clipboard_response?phrase=${encodeURIComponent(phrase)}`),
  github: () => get('/api/github/status'),
  command: (cmd) => post('/api/command', { cmd }),
  search: (q) => post('/api/search', { q }),
  report: (payload) => post('/api/report', payload),
  history: () => get('/api/history'),
};

/* ── Listener / voice ─────────────────────────────────────────────── */
export const voice = {
  pause: () => post('/api/listener/pause', {}),
  resume: () => post('/api/listener/resume', {}),
  testTts: (text) => post('/api/tts/test', { text }),
  meetingStart: () => post('/api/meeting/start', {}),
  meetingStop: () => post('/api/meeting/stop', {}),
};

/* ── Memory. The UI is built on the semantic store; the legacy flat
      list is exposed once, as a one-time import. ───────────────────── */
export const memory = {
  async list() {
    const r = await get('/api/memory/list');
    return r.ok ? { ok: true, items: r.data.memories || [] } : r;
  },
  add: ({ text, tags = [], importance = 5, type = 'fact' }) => post('/api/memory/add', { text, tags, importance, type }),
  update: ({ id, text, importance, type }) => post('/api/memory/update', { id, text, importance, type }),
  remove: (id) => post('/api/memory/delete', { id }),
  async legacy() {
    const r = await get('/api/memories');
    return list(r, 'memories');
  },
};

/* ── Tasks & reminders ────────────────────────────────────────────── */
export const tasks = {
  async list(all = false) {
    const r = await post('/api/tasks/list', { all });
    return r.ok ? { ok: true, items: r.data.tasks || [] } : r;
  },
  add: (text) => post('/api/tasks/add', { text }),
  complete: (id) => post('/api/tasks/complete', { id }),
  remove: (id) => post('/api/tasks/delete', { id }),
};

export const reminders = {
  async list() {
    const r = await post('/api/reminders/list', {});
    return r.ok ? { ok: true, items: r.data.reminders || [] } : r;
  },
  /** `due` is sent as the user's raw phrase — tasks.parse_when resolves it. */
  add: (text, due) => post('/api/reminders/add', { text, due }),
};

/* ── Notes ────────────────────────────────────────────────────────── */
export const notes = {
  async list(n = 10) {
    const r = await post('/api/notes/list', { n });
    return r.ok ? { ok: true, items: r.data.notes || [] } : r;
  },
  add: (text) => post('/api/notes/add', { text }),
  async search(q) {
    const r = await post('/api/notes/search', { q });
    return r.ok ? { ok: true, items: r.data.notes || [] } : r;
  },
};

/* ── Calendar / mail / music / messaging ──────────────────────────── */
export const calendar = {
  today: () => post('/api/calendar/today', {}),
  upcoming: (n = 5) => post('/api/calendar/upcoming', { n }),
};

export const mail = {
  check: (importantOnly = true, limit = 5) => post('/api/mail/check', { importantOnly, limit }),
  inbox: (limit = 10, onlyUnread = true) => post('/api/mail/inbox', { limit, onlyUnread }),
};

export const spotify = {
  play: () => post('/api/spotify/play', {}),
  pause: () => post('/api/spotify/pause', {}),
  next: () => post('/api/spotify/next', {}),
  now: () => post('/api/spotify/now', {}),
};

export const whatsapp = { send: (to, message) => post('/api/whatsapp/send', { to, message }) };
export const media = { download: (url, audio = false) => post('/api/ytdl', { url, audio }) };

/* ── Vision & documents ───────────────────────────────────────────── */
export const vision = {
  image: (image, question = '') => post('/api/vision/image', { image, question }, { timeout: 90000 }),
  screen: (question = '') => post('/api/screen', { question }, { timeout: 90000 }),
  parseDocument: (filename, data) => post('/api/parse_document', { filename, data }, { timeout: 60000 }),
};

/* ── Workflows & code ─────────────────────────────────────────────── */
export const workflows = { run: (mode) => post('/api/workflow', { mode }, { timeout: 60000 }) };

export const code = {
  generate: (prompt, lang = 'python', run = false) => post('/api/code/generate', { prompt, lang, run }, { timeout: 120000 }),
  run: (source, lang = 'python') => post('/api/code/run', { code: source, lang }, { timeout: 90000 }),
};

/* ── Security workspace ───────────────────────────────────────────── */
export const cyber = {
  hash: (text, algo = 'sha256') => post('/api/cyber/hash', { text, algo }),
  identify: (hash) => post('/api/cyber/identify', { hash }),
  crack: (hash, wordlist) => post('/api/cyber/crack', { hash, wordlist }, { timeout: 180000 }),
  portscan: (host, ports) => post('/api/cyber/portscan', { host, ports }, { timeout: 120000 }),
  dns: (host) => post('/api/cyber/dns', { host }),
  headers: (url) => post('/api/cyber/headers', { url }, { timeout: 30000 }),
  encode: (text, fmt = 'base64') => post('/api/cyber/encode', { text, fmt }),
  decode: (text, fmt = 'base64') => post('/api/cyber/decode', { text, fmt }),
  cve: (id) => post('/api/cyber/cve', { id }, { timeout: 30000 }),
  subdomains: (domain) => post('/api/cyber/subdomains', { domain }, { timeout: 120000 }),
  revshell: (type, lhost, lport) => post('/api/cyber/revshell', { type, lhost, lport }),
  dorks: (target) => post('/api/cyber/dorks', { target }),
  surface: (target) => post('/api/cyber/surface', { target }, { timeout: 180000 }),
};

/* ── Settings, vault, backup ──────────────────────────────────────── */
export const settings = {
  get: () => get('/api/settings/get'),
  save: (values) => post('/api/settings/save', values),
  reset: () => post('/api/settings/reset', {}),
  clearCache: () => post('/api/settings/clear_cache', {}),
  test: () => get('/api/settings/test'),
  testGoogle: () => get('/api/settings/test_google'),
  testSpotify: () => get('/api/settings/test_spotify'),
  setupTool: (tool) => post('/api/setup/tool', { tool }),
  exportUrl: '/api/settings/export',
};

export const vault = {
  save: (entry) => post('/api/vault/save', entry),
  read: (label) => post('/api/vault/get', { label }),
  remove: (label) => post('/api/vault/delete', { label }),
};

export const backup = {
  create: () => post('/api/backup/create', {}, { timeout: 60000 }),
  restore: (path) => post('/api/backup/restore', { path }, { timeout: 60000 }),
  cloudRestore: () => post('/api/cloud_restore', {}, { timeout: 60000 }),
};

/* ── Oversight ────────────────────────────────────────────────────────── */
export const oversight = {
  status: () => get('/api/oversight/status'),
  watchdogAdd: (url, label) => post('/api/oversight/watchdog/add', { url, label }),
  watchdogRemove: (url) => post('/api/oversight/watchdog/remove', { url }),
  watchdogCheck: (url) => post('/api/oversight/watchdog/check', { url }),
};
