/** Streaming-safe markdown → DOM.
 *  Builds nodes (never innerHTML) so model output can never inject markup.
 *  An unterminated ``` fence is held back as plain text until the closing
 *  fence arrives, which stops half-parsed code blocks flickering mid-stream. */

import { h, append } from './dom.js';
import { icon } from './icons.js';

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(\[[^\]]+\]\([^)\s]+\))|(https?:\/\/[^\s<>)]+)/g;

function inline(text) {
  const out = [];
  let last = 0;
  for (const m of String(text).matchAll(INLINE)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith('`')) out.push(h('code', null, t.slice(1, -1)));
    else if (t.startsWith('**')) out.push(h('strong', null, t.slice(2, -2)));
    else if (t.startsWith('*')) out.push(h('em', null, t.slice(1, -1)));
    else if (t.startsWith('[')) {
      const cut = t.indexOf('](');
      out.push(h('a', { href: t.slice(cut + 2, -1), target: '_blank', rel: 'noreferrer noopener' }, t.slice(1, cut)));
    } else out.push(h('a', { href: t, target: '_blank', rel: 'noreferrer noopener' }, t));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function codeBlock(lang, code, onCopy) {
  return h('div.code-block', null,
    h('header', null,
      h('span', null, lang || 'text'),
      h('span.spacer'),
      h('button.icon-btn', {
        type: 'button', 'aria-label': 'Copy code', title: 'Copy code',
        onClick: (e) => { navigator.clipboard?.writeText(code); onCopy?.(e.currentTarget); },
      }, icon('copy', 16)),
    ),
    h('pre', null, h('code', null, code)),
  );
}

function table(rows) {
  const [head, ...body] = rows;
  return h('table', null,
    h('thead', null, h('tr', null, ...head.map((c) => h('th', null, ...inline(c))))),
    h('tbody', null, ...body.map((r) => h('tr', null, ...r.map((c) => h('td', null, ...inline(c)))))),
  );
}

const cells = (line) => line.replace(/^\||\|$/g, '').split('|').map((s) => s.trim());

/**
 * @param {string} src raw markdown, possibly mid-stream
 * @param {{streaming?: boolean, onCopy?: Function}} opts
 * @returns {DocumentFragment}
 */
export function renderMarkdown(src, opts = {}) {
  const frag = document.createDocumentFragment();
  const lines = String(src ?? '').split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trimStart().startsWith('```')) {
      const lang = line.trim().slice(3).trim();
      const buf = [];
      let closed = false;
      i++;
      while (i < lines.length) {
        if (lines[i].trimStart().startsWith('```')) { closed = true; i++; break; }
        buf.push(lines[i]); i++;
      }
      if (!closed && opts.streaming) {
        // Fence still open — show the text plainly rather than a broken block.
        frag.appendChild(h('p.dim.t-mono', null, buf.join('\n')));
      } else {
        frag.appendChild(codeBlock(lang, buf.join('\n'), opts.onCopy));
      }
      continue;
    }

    if (!line.trim()) { i++; continue; }

    const head = /^(#{1,6})\s+(.*)$/.exec(line);
    if (head) {
      frag.appendChild(h(`h${Math.min(3, head[1].length)}`, null, ...inline(head[2])));
      i++; continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^\s*>\s?/, '')); i++; }
      frag.appendChild(h('blockquote', null, ...inline(buf.join(' '))));
      continue;
    }

    if (/^\s*([-*+]|\d+[.)])\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, '')); i++;
      }
      frag.appendChild(h(ordered ? 'ol' : 'ul', null, ...items.map((t) => h('li', null, ...inline(t)))));
      continue;
    }

    if (line.includes('|') && lines[i + 1] && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
      const rows = [cells(line)];
      i += 2;
      while (i < lines.length && lines[i].includes('|')) { rows.push(cells(lines[i])); i++; }
      frag.appendChild(table(rows));
      continue;
    }

    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) { frag.appendChild(h('hr.divider')); i++; continue; }

    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\s*>|\s*([-*+]|\d+[.)])\s)/.test(lines[i]) && !lines[i].trimStart().startsWith('```')) {
      buf.push(lines[i]); i++;
    }
    if (buf.length) frag.appendChild(h('p', null, ...inline(buf.join(' '))));
    else i++;
  }

  return frag;
}

/** Plain text for copy-to-clipboard and live-region announcements. */
export function toPlain(src) {
  return String(src ?? '').replace(/```[\s\S]*?```/g, ' code block ').replace(/[*_`#>]/g, '');
}

export { append };
