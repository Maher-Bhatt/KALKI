import re

def main():
    with open('app/ui/lib/dom.js', 'r', encoding='utf-8') as f:
        content = f.read()

    helper = """
export async function withCheckmark(btn, p) {
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
}
"""
    if "withCheckmark" not in content:
        content += helper
        with open('app/ui/lib/dom.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("dom.js patched")

if __name__ == "__main__":
    main()
