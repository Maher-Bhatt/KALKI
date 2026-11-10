/** Hash routing.
 *
 *  Hash rather than the History API because KALKI is also loaded from file://
 *  in the Linux and recovery paths, where pushState is unreliable. On every
 *  change focus moves to the destination heading and the route is announced. */

import { store, notify } from '../state/store.js';

const ROUTES = ['ask', 'today', 'memory', 'workbench', 'oversight', 'security', 'settings'];
let announcer = null;

export function setAnnouncer(el) { announcer = el; }

export function parse() {
  const raw = (location.hash || '#/ask').replace(/^#\/?/, '');
  const [name, ...rest] = raw.split('/');
  const route = ROUTES.includes(name) ? name : 'ask';
  const params = {};
  if (route === 'ask' && rest[0]) params.threadId = rest[0];
  if (route === 'settings' && rest[0]) params.section = rest[0];
  return { name: route, params };
}

export function go(name, params = {}) {
  const tail = params.threadId || params.section || '';
  location.hash = `#/${name}${tail ? '/' + tail : ''}`;
}

export function startRouter(onChange) {
  const apply = () => {
    store.route = parse();
    notify();
    onChange(store.route);
    requestAnimationFrame(() => {
      const heading = document.getElementById('view-title');
      heading?.focus({ preventScroll: true });
      if (announcer) announcer.textContent = heading ? `${heading.textContent}` : '';
    });
  };
  window.addEventListener('hashchange', apply);
  apply();
}

export { ROUTES };
