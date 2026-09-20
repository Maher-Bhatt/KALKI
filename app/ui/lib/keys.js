/** Global shortcut registry. One keydown listener for the whole app. */

const bindings = new Map();

const norm = (e) => [
  e.ctrlKey || e.metaKey ? 'mod' : '',
  e.shiftKey ? 'shift' : '',
  e.altKey ? 'alt' : '',
  e.key.length === 1 ? e.key.toLowerCase() : e.key,
].filter(Boolean).join('+');

/** @param {string} combo e.g. 'mod+k', 'mod+shift+m', 'Escape' */
export function bind(combo, handler, { description = '', allowInInput = false } = {}) {
  bindings.set(combo, { handler, description, allowInInput });
  return () => bindings.delete(combo);
}

export function shortcuts() {
  return [...bindings.entries()].map(([combo, b]) => ({ combo, description: b.description })).filter((s) => s.description);
}

export function label(combo) {
  const mod = navigator.platform?.toLowerCase().includes('mac') ? '⌘' : 'Ctrl';
  return combo.replace('mod', mod).split('+').map((p) => p.length === 1 ? p.toUpperCase() : p).join(' ');
}

export function install() {
  window.addEventListener('keydown', (e) => {
    const b = bindings.get(norm(e));
    if (!b) return;
    const t = e.target;
    const inField = t instanceof HTMLElement &&
      (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
    if (inField && !b.allowInInput) return;
    e.preventDefault();
    b.handler(e);
  });
}
