/** The one approval card: the exact content KALKI wants to act on, and Approve or Deny.
 *  Ask shows it in the conversation. Other screens show it under the top bar. */

import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';
import { decideApproval } from '../state/approvals.js';

export function approvalText(item) {
  return String(item?.description || item?.command || item?.text || item?.summary || '');
}

export function approvalCard(item, { position = 1, total = 1 } = {}) {
  let busy = false;
  const decide = async (decision, event) => {
    if (busy) return;
    busy = true;
    const card = event.currentTarget.closest('.approval');
    card?.querySelectorAll('button').forEach((b) => { b.disabled = true; });
    await decideApproval(item.id, decision);
    busy = false;
  };

  return h('section.approval', { 'aria-label': 'KALKI needs your approval' },
    h('div.approval-head', null,
      icon('alert', 15),
      h('strong', null, total > 1 ? `KALKI needs your approval (${position} of ${total})` : 'KALKI needs your approval'),
    ),
    h('div.approval-text', null, approvalText(item)),
    h('div.approval-actions', null,
      h('button.btn.gh', { type: 'button', onClick: (e) => decide('deny', e) }, 'Deny'),
      h('button.btn.pri', { type: 'button', onClick: (e) => decide('approve', e) }, 'Approve'),
    ),
  );
}
