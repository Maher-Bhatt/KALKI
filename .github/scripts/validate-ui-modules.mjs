/* Static validation for app/ui/: every module parses, and every static or
 * dynamic import resolves to a file that actually exports the names being
 * imported. No network, no jsdom — this is the fast check that runs on every
 * push; harness-based functional testing is a separate, manual pass.
 *
 * Run from the repository root: node .github/scripts/validate-ui-modules.mjs
 */
import fs from 'fs';
import path from 'path';
import vm from 'vm';

const root = path.join(process.cwd(), 'app', 'ui');
if (!fs.existsSync(root)) {
  console.error(`app/ui not found at ${root} — run this from the repository root.`);
  process.exit(1);
}

const files = [];
(function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p);
    else if (entry.name.endsWith('.js')) files.push(p);
  }
})(root);

let errors = 0;
const exportsOf = new Map();

for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  try {
    new vm.SourceTextModule(src, { identifier: f });
  } catch (e) {
    console.log(`SYNTAX   ${path.relative(root, f)}: ${e.message}`);
    errors++;
    continue;
  }
  const names = new Set();
  for (const m of src.matchAll(/^export\s+(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z0-9_$]+)/gm)) names.add(m[1]);
  for (const m of src.matchAll(/^export\s*\{([^}]+)\}/gm)) {
    for (const part of m[1].split(',')) {
      const t = part.trim();
      if (!t) continue;
      names.add(t.includes(' as ') ? t.split(/\s+as\s+/)[1].trim() : t);
    }
  }
  if (/^export\s+default/m.test(src)) names.add('default');
  exportsOf.set(path.resolve(f), names);
}

for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  const rel = path.relative(root, f);

  for (const m of src.matchAll(/import\s+([^'"]*?)\s*from\s*['"](\.[^'"]+)['"]/g)) {
    const target = path.resolve(path.dirname(f), m[2]);
    if (!fs.existsSync(target)) { console.log(`MISSING  ${rel} -> ${m[2]}`); errors++; continue; }
    const braces = m[1].trim().match(/\{([^}]*)\}/);
    if (!braces) continue;
    const have = exportsOf.get(target) || new Set();
    for (const part of braces[1].split(',')) {
      const t = part.trim();
      if (!t) continue;
      const name = t.split(/\s+as\s+/)[0].trim();
      if (name && !have.has(name)) { console.log(`NOEXPORT ${rel}: '${name}' not exported by ${m[2]}`); errors++; }
    }
  }
  for (const m of src.matchAll(/import\s*\(\s*['"](\.[^'"]+)['"]\s*\)/g)) {
    const target = path.resolve(path.dirname(f), m[1]);
    if (!fs.existsSync(target)) { console.log(`MISSING(dyn) ${rel} -> ${m[1]}`); errors++; }
  }
}

console.log(errors ? `\n${errors} problem(s) across ${files.length} modules` : `\nAll ${files.length} app/ui modules parse and resolve cleanly.`);
process.exit(errors ? 1 : 0);
