import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { oversight, activity, approvals } from '../api/endpoints.js';
import { store } from '../state/store.js';
import { skeletonRows, errorState, emptyState } from '../components/states.js';
import { promptDialog } from '../components/dialog.js';
import { ok, err } from '../state/toasts.js';

let data = { loading: true, alerts: [], watchedSites: [], thresholds: {}, activityList: [], approvalsList: [] };
let timer;
let countdownTimer;
let renderFn = () => {};

export async function loadOversight() {
  data.loading = true;
  renderFn();
  const [r, actR, appR] = await Promise.all([
    oversight.status().catch(e => ({ok: false, message: e.message})),
    activity.list().catch(e => ({ok: false, message: e.message})),
    approvals.list().catch(e => ({ok: false, message: e.message}))
  ]);
  
  data.loading = false;
  if (r.ok) {
    data.alerts = r.data.alerts || [];
    data.watchedSites = r.data.watchedSites || [];
    data.thresholds = r.data.thresholds || {};
  } else {
    data.error = r;
    data.alerts = []; data.watchedSites = []; data.thresholds = {};
  }
  
  data.activityList = actR.ok ? (actR.data?.activity || actR.data?.items || actR.data?.log || (Array.isArray(actR.data) ? actR.data : [])) : [];
  data.approvalsList = appR.ok ? (appR.data?.approvals || appR.data?.items || (Array.isArray(appR.data) ? appR.data : [])) : [];
  
  renderFn();
}

function updateCountdowns() {
  const spans = document.querySelectorAll('.approval-countdown');
  spans.forEach(span => {
    const expiresAt = Number(span.dataset.expiresAt);
    const ms = expiresAt * 1000 - Date.now();
    if (ms <= 0) {
      span.textContent = 'Expired';
    } else {
      span.textContent = Math.ceil(ms / 1000) + 's';
    }
  });
}

function startPolling() {
  stopPolling();
  loadOversight();
  timer = setInterval(loadOversight, 5000);
  countdownTimer = setInterval(updateCountdowns, 1000);
}

function stopPolling() {
  clearInterval(timer);
  clearInterval(countdownTimer);
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

async function undoActivity(id) {
  const r = await activity.undo(id);
  if (r.ok) { ok('Action undone'); loadOversight(); } else err(r.message, r.detail);
}

async function decideApproval(id, decision) {
  const r = await approvals.decide(id, decision);
  if (r.ok) { ok(decision === 'approve' ? 'Approved' : 'Denied'); loadOversight(); } else err(r.message, r.detail);
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

function formatTimeLeft(expiresAt) {
  const ms = expiresAt * 1000 - Date.now();
  if (ms <= 0) return 'Expired';
  return Math.ceil(ms / 1000) + 's';
}

export function oversightView() {
  const view = h('section.work.view', { 'aria-label': 'Oversight' });

  const left = h('div.hud-left');
  const center = h('div.hud-center');
  const right = h('div.hud-right');
  
  mount(view, left, center, right);

  view.render = () => {
    left.innerHTML = '';
    center.innerHTML = '';
    right.innerHTML = '';

    if (data.loading && !data.alerts.length && !data.activityList.length && !data.approvalsList.length) {
      mount(center, skeletonRows(5));
      return;
    }
    if (data.error && !data.alerts.length && !data.activityList.length && !data.approvalsList.length) {
      mount(center, errorState({ title: "Oversight didn't load", message: data.error.message, detail: data.error.detail, onRetry: loadOversight }));
      return;
    }

    // Left HUD: Live Activity + Thresholds
    const s = store.status || {};
    mount(left, 
      section('Live Activity', null, null,
        h('div.stack', null,
          h('div.row', null, h('span', null, 'System Uptime'), h('span.t-meta.muted', null, `${Math.round((s.uptimeSec||0)/60)} min`)),
          h('div.row', null, h('span', null, 'KALKI Memory'), h('span.t-meta.muted', null, s.memUsz ? `${s.memUsz} MB` : 'N/A')),
          h('div.row', null, h('span', null, 'Provider'), h('span.t-meta.muted', null, store.models?.current || 'auto'))
        )
      ),
      h('div', {style:{height: 'var(--space-6)'}}),
      section('Thresholds', null, null,
        h('div.stack', null,
          h('div.row', null, h('span', null, 'CPU Alert Level'), h('span.t-meta.muted', null, `${data.thresholds.cpu || 85}%`)),
          h('div.row', null, h('span', null, 'RAM Alert Level'), h('span.t-meta.muted', null, `${data.thresholds.ram || 85}%`)),
          h('div.row', null, h('span', null, 'Disk Warning'), h('span.t-meta.muted', null, `< ${data.thresholds.disk_gb || 5} GB`)),
          h('div.row', null, h('span', null, 'Battery Low'), h('span.t-meta.muted', null, `${data.thresholds.battery_low || 20}%`))
        )
      )
    );

    // Center HUD: Header + Approvals + Activity Log
    const centerHead = h('header.view-head', null,
      h('h1', { tabindex: '-1', id: 'view-title' }, 'Oversight'),
      h('span.spacer'),
      h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: loadOversight }, icon('refresh', 14), 'Refresh'),
    );
    const centerBody = h('div.view-body.scroll', {style: {display: 'flex', flexDirection: 'column', gap: 'var(--space-6)'}});

    const approvalsSection = section('Pending Approvals', null, null,
      data.approvalsList.length ? h('div.stack', null, ...data.approvalsList.map(a => h('div.toolrun', {style: {borderColor: 'var(--warning-line)'}},
        h('div.toolrun-head', null,
          icon('alert-triangle', 16, {color: 'var(--warning-text)'}),
          h('span', {style: {fontWeight: 500}}, a.action || a.title || 'Risky Action'),
          h('span.spacer'),
          h('span.t-meta.muted.approval-countdown', { 'data-expires-at': a.expiresAt }, a.expiresAt ? formatTimeLeft(a.expiresAt) : 'Pending')
        ),
        a.description ? h('div', {style: {marginTop: 'var(--space-2)', color: 'var(--text-muted)'}}, a.description) : null,
        h('div', {style: {display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-4)'}},
          h('button.btn.btn-sm', {type: 'button', onClick: () => decideApproval(a.id, 'approve'), style: {background: 'var(--warning-bg)', color: 'var(--warning-text)', borderColor: 'var(--warning-line)'}}, 'Approve'),
          h('button.btn.btn-sm.btn-ghost', {type: 'button', onClick: () => decideApproval(a.id, 'deny')}, 'Deny')
        )
      ))) : emptyState({ iconName: 'check', title: 'No pending approvals', body: 'All secure.' })
    );

    const activitySection = section('Activity Log', null, null,
      data.activityList.length ? h('div.stack', null, ...data.activityList.map(act => h('div.row', {style: {alignItems: 'flex-start'}},
        h('div', {style: {flex: 1}},
          h('div', null, act.action || act.title || act.description || 'System action'),
          h('div.t-meta.muted', null, 
            act.source ? `Source: ${act.source} • ` : '',
            new Date((act.ts || Date.now() / 1000) * 1000).toLocaleTimeString()
          )
        ),
        act.reversible ? h('button.btn.btn-sm.btn-ghost', {type: 'button', onClick: () => undoActivity(act.id)}, 'Undo') : null
      ))) : emptyState({ iconName: 'list', title: 'No activity', body: 'Nothing to display.' })
    );

    mount(centerBody, approvalsSection, activitySection);
    mount(center, centerHead, centerBody);

    // Right HUD: Watched Sites + Recent Alerts
    mount(right,
      section('Watched Sites', 'Add', addSite,
        data.watchedSites.length ? h('div.stack', null, ...data.watchedSites.map((w) => h('div.row', null,
          icon('globe', 16),
          h('span', { style: { flex: '1', minWidth: '0' } }, w.url),
          h('button.btn.btn-sm.btn-ghost', { type: 'button', onClick: (e) => checkSite(e.currentTarget, w.url) }, 'Check'),
          h('button.icon-btn', { type: 'button', onClick: () => removeSite(w.url) }, icon('close', 14))
        ))) : emptyState({ iconName: 'globe', title: 'No sites watched', body: 'Add URLs to get proactive alerts when they go down or SSL expires.' })
      ),
      h('div', {style:{height: 'var(--space-6)'}}),
      section('Recent Alerts', null, null,
        data.alerts.length ? h('div.stack', null, ...data.alerts.map((a) => h('div.row', null,
          icon(a.kind === 'battery' ? 'power' : a.kind === 'disk' ? 'drive' : a.kind === 'network' ? 'globe' : 'info', 16),
          h('span', { style: { flex: '1', minWidth: '0' } }, a.message),
          h('span.t-meta.muted', null, new Date((a.ts || Date.now() / 1000) * 1000).toLocaleTimeString())
        ))) : emptyState({ iconName: 'check', title: 'No recent alerts', body: 'All systems normal.' })
      )
    );
  };

  view.addEventListener('kalki:view-enter', startPolling);
  view.addEventListener('kalki:view-leave', stopPolling);
  
  renderFn = view.render;
  return view;
}
