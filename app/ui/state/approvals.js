/** Waiting approvals, shared by the top of every screen and the Ask conversation. */

import { approvals as api } from '../api/endpoints.js';
import { store, notify } from './store.js';
import { refreshStatus } from './status.js';
import { ok, err } from './toasts.js';

let knownCount = -1;

export function waitingApprovals() {
  return store.approvals || [];
}

export async function loadApprovals() {
  const r = await api.list();
  store.approvals = r.ok ? (r.data.approvals || []) : [];
  notify();
}

/** Call on every status update: reloads only when the number waiting has changed. */
export function syncApprovals() {
  const count = store.status?.pendingApprovals || 0;
  if (count !== knownCount) {
    knownCount = count;
    loadApprovals();
  }
}

function outcomeText(decision, data) {
  if (decision !== 'approve') return 'Denied';
  const result = Array.isArray(data?.result) ? data.result[1] : data?.result;
  return result ? String(result).slice(0, 160) : 'Approved';
}

export async function decideApproval(id, decision) {
  const r = await api.decide(id, decision);
  if (r.ok) ok(outcomeText(decision, r.data));
  else err(r.detail || r.message);
  await loadApprovals();
  refreshStatus();
}
