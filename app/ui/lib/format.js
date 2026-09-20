/** Formatting helpers. All output is user-facing English, sentence case. */

export function bytes(n) {
  if (!n && n !== 0) return '';
  const u = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${u[i]}`;
}

export function duration(sec) {
  sec = Math.max(0, Math.round(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

export function clock(sec) {
  sec = Math.max(0, Math.round(sec));
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`;
}

export function relative(ts) {
  if (!ts) return '';
  const d = typeof ts === 'number' ? new Date(ts < 1e12 ? ts * 1000 : ts) : new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 45) return 'just now';
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.round(diff / 86400)}d ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function dateTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

/** First line of a conversation, trimmed to a usable title. */
export function titleFrom(text) {
  const line = String(text || '').trim().split('\n')[0].replace(/\s+/g, ' ');
  return line.length > 60 ? line.slice(0, 57) + '…' : (line || 'New conversation');
}

/** Human label for a model id. Never invents capability claims. */
export function modelLabel(id) {
  if (!id) return 'auto';
  return String(id).replace(/-versatile$/, '').replace(/^models\//, '');
}
