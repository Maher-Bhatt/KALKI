/** One icon system: 20px grid, 1.5px stroke, currentColor, no external files.
 *  Icon-only controls must always carry an aria-label; icons are aria-hidden. */

const P = {
  ask:      'M4 15.5 2.5 18.5l3-1.5A7.5 7.5 0 1 1 4 15.5Z',
  today:    'M4 5.5h12v11H4zM4 8.5h12M7.5 3v3M12.5 3v3',
  memory:   'M10 3.5c-2 0-3 1.2-3 2.6 0 .4-.3.6-.7.8-1.1.5-1.8 1.5-1.8 2.7 0 1 .5 1.9 1.3 2.4M10 3.5c2 0 3 1.2 3 2.6 0 .4.3.6.7.8 1.1.5 1.8 1.5 1.8 2.7 0 1-.5 1.9-1.3 2.4M10 3.5v13M5.8 12c0 1.6 1.2 2.8 2.8 2.8M14.2 12c0 1.6-1.2 2.8-2.8 2.8',
  workbench:'M7.5 3.5 3.5 10l4 6.5M12.5 3.5 16.5 10l-4 6.5',
  security: 'M10 2.8 4.5 5v4.5c0 3.4 2.3 6.4 5.5 7.4 3.2-1 5.5-4 5.5-7.4V5Z',
  settings: 'M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM16.2 12a1.4 1.4 0 0 0 .3 1.5l.1.1a1.7 1.7 0 1 1-2.4 2.4l-.1-.1a1.4 1.4 0 0 0-2.3 1v.2a1.7 1.7 0 1 1-3.4 0v-.1a1.4 1.4 0 0 0-2.4-1l-.1.1a1.7 1.7 0 1 1-2.4-2.4l.1-.1a1.4 1.4 0 0 0-1-2.3h-.2a1.7 1.7 0 1 1 0-3.4h.1a1.4 1.4 0 0 0 1-2.4l-.1-.1a1.7 1.7 0 1 1 2.4-2.4l.1.1a1.4 1.4 0 0 0 1.5.3h.1a1.4 1.4 0 0 0 .9-1.3v-.2a1.7 1.7 0 1 1 3.4 0v.1a1.4 1.4 0 0 0 2.3 1l.1-.1a1.7 1.7 0 1 1 2.4 2.4l-.1.1a1.4 1.4 0 0 0 1 2.3h.2a1.7 1.7 0 1 1 0 3.4h-.1a1.4 1.4 0 0 0-1.3.9Z',
  mic:      'M10 3.5a2 2 0 0 1 2 2v4.5a2 2 0 1 1-4 0V5.5a2 2 0 0 1 2-2ZM5 9.5a5 5 0 0 0 10 0M10 14.5v3',
  micOff:   'M12 5.5a2 2 0 0 0-4 0v1M8 10.3v-.3M5 9.5a5 5 0 0 0 7.6 4.3M15 9.5V10M10 14.5v3M3.5 3.5l13 13',
  plus:     'M10 4.5v11M4.5 10h11',
  send:     'M3.5 10 16.5 4l-3 6 3 6Z',
  stop:     'M6.5 6.5h7v7h-7z',
  close:    'M5 5l10 10M15 5L5 15',
  copy:     'M7.5 7.5h8v8h-8zM12.5 7.5v-3h-8v8h3',
  refresh:  'M16 5v3.5h-3.5M4 15v-3.5h3.5M15.3 8.5A5.7 5.7 0 0 0 5.3 6.8M4.7 11.5a5.7 5.7 0 0 0 10 1.7',
  edit:     'M4 16h3l8.2-8.2a1.8 1.8 0 0 0-2.5-2.5L4.5 13.5Z',
  trash:    'M4.5 6h11M8 6V4.5h4V6M6 6v9.5h8V6M8.5 8.5v5M11.5 8.5v5',
  check:    'M4.5 10.5l3.5 3.5 7.5-8',
  flag:     'M5 17V4h9l-2 3 2 3H5',
  search:   'M9 15A6 6 0 1 0 9 3a6 6 0 0 0 0 12ZM13.5 13.5 17 17',
  pin:      'M8 3.5h4l-.5 4 2.5 2.5H6L8.5 7.5ZM10 10v6.5',
  attach:   'M15 9.5l-5.5 5.5a3.5 3.5 0 0 1-5-5l6-6a2.3 2.3 0 0 1 3.3 3.3l-6 6a1.2 1.2 0 0 1-1.6-1.6l5.3-5.3',
  screen:   'M3.5 4.5h13v9h-13zM7 16.5h6',
  play:     'M6.5 4.5 15 10l-8.5 5.5Z',
  pause:    'M7 5v10M13 5v10',
  next:     'M6 5l6 5-6 5ZM14 5v10',
  info:     'M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM10 9v5M10 6.2v.3',
  alert:    'M10 6.5v4.5M10 13.7v.3M9 3.4 2.6 15a1.1 1.1 0 0 0 1 1.7h12.8a1.1 1.1 0 0 0 1-1.7L11 3.4a1.1 1.1 0 0 0-2 0Z',
  chevron:  'M8 6l4 4-4 4',
  chevronD: 'M6 8l4 4 4-4',
  panel:    'M3.5 4.5h13v11h-13zM12.5 4.5v11',
  clock:    'M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM10 6v4.2l2.8 1.8',
  mail:     'M3.5 5.5h13v9h-13zM3.5 6l6.5 4.5L16.5 6',
  calendar: 'M4 5.5h12v11H4zM4 8.5h12M7.5 3v3M12.5 3v3M7 11.5h2',
  note:     'M5 3.5h7L15 6.5v10H5zM12 3.5v3.2h3',
  code:     'M7.5 7 5 10l2.5 3M12.5 7 15 10l-2.5 3',
  flow:     'M4 5.5h4v3H4zM12 5.5h4v3h-4zM8 7h4M6 8.5v4.5h8V11.5M10 13v3.5',
  spark:    'M10 3.5 11.4 8l4.6 1.5L11.4 11 10 15.5 8.6 11 4 9.5 8.6 8Z',
  link:     'M8.5 11.5a3 3 0 0 0 4.3 0l2.2-2.2a3 3 0 0 0-4.3-4.3l-1.2 1.2M11.5 8.5a3 3 0 0 0-4.3 0L5 10.7a3 3 0 0 0 4.3 4.3l1.2-1.2',
  offline:  'M3.5 3.5l13 13M6.4 12.3a5 5 0 0 1 2-1.5M3.5 9.4a9 9 0 0 1 3-2M16.5 9.4a9 9 0 0 0-6.8-2.4M9.4 15.2l.6.6.6-.6',
  vault:    'M3.5 4.5h13v11h-13zM10 7.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM10 12.5V15',
  download: 'M10 3.5v9M6.5 9.5 10 13l3.5-3.5M4 16.5h12',
  dots:     'M5 10h.01M10 10h.01M15 10h.01',
  prev:     'M14 5l-6 5 6 5ZM6 5v10',
  up:       'M10 16V5M5.5 9.5 10 5l4.5 4.5',
  music:    'M8 14.5V5l7-1.5V12M8 14.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM15 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z',
  cpu:      'M6.5 6.5h7v7h-7zM8.5 3.5v3M11.5 3.5v3M8.5 13.5v3M11.5 13.5v3M3.5 8.5h3M3.5 11.5h3M13.5 8.5h3M13.5 11.5h3',
  layers:   'M10 3 3 6.5 10 10l7-3.5ZM3 10l7 3.5 7-3.5M3 13.5 10 17l7-3.5',
  term:     'M4 5.5l4.5 4.5L4 14.5M10.5 15h5.5',
  act:      'M17.5 10h-3l-2.2 5.5-4.6-11L5.5 10h-3',
  sliders:  'M4 16v-5M4 7V4M10 16V9M10 6V4M16 16v-3M16 9V4M2 11h4M8 6h4M14 13h4',
  sun:      'M10 13.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM10 2v1.5M10 16.5V18M3.5 3.5l1 1M15.5 15.5l1 1M2 10h1.5M16.5 10H18M3.5 16.5l1-1M15.5 4.5l1-1',
  battery:  'M3 6.5h12v7H3zM15 9v2h2V9z',
  eye:      'M2.5 10S5.5 4.5 10 4.5 17.5 10 17.5 10 14.5 15.5 10 15.5 2.5 10 2.5 10ZM10 12.2a2.2 2.2 0 1 0 0-4.4 2.2 2.2 0 0 0 0 4.4Z',
  undo:     'M7 5 3.5 8.5 7 12M3.5 8.5H12a4.5 4.5 0 0 1 0 9H8',
  volume:   'M3.5 7.5h3.5l4-3.5v12l-4-3.5H3.5zM14.5 7.5a4 4 0 0 1 0 5M16.5 5.5a7 7 0 0 1 0 9',
  volumeOff:'M3.5 7.5h3.5l4-3.5v12l-4-3.5H3.5zM14 8l4 4M18 8l-4 4',
  pet:      'M10 14c-2.2 0-3.8-1.2-3.8-2.6 0-1.5 1.6-2.6 3.8-2.6s3.8 1.1 3.8 2.6c0 1.4-1.6 2.6-3.8 2.6ZM5.5 8a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8.5 5.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM11.5 5.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM14.5 8a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z',
  heart:    'M10 16.5s-6-3.8-6-7.5a3.5 3.5 0 0 1 6-2.3 3.5 3.5 0 0 1 6 2.3c0 3.7-6 7.5-6 7.5Z',
  food:     'M3.5 9h13c-.5 4.5-4 7-6.5 7s-6-2.5-6.5-7ZM7 5.5v1.5M10 4.5v2.5M13 5.5v1.5',
  ball:     'M10 17.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM4.5 10a7.5 7.5 0 0 1 7.5-7.5M15.5 10a7.5 7.5 0 0 1-7.5 7.5',
  export:   'M4 11.5v4a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-4M10 3.5v9M6.5 7 10 3.5 13.5 7',
  sparkles: 'M10 2.5 11.2 6.5 15.2 7.7 11.2 8.9 10 12.9 8.8 8.9 4.8 7.7 8.8 6.5ZM15 13.5 15.6 15.5 17.6 16.1 15.6 16.7 15 18.7 14.4 16.7 12.4 16.1 14.4 15.5Z',
};

/* The Filament v2 screens (and the design they were built from) name a few
 * icons differently from the original set. Resolve them here once instead of
 * letting an unknown name fall through to the info glyph. */
const ALIAS = {
  msg: 'ask', pen: 'edit', ref: 'refresh', chev: 'chevronD', mon: 'screen', clip: 'attach',
  x: 'close', check2: 'check', today2: 'today', stopped: 'stop', chat: 'ask',
  speaker: 'volume', sound: 'volume', paw: 'pet', love: 'heart', treat: 'food',
};

/** @param {keyof P} name */
export function icon(name, size = 20) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 20 20');
  svg.setAttribute('width', String(size));
  svg.setAttribute('height', String(size));
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.5');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', P[name] || P[ALIAS[name]] || P.info);
  svg.appendChild(path);
  return svg;
}

export const iconNames = Object.keys(P);

/** Turn <i data-i="name"> markers into real icons, now and whenever a view
 *  renders new ones. Views written against the design use these markers; this
 *  keeps them working without every call site importing icon(). */
export function hydrateIcons(root = document.body) {
  const swap = (scope) => {
    scope.querySelectorAll?.('i[data-i]').forEach((el) => {
      const svg = icon(el.dataset.i, Number(el.dataset.size) || 16);
      if (el.className) svg.setAttribute('class', el.className);
      if (el.getAttribute('style')) svg.setAttribute('style', el.getAttribute('style'));
      el.replaceWith(svg);
    });
  };
  swap(root);
  const obs = new MutationObserver((muts) => {
    for (const m of muts) {
      for (const n of m.addedNodes) {
        if (n.nodeType !== 1) continue;
        if (n.tagName === 'I' && n.dataset.i) {
          const svg = icon(n.dataset.i, Number(n.dataset.size) || 16);
          if (n.className) svg.setAttribute('class', n.className);
          if (n.getAttribute('style')) svg.setAttribute('style', n.getAttribute('style'));
          n.replaceWith(svg);
        } else if (n.querySelector && n.querySelector('i[data-i]')) {
          swap(n);
        }
      }
    }
  });
  obs.observe(root, { childList: true, subtree: true });
  return obs;
}
