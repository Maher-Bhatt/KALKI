import re

with open('c:/Jarvis/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Use regex to replace the entire drawOrb function up to the next function definition
pattern = r'function drawOrb\(\)\s*\{.*?\}\s*(?=function drawArcRing)'
replacement = '''function drawOrb() {
  if (!ox) return;
  try {
    ox.clearRect(0,0,W,H);
  } catch (err) {
    console.error("DRAW ERROR:", err);
  }
}

'''
html = re.sub(pattern, replacement, html, flags=re.DOTALL)

with open('c:/Jarvis/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
