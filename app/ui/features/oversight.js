import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { oversight } from '../api/endpoints.js';
import { store } from '../state/store.js';
import { skeletonRows, errorState, emptyState } from '../components/states.js';
import { promptDialog } from '../components/dialog.js';
import { ok, err } from '../state/toasts.js';

let data = { loading: true, alerts: [], watchedSites: [], thresholds: {} };
let timer;
let renderFn = () => {};

export async function loadOversight() {
  data.loading = true;
  renderFn();
  const r = await oversight.status();
  if (r.ok) {
    data = { loading: false, alerts: r.data.alerts || [], watchedSites: r.data.watchedSites || [], thresholds: r.data.thresholds || {} };
  } else {
    data = { loading: false, error: r, alerts: [], watchedSites: [], thresholds: {} };
  }
  renderFn();
}

function startPolling() {
  stopPolling();
  loadOversight();
  timer = setInterval(loadOversight, 20000);
}

function stopPolling() {
  clearInterval(timer);
}

async function addSite() {
  const url = await promptDialog({ title: 'Watch a site', label: 'URL (e.g. https://example.com)', confirmLabel: 'Watch' });
  if (!url) return;
  const r = await oversight.watchdogAdd(url, url);
  if (r.ok) { ok('Site added'); loadOversight(); } else err(r.message, r.detail);
}

async function removeSite(url) {
  const r = await oversight.watchdogRemove(url);
  if (r.ok) { ok('Site removed'); loadOversight(); } else err(r.message, r.detail);
}

async function checkSite(btn, url) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = '...';
  const r = await oversight.watchdogCheck(url);
  if (r.ok && r.data.result?.up) {
    btn.classList.add('is-success');
    btn.innerHTML = '&#10003;';
    setTimeout(() => { btn.classList.remove('is-success'); btn.innerHTML = orig; btn.disabled = false; }, 2000);
  } else {
    err('Site down or unreachable', r.detail);
    btn.innerHTML = orig;
    btn.disabled = false;
  }
}

function section(title, actionLabel, onAction, body) {
  return h('section.panel', null,
    h('div.panel-head', null,
      h('h2', null, title),
      h('span.spacer'),
      onAction ? h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: onAction }, icon('plus', 14), actionLabel) : null,
    ),
    h('div.panel-body', null, body),
  );
}

export function oversightView() {
  const body = h('div.view-body.scroll');
  const view = h('section.view', { 'aria-label': 'Oversight' },
    h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Oversight'),
      h('span.spacer'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: loadOversight }, icon('refresh', 14), 'Refresh'),
    ),
    body,
  );

  view.render = () => {
    const grid = h('div.grid-2');

    if (data.loading && !data.alerts.length) {
      mount(body, skeletonRows(5));
      return;
    }
    if (data.error && !data.alerts.length) {
      mount(body, errorState({ title: "Oversight didn't load", message: data.error.message, detail: data.error.detail, onRetry: loadOversight }));
      return;
    }

    // Live Activity Strip (derived from status)
    const s = store.status || {};
    grid.appendChild(section('Live Activity', null, null,
      h('div.stack', null,
        h('div.row', null, h('span', null, 'System Uptime'), h('span.t-meta.muted', null, `${Math.round((s.uptimeSec||0)/60)} min`)),
        h('div.row', null, h('span', null, 'KALKI Memory'), h('span.t-meta.muted', null, s.memUsz ? `${s.memUsz} MB` : 'N/A')),
        h('div.row', null, h('span', null, 'Provider'), h('span.t-meta.muted', null, store.models.current || 'auto'))
      )
    ));

    // Watched Sites
    grid.appendChild(section('Watched Sites', 'Add', addSite,
      data.watchedSites.length ? h('div.stack', null, ...data.watchedSites.map((w) => h('div.row', null,
        icon('globe', 16),
        h('span', { style: { flex: '1', minWidth: '0' } }, w.url),
        h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: (e) => checkSite(e.currentTarget, w.url) }, 'Check'),
        h('button.icon-btn', { type: 'button', onClick: () => removeSite(w.url) }, icon('close', 14))
      ))) : emptyState({ iconName: 'globe', title: 'No sites watched', body: 'Add URLs to get proactive alerts when they go down or SSL expires.' })
    ));

    // Thresholds
    grid.appendChild(section('Thresholds', null, null,
      h('div.stack', null,
        h('div.row', null, h('span', null, 'CPU Alert Level'), h('span.t-meta.muted', null, `${data.thresholds.cpu || 85}%`)),
        h('div.row', null, h('span', null, 'RAM Alert Level'), h('span.t-meta.muted', null, `${data.thresholds.ram || 85}%`)),
        h('div.row', null, h('span', null, 'Disk Warning'), h('span.t-meta.muted', null, `< ${data.thresholds.disk_gb || 5} GB`)),
        h('div.row', null, h('span', null, 'Battery Low'), h('span.t-meta.muted', null, `${data.thresholds.battery_low || 20}%`))
      )
    ));

    // Recent Alerts
    grid.appendChild(section('Recent Alerts', null, null,
      data.alerts.length ? h('div.stack', null, ...data.alerts.map((a) => h('div.row', null,
        icon(a.kind === 'battery' ? 'power' : a.kind === 'disk' ? 'drive' : a.kind === 'network' ? 'globe' : 'info', 16),
        h('span', { style: { flex: '1', minWidth: '0' } }, a.message),
        h('span.t-meta.muted', null, new Date(a.ts * 1000).toLocaleTimeString())
      ))) : emptyState({ iconName: 'check', title: 'No recent alerts', body: 'All systems normal.' })
    ));

    mount(body, grid);
  };

  view.addEventListener('kalki:view-enter', startPolling);
  view.addEventListener('kalki:view-leave', stopPolling);
  
  renderFn = view.render;
  return view;
}
