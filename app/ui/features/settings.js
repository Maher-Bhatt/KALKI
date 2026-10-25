/** Settings — sectioned, progressively disclosed, backed by the real config.
 *
 *  Secrets are never rendered. The server masks every key in
 *  SECRET_SETTING_KEYS and returns a separate `secretStatus` map; this UI
 *  shows Set / Not set and writes a replacement value, never round-tripping a
 *  masked string back into /api/settings/save. */

import { h, mount, frag } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { settings as api, voice, backup, system, vault } from '../api/endpoints.js';
import { store, set, applyUi } from '../state/store.js';
import { skeletonRows, errorState } from '../components/states.js';
import { openDialog, confirmDialog, promptDialog } from '../components/dialog.js';
import { ok, err } from '../state/toasts.js';
import { openDiagnostics } from './diagnostics.js';
import { shortcuts, label as keyLabel } from '../lib/keys.js';
import { getPetState, openPetSettings, triggerPetReaction } from './pet.js';

const SECTIONS = [
  ['general', 'Profile'], ['pet', 'Companion Pet'], ['appearance', 'Appearance'], ['voice', 'Voice'], ['models', 'Models'],
  ['memory', 'Memory'], ['integrations', 'Integrations'], ['privacy', 'Privacy'], ['security', 'Security'],
  ['performance', 'Performance'], ['shortcuts', 'Shortcuts'], ['backup', 'Backup'], ['advanced', 'Advanced'], ['about', 'About'],
];

const SECRET_KEYS = [
  ['GROQ_API_KEY', 'Groq'], ['OPENAI_API_KEY', 'OpenAI'], ['ANTHROPIC_API_KEY', 'Anthropic'],
  ['GEMINI_API_KEY', 'Google Gemini'], ['ELEVENLABS_API_KEY', 'ElevenLabs'],
  ['GITHUB_TOKEN', 'GitHub'], ['SHODAN_API_KEY', 'Shodan'], ['EMAIL_APP_PASSWORD', 'Email app password'],
];

const TTS_VOICE_PRESETS = [
  { id: 'en-US-AndrewMultilingualNeural', name: 'Andrew (Multilingual - Expressive & Natural)' },
  { id: 'en-US-AndrewNeural', name: 'Andrew (US - Confident)' },
  { id: 'en-GB-RyanNeural', name: 'Ryan (UK - Crisp)' },
  { id: 'en-US-BrianNeural', name: 'Brian (US - Deep & Clear)' },
  { id: 'en-US-GuyNeural', name: 'Guy (US - Authoritative)' },
  { id: 'en-US-TonyNeural', name: 'Tony (US - Casual & Friendly)' },
  { id: 'en-US-ChristopherNeural', name: 'Christopher (US - Conversational)' },
  { id: 'en-US-EricNeural', name: 'Eric (US - Smooth)' },
  { id: 'en-US-SteffanNeural', name: 'Steffan (US - Clear)' },
  { id: 'en-GB-ThomasNeural', name: 'Thomas (UK - Formal)' },
  { id: 'en-IN-PrabhatNeural', name: 'Prabhat (India - Natural)' },
  { id: 'en-US-JennyNeural', name: 'Jenny (US - Warm Female)' },
  { id: 'en-US-AriaNeural', name: 'Aria (US - Vibrant Female)' },
];

let active = 'general';
let renderFn = () => {};

export function openSettingsSection(name) {
  if (name && SECTIONS.some(([id]) => id === name)) active = name;
}

if (typeof window !== 'undefined') {
  window.addEventListener('kalki:online', () => {
    if (store.settings.error || !store.settings.values) {
      loadSettings();
    }
  });
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
  if (desc) {
    return h('div.row.sb', { style: { margin: '8px 0' } },
      h('div', null, h('div.sm', null, label), h('div.xs.mut', null, desc)),
      control
    );
  }
  return h('div.row.sb', { style: { margin: '8px 0' } }, h('span.sm', null, label), control);
}

function toggleRow(label, desc, key, onChange) {
  const checked = key === 'THEME_GLOW' ? store.settings.values[key] !== false : !!store.settings.values[key];
  const toggle = h('i.tg' + (checked ? '.on' : ''), {
    style: { cursor: 'pointer' },
    onClick: () => {
      const newVal = !checked;
      if (onChange) onChange(newVal); else save({ [key]: newVal });
    }
  });
  if (desc) {
    return h('div.row.sb', { style: { margin: '8px 0' } }, h('div', null, h('div.sm', null, label), h('div.xs.mut', null, desc)), toggle);
  }
  return h('div.row.sb', { style: { margin: '8px 0' } }, h('span.sm', null, label), toggle);
}

function textRow(label, desc, key, placeholder) {
  const input = h('input.input', {
    style: { maxWidth: '16rem' }, 'aria-label': label, placeholder,
    value: store.settings.values[key] || '',
    onChange: (e) => save({ [key]: e.target.value }),
  });
  if (desc) {
    return h('div.row.sb', { style: { margin: '8px 0' } }, h('div', null, h('div.sm', null, label), h('div.xs.mut', null, desc)), input);
  }
  return h('div.row.sb', { style: { margin: '8px 0' } }, h('span.sm', null, label), input);
}

function secretRow([key, label]) {
  const statusText = store.settings.secretStatus?.[key];
  const isSet = typeof statusText === 'boolean'
    ? statusText
    : typeof statusText === 'string'
      ? /set|configured|present|ok|true/i.test(statusText)
      : Boolean(store.settings.values?.[key]);

  return h('div.li', null,
    h('span', { style: { flex: '1' } }, label),
    h('span.chip' + (isSet ? '.ok' : ''), null, isSet ? 'Set' : 'Not set'),
    h('button.btn', {
      type: 'button',
      onClick: async () => {
        const v = await promptDialog({ title: `${label} key`, label: 'Paste the key. It is stored encrypted in the secure vault and never displayed in plain text.', confirmLabel: 'Save key' });
        if (!v) return;
        if (await save({ [key]: v }, `${label} key saved`)) {
          if (!store.settings.secretStatus) store.settings.secretStatus = {};
          store.settings.secretStatus[key] = true;
          loadSettings();
        }
      },
    }, isSet ? 'Replace' : 'Add key')
  );
}

/* ── Sections ────────────────────────────────────────────────────────── */

const SECTION_BODY = {
  general: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Profile'),
      textRow('Your name', 'How KALKI refers to you.', 'OWNER_NAME', 'Name'),
      textRow('Preferred address', 'What KALKI calls you out loud.', 'OWNER_TITLE', 'Sir'),
      textRow('City', 'Used for weather, time and local context.', 'OWNER_CITY', 'City'),
      textRow('State', null, 'OWNER_STATE', 'State'),
      textRow('Country', null, 'OWNER_COUNTRY', 'Country')
    )
  ],

  pet: () => {
    const petState = getPetState();
    return [
      h('div.card.col.g12', null,
        h('h2', null, 'AI Companion Mascot'),
        h('div.sub', null, 'Interactive desk mascot that lives in your workspace, reacts to conversations, music, and typing.'),
        row('Companion status', petState.enabled ? `Active: ${petState.name} (Lvl ${petState.level})` : 'Disabled',
          h('button.btn.pri', {
            type: 'button',
            onClick: () => openPetSettings(),
          }, 'Customize Pet')
        ),
        row('Species', `${petState.species.toUpperCase()} (${petState.name})`,
          h('button.btn', {
            type: 'button',
            onClick: () => {
              triggerPetReaction('happy', 3000, 'Hello from Settings! ✨');
              ok(`Interacted with ${petState.name}`);
            }
          }, 'Interact')
        )
      )
    ];
  },

  appearance: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Theme and layout'),
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
      toggleRow('Presence intensity', 'How brightly KALKI\u2019s filament reads at rest.', 'THEME_GLOW')
    )
  ],

  voice: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Speech output'),
      row('Output device', 'KALKI speaks replies unless this is off.',
        h('div.row.g8', null,
          h('span.chip' + (store.status?.ttsProbeError ? '.warn' : '.ok'), null,
            store.status?.ttsProbeError ? 'Audio device problem' : (store.status?.ttsProvider || 'edge')),
          h('button.btn', {
            type: 'button',
            onClick: async () => {
              const r = await voice.testTts('KALKI is ready.');
              if (r.ok) ok('Test phrase sent'); else err(r.message, r.detail);
            },
          }, 'Test voice')
        )
      ),
      row('Voice identity', 'Neural voice model for assistant speech (Andrew, Ryan, Brian, Guy, Tony, etc.).',
        h('select.select', {
          style: { maxWidth: '24rem', width: '100%' }, 'aria-label': 'Voice identity',
          onChange: (e) => save({ TTS_VOICE: e.target.value }),
        }, ...(() => {
          const cur = store.settings.values.TTS_VOICE || 'en-US-AndrewMultilingualNeural';
          const hasCur = TTS_VOICE_PRESETS.some((v) => v.id === cur);
          const list = hasCur ? TTS_VOICE_PRESETS : [{ id: cur, name: `Custom (${cur})` }, ...TTS_VOICE_PRESETS];
          return list.map((v) => h('option', { value: v.id, selected: cur === v.id }, v.name));
        })())
      ),
      row('Rate', 'Relative speed, e.g. +0% or -10%.',
        h('input.input', {
          style: { maxWidth: '8rem' }, 'aria-label': 'Rate', placeholder: '+0%',
          value: store.settings.values.TTS_RATE || '+0%',
          onChange: (e) => save({ TTS_RATE: e.target.value }),
        })
      ),
      row('Pitch', 'Relative pitch, e.g. +0Hz.',
        h('input.input', {
          style: { maxWidth: '8rem' }, 'aria-label': 'Pitch', placeholder: '+0Hz',
          value: store.settings.values.TTS_PITCH || '+0Hz',
          onChange: (e) => save({ TTS_PITCH: e.target.value }),
        })
      )
    ),
    h('div.card.col.g12', null,
      h('h2', null, 'Microphone'),
      row('Microphone access', store.status?.listenerPaused ? 'Released — other apps can use it.' : 'KALKI\u2019s listener holds the microphone.',
        h('button.btn', {
          type: 'button',
          onClick: async () => {
            const r = store.status?.listenerPaused ? await voice.resume() : await voice.pause();
            if (r.ok) ok(store.status?.listenerPaused ? 'Microphone reclaimed' : 'Microphone released');
            else err(r.message, r.detail);
          },
        }, store.status?.listenerPaused ? 'Reclaim microphone' : 'Release microphone')
      ),
      store.status?.listenerCapabilityNotice
        ? h('div.sm.t2', { style: { color: 'var(--warn)' } }, icon('info', 16), ' ', store.status.listenerCapabilityNotice)
        : null
    )
  ],

  models: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Default models'),
      h('div.sub', { style: { marginBottom: '6px' } }, 'KALKI routes to the first available provider when a role is set to auto, and falls back to a local Ollama model when the network is down.'),
      ...['MODEL_CHAT', 'MODEL_VISION', 'MODEL_CODING', 'MODEL_VOICE'].map((k) =>
        row(k.replace('MODEL_', '').toLowerCase(), null,
          h('select.select', {
            style: { maxWidth: '16rem' }, 'aria-label': k,
            onChange: (e) => save({ [k]: e.target.value }),
          }, ...['auto', ...store.models.available.filter((m) => m !== 'auto')].map((m) =>
            h('option', { value: m, selected: (store.settings.values[k] || 'auto') === m }, m)))
        )
      )
    ),
    h('div.card', null,
      h('h2', null, 'Provider keys'),
      h('div.sub', { style: { marginBottom: '6px' } }, 'KALKI never shows a saved key. Replace one to change it.'),
      ...SECRET_KEYS.slice(0, 5).map(secretRow)
    ),
    h('div.card', null,
      h('div.row.sb', null, h('h2', null, 'Usage'), h('span.xs.mut', null, 'Local on this machine')),
      h('div.sub', { style: { marginBottom: '6px' } }, 'Tokens and latency recorded per model on this machine.'),
      h('button.btn', { type: 'button', onClick: showMetrics }, 'View usage')
    ),
    h('div.card.col.g12', null,
      h('h2', null, 'Connection'),
      h('div.sub', { style: { marginBottom: '6px' } }, 'Verify your API keys and network access.'),
      h('button.btn.pri', {
        type: 'button',
        style: { alignSelf: 'flex-start' },
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
      }, 'Test connection')
    )
  ],

  memory: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Storage'),
      row('Stored memories', `${store.memory.items.length} on this machine.`,
        h('button.btn', { type: 'button', onClick: () => location.hash = '#/memory' }, 'Open memory')
      ),
      toggleRow('Cloud sync', 'Encrypt and mirror memory to your configured cloud target.', 'CLOUD_SYNC_ENABLED')
    )
  ],

  integrations: () => {
    const m = store.settings.meta;
    const card = (name, connected, desc, connect) => h('div.li', null,
      h('div', { style: { flex: '1', minWidth: '0' } },
        h('div.nm', null, name),
        h('div.xs.mut', null, connected ? 'Connected' : desc),
      ),
      h('span.chip' + (connected ? '.ok' : ''), null, connected ? 'OK' : 'Not set'),
      h('button.btn', { type: 'button', onClick: connect }, connected ? 'Reconnect' : 'Connect')
    );
    return [
      h('div.card', null,
        h('h2', null, 'Services'),
        h('div.sub', { style: { marginBottom: '6px' } }, 'Connect external services for rich context.'),
        card('Google Calendar', m.googleConfigured, 'KALKI can\u2019t read your day.',
          async () => { const r = await api.setupTool('google'); r.ok ? ok('Setup opened in a new window') : err(r.message, r.detail); }),
        card('Spotify', m.spotifyConfigured, 'Playback controls stay hidden.',
          async () => { const r = await api.setupTool('spotify'); r.ok ? ok('Setup opened in a new window') : err(r.message, r.detail); }),
        card('GitHub', !!store.settings.values.GITHUB_TOKEN, 'Surfaces notifications.',
          async () => { const v = await promptDialog({ title: 'GitHub token', label: 'A personal access token with notification scope.' }); if (v) { await save({ GITHUB_TOKEN: v }); loadSettings(); } })
      ),
      h('div.card.col.g12', null,
        h('h2', null, 'Email integration'),
        textRow('Email address', 'Used for the inbox digest.', 'EMAIL_ADDRESS', 'you@example.com'),
        secretRow(['EMAIL_APP_PASSWORD', 'Email app password'])
      )
    ];
  },

  privacy: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Local first'),
      h('div.sm.t2', null, 'KALKI runs entirely on this machine. Conversations, memory, tasks, notes and vault entries never leave it unless you connect an integration or enable cloud sync.'),
      toggleRow('Anonymous telemetry', 'Crash and usage counts only. No conversation content, ever.', 'TELEMETRY_ENABLED'),
      row('Privacy terms', null,
        h('button.btn.gh', { type: 'button', onClick: () => window.open('https://github.com/Maher-Bhatt/KALKI/blob/main/PRIVACY.md', '_blank', 'noreferrer') }, 'Open PRIVACY.md'))
    )
  ],

  security: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Access & Auth'),
      h('div.sm.t2', null, 'The local API is bound to 127.0.0.1 and authenticated with a per-install token stored in your user data folder. Only the KALKI window and its own helper processes can reach it.'),
      row('Credential vault', 'Hardware-bound encrypted storage for logins KALKI manages.',
        h('button.btn', { type: 'button', onClick: openVault }, 'Open vault')),
      toggleRow('Confirm dangerous actions', 'Ask before workflows that shut down, restart or delete.', 'REQUIRE_DANGEROUS_CONFIRMATION'),
      row('Security workspace', 'Show the advanced security tools in the navigation rail.',
        h('i.tg' + (store.ui.securityEnabled ? '.on' : ''), {
          style: { cursor: 'pointer' },
          onClick: () => { store.ui.securityEnabled = !store.ui.securityEnabled; applyUi(); window.dispatchEvent(new CustomEvent('kalki:nav-changed')); },
        }))
    )
  ],

  performance: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'System load'),
      h('div.sm.t2', null, 'KALKI runs in a conservative WebView2 configuration with GPU compositing disabled, so heavy visual effects are off by default. These are safe to leave alone.'),
      row('Enhanced visuals', 'Translucent glassmorphism with backdrop blur across surface panels.',
        h('i.tg' + (store.ui.enhancedVisuals ? '.on' : ''), {
          style: { cursor: 'pointer' },
          onClick: () => {
            store.ui.enhancedVisuals = !store.ui.enhancedVisuals;
            applyUi();
            renderFn();
            ok(store.ui.enhancedVisuals ? 'Enhanced visuals enabled' : 'Enhanced visuals disabled');
          },
        })),
      toggleRow('CPU alerts', 'Speak a warning when this machine is under sustained load.', 'CPU_ALERTS_ENABLED'),
      row('Cached data', store.settings.meta.cacheSize ? `${store.settings.meta.cacheSize} in the local data folder.` : 'Local data folder.',
        h('button.btn', {
          type: 'button',
          onClick: async () => {
            if (!(await confirmDialog({ title: 'Clear cached data?', description: 'Removes temporary files. Memory, tasks and settings are untouched.', confirmLabel: 'Clear cache', danger: false }))) return;
            const r = await api.clearCache();
            r.ok ? (ok('Cache cleared'), loadSettings()) : err(r.message, r.detail);
          },
        }, 'Clear cache'))
    )
  ],

  shortcuts: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Keyboard shortcuts'),
      ...shortcuts().map((s) => row(s.description, null, h('kbd', null, keyLabel(s.combo))))
    )
  ],

  backup: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Local backup'),
      row('Create a backup', 'Writes memory, tasks, notes and settings to a single archive.',
        h('button.btn', {
          type: 'button',
          onClick: async () => { const r = await backup.create(); r.ok ? ok(r.data.path ? `Backup written to ${r.data.path}` : 'Backup created') : err(r.message, r.detail); },
        }, 'Create backup')),
      row('Restore from a backup', 'Replaces local data with an archive you choose.',
        h('button.btn', {
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
        h('a.btn.gh', { href: api.exportUrl, download: 'kalki_config_backup.json' }, 'Export JSON'))
    ),
    h('div.card.col.g12', null,
      h('h2', null, 'Cloud Sync'),
      row('Restore from cloud', 'Pull memory and history from your configured cloud target.',
        h('button.btn', {
          type: 'button',
          onClick: async () => { const r = await backup.cloudRestore(); r.ok ? ok('Cloud restore finished') : err(r.message, r.detail); },
        }, 'Restore from cloud'))
    )
  ],

  advanced: () => [
    h('div.card.col.g12', null,
      h('h2', null, 'Developer tools'),
      row('Diagnostics', 'Live status payload, recent API calls and voice state.',
        h('button.btn', { type: 'button', onClick: openDiagnostics }, 'Open diagnostics')),
      h('div.rule'),
      secretRow(['SHODAN_API_KEY', 'Shodan']),
      h('div.rule'),
      row('Reset all settings', 'Restores defaults. Memory, tasks and notes are kept.',
        h('button.btn', {
          type: 'button',
          style: { color: 'var(--dng)' },
          onClick: async () => {
            if (!(await confirmDialog({ title: 'Reset every setting?', description: 'Your configuration returns to defaults. Memory, tasks and notes are not touched.', confirmLabel: 'Reset settings' }))) return;
            const r = await api.reset();
            r.ok ? (ok('Settings reset — reloading'), setTimeout(() => location.reload(), 1200)) : err(r.message, r.detail);
          },
        }, 'Reset settings'))
    )
  ],

  about: () => [
    h('div.card.col.g12', null,
      h('h1', { style: { fontSize: '20px', margin: '0' } }, 'KALKI'),
      h('div.sm.t2', null, 'A personal intelligence environment that runs on your own machine. Conversation, voice, memory, tasks and controlled system access, behind one local API.'),
      row('Version', null, h('span.mono.mut', { id: 'about-version' }, store.settings.values.CURRENT_VERSION || '—')),
      row('Platform', null, h('span.mono.mut', null, store.status?.platform || '—')),
      row('Uptime', null, h('span.mono.mut', null, store.status ? `${Math.round((store.status.uptimeSec || 0) / 60)} min` : '—')),
      h('div.rule'),
      h('div.row.g8', null,
        h('button.btn', { type: 'button', onClick: () => system.support() }, 'Support the project'),
        h('a.btn.gh', { href: 'https://github.com/Maher-Bhatt/KALKI', target: '_blank', rel: 'noreferrer' }, 'Source on GitHub'),
      )
    )
  ],
};

async function showMetrics() {
  const r = await system.metrics();
  const m = (r && r.ok && r.data && r.data.metrics) ? r.data.metrics : {};
  const totalCalls = m.total_calls || 0;
  const promptTokens = m.total_prompt_tokens || 0;
  const compTokens = m.total_completion_tokens || 0;
  const totalTokens = promptTokens + compTokens;
  const costUsd = typeof m.total_cost_usd === 'number' ? m.total_cost_usd.toFixed(4) : '0.0000';
  const avgLatency = typeof m.avg_latency_ms === 'number' ? Math.round(m.avg_latency_ms) : 0;

  const modelEntries = Object.entries(m).filter(([k, v]) =>
    !['total_calls', 'total_prompt_tokens', 'total_completion_tokens', 'total_cost_usd', 'avg_latency_ms', 'daily'].includes(k) &&
    typeof v === 'object' && v !== null
  );

  const statCard = (title, val, subtitle) => h('div.card.col.g4', { style: { flex: '1 1 120px', padding: '12px', background: 'var(--raised)' } },
    h('div.xs.mut', null, title),
    h('div.h2', { style: { fontSize: '18px', fontWeight: '700', color: 'var(--text)' } }, String(val)),
    subtitle ? h('div.xs.faint', null, subtitle) : null
  );

  let dlgClose = null;
  const body = h('div.col.g16', null,
    h('div.row.g12', { style: { flexWrap: 'wrap' } },
      statCard('Total Calls', totalCalls.toLocaleString(), `${avgLatency}ms avg latency`),
      statCard('Total Tokens', totalTokens.toLocaleString(), `${promptTokens.toLocaleString()} in / ${compTokens.toLocaleString()} out`),
      statCard('Est. Cost', `$${costUsd}`, 'Local usage tracking')
    ),
    h('div.card.col.g8', null,
      h('div.row.sb', null,
        h('strong', { style: { fontSize: '13px' } }, 'Activity by Model'),
        h('span.xs.mut', null, `${modelEntries.length} models tracked`)
      ),
      modelEntries.length === 0
        ? h('div.sm.mut', { style: { padding: '8px 0' } }, 'Telemetry logs start recording automatically as you converse with AI models.')
        : h('div.col.g6', null,
            ...modelEntries.map(([modName, stats]) => h('div.li', { style: { padding: '6px 8px', borderRadius: '6px', background: 'var(--inset)' } },
              h('div.col', { style: { flex: 1, minWidth: 0 } },
                h('strong.sm', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, modName),
                h('span.xs.mut', null, `${((stats.prompt_tokens || 0) + (stats.completion_tokens || 0)).toLocaleString()} tokens • ${Math.round(stats.avg_latency_ms || 0)}ms`)
              ),
              h('span.chip.ok', null, `${stats.calls || 0} calls`)
            ))
          )
    )
  );

  const dlg = openDialog({
    title: 'Model Usage & Performance',
    description: 'Recorded locally on this machine. Never shared or uploaded.',
    width: '34rem',
    body,
    actions: [
      h('button.btn.pri', { type: 'button', onClick: () => dlg.close() }, 'Done')
    ]
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
    body: h('div.col.g12', null,
      h('div.field', null, h('label', { for: 'v-label' }, 'Label'), h('input.input', { id: 'v-label', ref: (el) => { labelEl = el; } })),
      h('div.field', null, h('label', { for: 'v-user' }, 'Username'), h('input.input', { id: 'v-user', ref: (el) => { userEl = el; } })),
      h('div.field', null, h('label', { for: 'v-pass' }, 'Password'), h('input.input', { id: 'v-pass', type: 'password', ref: (el) => { passEl = el; } })),
    ),
    actions: [
      h('button.btn.gh', { type: 'button', onClick: () => close() }, 'Cancel'),
      h('button.btn.pri', { type: 'button', onClick: submit }, 'Save entry'),
    ],
    initialFocus: '#v-label',
  });
}

export function settingsView() {
  const main = h('div.view-body.scroll');
  const aside = h('div.view-body.scroll');
  const viewObj = { main, aside, render: () => {} };

  viewObj.render = () => {
    const s = store.settings;
    if (s.loading) {
      mount(main, skeletonRows(6));
      mount(aside, skeletonRows(3));
      return;
    }
    if (s.error) {
      mount(main, errorState({ title: "Settings didn't load", message: s.error.message, detail: s.error.detail, onRetry: loadSettings, onDiagnostics: openDiagnostics }));
      return;
    }

    mount(main, h('div.pad', null, 
      h('div.hd', null, 
        h('div', null, h('h1', null, 'Settings'), h('div.sub', null, 'Changes save when you leave a field.')), 
        h('a.btn', { href: api.exportUrl, download: 'kalki_config_backup.json' }, 'Export settings')
      ), 
      h('div.grid-sw', null, 
        h('div.snav', null, 
          ...SECTIONS.map(([id, label]) => 
            h(active === id ? 'a.s' : 'a', { 
              onClick: () => { active = id; renderFn(); },
              style: { cursor: 'pointer' }
            }, label)
          )
        ), 
        h('div.col.g16', null, 
          (SECTION_BODY[active] || SECTION_BODY.general)()
        )
      )
    ));

    mount(aside, frag(
      h('h1', { style: { fontSize: '16px' } }, 'Vault'), 
      h('div.card.col.g8', null, 
        h('div.sm.t2', null, 'Credentials live in a hardware-bound vault. Entries are write-only here.'), 
        h('div.row.g8', null, h('button.btn.pri', { onClick: openVault }, 'Open vault'))
      ), 
      h('div.card.col.g8', null, 
        h('h2', null, 'Backup'), 
        h('div.sm.t2', null, 'Memory, tasks and notes to a single archive.'), 
        h('div.row.g8', { style: { flexWrap: 'wrap' } }, 
          h('button.btn', {
            style: { whiteSpace: 'nowrap', flex: '1 1 auto', justifyContent: 'center' },
            onClick: async () => { const r = await backup.create(); r.ok ? ok(r.data.path ? `Backup written to ${r.data.path}` : 'Backup created') : err(r.message, r.detail); }
          }, 'Create backup'), 
          h('button.btn.gh', {
            style: { whiteSpace: 'nowrap', flex: '0 0 auto', justifyContent: 'center' },
            onClick: async () => {
            const path = await promptDialog({ title: 'Restore a backup', label: 'Full path to the backup archive', confirmLabel: 'Restore' });
            if (!path) return;
            if (!(await confirmDialog({ title: 'Replace local data?', description: 'Current memory, tasks and settings will be overwritten.', confirmLabel: 'Restore' }))) return;
            const r = await backup.restore(path);
            r.ok ? (ok('Restored — reloading'), setTimeout(() => location.reload(), 1200)) : err(r.message, r.detail);
          } }, 'Restore')
        )
      ), 
      h('div.card.col.g8', null, 
        h('h2', null, 'Connections'), 
        h('div.row.sb', null, h('span.sm', null, 'Google'), h('span.chip' + (s.meta?.googleConfigured ? '.ok' : ''), null, s.meta?.googleConfigured ? 'OK' : 'Not set')), 
        h('div.row.sb', null, h('span.sm', null, 'Spotify'), h('span.chip' + (s.meta?.spotifyConfigured ? '.ok' : ''), null, s.meta?.spotifyConfigured ? 'OK' : 'Not set')), 
        h('div.row.sb', null, h('span.sm', null, 'GitHub'), h('span.chip' + (s.values?.GITHUB_TOKEN ? '.ok' : ''), null, s.values?.GITHUB_TOKEN ? 'OK' : 'Not set'))
      )
    ));
  };

  renderFn = viewObj.render;
  return viewObj;
}
