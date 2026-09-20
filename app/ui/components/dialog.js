/** Dialogs use the native <dialog> element with showModal().
 *
 *  showModal() promotes the dialog into the browser's top layer and makes the
 *  rest of the document inert, so Tab cannot escape and Escape closes for
 *  free. No hand-rolled focus trap — the most bug-prone piece of accessibility
 *  code simply does not exist here. Focus returns to the trigger on close. */

import { h, mount } from '../lib/dom.js';
import { icon } from '../lib/icons.js';

let lastTrigger = null;

/**
 * @param {{id?:string, title:string, description?:string, body:Node,
 *          actions?:Node[], width?:string, onClose?:Function, initialFocus?:string}} opts
 */
export function openDialog(opts) {
  lastTrigger = document.activeElement;
  const dlg = h('dialog', { id: opts.id, 'aria-labelledby': 'dlg-title', style: opts.width ? { width: opts.width } : null });

  const close = (reason) => {
    if (dlg.open) dlg.close(reason || 'dismiss');
  };

  mount(dlg,
    h('div.dialog-head', null,
      h('div', null,
        h('h2', { id: 'dlg-title' }, opts.title),
        opts.description ? h('p', null, opts.description) : null,
      ),
      h('span.spacer'),
      h('button.icon-btn', { type: 'button', 'aria-label': 'Close', onClick: () => close() }, icon('close', 18)),
    ),
    h('div.dialog-body', null, opts.body),
    opts.actions?.length ? h('div.dialog-foot', null, ...opts.actions) : null,
  );

  dlg.addEventListener('close', () => {
    opts.onClose?.(dlg.returnValue);
    dlg.remove();
    if (lastTrigger instanceof HTMLElement && document.contains(lastTrigger)) lastTrigger.focus();
  });
  // Click on the backdrop (outside the dialog box) dismisses.
  dlg.addEventListener('click', (e) => { if (e.target === dlg) close(); });

  document.body.appendChild(dlg);
  dlg.showModal();
  const first = opts.initialFocus ? dlg.querySelector(opts.initialFocus) : null;
  (first || dlg.querySelector('input, textarea, button:not(.icon-btn)'))?.focus();
  return { el: dlg, close };
}

/** Confirmation used for destructive actions. Resolves true/false. */
export function confirmDialog({ title, description, confirmLabel = 'Confirm', danger = true }) {
  return new Promise((resolve) => {
    let decided = false;
    const { close } = openDialog({
      title,
      description,
      width: '26rem',
      body: h('div'),
      actions: [
        h('button.btn.btn-secondary', { type: 'button', onClick: () => { decided = true; close(); resolve(false); } }, 'Cancel'),
        h(`button.btn.${danger ? 'btn-danger' : 'btn-primary'}`, {
          type: 'button', onClick: () => { decided = true; close(); resolve(true); },
        }, confirmLabel),
      ],
      onClose: () => { if (!decided) resolve(false); },
    });
  });
}

/** Simple prompt used for rename. Resolves the string or null. */
export function promptDialog({ title, label, value = '', confirmLabel = 'Save' }) {
  return new Promise((resolve) => {
    let input;
    let decided = false;
    const submit = () => { decided = true; const v = input.value.trim(); close(); resolve(v || null); };
    const { close } = openDialog({
      title,
      width: '26rem',
      body: h('div.field', null,
        h('label', { for: 'prompt-field' }, label),
        h('input.input', {
          id: 'prompt-field', value, ref: (el) => { input = el; },
          onKeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); submit(); } },
        }),
      ),
      actions: [
        h('button.btn.btn-secondary', { type: 'button', onClick: () => { decided = true; close(); resolve(null); } }, 'Cancel'),
        h('button.btn.btn-primary', { type: 'button', onClick: submit }, confirmLabel),
      ],
      initialFocus: '#prompt-field',
      onClose: () => { if (!decided) resolve(null); },
    });
  });
}
