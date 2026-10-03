import { h, frag } from '../lib/dom.js';

export function presenceView() {
  const main = frag(h('div.pad', null, h('div.hd', null, h('div', null, h('h1', null, 'Presence and motion'), h('div.sub', null, 'One shape tells you what KALKI is doing. Try each state.')), h('button.btn.pri', {'id': 'demo'}, h('i', {'data-i': 'play'}), 'Play a conversation')), h('div.grid2', {style: {alignItems: 'start'}}, h('div.card.col.g12', null, h('div.orb', {'id': 'orb', 'data-s': 'idle'}, h('i.rg', null), h('i.rg', null), h('i.rg', null), h('i.arc', null), h('div.bars', null, h('i', null), h('i', null), h('i', null), h('i', null), h('i', null), h('i', null), h('i', null), h('i', null), h('i', null)), h('div.core', null)), h('div.row.g8', {style: {justifyContent: 'center'}}, h('span.chip', {'id': 'slab'}, 'Waiting for “hey kalki”')), h('div.cap', {'id': 'cap'}), h('div.seg', {'id': 'segs'}, h('button.btn.a', {'data-s': 'idle'}, 'Idle'), h('button.btn', {'data-s': 'listening'}, 'Listening'), h('button.btn', {'data-s': 'thinking'}, 'Thinking'), h('button.btn', {'data-s': 'speaking'}, 'Speaking'), h('button.btn', {'data-s': 'interrupting'}, 'Interrupt'), h('button.btn', {'data-s': 'error'}, 'Error'), h('button.btn', {'data-s': 'asleep'}, 'Asleep'))), h('div.card', null, h('h2', null, 'How each state looks'), h('table', null, h('tr', null, h('th', null, 'State'), h('th', null, 'What moves')), h('tr', null, h('td', null, 'Idle'), h('td.sm.t2', null, 'Steady glow. Nothing animates.')), h('tr', null, h('td', null, 'Listening'), h('td.sm.t2', null, 'Rings ripple out; the core grows with your voice level.')), h('tr', null, h('td', null, 'Thinking'), h('td.sm.t2', null, 'A short arc circles the core while the model works.')), h('tr', null, h('td', null, 'Speaking'), h('td.sm.t2', null, 'Bars move with the reply; captions follow the audio.')), h('tr', null, h('td', null, 'Interrupt'), h('td.sm.t2', null, 'Core shrinks in 180 ms, audio stops, then listening starts.')), h('tr', null, h('td', null, 'Error'), h('td.sm.t2', null, 'Red core with a dashed ring and a plain message.')), h('tr', null, h('td', null, 'Asleep'), h('td.sm.t2', null, 'Small dim core. The mic chip reads Mic off.'))))), h('div.grid2', {style: {marginTop: '14px', alignItems: 'start'}}, h('div.card', null, h('h2', null, 'Motion rules'), h('table', null, h('tr', null, h('th', null, 'Moment'), h('th', null, 'What moves'), h('th.n', null, 'Timing')), h('tr', null, h('td.sm', null, 'Switch screen'), h('td.sm.t2', null, 'Content fades'), h('td.n', null, '120 ms')), h('tr', null, h('td.sm', null, 'Open palette or dialog'), h('td.sm.t2', null, 'Scrim fades, panel scales from 98%'), h('td.n', null, '160 ms')), h('tr', null, h('td.sm', null, 'Reply streams in'), h('td.sm.t2', null, 'Text appears as received; caret blinks'), h('td.n', null, 'live')), h('tr', null, h('td.sm', null, 'Tool result arrives'), h('td.sm.t2', null, 'Card grows, status chip cross-fades'), h('td.n', null, '160 ms')), h('tr', null, h('td.sm', null, 'Task created'), h('td.sm.t2', null, 'Banner slides 8 px; Undo shows for 5 s'), h('td.n', null, '180 ms')), h('tr', null, h('td.sm', null, 'Confirmation'), h('td.sm.t2', null, 'Countdown bar drains; cancels at zero'), h('td.n', null, '30 s')), h('tr', null, h('td.sm', null, 'Meters change'), h('td.sm.t2', null, 'Value eases, no overshoot'), h('td.n', null, '400 ms')), h('tr', null, h('td.sm', null, 'New alert'), h('td.sm.t2', null, 'Filament edge shows once'), h('td.n', null, '1.2 s'))), h('div.sm.t2', {style: {marginTop: '10px'}}, 'With Reduce motion on, every move above becomes a fade of 120 ms or less, and presence states stay distinct by shape, not movement.')), h('div.card', null, h('h2', null, 'Where every feature lives'), h('div.col.g12', {style: {marginTop: '8px'}}, h('div', null, h('div.xs.mut', null, 'Ask'), h('div.sm.t2', null, 'Chat, files, screen vision, voice, model choice, history')), h('div', null, h('div.xs.mut', null, 'Today'), h('div.sm.t2', null, 'Briefing, calendar, tasks, reminders, notes, focus, mail, GitHub, WhatsApp, music, clipboard, updates')), h('div', null, h('div.xs.mut', null, 'Memory'), h('div.sm.t2', null, 'Pinned facts, semantic search, import, edit, importance')), h('div', null, h('div.xs.mut', null, 'Workbench'), h('div.sm.t2', null, 'Routines, code studio, vision, documents, skills')), h('div', null, h('div.xs.mut', null, 'Oversight'), h('div.sm.t2', null, 'Watched sites, alerts, approvals, activity with undo, health')), h('div', null, h('div.xs.mut', null, 'Settings'), h('div.sm.t2', null, 'Models, keys, usage, voice, privacy, vault, backup, shortcuts')), h('div', null, h('div.xs.mut', null, 'Everywhere'), h('div.sm.t2', null, 'Ctrl K palette, Ctrl Space quick ask, presence mark, privacy chips')))))));
  const aside = frag(h('h1', {style: {fontSize: '16px'}}, 'Voice'), h('div.card.col.g8', null, h('div.row.sb', null, h('span.sm', null, 'Wake words'), h('span.chip.ok', null, 'On')), h('span.mono.xs.t2', null, 'hey kalki · ok kalki'), h('div.row.sb', null, h('span.sm', null, 'Interrupt by talking'), h('i.tg.on', null)), h('div.row.sb', null, h('span.sm', null, 'Live captions'), h('i.tg.on', null))), h('div.card.col.g8', null, h('h2', null, 'Privacy'), h('div.sm.t2', null, 'The mic chip in the title bar turns amber whenever KALKI can hear you. Audio stays on this machine unless you pick a cloud voice.')), h('div.card.col.g8', null, h('h2', null, 'Quick ask'), h('div.row.sb', null, h('span.sm', null, 'Open from anywhere'), h('kbd', null, 'Ctrl Space'))));
  
  // Interactive parts for the presence view
  // Based on the script in the HTML
  const orb = main.querySelector('.orb');
  const cap = main.querySelector('#cap');
  const slab = main.querySelector('#slab');
  const segs = main.querySelectorAll('#segs button');
  const demoBtn = main.querySelector('#demo');
  
  let run = 0;
  
  const LAB = {
    idle: 'Waiting for “hey kalki”',
    listening: 'Listening. Captions appear as you speak',
    thinking: 'Working on it',
    speaking: 'Speaking. Talk to interrupt',
    interrupting: 'Stopped. Back to you',
    error: 'Could not hear you. Check the microphone',
    asleep: 'Asleep. Say the wake word or press Ctrl Space'
  };
  
  function setS(s) {
    orb.dataset.s = s;
    segs.forEach(b => b.classList.toggle('a', b.dataset.s === s));
    if(slab) slab.textContent = LAB[s];
    // .mark is in the shell, we can dispatch an event or just update the DOM directly for the demo
    const mark = document.querySelector('.mark');
    if (mark) mark.dataset.s = s;
    const mic = document.querySelector('#mic');
    if (mic) {
        mic.className = 'chip ' + (s==='listening' ? 'warn' : s==='asleep' ? '' : 'ok');
        mic.textContent = s==='listening' ? 'Mic live' : s==='asleep' ? 'Mic off' : 'Mic ready';
    }
  }
  
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  
  segs.forEach(b => b.onclick = () => {
    run++;
    const s = b.dataset.s;
    setS(s);
    if(cap) cap.textContent = s === 'error' ? 'I could not hear you. Check that the microphone is plugged in.' : '';
    if (s === 'interrupting') setTimeout(() => setS('listening'), 400);
  });
  
  if (demoBtn) demoBtn.onclick = async () => {
    const id = ++run;
    const ok = () => id === run;
    setS('idle');
    if(cap) cap.textContent = '';
    await sleep(600); if(!ok()) return;
    setS('listening');
    let u = '', q = 'what is on my calendar today'.split(' ');
    for (const w of q) {
      u += (u ? ' ' : '') + w;
      if(cap) cap.innerHTML = '<span class="t2">' + u + '</span>';
      await sleep(260); if(!ok()) return;
    }
    await sleep(300); setS('thinking');
    if(cap) cap.innerHTML = '<span class="mut">' + u + '<br>Checking your calendar</span>';
    await sleep(1400); if(!ok()) return;
    setS('speaking');
    let a = '', r = 'You have two events. Odoo Experience at 14:30, then a team sync at 17:00.'.split(' ');
    for (const w of r) {
      a += (a ? ' ' : '') + w;
      if(cap) cap.innerHTML = '<span class="mut">' + u + '</span><br>' + a;
      await sleep(190); if(!ok()) return;
    }
    await sleep(800); if(ok()) setS('idle');
  };

  return { main, aside };
}
