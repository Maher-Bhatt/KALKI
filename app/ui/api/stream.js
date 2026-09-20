/** SSE reader for POST /api/chat with {stream: true}.
 *
 *  The server emits `data: {"token": "..."}` repeatedly then
 *  `data: {"done": true, "model": "..."}`. Handled local commands answer in a
 *  single frame carrying both token and done. Aborting also calls /api/stop so
 *  speech halts with the text — stopping one without the other is wrong. */

import { post } from './client.js';

/**
 * @param {Array<{role:string,content:string}>} messages
 * @param {{onToken:(t:string)=>void, onDone:(info:{model?:string})=>void,
 *          onError:(e:{message:string,detail:string})=>void,
 *          signal?:AbortSignal, clientSpeech?:boolean}} handlers
 */
export async function streamChat(messages, handlers) {
  const { onToken, onDone, onError, signal, clientSpeech } = handlers;
  let stopped = false;

  const onAbort = () => { stopped = true; post('/api/stop', {}).catch(() => {}); };
  signal?.addEventListener('abort', onAbort, { once: true });

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ messages, stream: true, clientSpeech: !!clientSpeech }),
      signal,
    });

    if (res.status === 401) { onError({ message: 'Your session expired.', detail: '' }); return; }
    if (!res.ok || !res.body) {
      onError({ message: "KALKI couldn't reach the model.", detail: `HTTP ${res.status}` });
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let model;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let cut;
      while ((cut = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, cut).trim();
        buffer = buffer.slice(cut + 2);
        if (!frame.startsWith('data:')) continue;
        let payload;
        try { payload = JSON.parse(frame.slice(5).trim()); } catch { continue; }
        if (typeof payload.token === 'string' && payload.token) onToken(payload.token);
        if (payload.done) { model = payload.model || model; onDone({ model }); return; }
      }
    }
    onDone({ model, truncated: !stopped });
  } catch (err) {
    if (stopped || signal?.aborted) { onDone({ stopped: true }); return; }
    onError({ message: "KALKI's local service isn't responding.", detail: String(err?.message || err) });
  } finally {
    signal?.removeEventListener('abort', onAbort);
  }
}
