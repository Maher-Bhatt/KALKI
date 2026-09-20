/** Single API boundary. Every network call in KALKI goes through here.
 *
 *  The local server authenticates with the X-KALKI-Token header or the
 *  kalki_session cookie that index.html is served with. We never put the
 *  token in a URL and we never log it.
 *
 *  Several handlers answer {"ok": false} with HTTP 200, so a response is a
 *  failure when data.ok === false regardless of status. Raw exception text
 *  from the server's _safe_call wrapper is kept in `detail` and only ever
 *  shown in the diagnostics drawer — never as the primary message. */

/** @typedef {'offline'|'auth'|'timeout'|'not-configured'|'invalid'|'server'|'unavailable'} ErrorKind */

const MESSAGES = {
  offline: "KALKI's local service isn't responding.",
  auth: 'Your session expired.',
  timeout: 'That took too long and was cancelled.',
  'not-configured': "That capability isn't set up yet.",
  invalid: "That request wasn't accepted.",
  server: 'Something went wrong inside KALKI.',
  unavailable: "That capability isn't available on this machine.",
};

const log = [];
export const callLog = () => log.slice(-20);

function record(entry) {
  log.push(entry);
  if (log.length > 60) log.splice(0, log.length - 60);
}

function fail(kind, detail, status) {
  return { ok: false, kind, message: MESSAGES[kind] || MESSAGES.server, detail: detail || '', status: status || 0 };
}

/**
 * @param {string} path
 * @param {{method?: string, body?: any, signal?: AbortSignal, timeout?: number}} [opts]
 * @returns {Promise<{ok:true,data:any}|{ok:false,kind:ErrorKind,message:string,detail:string,status:number}>}
 */
export async function call(path, opts = {}) {
  const { method = 'POST', body, signal, timeout = 20000 } = opts;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort('timeout'), timeout);
  const onAbort = () => ctl.abort(signal?.reason);
  signal?.addEventListener('abort', onAbort, { once: true });
  const t0 = performance.now();

  try {
    const res = await fetch(path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'same-origin',
      signal: ctl.signal,
    });
    const ms = Math.round(performance.now() - t0);

    if (res.status === 401) { record({ path, kind: 'auth', status: 401, ms }); return fail('auth', '', 401); }
    if (res.status === 405) { record({ path, kind: 'invalid', status: 405, ms }); return fail('invalid', 'Wrong HTTP method for this route.', 405); }

    let data = null;
    const text = await res.text();
    if (text) { try { data = JSON.parse(text); } catch { data = { raw: text }; } }

    if (!res.ok) {
      record({ path, kind: 'server', status: res.status, ms });
      return fail('server', data?.error || text.slice(0, 400), res.status);
    }
    if (data && data.ok === false) {
      const detail = String(data.error || '');
      const kind = /not configured|missing|no credential|not linked|auth/i.test(detail) ? 'not-configured'
        : /required|invalid|empty/i.test(detail) ? 'invalid'
        : /unavailable|not installed|no module/i.test(detail) ? 'unavailable'
        : 'server';
      record({ path, kind, status: res.status, ms });
      return { ...fail(kind, detail, res.status), message: MESSAGES[kind] };
    }
    record({ path, kind: 'ok', status: res.status, ms });
    return { ok: true, data: data ?? {} };
  } catch (err) {
    const ms = Math.round(performance.now() - t0);
    const kind = String(err?.message || err).includes('timeout') || ctl.signal.reason === 'timeout' ? 'timeout' : 'offline';
    record({ path, kind, status: 0, ms });
    return fail(kind, String(err?.message || err));
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

export const get = (path, opts) => call(path, { ...opts, method: 'GET' });
export const post = (path, body, opts) => call(path, { ...opts, method: 'POST', body });

/** Public, token-free, cheap. The correct probe for "is the backend alive". */
export async function health() {
  const r = await get('/api/health', { timeout: 4000 });
  return r.ok;
}
