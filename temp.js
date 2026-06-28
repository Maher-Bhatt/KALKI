
/* ════════════════════════════════════════════════════════════════
   BOOT SEQUENCE
   ════════════════════════════════════════════════════════════════ */
const BOOT_LINES = [
  "[BOOT] Power-on self-test initiated",
  "[BOOT] Loading neural matrix .................. <span class='ok'>OK</span>",
  "[BOOT] Calibrating Agni reactor ................ <span class='ok'>OK</span>",
  "[BOOT] Bharat visual layer ..................... <span class='ok'>OK</span>",
  "[BOOT] Hardware guardrails ..................... <span class='ok'>OK</span>",
  "[BOOT] Initializing edge-tts neural voice ..... <span class='ok'>OK</span>",
  "[BOOT] Connecting Groq inference cluster ...... <span class='ok'>OK</span>",
  "[BOOT] Voice recognition layer online ......... <span class='ok'>OK</span>",
  "[BOOT] Memory bank loaded ..................... <span class='ok'>OK</span>",
  "[BOOT] Passive cyber surface engine ........... <span class='ok'>OK</span>",
  "[BOOT] System diagnostics ..................... <span class='ok'>OK</span>",
  "[BOOT] All subsystems nominal",
  "[BOOT] Awaiting orders, Sir.",
];
const bootEl = document.getElementById("bootLines");
let bootIdx = 0;
function tickBoot(){
  if (bootIdx >= BOOT_LINES.length){
    setTimeout(()=>document.getElementById("boot").classList.add("hide"), 350);
    setTimeout(()=>document.getElementById("boot").remove(), 1300);
    return;
  }
  const d = document.createElement("div");
  d.className = "line";
  d.innerHTML = BOOT_LINES[bootIdx++];
  bootEl.appendChild(d);
  setTimeout(tickBoot, 90 + Math.random()*110);
}
tickBoot();

/* ════════════════════════════════════════════════════════════════
   STATE
   ════════════════════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);
const STATE = {
  mode: "idle", history: [],
  micActive: false,
  freqData: new Uint8Array(72),
  timeData: new Uint8Array(1024),
  pulse: 0,
  cpu:0, ram:0, dsk:0, batt:null, mem:0,
  startedAt: Date.now(),
  mouseX: window.innerWidth/2, mouseY: window.innerHeight/2,
  pwrTarget: 87, netTarget: 60,
};

const pill = $("statusPill"), pillText = $("statusText");

function flashWake(){
  const f = document.createElement("div");
  f.className = "wake-flash";
  document.body.appendChild(f);
  setTimeout(()=>f.remove(), 900);
}

function setMode(m){
  if (STATE.mode === m) return;
  STATE.mode = m; STATE.pulse = 1.0;
  document.body.classList.remove("mode-idle","mode-listening","mode-thinking","mode-speaking");
  document.body.classList.add("mode-" + m);
  pillText.textContent =
    m === "idle"      ? "STANDBY"   :
    m === "listening" ? "LISTENING" :
    m === "thinking"  ? "PROCESSING":
    /*speaking*/        "SPEAKING";
}

/* ════════════════════════════════════════════════════════════════
   STATUS POLL
   ════════════════════════════════════════════════════════════════ */
function fmtUptime(s){
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
  if (h) return `${h}h${m}m`;
  if (m) return `${m}m${sec}s`;
  return `${sec}s`;
}

let lastSeenSeq = 0;
async function refreshStatus(){
  try{
    const r = await fetch("/api/status"); const d = await r.json();
    STATE.cpu = d.cpu ?? 0; STATE.ram = d.ram ?? 0; STATE.dsk = d.disk ?? 0;
    STATE.batt = d.batteryPct; STATE.mem = d.memCount || 0;
    $("sGroq").textContent   = d.groqConfigured ? "ONLINE" : "NO KEY";
    $("sGroq").className     = "v " + (d.groqConfigured ? "ok" : "bad");
    $("sOllama").textContent = d.ollamaOnline ? "ONLINE" : "OFFLINE";
    $("sOllama").className   = "v " + (d.ollamaOnline ? "ok" : "warn");
    $("sMem").textContent    = d.memCount;
    $("sUp").textContent     = fmtUptime(d.uptimeSec);
    $("topClock").textContent= d.timeFull || "";
    $("topOwner").textContent= d.owner || "Sir";
    $("topLoc").textContent  = d.city || "";
    $("topMode").textContent = "BHARAT/" + (d.hudQuality || "balanced").toUpperCase();
    if (d.hardware){
      const gpu = (d.hardware.gpu || "RTX").replace("RTX ", "RTX");
      const ram = d.hardware.ram_gb ? `${d.hardware.ram_gb}GB` : "32GB";
      $("sHardware").textContent = `${gpu} // ${ram}`;
    }

    if (d.conversationSeq && d.conversationSeq > lastSeenSeq && d.recentExchange){
      addLine(d.recentExchange.user, "user");
      addLine(d.recentExchange.reply, "kalki");
      pushStream("voice command captured","hot");
      lastSeenSeq = d.conversationSeq;
    } else if (d.conversationSeq && lastSeenSeq === 0) {
      lastSeenSeq = d.conversationSeq;
    }

    if (d.wakeRequested){
      pushStream("WAKE WORD HEARD","hot");
      flashWake();
      setMode("listening");
      if (recognizer && !STATE.micActive){
        try { recognizer.start(); STATE.micActive = true; $("micBtn").classList.add("active"); }
        catch(e){}
      }
    }

    if (d.speaking) setMode("speaking");
    else if (STATE.mode === "speaking") setMode(STATE.micActive ? "listening" : "idle");
    $("topNet").textContent  = "ONLINE"; $("topNet").className = "v ok";

    const pbtn = $("pauseListenerBtn");
    if (d.listenerPaused){
      pbtn.textContent = "◢ MIC: PAUSED (click to resume)";
      pbtn.dataset.paused = "1";
      pbtn.style.color = "var(--orange)";
    } else {
      pbtn.textContent = "◢ MIC: LISTENING";
      pbtn.dataset.paused = "0";
      pbtn.style.color = "";
    }

    const mailLine = $("calMailLine");
    const nUnread = d.unreadImportant || 0;
    mailLine.textContent = `📬 ${nUnread} unread important`;

    const evDiv = $("calEvents");
    const events = d.todayEvents || [];
    if (!events.length){
      evDiv.innerHTML = "<span style='color:var(--text-dim)'>Calendar clear today</span>";
    } else {
      // Build with textContent (NOT innerHTML) — a malicious calendar event
      // title must never be able to inject HTML/JS into the HUD origin.
      evDiv.textContent = "";
      events.slice(0,3).forEach(e => {
        const row = document.createElement("div");
        row.style.padding = "2px 0";
        const w = document.createElement("span");
        w.style.color = "var(--accent)";
        w.style.transition = "color .55s ease";
        w.textContent = e.when;
        const s = document.createElement("span");
        s.style.color = "var(--text)";
        s.textContent = "  " + e.summary;
        row.appendChild(w); row.appendChild(s);
        evDiv.appendChild(row);
      });
    }

    const np = $("calNowPlaying");
    if (d.nowPlaying){
      np.textContent = "♫ " + d.nowPlaying;
      np.style.display = "block";
    } else {
      np.style.display = "none";
    }
  } catch(e) {
    $("topNet").textContent="OFFLINE"; $("topNet").className="v bad";
  }
}
setInterval(refreshStatus, 1500); refreshStatus();

function updateBars(){
  const cpu = STATE.cpu, ram = STATE.ram, dsk = STATE.dsk;
  $("cpuFill").style.width = cpu.toFixed(1)+"%"; $("cpuNum").textContent  = cpu.toFixed(0)+"%";
  $("ramFill").style.width = ram.toFixed(1)+"%"; $("ramNum").textContent  = ram.toFixed(0)+"%";
  $("dskFill").style.width = dsk.toFixed(1)+"%"; $("dskNum").textContent  = dsk.toFixed(0)+"%";
  STATE.netTarget += (Math.random()-0.5)*8;
  STATE.netTarget = Math.max(35, Math.min(95, STATE.netTarget));
  $("netFill").style.width = STATE.netTarget.toFixed(0)+"%";
  $("netNum").textContent  = Math.round(STATE.netTarget)+"ms";
  if (STATE.batt == null){
    $("pwrFill").style.width = STATE.pwrTarget.toFixed(0)+"%";
    $("pwrNum").textContent  = Math.round(STATE.pwrTarget)+"%";
  } else {
    $("pwrFill").style.width = STATE.batt + "%";
    $("pwrNum").textContent  = STATE.batt + "%";
  }
}
setInterval(updateBars, 800);

/* ════════════════════════════════════════════════════════════════
   TELEMETRY STREAM
   ════════════════════════════════════════════════════════════════ */
const TELE_LINES = [
  "ent.scan complete (0 threats)", "neural net stable",
  "vocoder rate nominal", "core temp 41.2C",
  "memory write OK", "auth handshake verified",
  "groq endpoint p99 = 412ms", "wake-word listener active",
  "biosignal lock confirmed", "tts buffer flushed",
  "kernel idle 22%", "syslog: 0 errors",
  "ports 8888 LISTEN", "rng entropy ok",
  "audio sample rate 48kHz", "FFT bins 128 OK",
  "encryption AES-256", "uplink secure",
  "shield strength 100%", "bharat core synced",
  "passive surface map ready", "hsts/csp scanner armed",
  "rtx guardrail balanced", "gujarat node online",
];
const streamEl = $("stream");
function pushStream(text, cls){
  const d = document.createElement("div");
  if (cls) d.className = cls;
  const ts = new Date().toTimeString().slice(0,8);
  d.textContent = `${ts}  ▸ ${text}`;
  streamEl.insertBefore(d, streamEl.firstChild);
  while (streamEl.childNodes.length > 8) streamEl.removeChild(streamEl.lastChild);
}
setInterval(()=>pushStream(TELE_LINES[Math.floor(Math.random()*TELE_LINES.length)],
                            Math.random() < .18 ? "hot":""), 1200);
for (let i=0;i<5;i++) pushStream(TELE_LINES[i]);

/* ════════════════════════════════════════════════════════════════
   READOUT + CODE BLOCK RENDERING
   ════════════════════════════════════════════════════════════════ */
function parseCodeBlocks(text){
  const segments = [];
  const re = /```([a-zA-Z0-9_+\-]*)\n?([\s\S]*?)```/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null){
    if (m.index > last) segments.push({type:"text", text:text.slice(last, m.index)});
    segments.push({type:"code", lang:m[1] || "code", text:m[2]});
    last = m.index + m[0].length;
  }
  if (last < text.length) segments.push({type:"text", text:text.slice(last)});
  return segments;
}

function makeCodeBlock(lang, code){
  const wrap = document.createElement("div");
  wrap.className = "codeBlock";
  const head = document.createElement("div");
  head.className = "codeHead";
  const lbl = document.createElement("span"); lbl.textContent = lang;
  const btn = document.createElement("button");
  btn.className = "codeCopy"; btn.textContent = "COPY";
  btn.addEventListener("click", async ()=>{
    try{ await navigator.clipboard.writeText(code); }
    catch(e){
      const ta = document.createElement("textarea");
      ta.value = code; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch(_) {}
      document.body.removeChild(ta);
    }
    btn.textContent = "COPIED ✓"; btn.classList.add("copied");
    setTimeout(()=>{ btn.textContent = "COPY"; btn.classList.remove("copied"); }, 1800);
  });
  head.appendChild(lbl); head.appendChild(btn);
  const pre = document.createElement("pre");
  pre.textContent = code;
  wrap.appendChild(head); wrap.appendChild(pre);
  return wrap;
}

function typewriter(el, text, speed=14){
  el.classList.add("typing");
  let i = 0;
  function step(){
    if (i >= text.length){ el.classList.remove("typing"); return; }
    el.textContent += text[i++];
    setTimeout(step, speed);
  }
  step();
}

function addLine(text, who){
  const ro = $("readout");
  if (who === "kalki" && /```[\s\S]*?```/.test(text)){
    const segs = parseCodeBlocks(text);
    for (const s of segs){
      if (s.type === "code"){
        ro.appendChild(makeCodeBlock(s.lang, s.text.replace(/\s+$/,"")));
      } else {
        const t = s.text.trim();
        if (!t) continue;
        const div = document.createElement("div");
        div.className = "line kalki";
        ro.appendChild(div);
        typewriter(div, t);
      }
    }
  } else if (who === "kalki"){
    const div = document.createElement("div");
    div.className = "line kalki";
    ro.appendChild(div);
    typewriter(div, text);
  } else {
    const div = document.createElement("div");
    div.className = "line " + who;
    div.textContent = (who==="user"?"› ":"") + text;
    ro.appendChild(div);
  }
  while (ro.childNodes.length > 40) ro.removeChild(ro.firstChild);
  ro.scrollTop = ro.scrollHeight;
}

/* ════════════════════════════════════════════════════════════════
   FILE ATTACHMENTS
   ════════════════════════════════════════════════════════════════ */
const attachedFiles = [];
const MAX_TEXT_CHARS = 80000;

function renderAttachStrip(){
  const strip = $("attachStrip");
  strip.innerHTML = "";
  for (let i = 0; i < attachedFiles.length; i++){
    const f = attachedFiles[i];
    const chip = document.createElement("div");
    chip.className = "attach-chip";
    if (f.type === "image"){
      const im = document.createElement("img");
      im.src = `data:${f.mimeType};base64,${f.data}`;
      chip.appendChild(im);
    }
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = f.name + (f.type==="text" ? ` · ${f.data.length} chars` : "");
    chip.appendChild(name);
    const x = document.createElement("button");
    x.textContent = "×"; x.title = "Remove";
    x.addEventListener("click", ()=>{ attachedFiles.splice(i, 1); renderAttachStrip(); });
    chip.appendChild(x);
    strip.appendChild(chip);
  }
}

async function attachFile(file){
  if (!file) return;
  if (file.type.startsWith("image/")){
    const b64 = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result.split(",")[1]); r.onerror = rej;
      r.readAsDataURL(file);
    });
    attachedFiles.push({type:"image", name:file.name||"image.png",
                        data:b64, mimeType:file.type||"image/png"});
  } else {
    const text = await file.text();
    attachedFiles.push({type:"text", name:file.name||"file.txt",
                        data:text.slice(0, MAX_TEXT_CHARS)});
  }
  renderAttachStrip();
  pushStream(`attached ${file.name}`, "hot");
}

$("attachBtn").addEventListener("click", () => $("fileInput").click());
$("fileInput").addEventListener("change", async (ev) => {
  for (const f of ev.target.files){ await attachFile(f); }
  ev.target.value = "";
});

let dragCounter = 0;
window.addEventListener("dragenter", (e) => {
  if (e.dataTransfer && e.dataTransfer.types.includes("Files")){
    dragCounter++; $("dropZone").classList.add("active");
  }
});
window.addEventListener("dragleave", () => {
  if (--dragCounter <= 0){ dragCounter = 0; $("dropZone").classList.remove("active"); }
});
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", async (e) => {
  e.preventDefault(); dragCounter = 0; $("dropZone").classList.remove("active");
  if (!e.dataTransfer) return;
  for (const f of e.dataTransfer.files){ await attachFile(f); }
});
document.addEventListener("paste", async (e) => {
  if (!e.clipboardData) return;
  for (const item of e.clipboardData.items){
    if (item.kind === "file" && item.type.startsWith("image/")){
      const f = item.getAsFile(); if (f) await attachFile(f);
    }
  }
});

/* ════════════════════════════════════════════════════════════════
   SEND COMMAND
   ════════════════════════════════════════════════════════════════ */
async function postChat(){
  return fetch("/api/chat", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({messages: STATE.history}),
  });
}

async function send(text){
  text = (text||"").trim();
  const hasAttachments = attachedFiles.length > 0;
  if (!text && !hasAttachments) return;

  let displayText = text;
  if (hasAttachments){
    const names = attachedFiles.map(f => f.name).join(", ");
    displayText = (text ? text + " " : "") + `[attached: ${names}]`;
  }
  if (displayText) addLine(displayText, "user");
  $("input").value = "";
  setMode("thinking");

  const firstImage = attachedFiles.find(f => f.type === "image");
  if (firstImage){
    const question = text || "What is on this image, Sir? Solve or explain.";
    pushStream("dispatching image to vision", "hot");
    try{
      const r = await fetch("/api/vision/image", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({image:firstImage.data, question:question}),
      });
      const d = await r.json();
      addLine(d.reply || "...", "kalki");
      pushStream("vision reply received");
      setMode("speaking");
      const dur = Math.min(14000, Math.max(2200, (d.reply||"").length * 55));
      setTimeout(()=>setMode(STATE.micActive?"listening":"idle"), dur);
    }catch(e){
      addLine("Vision request failed: " + e.message, "error");
      setMode("idle");
    }
    attachedFiles.length = 0; renderAttachStrip();
    return;
  }

  let combined = text;
  for (const f of attachedFiles){
    if (f.type === "text"){
      combined += `\n\n--- FILE: ${f.name} ---\n${f.data}\n--- END ${f.name} ---`;
    }
  }
  attachedFiles.length = 0; renderAttachStrip();

  STATE.history.push({role:"user", content: combined || text});
  if (STATE.history.length > 40) STATE.history.splice(0, STATE.history.length - 40);
  pushStream("query dispatched -> "+(text || "[file]").slice(0,40), "hot");

  let r;
  try { r = await postChat(); }
  catch(e1){
    pushStream("link drop, retrying","warn");
    await new Promise(r=>setTimeout(r, 900));
    try { r = await postChat(); }
    catch(e2){
      addLine("Server unreachable, Sir.","error"); setMode("idle"); return;
    }
  }
  try{
    const d = await r.json();
    const reply = d.reply || "...";
    STATE.history.push({role:"assistant", content:reply});
    addLine(reply, "kalki");
    pushStream("response received ("+(d.source||"ai")+")");
    setMode("speaking");
    const dur = Math.min(14000, Math.max(2200, reply.length * 55));
    setTimeout(()=>setMode(STATE.micActive?"listening":"idle"), dur);
  }catch(e){
    addLine("Reply parse failed: "+e.message,"error"); setMode("idle");
  }
}

$("pauseListenerBtn").addEventListener("click", async ()=>{
  const paused = $("pauseListenerBtn").dataset.paused === "1";
  const target = paused ? "/api/listener/resume" : "/api/listener/pause";
  try{ await fetch(target,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}); }catch(e){}
  pushStream(paused ? "listener resumed" : "listener paused", paused ? "hot" : "warn");
});
$("stopBtn").addEventListener("click", async ()=>{
  try{ await fetch("/api/stop",{method:"POST"}); }catch(e){}
  setMode(STATE.micActive?"listening":"idle");
  pushStream("speech halted","warn");
});
$("sendBtn").addEventListener("click", () => send($("input").value));
$("input").addEventListener("keydown", e => { if (e.key === "Enter") send($("input").value); });
document.querySelectorAll(".qbtn").forEach(b => {
  if (b.dataset.cmd) b.addEventListener("click", () => send(b.dataset.cmd));
});
$("modelSel").addEventListener("change", async () => {
  await fetch("/api/model", {
    method: "POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({model: $("modelSel").value}),
  });
  pushStream("model switched -> " + $("modelSel").value, "hot");
});

/* ════════════════════════════════════════════════════════════════
   MIC
   ════════════════════════════════════════════════════════════════ */
let recognizer = null;
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR){
  recognizer = new SR();
  recognizer.continuous = true; recognizer.interimResults = false;
  recognizer.lang = "en-US";
  recognizer.onresult = ev => {
    const txt = ev.results[ev.results.length-1][0].transcript.trim();
    if (txt) send(txt);
  };
  recognizer.onerror = ()=>{};
  recognizer.onend = ()=>{ if (STATE.micActive){ try{recognizer.start()}catch(e){} } };
}
let audioCtx=null, analyser=null, micSrc=null, micStream=null;
async function pickNonBtMic(){
  try{
    const devs = await navigator.mediaDevices.enumerateDevices();
    const ins = devs.filter(d=>d.kind==='audioinput' && d.deviceId && d.deviceId!=='default');
    const bt = /bluetooth|hands-?free|headset|airpods|wireless|hfp|hsp/i;
    const good = /built-?in|internal|array|realtek/i;
    const pick = ins.find(d=>!bt.test(d.label) && good.test(d.label))
              || ins.find(d=>!bt.test(d.label));
    return pick ? pick.deviceId : null;
  }catch(e){ return null; }
}
async function enableMic(){
  if (audioCtx) return;
  try{
    // First grant (also unlocks device labels for enumeration)
    micStream = await navigator.mediaDevices.getUserMedia({audio:true});
    // Switch to a non-Bluetooth mic so a BT headset stays in high-quality
    // A2DP instead of dropping to muffled HFP whenever the mic is live.
    const id = await pickNonBtMic();
    if (id){
      try{
        micStream.getTracks().forEach(t=>t.stop());
        micStream = await navigator.mediaDevices.getUserMedia({audio:{
          deviceId:{exact:id},
          echoCancellation:true, noiseSuppression:true, autoGainControl:true
        }});
      }catch(e){ /* keep the original stream if the switch fails */ }
    }
    audioCtx = new (window.AudioContext||window.webkitAudioContext)();
    micSrc = audioCtx.createMediaStreamSource(micStream);
    analyser = audioCtx.createAnalyser(); analyser.fftSize = 2048;
    micSrc.connect(analyser);
    $("sMic").textContent = "ACTIVE"; $("sMic").className="v ok";
  }catch(e){}
}
function disableMic(){
  try{micStream&&micStream.getTracks().forEach(t=>t.stop())}catch(e){}
  try{audioCtx&&audioCtx.close()}catch(e){}
  audioCtx=analyser=micSrc=micStream=null;
  $("sMic").textContent = "stand-by"; $("sMic").className="v";
}
async function toggleMic(){
  STATE.micActive = !STATE.micActive;
  $("micBtn").classList.toggle("active", STATE.micActive);
  if (STATE.micActive){
    await enableMic();
    if (recognizer){ try{recognizer.start()}catch(e){} }
    setMode("listening"); pushStream("mic engaged","hot");
  } else {
    if (recognizer){ try{recognizer.stop()}catch(e){} }
    disableMic(); setMode("idle"); pushStream("mic disengaged");
  }
}
$("micBtn").addEventListener("click", toggleMic);

const reticle = $("reticle");
window.addEventListener("mousemove", e=>{
  STATE.mouseX = e.clientX; STATE.mouseY = e.clientY;
  reticle.style.display = "block";
  reticle.style.left = e.clientX+"px";
  reticle.style.top  = e.clientY+"px";
});

/* ════════════════════════════════════════════════════════════════
   CANVAS — Surya mandala (temple + accent)
   ════════════════════════════════════════════════════════════════ */
const orb = $("orb"), ox = orb.getContext("2d");
// Cap pixel density: a full-screen mandala at 2-3x DPR is the main GPU/heat
// cost. 1.5x still looks crisp but draws far fewer pixels.
let W=0, H=0, DPR = Math.min(1.5, Math.max(1, window.devicePixelRatio||1));
function resizeOrb(){
  W = window.innerWidth;
  H = window.innerHeight - 64 - 120; // exclude topbar + bottom bar
  orb.width = W*DPR; orb.height = H*DPR;
  orb.style.width = W+"px"; orb.style.height = H+"px";
  ox.setTransform(DPR,0,0,DPR,0,0);
}
window.addEventListener("resize", resizeOrb); resizeOrb();

const ORBIT = Array.from({length:120},()=>({
  a:Math.random()*Math.PI*2, r:0.85+Math.random()*0.95,
  s:0.35+Math.random()*0.85, size:1+Math.random()*2.4,
}));
const STARS = Array.from({length:150},()=>({
  x:Math.random()*W, y:Math.random()*H,
  s:0.3+Math.random()*1.2, twinkle:Math.random()*Math.PI*2,
}));

function accentRgba(alpha){
  const accent = getComputedStyle(document.body).getPropertyValue("--accent").trim();
  // hex like #ff0080 or #ffffff
  const r = parseInt(accent.slice(1,3),16);
  const g = parseInt(accent.slice(3,5),16);
  const b = parseInt(accent.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function modeColors(){
  const a = getComputedStyle(document.body).getPropertyValue("--accent").trim();
  const speeds = {idle:0.6, listening:2.0, thinking:4.0, speaking:2.5};
  return { core:"#ffffff", ring:a, accent:a, speed: speeds[STATE.mode]||1 };
}

function sampleFreq(){
  if (!analyser){
    for (let i=0;i<72;i++)
      STATE.freqData[i] = 16+Math.sin((t*0.005)+i*0.3)*14+Math.random()*8;
    return;
  }
  const tmp = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(tmp);
  for (let i=0;i<72;i++) STATE.freqData[i] = tmp[Math.floor(i/72*tmp.length)];
}
function sampleTime(){
  if (!analyser){
    for (let i=0;i<STATE.timeData.length;i++)
      STATE.timeData[i] = 128 + Math.sin((t*0.06)+i*0.12)*22 + Math.sin(i*0.03)*10;
    return;
  }
  const tmp = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(tmp);
  STATE.timeData = tmp;
}

let t = 0;
let chakraAngle = 0;   // accumulated so speed changes are smooth (no snap)
function drawOrb(){
  t++;
  const C = modeColors();
  const cx = W/2, cy = H/2;
  const R = Math.min(W,H) * 0.125; // Smaller radius to prevent overlapping
  const sp = C.speed * 4.0; // Extreme, fast animations for heavy load
  
  // Wheel rotation
  const chakraSp = (STATE.mode === "thinking") ? sp*2.5 : sp;
  chakraAngle += 0.005 * chakraSp;

  ox.clearRect(0,0,W,H);

  sampleFreq();
  let vol = 0;
  for (let i=0;i<72;i++) vol += STATE.freqData[i];
  vol = (vol / 72) / 255;

  // ── Sleek High-Tech AI Core ──
  // Ambient deep glow
  const coreGlow = ox.createRadialGradient(cx,cy,R*0.2, cx,cy,R*3.5);
  coreGlow.addColorStop(0, C.accent);
  coreGlow.addColorStop(0.3, "rgba(0,0,0,0.6)");
  coreGlow.addColorStop(1, "rgba(0,0,0,0)");
  ox.fillStyle = coreGlow;
  ox.globalAlpha = 0.5 + vol;
  ox.beginPath(); ox.arc(cx,cy,R*3.5,0,Math.PI*2); ox.fill();
  ox.globalAlpha = 1;

  // Swirling tech particles
  for (const p of STARS){
    p.twinkle += 0.08 * sp;
    p.x += Math.sin(t*0.01 + p.y*0.01) * 0.5;
    p.y -= 0.5 * sp;
    if (p.y < 0) p.y = H;
    if (p.x < 0) p.x = W;
    if (p.x > W) p.x = 0;
    ox.fillStyle = C.accent;
    ox.globalAlpha = 0.1 + Math.abs(Math.sin(p.twinkle))*0.4;
    ox.beginPath(); ox.arc(p.x, p.y, p.s*1.2, 0, Math.PI*2); ox.fill();
  }
  ox.globalAlpha = 1;

  // ── Audio-Reactive Plasma Ring ──
  const barInner = R*1.15;
  const barMax = R*0.45;
  ox.lineCap = "round";
  for (let i=0;i<72;i++){
    const a = (i/72)*Math.PI*2 + t*0.002*sp;
    const v = STATE.freqData[i]/255;
    const len = barMax * (0.1 + v*1.5);
    const x1 = cx + Math.cos(a)*barInner, y1 = cy + Math.sin(a)*barInner;
    const x2 = cx + Math.cos(a)*(barInner+len), y2 = cy + Math.sin(a)*(barInner+len);
    ox.strokeStyle = C.accent;
    ox.globalAlpha = 0.3 + v*0.7;
    ox.lineWidth = 3;
    ox.beginPath(); ox.moveTo(x1,y1); ox.lineTo(x2,y2); ox.stroke();
  }
  ox.globalAlpha = 1;

  // ── High-Tech Segmented Arcs ──
  drawArcRing(cx,cy, R*1.05, 3,  chakraAngle, C.ring, 2.5, 0.2);
  drawArcRing(cx,cy, R*1.35, 6, -chakraAngle*1.5, C.ring, 1.5, 0.4);
  drawArcRing(cx,cy, R*1.65, 12, chakraAngle*0.5, C.accent, 1.0, 0.15);

  // Orbiting data nodes
  for (const p of ORBIT){
    p.a += 0.008*sp*p.s;
    const rr = R*(1.8 + p.r*0.6) + Math.sin(t*0.02+p.a*4)*5;
    const px = cx + Math.cos(p.a)*rr, py = cy + Math.sin(p.a)*rr;
    ox.fillStyle = C.ring;
    ox.globalAlpha = 0.8;
    ox.beginPath(); ox.arc(px,py,p.size*1.5,0,Math.PI*2); ox.fill();
  }
  ox.globalAlpha = 1;

  // ── Central Plasma Core ──
  const coreBase = R*(0.75 + vol*0.15);
  const coreG = ox.createRadialGradient(cx,cy,0, cx,cy,coreBase);
  coreG.addColorStop(0, "#ffffff");
  coreG.addColorStop(0.2, C.core);
  coreG.addColorStop(0.8, C.accent);
  coreG.addColorStop(1, "rgba(0,0,0,0.8)");
  
  ox.shadowColor = C.accent;
  ox.shadowBlur = 30 + vol*50;
  ox.fillStyle = coreG;
  ox.beginPath(); ox.arc(cx,cy,coreBase,0,Math.PI*2); ox.fill();
  ox.shadowBlur = 0;
  
  ox.beginPath();
  for (let i=0;i<6;i++){
    const a = (i/6)*Math.PI*2 + Math.PI/6;
    const x = cx + Math.cos(a)*R*0.3, y = cy + Math.sin(a)*R*0.3;
    if (i===0) ox.moveTo(x,y); else ox.lineTo(x,y);
  }
  ox.closePath(); ox.strokeStyle = "#fff"; ox.lineWidth = 2; ox.stroke();
}

function drawArcRing(cx,cy,r,segments,phase,color,lineW,dim=0.5){
  const seg = (Math.PI*2)/segments;
  const gap = seg*0.18;
  for (let i=0;i<segments;i++){
    const a0 = i*seg+phase, a1 = a0+seg-gap;
    ox.strokeStyle = color;
    ox.globalAlpha = (i%2===0) ? 0.95 : dim;
    ox.lineWidth = lineW;
    ox.beginPath(); ox.arc(cx,cy,r,a0,a1); ox.stroke();
  }
  ox.globalAlpha = 1;
}
// Segment Devanagari (and any Unicode) text into proper grapheme clusters
// so matras/combining marks never get detached from their base letter.
const _segmenter = (typeof Intl !== 'undefined' && Intl.Segmenter)
  ? new Intl.Segmenter('hi', { granularity: 'grapheme' })
  : null;
function splitGraphemes(str) {
  if (_segmenter) return [..._segmenter.segment(str)].map(s => s.segment);
  // Fallback: split on Unicode code points (handles emoji, keeps surrogates together)
  return [...str];
}

function drawTextRing(cx,cy,r,text,phase,color,size){
  const clusters = splitGraphemes(text);
  if (clusters.length === 0) return;
  ox.save();
  ox.font = `600 ${size}px "Noto Sans Devanagari", "Mukta", sans-serif`;
  ox.textAlign = 'center'; ox.textBaseline = 'middle';
  ox.fillStyle = color; ox.globalAlpha = 1.0;

  // Measure total arc length needed
  const widths = clusters.map(c => ox.measureText(c).width);
  const gap = size * 0.22;  // inter-glyph spacing in px
  const totalArc = widths.reduce((s,w) => s + w + gap, 0);
  // Angular step proportional to each glyph's width
  const totalAngle = totalArc / r;  // in radians

  let angle = phase - totalAngle / 2; // centre the text
  for (let i = 0; i < clusters.length; i++) {
    const halfW = (widths[i] + gap) / 2;
    const midAngle = angle + halfW / r;
    ox.save();
    ox.translate(cx, cy);
    ox.rotate(midAngle - Math.PI / 2);
    ox.translate(0, -r);
    ox.rotate(Math.PI / 2);
    ox.fillText(clusters[i], 0, 0);
    ox.restore();
    angle += (widths[i] + gap) / r;
  }
  ox.restore();
  ox.globalAlpha = 1;
}
function drawHex(cx,cy,r,color,alpha=1){
  ox.fillStyle = color; ox.globalAlpha = alpha;
  ox.beginPath();
  for (let i=0;i<6;i++){
    const a = (i/6)*Math.PI*2 + Math.PI/6;
    const x = cx + Math.cos(a)*r, y = cy + Math.sin(a)*r;
    if (i===0) ox.moveTo(x,y); else ox.lineTo(x,y);
  }
  ox.closePath(); ox.fill();
  ox.globalAlpha = 1;
}

/* Indian motifs ─────────────────────────────────────────────── */
// Ring of lotus petals (almond/leaf shape) — the mandala signature.
function drawLotusRing(cx,cy,rBase,rTip,count,phase,color,alpha,fill){
  ox.globalAlpha = alpha;
  for (let i=0;i<count;i++){
    const a  = (i/count)*Math.PI*2 + phase;
    const dw = (Math.PI/count)*0.92;          // half angular width
    const rm = (rBase+rTip)/2;
    const bx = cx+Math.cos(a)*rBase,    by = cy+Math.sin(a)*rBase;
    const tx = cx+Math.cos(a)*rTip,     ty = cy+Math.sin(a)*rTip;
    const lx = cx+Math.cos(a-dw)*rm,    ly = cy+Math.sin(a-dw)*rm;
    const rx = cx+Math.cos(a+dw)*rm,    ry = cy+Math.sin(a+dw)*rm;
    ox.beginPath();
    ox.moveTo(bx,by);
    ox.quadraticCurveTo(lx,ly, tx,ty);
    ox.quadraticCurveTo(rx,ry, bx,by);
    ox.closePath();
    if (fill){ ox.fillStyle = color; ox.fill(); }
    else { ox.strokeStyle = color; ox.lineWidth = 1.4; ox.stroke(); }
  }
  ox.globalAlpha = 1;
}

// Ashoka Chakra — 24-spoke dharma wheel with rim pips.
function drawChakraWheel(cx,cy,r,spokes,phase,color,alpha){
  ox.save(); ox.translate(cx,cy); ox.rotate(phase);
  ox.globalAlpha = alpha; ox.strokeStyle = color; ox.fillStyle = color;
  ox.lineWidth = 1.3;
  ox.beginPath(); ox.arc(0,0,r,0,Math.PI*2); ox.stroke();
  ox.beginPath(); ox.arc(0,0,r*0.90,0,Math.PI*2); ox.stroke();
  ox.beginPath(); ox.arc(0,0,r*0.12,0,Math.PI*2); ox.stroke();
  for (let i=0;i<spokes;i++){
    const a = (i/spokes)*Math.PI*2;
    ox.beginPath();
    ox.moveTo(Math.cos(a)*r*0.12, Math.sin(a)*r*0.12);
    ox.lineTo(Math.cos(a)*r*0.90, Math.sin(a)*r*0.90);
    ox.stroke();
    ox.beginPath();
    ox.arc(Math.cos(a)*r*0.90, Math.sin(a)*r*0.90, 1.2, 0, Math.PI*2); ox.fill();
  }
  ox.restore(); ox.globalAlpha = 1;
}

// Small rotated-square stud for rangoli/mandala accents.
function drawDiamond(cx,cy,s,color,alpha){
  ox.save(); ox.translate(cx,cy); ox.rotate(Math.PI/4);
  ox.globalAlpha = alpha; ox.fillStyle = color;
  ox.fillRect(-s,-s,s*2,s*2);
  ox.restore(); ox.globalAlpha = 1;
}

// Trishul (trident) — drawn as a clean vector, no script/text.
function drawTrishul(cx,cy,h,color){
  ox.save(); ox.translate(cx,cy);
  ox.strokeStyle = color; ox.fillStyle = color;
  ox.lineWidth = Math.max(1.3, h*0.013); ox.lineCap = "round"; ox.lineJoin = "round";
  const w = h*0.26;                 // half-spread of the outer prongs
  const top = -h*0.50, bot = h*0.50;
  const base = -h*0.16;             // where the three prongs meet the shaft
  // shaft
  ox.beginPath(); ox.moveTo(0, base); ox.lineTo(0, bot*0.86); ox.stroke();
  // centre prong
  ox.beginPath(); ox.moveTo(0, base); ox.lineTo(0, top); ox.stroke();
  // centre spear tip (leaf)
  ox.beginPath();
  ox.moveTo(0, top - h*0.05);
  ox.quadraticCurveTo( w*0.16, top + h*0.02, 0, top + h*0.07);
  ox.quadraticCurveTo(-w*0.16, top + h*0.02, 0, top - h*0.05);
  ox.closePath(); ox.stroke();
  // outer prongs — curve out from base, rise, finish in tips
  for (const dir of [-1, 1]){
    ox.beginPath();
    ox.moveTo(0, base);
    ox.quadraticCurveTo(dir*w*1.15, base, dir*w, top + h*0.14);
    ox.lineTo(dir*w, top + h*0.01);
    ox.stroke();
    // prong tip
    ox.beginPath();
    ox.moveTo(dir*w, top - h*0.02);
    ox.quadraticCurveTo(dir*(w + w*0.14), top + h*0.05, dir*w, top + h*0.08);
    ox.stroke();
  }
  // crossbar joining the prong bases
  ox.beginPath(); ox.moveTo(-w, base); ox.lineTo(w, base); ox.stroke();
  // damaru knot on the lower shaft
  ox.beginPath(); ox.arc(0, h*0.18, h*0.045, 0, Math.PI*2); ox.stroke();
  ox.restore();
}

orb.addEventListener("click", toggleMic);

/* ════════════════════════════════════════════════════════════════
   WAVEFORM
   ════════════════════════════════════════════════════════════════ */
const wave = $("wave"), wx = wave.getContext("2d");
function resizeWave(){
  wave.width = window.innerWidth*DPR; wave.height = 34*DPR;
  wave.style.width = window.innerWidth+"px"; wave.style.height = "34px";
  wx.setTransform(DPR,0,0,DPR,0,0);
}
window.addEventListener("resize", resizeWave); resizeWave();
function drawWave(){
  sampleTime();
  const ww = window.innerWidth, wh = 34;
  wx.clearRect(0,0,ww,wh);
  const accent = getComputedStyle(document.body).getPropertyValue("--accent").trim();
  wx.strokeStyle = accent; wx.lineWidth = 1.5;
  wx.globalAlpha = 0.85;
  wx.shadowColor = accent; wx.shadowBlur = 8;
  wx.beginPath();
  const N = STATE.timeData.length;
  for (let i=0;i<ww;i++){
    const v = STATE.timeData[Math.floor(i/ww*N)] / 255;
    const y = wh/2 + (v-0.5)*wh*0.95;
    if (i===0) wx.moveTo(i,y); else wx.lineTo(i,y);
  }
  wx.stroke(); wx.shadowBlur = 0;
  wx.strokeStyle = "rgba(255,255,255,0.15)"; wx.lineWidth = 1;
  for (let i=0;i<ww;i+=40){
    wx.beginPath(); wx.moveTo(i,0); wx.lineTo(i,3); wx.stroke();
    wx.beginPath(); wx.moveTo(i,wh-3); wx.lineTo(i,wh); wx.stroke();
  }
  wx.globalAlpha = 1;
}

/* ════════════════════════════════════════════════════════════════
   DIAL + GAUGE
   ════════════════════════════════════════════════════════════════ */
const dial = $("dial"), dx = dial.getContext("2d");
const gauge = $("gauge"), gx = gauge.getContext("2d");
function resizeMini(){
  for (const c of [dial,gauge]){
    const r = c.getBoundingClientRect();
    c.width = r.width*DPR; c.height = r.height*DPR;
    c.getContext("2d").setTransform(DPR,0,0,DPR,0,0);
  }
}
window.addEventListener("resize", resizeMini); setTimeout(resizeMini, 30);

function drawDial(){
  const r = dial.getBoundingClientRect();
  const W2 = r.width, H2 = r.height;
  if (!W2) return;
  dx.clearRect(0,0,W2,H2);
  const cx = W2/2, cy = H2/2 + 8, R = Math.min(W2,H2)*0.38;
  const accent = getComputedStyle(document.body).getPropertyValue("--accent").trim();
  dx.strokeStyle = "rgba(255,255,255,0.4)"; dx.lineWidth = 1; dx.globalAlpha = 0.8;
  dx.beginPath(); dx.arc(cx,cy,R,0,Math.PI*2); dx.stroke();
  for (let i=0;i<36;i++){
    const a = (i/36)*Math.PI*2;
    const r0 = R, r1 = R - (i%9===0 ? 8 : 4);
    dx.beginPath();
    dx.moveTo(cx+Math.cos(a)*r0, cy+Math.sin(a)*r0);
    dx.lineTo(cx+Math.cos(a)*r1, cy+Math.sin(a)*r1);
    dx.stroke();
  }
  dx.font = "10px JetBrains Mono,monospace"; dx.fillStyle = "#fff";
  dx.textAlign = "center"; dx.textBaseline = "middle";
  for (const [lbl,a] of [["N",-Math.PI/2],["E",0],["S",Math.PI/2],["W",Math.PI]]){
    dx.fillText(lbl, cx+Math.cos(a)*(R-14), cy+Math.sin(a)*(R-14));
  }
  const heading = (t*0.003) % (Math.PI*2);
  dx.strokeStyle = accent; dx.lineWidth = 2;
  dx.beginPath(); dx.moveTo(cx,cy);
  dx.lineTo(cx+Math.cos(heading-Math.PI/2)*R*0.78, cy+Math.sin(heading-Math.PI/2)*R*0.78);
  dx.stroke();
  dx.fillStyle = accent; dx.beginPath(); dx.arc(cx,cy,3,0,Math.PI*2); dx.fill();
  dx.fillStyle = "#fff"; dx.globalAlpha = 0.8;
  dx.font = "11px JetBrains Mono,monospace";
  const deg = Math.round((heading/(Math.PI*2))*360);
  dx.fillText(`HDG ${String(deg).padStart(3,"0")}°`, cx, cy + R + 14);
  dx.globalAlpha = 1;
}

function drawGauge(){
  const r = gauge.getBoundingClientRect();
  const W2 = r.width, H2 = r.height;
  if (!W2) return;
  gx.clearRect(0,0,W2,H2);
  const cx = W2/2, cy = H2*0.85, R = Math.min(W2,H2*1.6)*0.42;
  const accent = getComputedStyle(document.body).getPropertyValue("--accent").trim();
  const a0 = Math.PI*1.15, a1 = Math.PI*1.85;
  gx.strokeStyle = "rgba(255,255,255,0.18)"; gx.lineWidth = 6;
  gx.beginPath(); gx.arc(cx,cy,R,a0,a1); gx.stroke();
  const val = STATE.batt != null ? STATE.batt : STATE.pwrTarget;
  const a = a0 + (a1-a0) * (val/100);
  gx.strokeStyle = accent; gx.lineWidth = 6;
  gx.shadowColor = accent; gx.shadowBlur = 10;
  gx.beginPath(); gx.arc(cx,cy,R,a0,a); gx.stroke();
  gx.shadowBlur = 0;
  gx.strokeStyle = "rgba(255,255,255,0.5)"; gx.lineWidth = 1;
  for (let i=0;i<=10;i++){
    const ang = a0 + (a1-a0)*(i/10);
    const r0 = R - 8, r1 = R + 4;
    gx.beginPath();
    gx.moveTo(cx+Math.cos(ang)*r0, cy+Math.sin(ang)*r0);
    gx.lineTo(cx+Math.cos(ang)*r1, cy+Math.sin(ang)*r1);
    gx.stroke();
  }
  gx.fillStyle = "#fff"; gx.font = "bold 18px JetBrains Mono,monospace";
  gx.textAlign = "center"; gx.textBaseline = "middle";
  gx.fillText(Math.round(val) + "%", cx, cy - R*0.45);
  gx.font = "9px JetBrains Mono,monospace"; gx.fillStyle = "rgba(255,255,255,0.6)";
  gx.fillText("AGNI OUTPUT", cx, cy - R*0.45 + 16);
}

/* ════════════════════════════════════════════════════════════════
   MAIN LOOP — 30 fps, pause on hidden tab
   ════════════════════════════════════════════════════════════════ */
let _lastFrame = 0, _dialFrame = 0;
function frameInterval(){
  // Full 30fps only when something is happening; idle coasts at 12fps to
  // keep the laptop cool. Mic/listening/thinking/speaking = active.
  const active = STATE.micActive || (STATE.mode && STATE.mode !== "idle")
                 || STATE.pulse > 0.02;
  return active ? (1000/30) : (1000/12);
}
function loop(ts){
  if (document.hidden){ setTimeout(()=>requestAnimationFrame(loop), 500); return; }
  if (!_lastFrame) _lastFrame = ts;
  if (ts - _lastFrame >= frameInterval()){
    _lastFrame = ts;
    drawOrb(); drawWave();
    if (++_dialFrame >= 6){ _dialFrame = 0; drawDial(); drawGauge(); }
  }
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden){ _lastFrame = 0; _dialFrame = 0; }
});

setTimeout(()=>addLine("KALKI online. Awaiting orders, Sir.","kalki"), 1600);
