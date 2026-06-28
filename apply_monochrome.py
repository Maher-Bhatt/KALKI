import re

with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Fonts
html = re.sub(
    r'@import url\([^\)]+\);',
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');",
    html
)
html = html.replace('"Mukta", "Cinzel", serif', '"Inter", sans-serif')
html = html.replace('"Cinzel", serif', '"Inter", sans-serif')
html = html.replace('"Cinzel",serif', '"Inter", sans-serif')
html = html.replace('"JetBrains Mono","Consolas",monospace', '"JetBrains Mono", monospace')

# 2. CSS Variables
css_vars = """
:root{
  --bg: #0a0a0a;
  --bg-elev: #111111;
  --bg-panel: rgba(15, 15, 15, 0.9);
  --text: #ffffff;
  --text-dim: #888888;
  --frame: #333333;
  --frame-strong: #666666;
  --accent: #ffffff;
  --accent-glow: transparent;
  --accent-soft: rgba(255, 255, 255, 0.1);
  --lime: #00ff00;
  --orange: #ff9900;
  --red: #ff3333;
}
"""
html = re.sub(r':root\s*\{.*?\}(?=\s*/\* state-driven accents)', css_vars, html, flags=re.DOTALL)

# 3. State-driven accents (pure monochrome)
state_accents = """/* state-driven accents */
body.mode-idle      { --accent: #ffffff; --accent-glow:transparent; --accent-soft:rgba(255,255,255,0.05); }
body.mode-listening { --accent: #ffffff; --accent-glow:rgba(255,255,255,0.2); --accent-soft:rgba(255,255,255,0.1); }
body.mode-thinking  { --accent: #ffffff; --accent-glow:transparent; --accent-soft:rgba(255,255,255,0.05); }
body.mode-speaking  { --accent: #ffffff; --accent-glow:transparent; --accent-soft:rgba(255,255,255,0.1); }
"""
html = re.sub(r'/\* state-driven accents \*/.*?\}', state_accents, html, count=1, flags=re.DOTALL)

# 4. Background and Overlays
# Fix the broken body::before / body::after from previous replacement
html = re.sub(
    r'body::before\s*\{.*?\}',
    'body::before{\n  content:"";position:fixed;inset:0;z-index:0;pointer-events:none;\n  background: #0a0a0a;\n}',
    html,
    flags=re.DOTALL
)
html = re.sub(
    r'body::after\s*\{.*?\}',
    'body::after{\n  content:"";position:fixed;inset:0;z-index:1;pointer-events:none;\n  background: radial-gradient(circle at 50% 50%, var(--accent-soft) 0%, transparent 60%);\n  transition: background .8s ease;\n  opacity: 0.6;\n}',
    html,
    flags=re.DOTALL
)

# 5. Fix UI panels and Buttons
html = re.sub(
    r'\.hud\s*\{([^\}]+)\}',
    '.hud {\n  position:fixed; z-index:15;\n  border: 1px solid var(--frame);\n  background: var(--bg-panel);\n  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);\n  padding:15px 17px; font-size:12px;\n  border-radius: 6px;\n  box-shadow: 0 4px 20px rgba(0,0,0,0.5);\n}',
    html
)
html = re.sub(
    r'\.qbtn\s*\{([^\}]+)\}',
    '.qbtn {\n  background: rgba(20,20,20,0.9);\n  border: 1px solid var(--frame);\n  color: var(--text);\n  padding: 6px 12px;\n  border-radius: 4px;\n  cursor: pointer;\n  text-align: left;\n  font-family: "Inter", sans-serif;\n  font-size: 11px;\n  font-weight: 600;\n  text-transform: uppercase;\n  transition: all 0.2s ease;\n}',
    html
)
html = re.sub(
    r'\.qbtn:hover\s*\{([^\}]+)\}',
    '.qbtn:hover {\n  background: rgba(255,255,255,0.1);\n  border-color: var(--text);\n}',
    html
)

# 6. Topbar Logo & Text
html = html.replace('Bharat Core', 'System Core')
html = html.replace('BHARAT', 'SYSTEM')

logo_svg = """<svg viewBox="0 0 100 100" class="chakra" aria-hidden="true">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#ffffff" stroke-width="3" stroke-dasharray="10 4"/>
        <circle cx="50" cy="50" r="25" fill="none" stroke="#ffffff" stroke-width="1"/>
        <circle cx="50" cy="50" r="10" fill="#ffffff"/>
      </svg>"""
html = re.sub(r'<svg viewBox="0 0 100 100" class="chakra".*?</svg>', logo_svg, html, flags=re.DOTALL)

# 7. Remove Center Mandala
html = re.sub(r'<img id="center-mandala"[^>]*>', '', html)

# 8. Rewrite drawOrb to minimal white ring
drawOrb_code = """function drawOrb() {
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
    
    const glow = ox.createRadialGradient(cx, cy, R*0.5, cx, cy, R*1.5);
    glow.addColorStop(0, "rgba(255,255,255," + (0.05 + vol*0.2) + ")");
    glow.addColorStop(1, "rgba(0,0,0,0)");
    
    ox.fillStyle = glow;
    ox.beginPath(); ox.arc(cx, cy, R*1.5, 0, Math.PI*2); ox.fill();
    
    ox.strokeStyle = "#ffffff";
    ox.lineWidth = 1 + vol*3;
    ox.globalAlpha = 0.5 + vol*0.5;
    ox.beginPath(); ox.arc(cx, cy, R, 0, Math.PI*2); ox.stroke();
    ox.globalAlpha = 1;
    
    // audio ring
    ox.beginPath();
    for(let i=0; i<72; i++) {
        let angle = (i/72) * Math.PI * 2 + (t*0.01);
        let v = STATE.freqData[i]/255;
        let ext = R + (v * R * 0.3);
        let px = cx + Math.cos(angle) * ext;
        let py = cy + Math.sin(angle) * ext;
        if(i===0) ox.moveTo(px,py);
        else ox.lineTo(px,py);
    }
    ox.closePath();
    ox.lineWidth = 1;
    ox.stroke();
    
  } catch (err) {
    console.error("DRAW ERROR:", err);
  }
}"""
html = re.sub(r'function drawOrb\(\)\s*\{.*?\}\s*(?=function drawArcRing|function )', drawOrb_code + "\n\n", html, flags=re.DOTALL)

# Remove Kalash dial shape
html = re.sub(
    r'\.dial\s*\{([^\}]+)\}',
    '.dial {\n  position:relative;width:100%;height:110px;margin-top:6px;\n  border: 1px solid var(--frame);\n  border-radius: 50%;\n  background: rgba(15,15,15, 0.8);\n}',
    html
)

# Remove stray color codes just in case
html = html.replace('#C9A84C', '#ffffff')
html = html.replace('rgba(201, 168, 76,', 'rgba(255,255,255,')
html = html.replace('rgba(201,168,76,', 'rgba(255,255,255,')
html = html.replace('var(--saffron)', '#ffffff')
html = html.replace('var(--amber)', '#ffffff')
html = html.replace('var(--gold)', '#ffffff')

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
