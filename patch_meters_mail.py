import re

# 1. Update server.py
with open('c:/Jarvis/server.py', 'r', encoding='utf-8') as f:
    server_py = f.read()

needs_mail_code = """
def needs_mail(text):
    low = text.lower()
    return any(k in low for k in ('mail', 'email', 'inbox'))

def ask_ai(user_messages, force_search=False):"""

if 'def needs_mail' not in server_py:
    server_py = server_py.replace('def ask_ai(user_messages, force_search=False):', needs_mail_code)

mail_injection = """
    if last_user and needs_mail(last_user):
        import mail as mailmod
        try:
            em = mailmod.summary_for_speech(limit=5)
            sys_prompt += f"\\n\\nCURRENT INBOX SUMMARY:\\n{em}\\n"
        except Exception as e:
            sys_prompt += f"\\n\\nCURRENT INBOX SUMMARY:\\nCould not fetch mail: {e}\\n"

    msgs = [{"role": "system", "content": sys_prompt}] + user_messages"""

if 'CURRENT INBOX SUMMARY' not in server_py:
    server_py = server_py.replace('    msgs = [{"role": "system", "content": sys_prompt}] + user_messages', mail_injection)

with open('c:/Jarvis/server.py', 'w', encoding='utf-8') as f:
    f.write(server_py)

# 2. Update index.html
with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    index_html = f.read()

# Change Titles
index_html = index_html.replace('NAVIGATION DIAL', 'CPU LOAD (60s)')
index_html = index_html.replace('REACTOR OUTPUT', 'MEMORY USAGE (60s)')

# Inject history variables and drawing logic
js_additions = """
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

"""

# Hook into updateDiag
updateDiag_injection = """
      $("sUp").textContent = d.uptime||"0s";
      
      cpuHistory.push(parseInt(d.cpu||0));
      cpuHistory.shift();
      ramHistory.push(parseInt(d.ram||0));
      ramHistory.shift();
      
      drawHistoryGraph("dial", cpuHistory, "#ffffff");
      drawHistoryGraph("gauge", ramHistory, "#aaaaaa");
"""

if 'cpuHistory = new Array' not in index_html:
    index_html = index_html.replace('const orb = $("orb"), ox = orb.getContext("2d");', js_additions + '\nconst orb = $("orb"), ox = orb.getContext("2d");')

if 'cpuHistory.push(' not in index_html:
    index_html = index_html.replace('$("sUp").textContent = d.uptime||"0s";', updateDiag_injection)

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(index_html)
