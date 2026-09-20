/** Hyperscript + DOM helpers. No innerHTML anywhere — nodes are built, not parsed. */

/**
 * @param {string} tag  'div' or 'div.cls.cls2'
 * @param {object|null} props  attributes; on* become listeners, style takes an object
 * @param {...(Node|string|number|null|false|Array)} children
 */
export function h(tag, props, ...children) {
  const [name, ...classes] = tag.split('.');
  const el = name === 'svg' || name === 'path' || name === 'circle' || name === 'rect' || name === 'line' || name === 'polyline'
    ? document.createElementNS('http://www.w3.org/2000/svg', name)
    : document.createElement(name || 'div');
  if (classes.length) el.setAttribute('class', classes.join(' '));
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.setAttribute('class', [...classes, v].join(' '));
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k === 'dataset') Object.assign(el.dataset, v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'ref' && typeof v === 'function') v(el);
      else if (k === 'value' && 'value' in el) el.value = v;
      else if (k === 'checked' || k === 'disabled' || k === 'selected') { if (v) el.setAttribute(k, ''); el[k] = !!v; }
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    }
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const c of children.flat(4)) {
    if (c === null || c === undefined || c === false || c === true) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function frag(...children) {
  const f = document.createDocumentFragment();
  append(f, children);
  return f;
}

export function mount(container, ...nodes) {
  container.replaceChildren();
  append(container, nodes);
  return container;
}

export const qs = (sel, root = document) => root.querySelector(sel);
export const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function on(target, type, fn, opts) {
  target.addEventListener(type, fn, opts);
  return () => target.removeEventListener(type, fn, opts);
}

/** Auto-grow a textarea between min and max rows without layout thrash. */
export function autosize(ta, maxPx = 168) {
  const fit = () => { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, maxPx) + 'px'; };
  ta.addEventListener('input', fit);
  requestAnimationFrame(fit);
  return fit;
}

/** Keep a scroller pinned to the bottom only when the user is already near it. */
export function stickyScroll(el, threshold = 120) {
  let pinned = true;
  el.addEventListener('scroll', () => {
    pinned = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, { passive: true });
  return {
    get pinned() { return pinned; },
    toBottom(force) { if (force || pinned) el.scrollTop = el.scrollHeight; },
  };
}

export function debounce(fn, ms = 160) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

export async function withCheckmark(btn, p) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  const styleW = btn.style.width;
  if (!styleW) btn.style.width = btn.offsetWidth + 'px';
  try {
    const res = await p;
    if (res && res.ok === false) {
      btn.disabled = false;
      btn.innerHTML = orig;
      btn.style.width = styleW;
      return res;
    }
    btn.classList.add('is-success');
    btn.innerHTML = '&#10003;';
    setTimeout(() => { 
      btn.classList.remove('is-success'); 
      btn.innerHTML = orig; 
      btn.style.width = styleW;
      btn.disabled = false; 
    }, 2000);
    return res;
  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = orig;
    btn.style.width = styleW;
    throw err;
  }
}
