import re

with open(r'E:\PROJECT\KALKI-main\app\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Fix responsive header
html = html.replace('.top-meta > div:not(:last-child) { display:none; }', 
                    '.top-meta { flex-wrap: wrap; height: auto; padding: 0.5rem 0; gap: 0.5rem; }')

# 2. Fix the Pill position so it floats at the center bottom again (instead of just sitting wherever)
html = html.replace('.pill {\n    color:#ffffff;', 
                    '.pill {\n    position: fixed;\n    bottom: 6rem;\n    left: 50%;\n    transform: translateX(-50%);\n    color:#ffffff;')

html = html.replace('.pill:hover {\n    transform: scale(1.05);', 
                    '.pill:hover {\n    transform: translateX(-50%) scale(1.05);')

# 3. Remove the orb canvas and its animation loop
html = re.sub(r'<div id="center-container">.*?<canvas id="orb"></canvas>.*?</div>', '', html, flags=re.DOTALL)
html = re.sub(r'const orb = document\.getElementById\("orb"\);.*?requestAnimationFrame\(drawOrb\);', '', html, flags=re.DOTALL)
html = re.sub(r'document\.getElementById\("center-container"\).*?;', '', html, flags=re.DOTALL)
html = re.sub(r'function resizeOrb\(\).*?resizeOrb\(\);', '', html, flags=re.DOTALL)

with open(r'E:\PROJECT\KALKI-main\app\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("index.html patched")
