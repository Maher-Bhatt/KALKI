/** Settings — sectioned, progressively disclosed, backed by the real config.
 *
 *  Secrets are never rendered. The server masks every key in
 *  SECRET_SETTING_KEYS and returns a separate `secretStatus` map; this UI
 *  shows Set / Not set and writes a replacement value, never round-tripping a
 *  masked string back into /api/settings/save. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { settings as api, voice, backup, system, vault } from '../api/endpoints.js';
import { store, set, applyUi } from '../state/store.js';
import { skeletonRows, errorState } from '../components/states.js';
import { openDialog, confirmDialog, promptDialog } from '../components/dialog.js';
import { ok, err } from '../state/toasts.js';
import { openDiagnostics } from './diagnostics.js';
import { shortcuts, label as keyLabel } from '../lib/keys.js';

const SECTIONS = [
  ['general', 'General'], ['appearance', 'Appearance'], ['voice', 'Voice'], ['models', 'Models'],
  ['memory', 'Memory'], ['integrations', 'Integrations'], ['privacy', 'Privacy'], ['security', 'Security'],
  ['performance', 'Performance'], ['shortcuts', 'Shortcuts'], ['backup', 'Backup'], ['advanced', 'Advanced'], ['about', 'About'],
];

const SECRET_KEYS = [
  ['GROQ_API_KEY', 'Groq'], ['OPENAI_API_KEY', 'OpenAI'], ['ANTHROPIC_API_KEY', 'Anthropic'],
  ['GEMINI_API_KEY', 'Google Gemini'], ['ELEVENLABS_API_KEY', 'ElevenLabs'],
  ['GITHUB_TOKEN', 'GitHub'], ['SHODAN_API_KEY', 'Shodan'], ['EMAIL_APP_PASSWORD', 'Email app password'],
];

let active = 'general';
let renderFn = () => {};

export function openSettingsSection(name) {
  if (name && SECTIONS.some(([id]) => id === name)) active = name;
}

export async function loadSettings() {
  set('settings', { loading: true });
  const r = await api.get();
  if (!r.ok) { set('settings', { loading: false, error: r }); return; }
  set('settings', {
    loading: false, error: null,
    values: r.data.settings || {},
    secretStatus: r.data.secretStatus || {},
    meta: {
      cacheSize: r.data.cacheSize,
      googleConfigured: r.data.googleConfigured,
      spotifyConfigured: r.data.spotifyConfigured,
    },
  });
}

async function save(patch, message = 'Saved') {
  set('settings', { saving: true });
  const r = await api.save(patch);
  set('settings', { saving: false });
  if (r.ok) { ok(message); Object.assign(store.settings.values, patch); renderFn(); }
  else err(r.message, r.detail);
  return r.ok;
}

/* ── Building blocks ─────────────────────────────────────────────────── */

function row(label, desc, control) {
  return h('div.settings-row', { style: { borderBottom: '1px solid var(--filament-2)', padding: 'var(--space-3) 0', display: 'flex', alignItems: 'center' } },
    h('div', null, h('div.label.t-mono', null, label), desc ? h('div.desc.t-meta.muted', { style: { marginTop: 'var(--space-1)' } }, desc) : null),
    h('span.spacer', { style: { flex: '1', minWidth: 'var(--space-4)' } }),
    control,
  );
}

function toggleRow(label, desc, key, onChange) {
  const checked = !!store.settings.values[key];
  return row(label, desc, h('label.toggle', null,
    h('input', {
      type: 'checkbox', checked, 'aria-label': label,
      onChange: (e) => (onChange ? onChange(e.target.checked) : save({ [key]: e.target.checked })),
    }),
    h('i'),
  ));
}

function textRow(label, desc, key, placeholder) {
  return row(label, desc, h('input.input', {
    style: { maxWidth: '16rem' }, 'aria-label': label, placeholder,
    value: store.settings.values[key] || '',
    onChange: (e) => save({ [key]: e.target.value }),
  }));
}

function secretRow([key, label]) {
  const statusText = store.settings.secretStatus?.[key];
  const isSet = typeof statusText === 'string'
    ? /set|configured|present|ok/i.test(statusText)
    : Boolean(store.settings.values[key]);

  return row(label, isSet ? 'A key is stored in the encrypted vault.' : 'No key stored.',
    h('div.inline', null,
      h('span.chip', { class: isSet ? 'chip chip-success' : 'chip' }, isSet ? 'Set' : 'Not set'),
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async () => {
          const v = await promptDialog({ title: `${label} key`, label: 'Paste the key. It is stored encrypted and never displayed again.', confirmLabel: 'Save key' });
          if (!v) return;
          if (await save({ [key]: v }, `${label} key saved`)) loadSettings();
        },
      }, isSet ? 'Replace' : 'Add'),
    ));
}

/* ── Sections ────────────────────────────────────────────────────────── */

const SECTION_BODY = {
  general: () => h('div.settings-section', null,
    textRow('Your name', 'How KALKI refers to you.', 'OWNER_NAME', 'Name'),
    textRow('Preferred address', 'What KALKI calls you out loud.', 'OWNER_TITLE', 'Sir'),
    textRow('City', 'Used for weather, time and local context.', 'OWNER_CITY', 'City'),
    textRow('State', null, 'OWNER_STATE', 'State'),
    textRow('Country', null, 'OWNER_COUNTRY', 'Country'),
  ),

  appearance: () => h('div.settings-section', null,
    row('Theme', 'Dark is the flagship. Light is designed separately, not inverted.',
      h('select.select', {
        style: { maxWidth: '10rem' }, 'aria-label': 'Theme',
        onChange: (e) => { store.ui.theme = e.target.value; applyUi(); save({ THEME_MODE: e.target.value }); },
      }, ...['dark', 'light'].map((t) => h('option', { value: t, selected: store.ui.theme === t }, t)))),
    row('Motion', 'Turning motion off keeps every state legible — only movement is removed.',
      h('select.select', {
        style: { maxWidth: '10rem' }, 'aria-label': 'Motion',
        onChange: (e) => { store.ui.motion = e.target.value; applyUi(); save({ THEME_MOTION: e.target.value === 'off' ? 0 : 1 }); },
      }, h('option', { value: 'auto', selected: store.ui.motion === 'auto' }, 'Follow system'),
         h('option', { value: 'off', selected: store.ui.motion === 'off' }, 'Off'))),
    row('Density', 'Compact fits more on smaller windows.',
      h('select.select', {
        style: { maxWidth: '10rem' }, 'aria-label': 'Density',
        onChange: (e) => { store.ui.density = e.target.value; applyUi(); renderFn(); },
      }, ...['comfortable', 'compact'].map((d) => h('option', { value: d, selected: store.ui.density === d }, d)))),
    row('Presence intensity', 'How brightly KALKI\u2019s filament reads at rest.',
      h('label.toggle', null,
        h('input', {
          type: 'checkbox', checked: store.settings.values.THEME_GLOW !== false, 'aria-label': 'Presence glow',
          onChange: (e) => save({ THEME_GLOW: e.target.checked }),
        }), h('i'))),
  ),

  voice: () => h('div.settings-section', null,
    row('Speech output', 'KALKI speaks replies unless this is off.',
      h('div.inline', null,
        h('span.chip', { class: store.status?.ttsProbeError ? 'chip chip-warning' : 'chip chip-success' },
          store.status?.ttsProbeError ? 'Audio device problem' : (store.status?.ttsProvider || 'edge')),
        h('button.btn.btn-sm.btn-secondary', {
          type: 'button',
          onClick: async () => {
            const r = await voice.testTts('KALKI is ready.');
            if (r.ok) ok('Test phrase sent'); else err(r.message, r.detail);
          },
        }, 'Test voice'),
      )),
    textRow('Voice', 'An edge-tts voice name, e.g. en-GB-RyanNeural.', 'TTS_VOICE', 'en-GB-RyanNeural'),
    textRow('Rate', 'Relative speed, e.g. +0% or -10%.', 'TTS_RATE', '+0%'),
    textRow('Pitch', 'e.g. +0Hz.', 'TTS_PITCH', '+0Hz'),
    row('Microphone', store.status?.listenerPaused ? 'Released — other apps can use it.' : 'KALKI\u2019s listener holds the microphone.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async () => {
          const r = store.status?.listenerPaused ? await voice.resume() : await voice.pause();
          if (r.ok) ok(store.status?.listenerPaused ? 'Microphone reclaimed' : 'Microphone released');
          else err(r.message, r.detail);
        },
      }, store.status?.listenerPaused ? 'Reclaim microphone' : 'Release microphone')),
    store.status?.listenerCapabilityNotice
      ? h('div.toolrun.toolrun-confirm', null, h('div.toolrun-head', null, icon('info', 16), h('span', null, store.status.listenerCapabilityNotice)))
      : null,
  ),

  models: () => h('div.settings-section', null,
    h('p.t-body-sm.muted', null, 'KALKI routes to the first available provider when a role is set to auto, and falls back to a local Ollama model when the network is down.'),
    ...['MODEL_CHAT', 'MODEL_VISION', 'MODEL_CODING', 'MODEL_VOICE'].map((k) =>
      row(k.replace('MODEL_', '').toLowerCase(), null,
        h('select.select', {
          style: { maxWidth: '16rem' }, 'aria-label': k,
          onChange: (e) => save({ [k]: e.target.value }),
        }, ...['auto', ...store.models.available.filter((m) => m !== 'auto')].map((m) =>
          h('option', { value: m, selected: (store.settings.values[k] || 'auto') === m }, m))))),
    h('hr.divider'),
    ...SECRET_KEYS.slice(0, 5).map(secretRow),
    h('hr.divider'),
    row('Connection', 'Verify your API keys and network access.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async (e) => {
          const btn = e.currentTarget;
          const orig = btn.innerHTML;
          btn.disabled = true;
          btn.textContent = 'Testing...';
          const r = await api.test();
          if (r.ok && r.data.groq === 'OK') {
            btn.classList.add('is-success');
            btn.innerHTML = '&#10003; Connected';
            setTimeout(() => { btn.classList.remove('is-success'); btn.innerHTML = orig; btn.disabled = false; }, 2000);
          } else {
            err(r.message || 'Connection failed', r.detail || (r.data && r.data.groq !== 'OK' ? `Groq: ${r.data.groq}` : 'Unknown'));
            btn.innerHTML = orig;
            btn.disabled = false;
          }
        },
      }, 'Test connection')),
    row('Usage', 'Tokens and latency recorded per model on this machine.',
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: showMetrics }, 'View usage')),
  ),

  memory: () => h('div.settings-section', null,
    row('Stored memories', `${store.memory.items.length} on this machine.`,
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: () => location.hash = '#/memory' }, 'Open memory')),
    toggleRow('Cloud sync', 'Encrypt and mirror memory to your configured cloud target.', 'CLOUD_SYNC_ENABLED'),
  ),

  integrations: () => {
    const m = store.settings.meta;
    const card = (name, connected, desc, connect) => h('div.row', null,
      h('span.dot', { class: connected ? 'dot dot-success' : 'dot' }),
      h('div', { style: { flex: '1', minWidth: '0' } },
        h('div.t-body-sm', null, name),
        h('div.t-meta.muted', null, connected ? 'Connected' : desc),
      ),
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: connect }, connected ? 'Reconnect' : 'Connect'),
    );
    return h('div.settings-section', null,
      card('Google Calendar', m.googleConfigured, 'Not connected — KALKI can\u2019t read your day.',
        async () => { const r = await api.setupTool('google'); r.ok ? ok('Setup opened in a new window') : err(r.message, r.detail); }),
      card('Spotify', m.spotifyConfigured, 'Not connected — playback controls stay hidden.',
        async () => { const r = await api.setupTool('spotify'); r.ok ? ok('Setup opened in a new window') : err(r.message, r.detail); }),
      card('GitHub', !!store.settings.values.GITHUB_TOKEN, 'Add a token to surface notifications.',
        async () => { const v = await promptDialog({ title: 'GitHub token', label: 'A personal access token with notification scope.' }); if (v) { await save({ GITHUB_TOKEN: v }); loadSettings(); } }),
      h('hr.divider'),
      textRow('Email address', 'Used for the inbox digest.', 'EMAIL_ADDRESS', 'you@example.com'),
      secretRow(['EMAIL_APP_PASSWORD', 'Email app password']),
    );
  },

  privacy: () => h('div.settings-section', null,
    h('p.t-body-sm.muted', null, 'KALKI runs entirely on this machine. Conversations, memory, tasks, notes and vault entries never leave it unless you connect an integration or enable cloud sync.'),
    toggleRow('Anonymous telemetry', 'Crash and usage counts only. No conversation content, ever.', 'TELEMETRY_ENABLED'),
    row('Read the privacy terms', null,
      h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => window.open('https://github.com/Maher-Bhatt/KALKI/blob/main/PRIVACY.md', '_blank', 'noreferrer') }, 'Open PRIVACY.md')),
  ),

  security: () => h('div.settings-section', null,
    h('p.t-body-sm.muted', null, 'The local API is bound to 127.0.0.1 and authenticated with a per-install token stored in your user data folder. Only the KALKI window and its own helper processes can reach it.'),
    row('Credential vault', 'Hardware-bound encrypted storage for logins KALKI manages.',
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: openVault }, 'Open vault')),
    toggleRow('Confirm dangerous actions', 'Ask before workflows that shut down, restart or delete.', 'REQUIRE_DANGEROUS_CONFIRMATION'),
    row('Security workspace', 'Show the advanced security tools in the navigation rail.',
      h('label.toggle', null,
        h('input', {
          type: 'checkbox', checked: store.ui.securityEnabled, 'aria-label': 'Show security workspace',
          onChange: (e) => { store.ui.securityEnabled = e.target.checked; applyUi(); window.dispatchEvent(new CustomEvent('kalki:nav-changed')); },
        }), h('i'))),
  ),

  performance: () => h('div.settings-section', null,
    h('p.t-body-sm.muted', null, 'KALKI runs in a conservative WebView2 configuration with GPU compositing disabled, so heavy visual effects are off by default. These are safe to leave alone.'),
    row('Enhanced visuals', 'Adds translucency to two surfaces. Can cost frames on this renderer.',
      h('label.toggle', null,
        h('input', {
          type: 'checkbox', checked: document.documentElement.dataset.enhanced === 'on', 'aria-label': 'Enhanced visuals',
          onChange: (e) => { document.documentElement.dataset.enhanced = e.target.checked ? 'on' : 'off'; },
        }), h('i'))),
    toggleRow('CPU alerts', 'Speak a warning when this machine is under sustained load.', 'CPU_ALERTS_ENABLED'),
    row('Cached data', store.settings.meta.cacheSize ? `${store.settings.meta.cacheSize} in the local data folder.` : 'Local data folder.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async () => {
          if (!(await confirmDialog({ title: 'Clear cached data?', description: 'Removes temporary files. Memory, tasks and settings are untouched.', confirmLabel: 'Clear cache', danger: false }))) return;
          const r = await api.clearCache();
          r.ok ? (ok('Cache cleared'), loadSettings()) : err(r.message, r.detail);
        },
      }, 'Clear cache')),
  ),

  shortcuts: () => h('div.settings-section', null,
    ...shortcuts().map((s) => row(s.description, null, h('span.kbd', null, keyLabel(s.combo)))),
  ),

  backup: () => h('div.settings-section', null,
    row('Create a backup', 'Writes memory, tasks, notes and settings to a single archive.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async () => { const r = await backup.create(); r.ok ? ok(r.data.path ? `Backup written to ${r.data.path}` : 'Backup created') : err(r.message, r.detail); },
      }, 'Create backup')),
    row('Restore from a backup', 'Replaces local data with an archive you choose.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async () => {
          const path = await promptDialog({ title: 'Restore a backup', label: 'Full path to the backup archive', confirmLabel: 'Restore' });
          if (!path) return;
          if (!(await confirmDialog({ title: 'Replace local data?', description: 'Current memory, tasks and settings will be overwritten.', confirmLabel: 'Restore' }))) return;
          const r = await backup.restore(path);
          r.ok ? (ok('Restored — reloading'), setTimeout(() => location.reload(), 1200)) : err(r.message, r.detail);
        },
      }, 'Restore')),
    row('Export settings', 'Downloads your configuration as JSON. Secrets are masked.',
      h('a.btn.btn-sm.btn-ghost', { href: api.exportUrl, download: 'kalki_config_backup.json' }, 'Export')),
    row('Restore from cloud', 'Pull memory and history from your configured cloud target.',
      h('button.btn.btn-sm.btn-ghost', {
        type: 'button',
        onClick: async () => { const r = await backup.cloudRestore(); r.ok ? ok('Cloud restore finished') : err(r.message, r.detail); },
      }, 'Restore from cloud')),
  ),

  advanced: () => h('div.settings-section', null,
    row('Diagnostics', 'Live status payload, recent API calls and voice state.',
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: openDiagnostics }, 'Open diagnostics')),
    secretRow(['SHODAN_API_KEY', 'Shodan']),
    row('Reset all settings', 'Restores defaults. Memory, tasks and notes are kept.',
      h('button.btn.btn-sm.btn-danger', {
        type: 'button',
        onClick: async () => {
          if (!(await confirmDialog({ title: 'Reset every setting?', description: 'Your configuration returns to defaults. Memory, tasks and notes are not touched.', confirmLabel: 'Reset settings' }))) return;
          const r = await api.reset();
          r.ok ? (ok('Settings reset — reloading'), setTimeout(() => location.reload(), 1200)) : err(r.message, r.detail);
        },
      }, 'Reset settings')),
  ),

  about: () => h('div.settings-section', null,
    h('div.stack', null,
      h('h2.t-title-2', null, 'KALKI'),
      h('p.t-body-sm.muted', null, 'A personal intelligence environment that runs on your own machine. Conversation, voice, memory, tasks and controlled system access, behind one local API.'),
      row('Version', null, h('span.t-mono.muted', { id: 'about-version' }, store.settings.values.CURRENT_VERSION || '—')),
      row('Platform', null, h('span.t-mono.muted', null, store.status?.platform || '—')),
      row('Uptime', null, h('span.t-mono.muted', null, store.status ? `${Math.round((store.status.uptimeSec || 0) / 60)} min` : '—')),
      h('hr.divider'),
      h('div.inline.wrap', null,
        h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: () => system.support() }, 'Support the project'),
        h('a.btn.btn-sm.btn-ghost', { href: 'https://github.com/Maher-Bhatt/KALKI', target: '_blank', rel: 'noreferrer' }, 'Source on GitHub'),
      ),
    ),
  ),
};

async function showMetrics() {
  const r = await system.metrics();
  openDialog({
    title: 'Model usage',
    description: 'Recorded locally. Nothing is sent anywhere.',
    width: '32rem',
    body: r.ok && r.data.metrics && Object.keys(r.data.metrics).length
      ? h('pre.pre-out', null, JSON.stringify(r.data.metrics, null, 2))
      : h('p.muted.t-body-sm', null, 'No usage recorded yet. Metrics appear after your first few replies.'),
    actions: [],
  });
}

async function openVault() {
  let labelEl, userEl, passEl;
  const submit = async () => {
    const entry = { label: labelEl.value.trim(), username: userEl.value.trim(), password: passEl.value };
    if (!entry.label) { labelEl.focus(); return; }
    const r = await vault.save(entry);
    if (r.ok) { ok('Saved to the vault'); close(); } else err(r.message, r.detail);
  };
  const { close } = openDialog({
    title: 'Credential vault',
    description: 'Encrypted with a key bound to this machine. Entries are never shown in the interface once saved.',
    width: '30rem',
    body: h('div.stack', null,
      h('div.field', null, h('label', { for: 'v-label' }, 'Label'), h('input.input', { id: 'v-label', ref: (el) => { labelEl = el; } })),
      h('div.field', null, h('label', { for: 'v-user' }, 'Username'), h('input.input', { id: 'v-user', ref: (el) => { userEl = el; } })),
      h('div.field', null, h('label', { for: 'v-pass' }, 'Password'), h('input.input', { id: 'v-pass', type: 'password', ref: (el) => { passEl = el; } })),
    ),
    actions: [
      h('button.btn.btn-secondary', { type: 'button', onClick: () => close() }, 'Cancel'),
      h('button.btn.btn-primary', { type: 'button', onClick: submit }, 'Save entry'),
    ],
    initialFocus: '#v-label',
  });
}

export function settingsView() {
  const body = h('div.view-body.scroll');
  const view = h('section.view', { 'aria-label': 'Settings' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Settings'),
      h('span.spacer'),
      store.settings.saving ? h('span.t-meta.muted', { role: 'status' }, 'Saving…') : null,
    ),
    body,
  );

  view.render = () => {
    const s = store.settings;
    if (s.loading) return mount(body, skeletonRows(6));
    if (s.error) return mount(body, errorState({ title: "Settings didn't load", message: s.error.message, detail: s.error.detail, onRetry: loadSettings, onDiagnostics: openDiagnostics }));

    mount(body, h('div.settings-layout', null,
      h('nav.settings-nav', { 'aria-label': 'Settings sections' },
        ...SECTIONS.map(([id, label]) => h('button', {
          type: 'button', 'aria-current': active === id ? 'true' : null,
          onClick: () => { active = id; renderFn(); },
        }, label))),
      h('div.scroll', { style: { minHeight: '0' } }, (SECTION_BODY[active] || SECTION_BODY.general)()),
    ));
  };

  renderFn = view.render;
  return view;
}
