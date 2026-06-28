import re

with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove the old .hud block (which was left behind)
html = re.sub(r'\.hud\{.*?\.hud \.title\{.*?\n\}', '', html, flags=re.DOTALL)

# 2. Update .pill and .top-meta tags
# Current .pill
html = re.sub(
    r'\.pill\s*\{[^\}]+\}',
    '.pill {\n  color:var(--saffron);\n  border: 1px solid var(--gold);\n  border-radius: 20px;\n  background: rgba(10,10,10,0.85);\n  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);\n  text-transform:uppercase; z-index:25; font-weight:600;\n  box-shadow: 0 4px 12px rgba(0,0,0,0.6);\n  font-family:"Cinzel", serif;\n  transition: border-color .5s ease;\n}',
    html
)
# Current .top-meta div
html = re.sub(
    r'\.top-meta div\s*\{[^\}]+\}',
    '.top-meta div {\n  padding:4px 12px;\n  border-radius:20px;\n  border: 1px solid var(--gold);\n  background:rgba(10,10,10,0.8);\n  color:var(--saffron);\n}',
    html
)

# 3. Status dots
html = re.sub(
    r'\.dot\.online\s*\{[^\}]+\}',
    '.dot.online { background:#00ff00; box-shadow: 0 0 8px #00ff00; }',
    html
)
html = re.sub(
    r'\.dot\.standby\s*\{[^\}]+\}',
    '.dot.standby { background:var(--amber); box-shadow: 0 0 8px var(--amber); }',
    html
)

# 4. Progress bars (track and fill)
html = re.sub(
    r'\.track\s*\{[^\}]+\}',
    '.track {\n  flex:1; height:4px; background:rgba(20,20,20,0.9);\n  border-radius:2px; overflow:hidden;\n  border: 1px solid rgba(255,215,0,0.2);\n}',
    html
)
html = re.sub(
    r'\.fill\s*\{[^\}]+\}',
    '.fill {\n  height:100%; background:var(--gold);\n  box-shadow: 0 0 5px var(--gold);\n  transition: width 0.3s ease;\n}',
    html
)

# 5. Bottom message bar ("KALKI online. Awaiting orders, Sir.")
# This is in the boot lines and .stream
html = re.sub(
    r'\.stream div\s*\{[^\}]+\}',
    '.stream div {\n  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; animation:streamIn .2s ease-out;\n  background: rgba(10,10,10,0.9);\n  color: var(--gold);\n  border-left: 3px solid var(--saffron);\n  padding: 4px 8px;\n  margin-bottom: 4px;\n}',
    html
)

# 6. Bottom Command Bar
html = re.sub(
    r'\.composer\s*\{[^\}]+\}',
    '.composer {\n  position:fixed; bottom:28px; left:50%; transform:translateX(-50%); width:600px;\n  display:flex; align-items:center; gap:8px;\n  background:rgba(10,10,10,0.9);\n  border:1px solid var(--gold);\n  border-radius:8px;\n  padding:8px 12px;\n  z-index:20;\n  box-shadow:0 0 15px rgba(255,215,0,0.2);\n  transition: box-shadow 0.3s ease;\n}\n.composer:focus-within {\n  animation: breatheGlow 2s infinite alternate;\n}\n@keyframes breatheGlow {\n  from { box-shadow: 0 0 10px rgba(255,215,0,0.2); }\n  to { box-shadow: 0 0 25px rgba(255,215,0,0.6); }\n}',
    html
)

# Add lotus to composer
if '.composer::before' not in html:
    html = html.replace('.composer {', '.composer::before { content: "🪷"; color: var(--gold); margin-right: 8px; }\n.composer::after { content: "🪷"; color: var(--gold); margin-left: 8px; }\n.composer {')

# 7. Tactical ops buttons (qbtn)
html = re.sub(
    r'\.qbtn\s*\{[^\}]+\}',
    '.qbtn {\n  background: rgba(10,10,10,0.9);\n  border: 1px solid var(--gold);\n  color: var(--gold);\n  padding: 6px 12px;\n  border-radius: 4px;\n  cursor: pointer;\n  text-align: left;\n  font-family: "Cinzel", serif;\n  font-size: 11px;\n  transition: all 0.3s ease;\n}\n.qbtn:hover {\n  background: rgba(255,215,0,0.15);\n  box-shadow: 0 0 10px rgba(255,215,0,0.3);\n}',
    html
)

# Replace '◢ ' with lotus SVG or emoji
html = html.replace('◢ ', '🪷 ')
html = html.replace('▸ ', '🪷 ')

# 8. Audio waveform color
html = html.replace('wx.strokeStyle = `hsla(${hue}, 80%, 60%, ${a})`;', 'wx.strokeStyle = `rgba(255, 215, 0, ${a})`;')
html = html.replace('wx.strokeStyle = C.accent;', 'wx.strokeStyle = "#FFD700";')
html = html.replace('wx.fillStyle = `hsla(${hue}, 80%, 60%, ${a})`;', 'wx.fillStyle = `rgba(255, 215, 0, ${a})`;')

# 9. Gauge colors (remove cyan)
html = html.replace('drawArcRing(cx, cy, R, 40, t*0.01, "#00ffcc", 2, 0.2);', 'drawArcRing(cx, cy, R, 40, t*0.01, "#FFD700", 2, 0.2);')
html = html.replace('drawArcRing(cx, cy, R*0.8, 12, -t*0.005, C.ring, 4, 0.3);', 'drawArcRing(cx, cy, R*0.8, 12, -t*0.005, "#FF6B00", 4, 0.3);')

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
