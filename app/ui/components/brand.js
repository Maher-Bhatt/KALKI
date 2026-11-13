/** KALKI's mark and the ink-wash mountains behind the greeting. Both are drawn here, in
 *  the page's own colours, so they follow the light and dark themes. */

import { h } from '../lib/dom.js';

const NS = 'http://www.w3.org/2000/svg';

function svg(tag, attrs, ...children) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, String(v));
  for (const c of children) if (c) el.appendChild(c);
  return el;
}

/** Two peaks: the K of KALKI read as a mountain. */
export function brandMark(size = 22) {
  return svg('svg', { viewBox: '0 0 24 24', width: size, height: size, fill: 'none', 'aria-hidden': 'true', class: 'brand-mark' },
    svg('path', { d: 'M2.5 20 10 5.5 17.5 20', stroke: 'currentColor', 'stroke-width': 2.1, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }),
    svg('path', { d: 'M9.5 20 15.2 9.6 21.5 20', stroke: 'currentColor', 'stroke-width': 2.1, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', opacity: 0.55 }),
  );
}

export function brand() {
  return h('div.brand', null, brandMark(24), h('span.brand-name', null, 'KALKI', h('span.brand-ai', null, ' AI')));
}

let artId = 0;

/** Layered ridges in ink wash, fading into mist at the left and bottom. */
export function mountainArt() {
  artId += 1;
  const fade = `kalki-fade-${artId}`;
  const mist = `kalki-mist-${artId}`;
  const mask = `kalki-mask-${artId}`;
  const ridge = (d, opacity) => svg('path', { d, fill: 'currentColor', opacity });
  return svg('svg', { viewBox: '0 0 640 300', class: 'mountain-art', 'aria-hidden': 'true', preserveAspectRatio: 'xMaxYMin slice' },
    svg('defs', null,
      svg('linearGradient', { id: fade, x1: 0, y1: 0, x2: 1, y2: 0 },
        svg('stop', { offset: '0', 'stop-color': '#fff', 'stop-opacity': 0 }),
        svg('stop', { offset: '0.45', 'stop-color': '#fff', 'stop-opacity': 0.9 }),
        svg('stop', { offset: '1', 'stop-color': '#fff', 'stop-opacity': 1 })),
      svg('linearGradient', { id: mist, x1: 0, y1: 0, x2: 0, y2: 1 },
        svg('stop', { offset: '0', class: 'mist-stop', 'stop-opacity': 0 }),
        svg('stop', { offset: '1', class: 'mist-stop', 'stop-opacity': 0.9 })),
      svg('mask', { id: mask },
        svg('rect', { x: 0, y: 0, width: 640, height: 300, fill: `url(#${fade})` })),
    ),
    svg('g', { mask: `url(#${mask})` },
      svg('circle', { cx: 470, cy: 70, r: 34, fill: 'currentColor', opacity: 0.05 }),
      ridge('M120 210 C170 190 205 160 250 150 C290 140 310 112 345 92 C362 82 372 66 392 52 C404 44 414 46 424 58 C440 76 452 90 474 98 C500 108 520 128 548 132 C580 136 610 150 640 160 L640 300 L120 300 Z', 0.13),
      ridge('M392 52 C398 70 392 84 404 96 C414 106 410 118 420 128 L428 96 C432 84 426 70 424 58 Z', 0.12),
      ridge('M60 250 C120 236 170 214 220 206 C270 198 300 176 340 166 C380 156 400 142 432 138 C466 134 488 152 520 162 C556 174 600 178 640 190 L640 300 L60 300 Z', 0.16),
      ridge('M0 284 C80 268 150 256 220 252 C300 248 340 232 400 226 C470 220 520 236 580 240 C606 242 624 246 640 250 L640 300 L0 300 Z', 0.2),
      svg('rect', { x: 0, y: 150, width: 640, height: 150, fill: `url(#${mist})`, class: 'mountain-mist' }),
    ),
  );
}
