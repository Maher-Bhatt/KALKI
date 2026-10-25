"""Heuristic audit: find buttons/controls in feature views that have no handler (design stubs)
and hardcoded numbers/strings copied from design/kalki-v2.html."""
import re, glob, os
root = r'e:\KALKI-main\app\ui\features'
design = open(r'e:\KALKI-main\design\kalki-v2.html', encoding='utf-8').read()

# strings from the design that appear verbatim in JS string literals = mock data candidates
design_text = set(t.strip() for t in re.findall(r'>([^<>{}]{6,80})<', design))
for f in sorted(glob.glob(os.path.join(root, '*.js'))):
    src = open(f, encoding='utf-8', errors='ignore').read()
    name = os.path.basename(f)
    lits = set(re.findall(r"'([^'\n]{6,80})'", src)) | set(re.findall(r'"([^"\n]{6,80})"', src))
    hits = sorted(l for l in lits if l.strip() in design_text)
    stubs = re.findall(r"h\('button[^']*',\s*(?:null|\{(?![^}]*onClick)[^}]*\})", src)
    dataI = len(re.findall(r"'data-i'", src))
    print(f"\n== {name}: data-i icons={dataI}, handlerless buttons={len(stubs)}, design-copied strings={len(hits)}")
    for l in hits[:40]:
        print('   ', repr(l))
