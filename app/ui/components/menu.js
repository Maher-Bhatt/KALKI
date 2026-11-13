/** A small popup menu, opened from a button.
 *
 *  Items are { label, icon, hint, danger, run }, or { info, detail } for a line of text,
 *  or 'rule' for a divider. Arrow keys move between items, Escape closes and returns
 *  focus to the button, and clicking elsewhere closes it. */

import { h } from '../lib/dom.js';
import { icon } from '../lib/icons.js';

let closeOpenMenu = null;

export function openMenu(anchor, items, { align = 'right' } = {}) {
  closeOpenMenu?.();

  const close = (refocus = false) => {
    menu.remove();
    anchor.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', onOutside, true);
    window.removeEventListener('resize', onResize);
    closeOpenMenu = null;
    if (refocus) anchor.focus();
  };

  const rows = items.filter(Boolean).map((item) => {
    if (item === 'rule') return h('div.menu-rule', { role: 'separator' });
    if (item.info) return h('div.menu-info', null, h('strong', null, item.info), item.detail || null);
    return h('button.menu-item' + (item.danger ? '.dng' : ''), {
      type: 'button',
      role: 'menuitem',
      onClick: () => { close(true); item.run?.(); },
    }, item.icon ? icon(item.icon, 15) : null, item.label, item.hint ? h('span.menu-hint', null, item.hint) : null);
  });

  const menu = h('div.menu', { role: 'menu' }, ...rows);

  menu.addEventListener('keydown', (e) => {
    const buttons = [...menu.querySelectorAll('.menu-item')];
    const at = buttons.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(true); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); buttons[(at + 1) % buttons.length]?.focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); buttons[(at - 1 + buttons.length) % buttons.length]?.focus(); }
    else if (e.key === 'Home') { e.preventDefault(); buttons[0]?.focus(); }
    else if (e.key === 'End') { e.preventDefault(); buttons[buttons.length - 1]?.focus(); }
  });

  function onOutside(e) {
    if (!menu.contains(e.target) && !anchor.contains(e.target)) close();
  }
  function onResize() { close(); }

  document.body.appendChild(menu);
  const box = anchor.getBoundingClientRect();
  const width = menu.offsetWidth;
  const left = align === 'right' ? box.right - width : box.left;
  menu.style.left = `${Math.max(8, Math.min(left, window.innerWidth - width - 8))}px`;
  const below = box.bottom + 6;
  const fitsBelow = below + menu.offsetHeight < window.innerHeight - 8;
  menu.style.top = `${fitsBelow ? below : Math.max(8, box.top - menu.offsetHeight - 6)}px`;

  anchor.setAttribute('aria-expanded', 'true');
  document.addEventListener('pointerdown', onOutside, true);
  window.addEventListener('resize', onResize);
  closeOpenMenu = close;
  menu.querySelector('.menu-item')?.focus();
  return close;
}
