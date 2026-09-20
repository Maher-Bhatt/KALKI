/** KALKI frontend entry point.
 *
 *  No build step: this is a native ES module graph served from /ui/. WebView2
 *  is evergreen Chromium, so modules, <dialog>, :has() and custom properties
 *  all work natively. Editing a file and pressing F5 is the whole dev loop,
 *  in development and in a packaged install alike. */

import { store, loadUi, subscribe, notify, applyUi } from './state/store.js';
import { startStatus, onExchange, loadModels } from './state/status.js';
import { loadThreads, ensureActive, appendVoiceExchange, openThread } from './state/conversations.js';
import { install as installKeys, bind } from './lib/keys.js';
import { buildShell } from './features/shell.js';
import { startRouter, setAnnouncer, go } from './features/router.js';
import { openPalette } from './features/palette.js';
import { askView, stopStreaming } from './features/ask.js';
import { todayView, loadToday, syncFocus } from './features/today.js';
import { memoryView, loadMemory } from './features/memory.js';
import { workbenchView } from './features/workbench.js';
import { oversightView, loadOversight } from './features/oversight.js';
import { securityView } from './features/security.js';
import { settingsView, loadSettings, openSettingsSection } from './features/settings.js';
import { openDiagnostics } from './features/diagnostics.js';

const VIEWS = {
  ask: { build: askView, load: () => loadModels() },
  today: { build: todayView, load: () => { loadToday(); syncFocus(); } },
  memory: { build: memoryView, load: loadMemory },
  workbench: { build: workbenchView, load: () => {} },
  oversight: { build: oversightView, load: () => loadOversight() },
  security: { build: securityView, load: () => {} },
  settings: { build: settingsView, load: () => { loadSettings(); loadModels(); } },
};

let shell = null;
let currentView = null;
let currentName = null;

function mountView(route) {
  if (route.name === 'settings') openSettingsSection(route.params.section);
  if (route.name === 'ask' && route.params.threadId) openThread(route.params.threadId);

  if (currentName !== route.name) {
    currentName = route.name;
    const spec = VIEWS[route.name] || VIEWS.ask;
    currentView = spec.build();
    shell.viewSlot.replaceChildren(currentView);
    spec.load();
  }
  currentView?.render?.();
}

function render() {
  shell.render();
  currentView?.render?.();
}

function installShortcuts() {
  installKeys();
  bind('mod+k', () => openPalette(), { description: 'Open the command palette', allowInInput: true });
  bind('mod+1', () => go('ask'), { description: 'Go to Ask' });
  bind('mod+2', () => go('today'), { description: 'Go to Today' });
  bind('mod+3', () => go('memory'), { description: 'Go to Memory' });
  bind('mod+4', () => go('workbench'), { description: 'Go to Workbench' });
  bind('mod+5', () => go('oversight'), { description: 'Go to Oversight' });
  bind('mod+,', () => go('settings'), { description: 'Open settings' });
  bind('mod+n', async () => {
    const { newThread } = await import('./state/conversations.js');
    await newThread();
    go('ask');
    setTimeout(() => currentView?.focusComposer?.(), 60);
  }, { description: 'Start a new conversation' });
  bind('mod+b', () => shell.toggleRail(), { description: 'Pin or unpin the navigation rail' });
  bind('mod+shift+v', () => window.dispatchEvent(new CustomEvent('kalki:voice-toggle')), { description: 'Open voice' });
  bind('mod+shift+d', () => openDiagnostics(), { description: 'Open diagnostics' });
  bind('mod+/', () => go('settings', { section: 'shortcuts' }), { description: 'Show keyboard shortcuts' });
  bind('Escape', () => { if (store.conv.streaming) stopStreaming(); }, { description: 'Stop generating', allowInInput: true });
}

async function boot() {
  const root = document.getElementById('app');
  if (!root) return;

  store.ui.debug = new URLSearchParams(location.search).has('debug');
  loadUi();

  // Follow the OS motion preference unless the user has overridden it.
  if (store.ui.motion === 'auto' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.dataset.motion = 'off';
  }

  shell = buildShell(root);
  setAnnouncer(shell.announcer);
  installShortcuts();

  subscribe(render);

  await loadThreads();
  await ensureActive();
  onExchange(appendVoiceExchange);
  startStatus();
  loadModels();

  startRouter(mountView);
  render();

  document.getElementById('boot')?.remove();

  if (store.ui.debug) {
    window.__kalki = {
      get state() { return store; },
      diagnostics: openDiagnostics,
      palette: openPalette,
    };
  }

  // The service worker serves the shell network-first, so an update lands on
  // the next launch rather than being cached forever.
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('/service-worker.js').catch(() => { /* optional */ });
  }
}

window.addEventListener('error', (e) => {
  console.error('[kalki] uncaught', e.error || e.message);
});
window.addEventListener('unhandledrejection', (e) => {
  console.error('[kalki] unhandled rejection', e.reason);
});

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot().catch(e => { const b = document.getElementById('boot'); if (b) b.innerHTML = '<div style="color:red">' + e.message + '<br>' + e.stack + '</div>'; });

export { applyUi, notify };
