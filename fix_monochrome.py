import re

with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix topbar gradient
html = re.sub(
    r'\.topbar\s*\{([^\}]+)\}',
    '.topbar{\n  position:fixed;top:0;left:0;right:0;height:64px;z-index:20;\n  display:flex;align-items:center;justify-content:space-between;\n  padding:0 28px;\n  border-bottom: 1px solid var(--frame);\n  background: rgba(10,10,10,0.9);\n  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);\n}',
    html
)

# Fix readout line background
html = re.sub(
    r'\.readout \.line\s*\{([^\}]+)\}',
    '.readout .line{\n  display:block;margin:5px 0;padding:10px 14px 10px 18px;\n  border:1px solid var(--frame-strong);\n  background: rgba(15,15,15,0.9);\n  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);\n  font-size:13px;line-height:1.55;color:var(--text);\n  word-wrap:break-word;white-space:pre-wrap;\n  position:relative;\n  border-radius:4px;\n  animation: lineIn .28s ease-out;\n}',
    html
)

# Remove composer lotus icons
html = re.sub(r'\.composer::before\s*\{[^\}]+\}', '', html)
html = re.sub(r'\.composer::after\s*\{[^\}]+\}', '', html)

# Fix composer input background
html = re.sub(
    r'#input\s*\{([^\}]+)\}',
    '#input{\n  flex:1;background:#111111;\n  border:1px solid var(--frame-strong);color:var(--text);\n  padding:14px 22px;font-size:14px;font-family:inherit;outline:none;\n  letter-spacing:0;\n  clip-path:polygon(14px 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,14px 100%,0 50%);\n  transition: border-color .25s;\n}',
    html
)

# Fix lime and red variables to white/gray for monochrome
html = html.replace('--lime: #00ff00;', '--lime: #ffffff;')
html = html.replace('--red: #ff3333;', '--red: #cccccc;')

# Add click event listener to #center-container
# Find the line: window.addEventListener("resize", resizeOrb); resizeOrb();
# and append the click listener there.
if 'center-container").addEventListener("click"' not in html:
    html = html.replace(
        'window.addEventListener("resize", resizeOrb); resizeOrb();',
        'window.addEventListener("resize", resizeOrb); resizeOrb();\n\ndocument.getElementById("center-container").addEventListener("click", () => { if(typeof toggleMic === "function") toggleMic(); });'
    )

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
