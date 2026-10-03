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
      span.textContent = 'expires in ' + Math.ceil(ms / 1000) + ' s';
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
    btn.classList.add('ok');
    btn.innerHTML = '&#10003;';
    setTimeout(() => { btn.classList.remove('ok'); btn.innerHTML = orig; btn.disabled = false; }, 2000);
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

function formatTimeLeft(expiresAt) {
  const ms = expiresAt * 1000 - Date.now();
  if (ms <= 0) return 'Expired';
  return Math.ceil(ms / 1000) + 's';
}

function formatTime(ts) {
  return new Date((ts || Date.now() / 1000) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function oversightView() {
  const main = h('div.pad', { 'aria-label': 'Oversight' });
  const aside = h('div', { style: { display: 'contents' } });

  main.addEventListener('kalki:view-enter', startPolling);
  main.addEventListener('kalki:view-leave', stopPolling);

  function render() {
    if (data.loading && !data.alerts.length && !data.activityList.length && !data.approvalsList.length) {
      mount(main, skeletonRows(5));
      mount(aside);
      return;
    }
    if (data.error && !data.alerts.length && !data.activityList.length && !data.approvalsList.length) {
      mount(main, errorState({ title: "Oversight didn't load", message: data.error.message, detail: data.error.detail, onRetry: loadOversight }));
      mount(aside);
      return;
    }

    mount(main,
      h('div.hd', null,
        h('div', null,
          h('h1', null, 'Oversight'),
          h('div.sub', null, 'KALKI watches in the background and tells you when something needs you.')
        ),
        h('button.btn.pri', { onClick: addSite }, h('i', { 'data-i': 'plus' }), 'Watch a site')
      ),
      h('div.grid2', null,
        h('div.card', null,
          h('div.row.sb', null, h('h2', null, 'Watched sites'), h('span.xs.mut', null, `${data.watchedSites.length} sites`)),
          ...data.watchedSites.map(w => 
            h('div.li', null,
              h('div', { style: { flex: '1' } },
                h('div.nm', null, w.url),
                h('div.xs.mut', null, w.status_text || 'Active')
              ),
              h('button.btn.btn-sm.gh', { onClick: (e) => checkSite(e.currentTarget, w.url) }, 'Check'),
              h('button.ib', { onClick: () => removeSite(w.url), title: 'Remove' }, h('i', {'data-i': 'trash'})),
              h('span.chip', { class: w.status === 'down' ? 'dng' : 'ok' }, w.status === 'down' ? 'Down' : 'Up')
            )
          )
        ),
        h('div.card', null,
          h('div.row.sb', null, h('h2', null, 'Recent alerts'), h('button.btn.gh', { style: { height: '22px' }, onClick: () => { data.alerts = []; renderFn(); } }, 'Clear')),
          ...data.alerts.map(a => 
            h('div.li', null,
              h('span.chip', { class: a.level === 'High' ? 'dng' : a.level === 'Medium' ? 'warn' : '' }, a.level || 'Info'),
              h('span.sm', { style: { flex: '1' } }, a.message),
              h('span.xs.mut', null, formatTime(a.ts))
            )
          )
        )
      ),
      h('div.grid2', { style: { marginTop: '14px' } },
        h('div.card', null,
          h('div.row.sb', null, h('h2', null, 'Waiting for you'), h('span.chip.warn', null, `${data.approvalsList.length} approvals`)),
          ...data.approvalsList.map(a => 
            h('div.li.new', { style: { paddingLeft: '10px' } },
              h('div', { style: { flex: '1' } },
                h('div.nm', null, a.action || a.title),
                h('div.xs.mut.approval-countdown', { 'data-expires-at': a.expiresAt }, a.description ? `${a.description} ╖ expires in ${formatTimeLeft(a.expiresAt)}` : `expires in ${formatTimeLeft(a.expiresAt)}`),
                h('div.meter', { style: { marginTop: '6px' } }, h('i', { style: { width: '80%' } }))
              ),
              h('button.btn.gh', { onClick: () => decideApproval(a.id, 'deny') }, 'Deny'),
              h('button.btn.pri', { onClick: () => decideApproval(a.id, 'approve') }, 'Approve')
            )
          )
        ),
        h('div.card', null,
          h('div.row.sb', null, h('h2', null, 'What KALKI did'), h('span.row.g4', null, h('span.chip', null, 'All'), h('span.chip', null, 'Reversible'))),
          ...data.activityList.map(act => 
            h('div.li.tl' + (act.reversible ? '.u' : ''), null,
              h('span.mono.xs.mut', { style: { width: '38px' } }, formatTime(act.ts)),
              h('span.sm', { style: { flex: '1' } }, act.action || act.title || act.description),
              act.reversible ? h('button.btn.gh', { style: { height: '22px' }, onClick: () => undoActivity(act.id) }, 'Undo') : null
            )
          )
        )
      ),
      h('div.card', { style: { marginTop: '14px' } },
        h('h2', null, 'Alert thresholds'),
        h('div.grid3', { style: { marginTop: '10px' } },
          h('div.col.g8', null,
            h('div.row.sb', null, h('span.sm', null, 'CPU'), h('span.mono.xs', null, `${data.thresholds.cpu || 85}%`)),
            h('div.meter', null, h('i', { style: { width: `${data.thresholds.cpu || 85}%` } }))
          ),
          h('div.col.g8', null,
            h('div.row.sb', null, h('span.sm', null, 'Memory'), h('span.mono.xs', null, `${data.thresholds.ram || 85}%`)),
            h('div.meter', null, h('i', { style: { width: `${data.thresholds.ram || 85}%` } }))
          ),
          h('div.col.g8', null,
            h('div.row.sb', null, h('span.sm', null, 'Disk'), h('span.mono.xs', null, `${data.thresholds.disk_gb || 5} GB`)),
            h('div.meter', null, h('i', { style: { width: `${Math.min(100, (data.thresholds.disk_gb || 5) * 10)}%` } }))
          )
        )
      )
    );

    const s = store.status || {};
    mount(aside,
      h('h1', { style: { fontSize: '16px' } }, 'Health'),
      h('div.card.col.g12', null,
        h('div.row.sb', null, h('span.sm', null, 'Local service'), h('span.chip.ok', null, 'Running')),
        h('div.row.sb', null, h('span.sm', null, 'Provider'), h('span.chip.ok', null, store.models?.current || 'Connected')),
        h('div.row.sb', null, h('span.sm', null, 'Uptime'), h('span.chip.ok', null, `${Math.round((s.uptimeSec||0)/60)} min`)),
        h('div.row.sb', null, h('span.sm', null, 'Memory'), h('span.chip.ok', null, s.memUsz ? `${s.memUsz} MB` : 'N/A'))
      ),
      h('div.card.col.g8', null,
        h('h2', null, 'Diagnostics'),
        h('pre', { style: { fontSize: '11px', lineHeight: '16px' } }, store.diagnosticsText || '14:02 status ok\n14:01 watch: finmate down\n13:58 clipboard prompt\n13:40 tts ok 212 ms')
      )
    );
  }

  renderFn = render;
  return { main, aside, render };
}
