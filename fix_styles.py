import re

with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. COLOR FIX
# Replace #FFD700 (bright gold) and var(--gold) with #C9A84C
html = html.replace('#FFD700', '#C9A84C')
html = html.replace('#FFFF00', '#C9A84C')
html = html.replace('rgba(255, 215, 0,', 'rgba(201, 168, 76,') # rgba of FFD700
html = html.replace('rgba(255,215,0,', 'rgba(201,168,76,')

# Update CSS variables to use #C9A84C
html = re.sub(r'--gold:\s*[^;]+;', '--gold: #C9A84C;', html)
html = re.sub(r'--text:\s*[^;]+;', '--text: #C9A84C;', html)
html = re.sub(r'--accent:\s*[^;]+;', '--accent: #C9A84C;', html)

# Remove glows in modes
html = html.replace('--accent-glow:rgba(255,215,0,0.4)', '--accent-glow:transparent')
html = html.replace('--accent-glow:rgba(255,153,51,0.5)', '--accent-glow:transparent')
html = html.replace('--accent-glow:rgba(255,107,0,0.5)', '--accent-glow:transparent')
html = html.replace('--accent-glow:rgba(201,168,76,0.4)', '--accent-glow:transparent')

# 2. CENTER FIX - Perfectly circular and centered
html = re.sub(
    r'#center-mandala\s*\{[^\}]+\}',
    '#center-mandala {\n  position: absolute;\n  width: 350px;\n  height: 350px;\n  object-fit: contain;\n  animation: rotateMandala 20s linear infinite;\n  z-index: 5;\n  border-radius: 50%;\n}',
    html
)
html = re.sub(
    r'#orb\s*\{[^\}]+\}',
    '#orb {\n  position: absolute;\n  left:50%; top:50%;\n  transform: translate(-50%, -50%);\n  width: 450px;\n  height: 450px;\n  z-index: 6;\n  pointer-events: none;\n}',
    html
)
html = re.sub(
    r'@keyframes glowPulse\s*\{[^\}]+\}',
    '',
    html
)

# 3. BORDER FIX - Thin and elegant, no glow
html = re.sub(
    r'\.hud\s*\{([^\}]+)\}',
    '.hud {\n  position:fixed; z-index:15;\n  border: 1px solid #C9A84C;\n  background: rgba(10,10,10,0.85);\n  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);\n  padding:15px 17px; font-size:12px;\n  border-radius: 4px;\n  box-shadow: none;\n}',
    html
)
# Remove lotus corners and outer borders for HUD
html = re.sub(r'\.hud::before\s*\{[^\}]+\}', '', html)
html = re.sub(r'\.hud::after\s*\{[^\}]+\}', '', html)

# 4. BUTTON FIX - Remove emoji/icons from tactical ops buttons
html = html.replace('🪷 ', '')
html = html.replace('▸ ', '')
html = html.replace('◢ ', '')

html = re.sub(
    r'\.qbtn\s*\{([^\}]+)\}',
    '.qbtn {\n  background: rgba(10,10,10,0.9);\n  border: 1px solid #C9A84C;\n  color: #C9A84C;\n  padding: 6px 12px;\n  border-radius: 4px;\n  cursor: pointer;\n  text-align: left;\n  font-family: "Cinzel", serif;\n  font-size: 11px;\n  transition: all 0.3s ease;\n  box-shadow: none;\n}',
    html
)
html = re.sub(
    r'\.qbtn:hover\s*\{([^\}]+)\}',
    '.qbtn:hover {\n  background: rgba(201,168,76,0.15);\n  box-shadow: none;\n}',
    html
)

# 5. BACKGROUND FIX - True black #0a0a0a
html = re.sub(
    r'background:\s*radial-gradient\([^\)]+\)',
    'background: #0a0a0a',
    html
)
# Ensure the body uses pure black
html = re.sub(r'--bg:\s*[^;]+;', '--bg: #0a0a0a;', html)

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
