import os

def patch_router():
    path = "app/ui/features/router.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_r = "const ROUTES = ['ask', 'today', 'memory', 'workbench', 'oversight', 'security', 'settings'];"
    new_r = "const ROUTES = ['ask', 'today', 'memory', 'workbench', 'oversight', 'security', 'settings', 'pres'];"
    if old_r in content:
        content = content.replace(old_r, new_r, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched router.js: added 'pres' route")
    else:
        print("Warning: old ROUTES not found in router.js")


def patch_security():
    path = "app/ui/features/security.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_sec = '''  if (r.ok) {
    const { ok: _drop, ...rest } = r.data;
    result = rest;'''

    new_sec = '''  if (r.ok) {
    const rest = (r.data && typeof r.data === 'object') ? { ...r.data } : { result: r.data };
    delete rest.ok;
    result = rest;'''

    if old_sec in content:
        content = content.replace(old_sec, new_sec, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched security.js: safe data destructuring")
    else:
        print("Warning: old_sec not found in security.js")


def patch_dom():
    path = "app/ui/lib/dom.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_chk = '''export async function withCheckmark(btn, p) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  const styleW = btn.style.width;
  if (!styleW) btn.style.width = btn.offsetWidth + 'px';
  try {
    const res = await p;
    if (res && res.ok === false) {
      btn.disabled = false;
      btn.innerHTML = orig;
      btn.style.width = styleW;
      return res;
    }
    btn.classList.add('is-success');
    btn.innerHTML = '&#10003;';
    setTimeout(() => { 
      btn.classList.remove('is-success'); 
      btn.innerHTML = orig; 
      btn.style.width = styleW;
      btn.disabled = false; 
    }, 2000);
    return res;
  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = orig;
    btn.style.width = styleW;
    throw err;
  }
}'''

    new_chk = '''export async function withCheckmark(btn, p) {
  const origNodes = Array.from(btn.childNodes);
  btn.disabled = true;
  const styleW = btn.style.width;
  if (!styleW) btn.style.width = btn.offsetWidth + 'px';
  const restore = () => {
    btn.replaceChildren(...origNodes);
    btn.style.width = styleW;
    btn.disabled = false;
    btn.classList.remove('is-success');
  };
  try {
    const res = await p;
    if (res && res.ok === false) {
      restore();
      return res;
    }
    btn.classList.add('is-success');
    btn.textContent = '✓';
    setTimeout(restore, 2000);
    return res;
  } catch (err) {
    restore();
    throw err;
  }
}'''

    if old_chk in content:
        content = content.replace(old_chk, new_chk, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched dom.js: withCheckmark preserves child nodes and listeners")
    else:
        print("Warning: old_chk not found in dom.js")


def patch_store():
    path = "app/ui/state/store.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_set = '''export function set(slice, patch) {
  Object.assign(store[slice], patch);
  notify();
}'''

    new_set = '''export function set(slice, patch) {
  store[slice] = Object.assign(store[slice] || {}, patch);
  notify();
}'''

    if old_set in content:
        content = content.replace(old_set, new_set, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched store.js: safe slice default in set()")
    else:
        print("Warning: old_set not found in store.js")


def patch_tokens():
    path = "app/ui/tokens.css"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("@media(prefers-color-scheme:light){:root{}}\n", "").replace("@media(prefers-color-scheme:light){:root{}}", "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print("Patched tokens.css: cleaned empty light mode query")


def patch_ask():
    path = "app/ui/features/ask.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pre-append composer to welcome slot if no messages during initial view construction
    old_ask_init = '''  const composerSlot = h('div.welcome-comp-slot');

  const welcomeWrap = h('div.welcome-stage', null,'''

    new_ask_init = '''  const composerSlot = h('div.welcome-comp-slot');
  if (!conv.active()?.messages?.length) {
    composerSlot.appendChild(c.el);
  }

  const welcomeWrap = h('div.welcome-stage', null,'''

    if old_ask_init in content:
        content = content.replace(old_ask_init, new_ask_init, 1)
        print("Patched ask.js: initial composer placement prevents layout jump")
    else:
        print("Warning: old_ask_init not found in ask.js")

    # Add onError fallback to album art cover image
    old_art = '''        const artEl = d.thumbnail
          ? h('img.music-cover', {
              src: d.thumbnail,
              alt: title,'''

    new_art = '''        const artEl = d.thumbnail
          ? h('img.music-cover', {
              src: d.thumbnail,
              alt: title,
              onError: (e) => {
                const p = e.target.parentElement;
                if (p) {
                  const fallback = h('div.music-cover-fallback', null, icon('music', 20));
                  p.replaceChild(fallback, e.target);
                }
              },'''

    if old_art in content:
        content = content.replace(old_art, new_art, 1)
        print("Patched ask.js: album art error fallback")
    else:
        print("Warning: old_art not found in ask.js")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    patch_router()
    patch_security()
    patch_dom()
    patch_store()
    patch_tokens()
    patch_ask()
    print("All UI patches applied successfully!")
