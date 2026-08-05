
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
  speakingPause: false,
  busyMode: localStorage.getItem("busyMode") === "true",
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
  document.body.classList.remove("mode-idle","mode-listening","mode-thinking","mode-speaking","mode-busy");
  document.body.classList.add("mode-" + m);
  pillText.textContent =
    m === "idle"      ? "STANDBY"   :
    m === "listening" ? "LISTENING" :
    m === "thinking"  ? "PROCESSING":
    m === "busy"      ? "BUSY"      :
    /*speaking*/        "SPEAKING";
}

/* ════════════════════════════════════════════════════════════════
   STATUS POLL
   ════════════════════════════════════════════════════════════════ */
function fmtUptime(s){
  const h = Math.floor(s/3600);
  const m = Math.floor((s%3600)/60);
  const sec = s % 60;
  
  if (h > 0) return `${h}h${m.toString().padStart(2, '0')}m`;
  if (m > 0) return `${m}m${sec.toString().padStart(2, '0')}s`;
  return `${sec}s`;
}

let lastSeenSeq = 0;
async function refreshStatus(){
  try{
    const r = await fetch("/api/status"); const d = await r.json();
    STATE.networkAlerted = false;
    if(typeof updateDashboard === "function") updateDashboard(d);

    if (d.terminalLogs) {
      const term = document.getElementById('liveTerminal');
      if (term) {
        term.innerHTML = '';
        d.terminalLogs.forEach(log => {
          const line = document.createElement('div');
          line.className = 'term-line';
          line.innerText = '> ' + log;
          term.appendChild(line);
        });
        term.scrollTop = term.scrollHeight;
      }
    }
    
    // Resource overload detection
    if (d.cpu > 95) {
      if (!STATE.cpuAlerted && d.cpuAlertsEnabled) {
        STATE.cpuAlerted = true;
        triggerSystemError("cpu_core", "sustained_load_critical", "CPU utilization has spiked critically to " + Math.round(d.cpu) + "%. This may cause UI stuttering or slow speech synthesis.", "Close background applications or compile processes.");
      }
    } else if (d.cpu < 85) {
      STATE.cpuAlerted = false;
    }
    
    if (d.ram > 95) {
      if (!STATE.ramAlerted) {
        STATE.ramAlerted = true;
        triggerSystemError("memory", "out_of_memory_warning", "System virtual memory is almost exhausted (" + Math.round(d.ram) + "% active).", "Terminate memory-intensive tasks immediately.");
      }
    } else if (d.ram < 85) {
      STATE.ramAlerted = false;
    }
    
    if (d.disk > 98) {
      if (!STATE.diskAlerted) {
        STATE.diskAlerted = true;
        triggerSystemError("storage", "local_disk_full", "Local storage is critically full. Disk usage is above 98%. Operations requiring temporary files may fail.", "Clean up temp files or move large media off the partition.");
      }
    } else if (d.disk < 95) {
      STATE.diskAlerted = false;
    }
    STATE.cpu = d.cpu ?? 0; STATE.ram = d.ram ?? 0; STATE.dsk = d.disk ?? 0;
    STATE.batt = d.batteryPct; STATE.mem = d.memCount || 0;
    $("sGroq").textContent   = d.groqConfigured ? "ONLINE" : "NO KEY";
    $("sGroq").className     = "v " + (d.groqConfigured ? "ok" : "bad");
    $("sOllama").textContent = d.ollamaOnline ? "ONLINE" : "OFFLINE";
    $("sOllama").className   = "v " + (d.ollamaOnline ? "ok" : "warn");
    $("sVoice").textContent = d.ttsVoice
      ? d.ttsVoice.replace("MultilingualNeural", "").replace("Neural", " · Neural")
      : "NOT CONFIGURED";
    if (d.updateProgress && d.updateProgress.active) {
      $("sMem").textContent = `UPDATING ${d.updateProgress.pct}%`;
      $("sMem").style.color = "var(--orange)";
    } else {
      $("sMem").textContent = d.memCount;
      $("sMem").style.color = "";
    }
    $("sUp").textContent     = fmtUptime(d.uptimeSec);
    $("topClock").textContent= d.timeFull || "";
    $("topOwner").textContent= d.owner || "Sir";
    $("topLoc").textContent  = d.city || "";
    $("topMode").textContent = "SYSTEM/" + (d.hudQuality || "balanced").toUpperCase();
    if (d.hardware){
      const gpu = d.hardware.gpu || "GPU unavailable";
      const ram = d.hardware.ram_gb ? `${d.hardware.ram_gb}GB` : "RAM unavailable";
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

    if (STATE.busyMode) {
      setMode("busy");
      $("sMic").textContent = "LOCKED";
      $("sMic").className = "v bad";
      $("pauseListenerBtn").textContent = "MIC: PAUSED (click to resume)";
      $("pauseListenerBtn").style.color = "var(--orange)";
      if (STATE.micActive) {
        STATE.micActive = false;
        if ($("micBtn")) $("micBtn").classList.remove("active");
        if (recognizer) { try { recognizer.stop(); } catch(e){} }
        disableMic();
      }
    } else {
      if (d.wakeRequested){
        pushStream("WAKE WORD HEARD","hot");
        flashWake();
        setMode("listening");
        if (!STATE.micActive){
          STATE.micActive = true;
          if ($("micBtn")) $("micBtn").classList.add("active");
          enableMic().then(() => {
            if (recognizer){ try{recognizer.start()}catch(e){} }
          });
        }
      }

      if (d.speaking) {
        setMode("speaking");
        if (STATE.micActive && !STATE.speakingPause) {
          STATE.speakingPause = true;
          if ($("micBtn")) $("micBtn").classList.remove("active");
          if (recognizer) { try { recognizer.stop(); } catch(e){} }
          disableMic();
        }
      } else {
        if (STATE.speakingPause) {
          STATE.speakingPause = false;
          if (STATE.micActive) {
            if ($("micBtn")) $("micBtn").classList.add("active");
            enableMic().then(() => {
              if (recognizer) { try { recognizer.start(); } catch(e){} }
            });
          }
        }
        if (STATE.mode === "speaking" || STATE.mode === "busy") {
          setMode(STATE.micActive ? "listening" : "idle");
        }
      }
      $("topNet").textContent  = "ONLINE"; $("topNet").className = "v ok";

      const micMuted = (d.listenerMicMuted !== null && d.listenerMicMuted !== undefined)
          ? d.listenerMicMuted
          : (d.speaking || d.listenerPaused);

      const pbtn = $("pauseListenerBtn");
      if (micMuted){
        pbtn.textContent = d.listenerPaused ? "MIC: PAUSED (click to resume)" : "MIC: MUTED";
        pbtn.dataset.paused = d.listenerPaused ? "1" : "0";
        pbtn.style.color = "var(--orange)";
        if (STATE.micActive) {
          STATE.micActive = false;
          if ($("micBtn")) $("micBtn").classList.remove("active");
          if (recognizer) { try { recognizer.stop(); } catch(e){} }
          disableMic();
          setMode("idle");
        }
      } else {
        pbtn.textContent = "MIC: LISTENING";
        pbtn.dataset.paused = "0";
        pbtn.style.color = "";
      }
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
    if (!STATE.networkAlerted) {
      STATE.networkAlerted = true;
      triggerSystemError("uplink", "server_offline_timeout", "Uplink to local assistant server failed. The server is not responding to health pings.", "Make sure the server is running. If this is your first time, run KALKI_Setup_Wizard.exe to initialize your configuration.");
    }
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
const streamEl = $("stream");
function pushStream(text, cls){
  const d = document.createElement("div");
  if (cls) d.className = cls;
  const ts = new Date().toTimeString().slice(0,8);
  d.textContent = `${ts}  ${text}`;
  streamEl.insertBefore(d, streamEl.firstChild);
  while (streamEl.childNodes.length > 8) streamEl.removeChild(streamEl.lastChild);
}
pushStream("Assistant ready", "hot");
pushStream("Activity will appear here as you use KALKI");

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
      triggerSystemError("vision", "api_request_failed", "Vision request failed: " + e.message, "Check your Google Gemini API Key or Groq configuration in settings.");
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
      addLine("Server unreachable, Sir.","error");
      triggerSystemError("ai_link", "server_unreachable", "Failed to communicate with KALKI server. The local backend may have terminated or network settings are misconfigured.", "Verify python process is active and listening on port 8000.");
      setMode("idle"); return;
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
    
    // Auto-wake microphone if KALKI asks a question or requests confirmation
    const isQuestion = reply.includes("?") || reply.toLowerCase().includes("say confirm");
    if (isQuestion && typeof enableMic === "function") {
      setTimeout(() => {
        STATE.micActive = true;
        if ($("micBtn")) $("micBtn").classList.add("active");
        enableMic().then(() => {
          if (recognizer){ try{recognizer.start()}catch(e){} }
          setMode("listening");
        });
      }, dur);
    } else {
      setTimeout(()=>setMode(STATE.micActive?"listening":"idle"), dur);
    }
  }catch(e){
    addLine("Reply parse failed: "+e.message,"error");
    triggerSystemError("response_parse", "malformed_json_payload", "Failed to parse response payload: " + e.message, "Check server logs for internal exceptions or python runtime logs.");
    setMode("idle");
  }
}

$("pauseListenerBtn").addEventListener("click", async ()=>{
  const paused = $("pauseListenerBtn").dataset.paused === "1";
  const target = paused ? "/api/listener/resume" : "/api/listener/pause";
  try{ await fetch(target,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}); }catch(e){}
  pushStream(paused ? "listener resumed" : "listener paused", paused ? "hot" : "warn");
  if (!paused && STATE.micActive) {
    STATE.micActive = false;
    if ($("micBtn")) $("micBtn").classList.remove("active");
    if (recognizer) { try { recognizer.stop(); } catch(e){} }
    disableMic();
    setMode("idle");
  }
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

let _fetchingModels = false;
async function fetchModels() {
  if (_fetchingModels) return;
  _fetchingModels = true;
  try {
    const r = await fetch("/api/models");
    if (!r.ok) return;
    const d = await r.json();
    if (d.models && d.models.length > 0) {
      const sel = $("modelSel");
      const currentVal = sel.value;
      sel.innerHTML = "";
      for (const m of d.models) {
        const opt = document.createElement("option");
        opt.value = m;
        let label = m;
        if (m === "auto") label = "auto (smart routing)";
        else if (m.toLowerCase().includes("8b")) label += " (fast)";
        else if (m.toLowerCase().includes("70b")) label += " (smart)";
        opt.textContent = label;
        sel.appendChild(opt);
      }
      if (d.models.includes(currentVal)) {
        sel.value = currentVal;
      } else if (d.models.includes(STATE.model)) {
        sel.value = STATE.model;
      }
    }
  } catch(e) {
  } finally {
    _fetchingModels = false;
  }
}
setTimeout(fetchModels, 2000);
setInterval(fetchModels, 60000); // Check for new models every minute


/* ════════════════════════════════════════════════════════════════
   MIC & Speech Recognition
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
  recognizer.onend = ()=>{ if (STATE.micActive && !STATE.speakingPause && !STATE.busyMode){ try{recognizer.start()}catch(e){} } };
}
let audioCtx=null, analyser=null, micSrc=null, micStream=null;
async function enableMic(){
  if (audioCtx) return;
  try{
    micStream = await navigator.mediaDevices.getUserMedia({audio:true});
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
  const mbtn = $("micBtn");
  if (mbtn) mbtn.classList.toggle("active", STATE.micActive);
  if (STATE.micActive){
    await enableMic();
    if (recognizer){ try{recognizer.start()}catch(e){} }
    setMode("listening"); pushStream("mic engaged","hot");
  } else {
    if (recognizer){ try{recognizer.stop()}catch(e){} }
    disableMic(); setMode("idle"); pushStream("mic disengaged");
  }
}
if ($("micBtn")) $("micBtn").addEventListener("click", toggleMic);

const reticle = $("reticle");
window.addEventListener("mousemove", e=>{
  STATE.mouseX = e.clientX; STATE.mouseY = e.clientY;
  reticle.style.display = "block";
  reticle.style.left = e.clientX+"px";
  reticle.style.top  = e.clientY+"px";
});

/* ════════════════════════════════════════════════════════════════
   SETTINGS MODAL LOGIC
   ════════════════════════════════════════════════════════════════ */
function showNotice(msg, isErr=false) {
  const n = $("settingsNotice");
  n.style.display = "block";
  n.style.color = isErr ? "var(--red)" : "var(--lime)";
  n.style.borderColor = isErr ? "var(--red)" : "var(--lime)";
  n.textContent = msg;
  setTimeout(()=>n.style.display="none", 4000);
}

$("settingsBtn").addEventListener("click", openSettingsModal);
if($("topSettingsBtn")) $("topSettingsBtn").addEventListener("click", openSettingsModal);

// Settings tabs use the standard tab pattern so they work with keyboard and
// assistive technology as well as the mouse.
const settingsTabs = [...document.querySelectorAll(".tab-btn")];
if (settingsTabs[0]?.parentElement) {
  settingsTabs[0].parentElement.setAttribute("role", "tablist");
  settingsTabs[0].parentElement.setAttribute("aria-orientation", "vertical");
}
function activateSettingsTab(button, shouldFocus = false) {
  settingsTabs.forEach(tab => {
    const selected = tab === button;
    const panel = $(tab.dataset.tab);
    tab.classList.toggle("active", selected);
    tab.style.color = selected ? "var(--text)" : "var(--text-dim)";
    tab.style.borderLeftColor = selected ? "var(--accent)" : "transparent";
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (panel) {
      panel.style.display = selected ? "block" : "none";
      panel.hidden = !selected;
    }
  });
  if (shouldFocus) button.focus();
}
settingsTabs.forEach((button, index) => {
  const panel = $(button.dataset.tab);
  button.setAttribute("role", "tab");
  button.setAttribute("aria-controls", button.dataset.tab);
  button.setAttribute("aria-selected", String(button.classList.contains("active")));
  button.tabIndex = button.classList.contains("active") ? 0 : -1;
  if (panel) panel.setAttribute("role", "tabpanel");
  button.addEventListener("click", () => activateSettingsTab(button));
  button.addEventListener("keydown", (event) => {
    if (!['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const targetIndex = event.key === 'Home' ? 0 : event.key === 'End' ? settingsTabs.length - 1
      : (index + (event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : -1) + settingsTabs.length) % settingsTabs.length;
    activateSettingsTab(settingsTabs[targetIndex], true);
  });
});

// The legacy markup uses visual labels. Attach them programmatically to their
// form controls so every settings field has an accessible name.
document.querySelectorAll("#settingsModal input, #settingsModal select").forEach((control, index) => {
  if (control.getAttribute("aria-label")) return;
  const label = control.closest("div")?.querySelector("label");
  if (label) {
    if (!control.id) control.id = `settings-field-${index}`;
    label.htmlFor = control.id;
  } else {
    control.setAttribute("aria-label", control.placeholder || "KALKI setting");
  }
});

async function openSettingsModal() {
  try {
    const r = await fetch("/api/settings/get");
    const d = await r.json();
    if(d.ok) {
      $("set_owner_name").value = d.settings.OWNER_NAME || "";
      $("set_owner_title").value = d.settings.OWNER_TITLE || "";
      $("set_owner_city").value = d.settings.OWNER_CITY || "";
      $("set_owner_state").value = d.settings.OWNER_STATE || "";
      $("set_owner_country").value = d.settings.OWNER_COUNTRY || "";
      $("set_email_address").value = d.settings.EMAIL_ADDRESS || "";
      const setSecret = (id, val, configured) => {
        const el = $(id);
        if(!el) return;
        el.value = (val === "PASTE_YOUR_GROQ_KEY_HERE") ? "" : (val || "");
        el.placeholder = configured ? "[ CONFIGURED - HIDDEN ]" : "";
      };
      
      setSecret("set_email_app_password", d.settings.EMAIL_APP_PASSWORD, d.secretStatus?.EMAIL_APP_PASSWORD);
      setSecret("set_github_token", d.settings.GITHUB_TOKEN, d.secretStatus?.GITHUB_TOKEN);
      setSecret("set_shodan_api_key", d.settings.SHODAN_API_KEY, d.secretStatus?.SHODAN_API_KEY);
      setSecret("set_groq_key", d.settings.GROQ_API_KEY, d.secretStatus?.GROQ_API_KEY);
      setSecret("set_openai_key", d.settings.OPENAI_API_KEY, d.secretStatus?.OPENAI_API_KEY);
      setSecret("set_anthropic_key", d.settings.ANTHROPIC_API_KEY, d.secretStatus?.ANTHROPIC_API_KEY);
      setSecret("set_gemini_key", d.settings.GEMINI_API_KEY, d.secretStatus?.GEMINI_API_KEY);
      setSecret("set_elevenlabs_key", d.settings.ELEVENLABS_API_KEY, d.secretStatus?.ELEVENLABS_API_KEY);
      setSecret("set_cloud_sync_passphrase", d.settings.CLOUD_SYNC_PASSPHRASE, d.secretStatus?.CLOUD_SYNC_PASSPHRASE);
      
      if ($("set_spotify_id")) $("set_spotify_id").value = d.settings.SPOTIFY_CLIENT_ID || "";
      setSecret("set_spotify_secret", d.settings.SPOTIFY_CLIENT_SECRET, d.secretStatus?.SPOTIFY_CLIENT_SECRET);
      
      // Google Manual
      if ($("set_google_client_id")) $("set_google_client_id").value = d.settings.GOOGLE_CLIENT_ID || "";
      setSecret("set_google_client_secret", d.settings.GOOGLE_CLIENT_SECRET, d.secretStatus?.GOOGLE_CLIENT_SECRET);
      if ($("set_google_project_id")) $("set_google_project_id").value = d.settings.GOOGLE_PROJECT_ID || "";
      
      $("set_model_chat").value = d.settings.MODEL_CHAT || "auto";
      $("set_model_vision").value = d.settings.MODEL_VISION || "auto";
      $("set_model_coding").value = d.settings.MODEL_CODING || "auto";
      $("set_model_voice").value = d.settings.MODEL_VOICE || "auto";
      
      $("set_telemetry_enabled").checked = d.settings.TELEMETRY_ENABLED !== false;
      $("set_cpu_alerts_enabled").checked = d.settings.CPU_ALERTS_ENABLED !== false;
      $("set_screensaver_enabled").checked = d.settings.SCREENSAVER_ENABLED !== false;
      $("set_screensaver_idle_mins").value = d.settings.SCREENSAVER_IDLE_MINS || 5;
      $("set_tts_voice").value = d.settings.TTS_VOICE || "";
      if ($("set_tts_provider")) $("set_tts_provider").value = d.settings.TTS_PROVIDER || "edge";
      if ($("set_tts_rate")) $("set_tts_rate").value = d.settings.TTS_RATE || "+0%";
      if ($("set_tts_pitch")) $("set_tts_pitch").value = d.settings.TTS_PITCH || "+0Hz";
      if ($("set_tts_volume")) $("set_tts_volume").value = d.settings.TTS_VOLUME || "+0%";
      if ($("set_tts_output_device")) $("set_tts_output_device").value = d.settings.TTS_OUTPUT_DEVICE || "";
      if ($("set_tts_groq_timeout_sec")) $("set_tts_groq_timeout_sec").value = d.settings.TTS_GROQ_TIMEOUT_SEC || 3;
      
      if ($("lbl_google_status")) {
        $("lbl_google_status").innerHTML = d.googleConfigured ? "[LINKED]" : "[NOT CONFIGURED]";
        $("lbl_google_status").style.color = d.googleConfigured ? "var(--lime)" : "var(--orange)";
      }
      if ($("lbl_spotify_status")) {
        $("lbl_spotify_status").innerHTML = d.spotifyConfigured ? "[LINKED]" : "[NOT CONFIGURED]";
        $("lbl_spotify_status").style.color = d.spotifyConfigured ? "var(--lime)" : "var(--orange)";
      }
      if ($("lbl_groq_status")) {
        const hasGroq = !!(d.secretStatus && d.secretStatus.GROQ_API_KEY);
        $("lbl_groq_status").innerHTML = hasGroq ? "[PRESENT]" : "[MISSING]";
        $("lbl_groq_status").style.color = hasGroq ? "var(--lime)" : "var(--red)";
      }
      
      if(d.cacheSize && $("lbl_cache_size")) $("lbl_cache_size").innerHTML = d.cacheSize;
      
      const mbtn = $("modalToggleAssistantBtn");
      mbtn.innerText = STATE.busyMode ? "BUSY MODE: ON" : "BUSY MODE: OFF";
      mbtn.style.borderColor = STATE.busyMode ? "var(--red)" : "var(--lime)";
      mbtn.style.color = STATE.busyMode ? "var(--red)" : "var(--lime)";
      
      if (typeof loadMemoryList === "function") await loadMemoryList();
    }
  } catch(e) {}
  $("settingsModal").style.display = "flex";
  setTimeout(() => $("closeSettingsBtn").focus(), 0);
}

$("closeSettingsBtn").addEventListener("click", () => {
  $("settingsModal").style.display = "none";
  $("settingsNotice").style.display = "none";
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("settingsModal").style.display === "flex") {
    $("closeSettingsBtn").click();
    return;
  }
  if (event.key === "Tab" && $("settingsModal").style.display === "flex") {
    const focusable = [...$("settingsModal").querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )].filter(el => !el.disabled && el.offsetParent !== null);
    if (!focusable.length) return;
    const current = focusable.indexOf(document.activeElement);
    const next = event.shiftKey
      ? (current <= 0 ? focusable.length - 1 : current - 1)
      : (current === focusable.length - 1 ? 0 : current + 1);
    event.preventDefault();
    focusable[next].focus();
  }
});

$("saveSettingsBtn").addEventListener("click", async () => {
  if (!$("set_owner_name").value.trim()) return showNotice("Owner name cannot be empty", true);
  if (!$("set_owner_title").value.trim()) return showNotice("Owner title cannot be empty", true);

  const updates = {
    OWNER_NAME: $("set_owner_name").value,
    OWNER_TITLE: $("set_owner_title").value,
    OWNER_CITY: $("set_owner_city").value,
    OWNER_STATE: $("set_owner_state").value,
    OWNER_COUNTRY: $("set_owner_country").value,
    EMAIL_ADDRESS: $("set_email_address") ? $("set_email_address").value : "",
    EMAIL_APP_PASSWORD: $("set_email_app_password") ? $("set_email_app_password").value : "",
    GITHUB_TOKEN: $("set_github_token") ? $("set_github_token").value : "",
    SHODAN_API_KEY: $("set_shodan_api_key") ? $("set_shodan_api_key").value : "",
    GROQ_API_KEY: $("set_groq_key") ? $("set_groq_key").value : "",
    OPENAI_API_KEY: $("set_openai_key") ? $("set_openai_key").value : "",
    ANTHROPIC_API_KEY: $("set_anthropic_key") ? $("set_anthropic_key").value : "",
    GEMINI_API_KEY: $("set_gemini_key") ? $("set_gemini_key").value : "",
    ELEVENLABS_API_KEY: $("set_elevenlabs_key") ? $("set_elevenlabs_key").value : "",
    CLOUD_SYNC_PASSPHRASE: $("set_cloud_sync_passphrase") ? $("set_cloud_sync_passphrase").value : "",
    SPOTIFY_CLIENT_ID: $("set_spotify_id") ? $("set_spotify_id").value : "",
    SPOTIFY_CLIENT_SECRET: $("set_spotify_secret") ? $("set_spotify_secret").value : "",
    GOOGLE_CLIENT_ID: $("set_google_client_id") ? $("set_google_client_id").value : "",
    GOOGLE_CLIENT_SECRET: $("set_google_client_secret") ? $("set_google_client_secret").value : "",
    GOOGLE_PROJECT_ID: $("set_google_project_id") ? $("set_google_project_id").value : "",
    MODEL_CHAT: $("set_model_chat").value,
    MODEL_VISION: $("set_model_vision").value,
    MODEL_CODING: $("set_model_coding").value,
    MODEL_VOICE: $("set_model_voice").value,
    TELEMETRY_ENABLED: $("set_telemetry_enabled").checked,
    CPU_ALERTS_ENABLED: $("set_cpu_alerts_enabled").checked,
    SCREENSAVER_ENABLED: $("set_screensaver_enabled").checked,
    SCREENSAVER_IDLE_MINS: parseInt($("set_screensaver_idle_mins").value) || 5,
    TTS_PROVIDER: $("set_tts_provider") ? $("set_tts_provider").value : "edge",
    TTS_VOICE: $("set_tts_voice").value,
    TTS_RATE: $("set_tts_rate") ? $("set_tts_rate").value : "+0%",
    TTS_PITCH: $("set_tts_pitch") ? $("set_tts_pitch").value : "+0Hz",
    TTS_VOLUME: $("set_tts_volume") ? $("set_tts_volume").value : "+0%",
    TTS_OUTPUT_DEVICE: $("set_tts_output_device") ? $("set_tts_output_device").value : "",
    TTS_GROQ_TIMEOUT_SEC: parseInt($("set_tts_groq_timeout_sec") ? $("set_tts_groq_timeout_sec").value : "3") || 3
  };
  try {
    const resp = await fetch("/api/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({updates})
    });
    const result = await resp.json();
    if (!resp.ok || result.ok === false) {
      showNotice("Save failed: " + (result.error || resp.statusText), true);
      return;
    }
    showNotice("Configuration saved successfully!");
    // These previously only ran on their own timers
    if (typeof fetchModels === "function") await fetchModels();
    if (typeof refreshStatus === "function") await refreshStatus();
  } catch(e) {
    showNotice("Save failed: " + e.message, true);
  }
});

if ($("testVoiceBtn")) {
  $("testVoiceBtn").addEventListener("click", async () => {
    try {
      if ($("lbl_tts_status")) $("lbl_tts_status").textContent = "TTS STATUS: STARTING TEST...";
      showNotice("Speaking test phrase...", false);
      const r = await fetch("/api/tts/test", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({})
      });
      const d = await r.json();
      const status = d.ok ? `TTS STATUS: ${d.provider || "edge"} STARTED` : `TTS STATUS: ${d.lastError || "FAILED"}`;
      if ($("lbl_tts_status")) $("lbl_tts_status").textContent = status;
      showNotice(d.ok ? "Voice test started." : (d.lastError || "Voice test failed."), !d.ok);
    } catch(e) {
      if ($("lbl_tts_status")) $("lbl_tts_status").textContent = "TTS STATUS: " + e.message;
      showNotice("Voice test failed: " + e.message, true);
    }
  });
}

$("runGoogleSetup").addEventListener("click", async () => {
  showNotice("Launching Google Oauth Flow...");
  await fetch("/api/setup/tool", { method: "POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({tool:"google"}) });
});

if($("testGoogleBtn")) $("testGoogleBtn").addEventListener("click", async () => {
  showNotice("Testing Google Connection...", false);
  const r = await fetch("/api/settings/test_google");
  const d = await r.json();
  showNotice(d.message, !d.ok);
});

if($("testSpotifyBtn")) $("testSpotifyBtn").addEventListener("click", async () => {
  showNotice("Testing Spotify Connection...", false);
  const r = await fetch("/api/settings/test_spotify");
  const d = await r.json();
  showNotice(d.message, !d.ok);
});

$("runSpotifySetup").addEventListener("click", async () => {
  showNotice("Launching Spotify Setup...");
  await fetch("/api/setup/tool", { method: "POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({tool:"spotify"}) });
});

if ($("reconnectSpotifyBtn")) {
  $("reconnectSpotifyBtn").addEventListener("click", async () => {
    if (!confirm("This will disconnect Spotify and require you to log in again. Continue?")) return;
    showNotice("Reconnecting Spotify...", false);
    await fetch("/api/setup/tool", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({tool: "reconnect_spotify"})
    });
  });
}

$("testSettingsBtn").addEventListener("click", async () => {
  try {
    showNotice("Testing connections...", false);
    const r = await fetch("/api/settings/test");
    const d = await r.json();
    if(d.ok) {
      showNotice(`Groq: ${d.groq} | Spotify: ${d.spotify}`);
    } else {
      showNotice(d.error || "Connection test failed", true);
    }
  } catch(e) {
    showNotice("Error calling test endpoint", true);
  }
});

$("resetSettingsBtn").addEventListener("click", async () => {
  if(!confirm("Are you sure you want to reset all configurations and caches?")) return;
  try {
    const r = await fetch("/api/settings/reset", { method: "POST", headers: {"Content-Type": "application/json"}, body: "{}" });
    const d = await r.json();
    if(d.ok) {
      showNotice("Configurations wiped. Please restart KALKI.");
      setTimeout(() => location.reload(), 2000);
    }
  } catch(e) {
    showNotice("Failed to reset configurations", true);
  }
});

$("clearCacheBtn").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/settings/clear_cache", { method: "POST", headers: {"Content-Type": "application/json"}, body: "{}" });
    const d = await r.json();
    showNotice(d.ok ? "Cache cleared successfully." : "Failed to clear cache.");
    if(d.ok && $("lbl_cache_size")) $("lbl_cache_size").innerHTML = "0.0 MB";
  } catch(e) { showNotice("Error clearing cache", true); }
});

$("exportSettingsBtn").addEventListener("click", () => {
  window.open("/api/settings/export", "_blank");
});

$("importSettingsBtn").addEventListener("click", () => {
    alert("Import settings logic not connected yet.");
});

if ($("restoreSettingsBtn")) {
  $("restoreSettingsBtn").addEventListener("click", async () => {
      if(!confirm("Restore memory and history from cloud? Local files will be overwritten.")) return;
      let passphrase = prompt("Enter your cloud sync passphrase (leave blank if already saved in settings):");
      if (passphrase === null) return;
      try {
          let res = await fetch("/api/cloud_restore", { 
              method: "POST", 
              headers: {"Content-Type":"application/json"}, 
              body: JSON.stringify({passphrase: passphrase}) 
          });
          let data = await res.json();
          if(data.ok) alert(data.message || "Restore successful.");
          else alert("Restore failed: " + data.error);
      } catch(e) {
          alert("Error: " + e);
      }
  });
}

if ($("createBackupBtn")) {
  $("createBackupBtn").addEventListener("click", async () => {
    try {
      showNotice("Creating backup...", false);
      const r = await fetch("/api/backup/create", { method: "POST" });
      const d = await r.json();
      showNotice(d.message || "Backup completed.", !d.ok);
    } catch(e) {
      showNotice("Backup failed: " + e.message, true);
    }
  });
}

if ($("restoreBackupBtn")) {
  $("restoreBackupBtn").addEventListener("click", async () => {
    const path = $("restoreFilePath").value.trim();
    if (!path) return showNotice("Please enter backup ZIP file path", true);
    try {
      showNotice("Restoring backup...", false);
      const r = await fetch("/api/backup/restore", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ filePath: path })
      });
      const d = await r.json();
      showNotice(d.message || "Restore completed.", !d.ok);
      if (d.ok) {
        setTimeout(() => location.reload(), 2000);
      }
    } catch(e) {
      showNotice("Restore failed: " + e.message, true);
    }
  });
}

if ($("addMemoryBtn")) {
  $("addMemoryBtn").addEventListener("click", async () => {
    const text = $("newMemoryFact").value.trim();
    if (!text) return;
    try {
      const r = await fetch("/api/memory/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ text })
      });
      const d = await r.json();
      if (d.ok) {
        $("newMemoryFact").value = "";
        showNotice("Fact stored in memory bank.");
        if (typeof loadMemoryList === "function") loadMemoryList();
      } else {
        showNotice(d.error || "Failed to store fact", true);
      }
    } catch(e) {
      showNotice("Error storing fact", true);
    }
  });
}

async function loadMemoryList() {
  const container = $("memoryNodesContainer");
  if (!container) return;
  try {
    const r = await fetch("/api/memory/list");
    const d = await r.json();
    if (d.ok && d.memories) {
      if (d.memories.length === 0) {
        container.innerHTML = `<p style="font-size:1.2rem; color:var(--text-dim); text-align:center; padding:1rem;">No facts stored yet.</p>`;
        return;
      }
      container.innerHTML = "";
      d.memories.forEach(m => {
        const item = document.createElement("div");
        item.style.display = "flex";
        item.style.justifyContent = "space-between";
        item.style.alignItems = "center";
        item.style.padding = "0.8rem";
        item.style.borderBottom = "0.1rem solid #222";
        item.style.fontSize = "1.15rem";
        
        const txt = document.createElement("span");
        txt.style.flex = "1";
        txt.style.marginRight = "1rem";
        txt.textContent = m.text;
        
        const delBtn = document.createElement("button");
        delBtn.className = "qbtn";
        delBtn.textContent = "✕";
        delBtn.style.color = "var(--red)";
        delBtn.style.background = "transparent";
        delBtn.style.border = "none";
        delBtn.style.cursor = "pointer";
        delBtn.style.fontSize = "1.3rem";
        delBtn.addEventListener("click", async () => {
          if (!confirm("Delete this fact from memory?")) return;
          try {
            const res = await fetch("/api/memory/delete", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({ id: m.id })
            });
            const resD = await res.json();
            if (resD.ok) {
              loadMemoryList();
            } else {
              alert(resD.error || "Delete failed");
            }
          } catch(err) {
            alert("Error deleting: " + err.message);
          }
        });
        
        item.appendChild(txt);
        item.appendChild(delBtn);
        container.appendChild(item);
      });
    }
  } catch(e) {
    container.innerHTML = `<p style="font-size:1.2rem; color:var(--red); text-align:center; padding:1rem;">Failed to load memories.</p>`;
  }
}

$("modalToggleAssistantBtn").addEventListener("click", async () => {
  STATE.busyMode = !STATE.busyMode;
  localStorage.setItem("busyMode", STATE.busyMode ? "true" : "false");
  
  const mbtn = $("modalToggleAssistantBtn");
  mbtn.innerText = STATE.busyMode ? "BUSY MODE: ON" : "BUSY MODE: OFF";
  mbtn.style.borderColor = STATE.busyMode ? "var(--red)" : "var(--lime)";
  mbtn.style.color = STATE.busyMode ? "var(--red)" : "var(--lime)";
  
  if (STATE.busyMode) {
    STATE.micActive = false;
    if ($("micBtn")) $("micBtn").classList.remove("active");
    if (recognizer) { try { recognizer.stop(); } catch(e){} }
    disableMic();
    setMode("busy");
    pushStream("busy mode engaged - mic disabled", "warn");
    try { await fetch("/api/listener/pause", {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"}); } catch(e){}
  } else {
    setMode("idle");
    pushStream("busy mode disengaged - resuming normal status", "hot");
    try { await fetch("/api/listener/resume", {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"}); } catch(e){}
  }
});

const cpuHistory = new Array(60).fill(0);
const ramHistory = new Array(60).fill(0);

function drawHistoryGraph(canvasId, dataArray, color) {
  const c = document.getElementById(canvasId);
  if (!c) return;
  const ctx = c.getContext("2d");
  const w = c.clientWidth;
  const h = c.clientHeight;
  if (c.width !== w * DPR) {
    c.width = w * DPR; c.height = h * DPR;
    ctx.scale(DPR, DPR);
  }
  ctx.clearRect(0, 0, w, h);
  
  // draw grid
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for(let i=1; i<4; i++) {
    let y = h * (i/4);
    ctx.moveTo(0, y); ctx.lineTo(w, y);
  }
  ctx.stroke();
  
  ctx.beginPath();
  const step = w / (dataArray.length - 1);
  for(let i=0; i<dataArray.length; i++) {
    let val = dataArray[i];
    let x = i * step;
    let y = h - (val / 100) * (h * 0.8) - (h * 0.1); // Scale 0-100 to canvas with 10% padding
    if (i===0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();
  
  // Fill under
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = color.replace(")", ", 0.1)").replace("rgb", "rgba");
  if(ctx.fillStyle === color) ctx.fillStyle = "rgba(255,255,255,0.1)"; // fallback
  ctx.fill();
}


const orb = $("orb"), ox = orb.getContext("2d");
// Cap pixel density: a full-screen mandala at 2-3x DPR is the main GPU/heat
// cost. 1.5x still looks crisp but draws far fewer pixels.
let W=0, H=0, DPR = Math.min(1.5, Math.max(1, window.devicePixelRatio||1));

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
function drawOrb() {
  if (!ox) return;
  try {
    t++;
    const cx = W/2, cy = H/2;
    const R = Math.min(W,H) * 0.35;
    
    ox.clearRect(0,0,W,H);
    
    sampleFreq();
    let vol = 0;
    for (let i=0;i<72;i++) vol += STATE.freqData[i];
    vol = (vol / 72) / 255;
    
    const colors = modeColors();
    const cCore = colors.core;
    const cAccent = colors.accent;
    
    // Accumulate angle
    chakraAngle += 0.005 * colors.speed * (1 + vol*2);
    
    // 1) Base Glow
    const glow = ox.createRadialGradient(cx, cy, R*0.3, cx, cy, R*1.6);
    glow.addColorStop(0, accentRgba(0.1 + vol*0.3));
    glow.addColorStop(0.5, accentRgba(0.05 + vol*0.1));
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ox.fillStyle = glow;
    ox.beginPath(); ox.arc(cx, cy, R*1.6, 0, Math.PI*2); ox.fill();
    
    // 2) Outer Arc Rings (Counter-rotating)
    drawArcRing(cx, cy, R*1.05, 3, chakraAngle*1.2, cAccent, 1.5, 0.4);
    drawArcRing(cx, cy, R*1.12, 5, -chakraAngle*0.8, cCore, 1, 0.2);
    
    // 3) Audio waveform rim
    ox.beginPath();
    ox.strokeStyle = cAccent;
    ox.lineWidth = 1.5;
    for(let i=0; i<72; i++) {
        let angle = (i/72) * Math.PI * 2 + (chakraAngle*0.5);
        let v = STATE.freqData[i]/255;
        let ext = R + (v * R * 0.2);
        let px = cx + Math.cos(angle) * ext;
        let py = cy + Math.sin(angle) * ext;
        if(i===0) ox.moveTo(px,py);
        else ox.lineTo(px,py);
    }
    ox.closePath();
    ox.stroke();
    
    // 4) Chakra Wheel / Reactor Core
    drawChakraWheel(cx, cy, R*0.85, 24, chakraAngle*1.5, cCore, 0.7 + vol*0.3);
    
    // 5) Inner Lotus / Geometrics
    drawLotusRing(cx, cy, R*0.3, R*0.65, 12, -chakraAngle, cAccent, 0.5 + vol*0.3, false);
    
    // 6) Center Core pulse
    ox.beginPath();
    ox.arc(cx, cy, R*0.2 + vol*R*0.1, 0, Math.PI*2);
    ox.fillStyle = cCore;
    ox.globalAlpha = 0.8 + vol*0.2;
    ox.fill();
    ox.globalAlpha = 1;
    
  } catch (err) {
    console.error("DRAW ERROR:", err);
  }
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
const dial = $("dial"), dx = dial ? dial.getContext("2d") : null;
const gauge = $("gauge"), gx = gauge ? gauge.getContext("2d") : null;
function resizeMini(){
  for (const c of [dial,gauge]){
    if (!c) continue;
    const r = c.getBoundingClientRect();
    c.width = r.width*DPR; c.height = r.height*DPR;
    c.getContext("2d").setTransform(DPR,0,0,DPR,0,0);
  }
}
window.addEventListener("resize", resizeMini); setTimeout(resizeMini, 30);

function drawDial(){
  if (!dial) return;
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
  if (!gauge) return;
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
function triggerSystemError(subsystem, code, message, action) {
  $("errSubsystem").textContent = subsystem.toUpperCase();
  $("errCode").textContent = code.toUpperCase();
  $("errMessage").textContent = message;
  if (action) {
    $("errActionContainer").style.display = "flex";
    $("errAction").textContent = action;
  } else {
    $("errActionContainer").style.display = "none";
  }
  $("systemErrorModal").style.display = "flex";
  pushStream("SYSTEM ANOMALY: [" + subsystem + "] - " + code, "warn");
}

$("acknowledgeErrBtn").addEventListener("click", () => {
  $("systemErrorModal").style.display = "none";
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden){ _lastFrame = 0; _dialFrame = 0; }
});

setTimeout(()=>addLine("Hi — type a question below, use the microphone, or open Settings to personalise KALKI.","kalki"), 1600);

if (STATE.busyMode) {
  fetch("/api/listener/pause", {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"}).catch(()=>{});
}
// -------------------------------------------------------------------------
// FLUID ADAPTIVE UI SCALER
// -------------------------------------------------------------------------
function adaptUI() {
  const baseW = 2560; // 2K Design Base Width
  const baseH = 1440; // 2K Design Base Height
  let scale = Math.min(window.innerWidth / baseW, window.innerHeight / baseH);
  if (scale > 1) scale = 1; // Don't scale up past 100%, only shrink for smaller laptops
  
  // Set global rem scale. 1rem = 10px * scale
  document.documentElement.style.fontSize = `${10 * scale}px`;
  document.documentElement.style.setProperty('--ui-scale', scale);
  
  // Remove legacy transform scaling
  document.body.style.transform = "none";
  document.body.style.width = "100%";
  document.body.style.height = "100%";
}
window.addEventListener('resize', adaptUI);
adaptUI();
// Developer Dashboard Logic
let frames = 0;
let lastFpsTime = performance.now();
let currentFps = 0;

function updateDashboard(statusData) {
  const dash = document.getElementById('dev-dashboard');
  if (!dash || dash.style.display === 'none') return;
  
  const now = performance.now();
  frames++;
  if (now - lastFpsTime >= 1000) {
    currentFps = Math.round((frames * 1000) / (now - lastFpsTime));
    frames = 0;
    lastFpsTime = now;
  }
  
  const mem = performance.memory ? (performance.memory.usedJSHeapSize / 1048576).toFixed(1) + ' MB' : 'N/A';
  
  dash.innerHTML = `
    <strong>KALKI DEV DASHBOARD</strong><br>
    FPS: ${currentFps} | Mem: ${mem}<br>
    Scale: ${document.documentElement.style.getPropertyValue('--ui-scale') || 1} | DPR: ${window.devicePixelRatio}<br>
    Res: ${window.innerWidth}x${window.innerHeight} | Canvas: ${Math.round(window.innerWidth*window.devicePixelRatio)}x${Math.round(window.innerHeight*window.devicePixelRatio)}<br>
    Audio Latency: ~50ms | CPU: ${statusData.cpu || 0}%<br>
    Voice State: ${statusData.speaking ? 'SPEAKING' : 'LISTENING'}<br>
    Rec Queue: IDLE | Threads: OK
  `;
}
