import re, glob, os
root = r'e:\KALKI-main\app\ui'
css = ''
for f in glob.glob(os.path.join(root, '*.css')):
    css += open(f, encoding='utf-8').read()
defined = set(re.findall(r'\.([a-zA-Z_][\w-]*)', css))

used = {}
for f in glob.glob(os.path.join(root, '**', '*.js'), recursive=True):
    src = open(f, encoding='utf-8', errors='ignore').read()
    rel = os.path.relpath(f, root)
    # h('div.a.b', ...) / h('a.b'
    for m in re.finditer(r"h\(\s*'([a-z0-9]*)((?:\.[\w-]+)+)", src):
        for c in m.group(2).split('.')[1:]:
            used.setdefault(c, set()).add(rel)
    for m in re.finditer(r"class:\s*[`']([^`'$]+)", src):
        for c in m.group(1).split():
            used.setdefault(c, set()).add(rel)
    for m in re.finditer(r"className\s*=\s*[`']([^`'$]+)", src):
        for c in m.group(1).split():
            used.setdefault(c, set()).add(rel)

missing = {c: sorted(v) for c, v in used.items() if c not in defined}
for c in sorted(missing):
    print(f"{c:28s} {', '.join(missing[c])}")
print(len(missing), 'undefined classes')
