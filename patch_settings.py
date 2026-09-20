import re

def main():
    with open('app/ui/features/settings.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_usage_row = """    row('Usage', 'Tokens and latency recorded per model on this machine.',
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: showMetrics }, 'View usage')),"""

    new_usage_row = """    row('Connection', 'Verify your API keys and network access.',
      h('button.btn.btn-sm.btn-secondary', {
        type: 'button',
        onClick: async (e) => {
          const btn = e.currentTarget;
          const orig = btn.innerHTML;
          btn.disabled = true;
          btn.textContent = 'Testing...';
          const r = await api.test();
          if (r.ok && r.data.groq === 'OK') {
            btn.classList.add('is-success');
            btn.innerHTML = '&#10003; Connected';
            setTimeout(() => { btn.classList.remove('is-success'); btn.innerHTML = orig; btn.disabled = false; }, 2000);
          } else {
            err(r.message || 'Connection failed', r.detail || (r.data && r.data.groq !== 'OK' ? `Groq: ${r.data.groq}` : 'Unknown'));
            btn.innerHTML = orig;
            btn.disabled = false;
          }
        },
      }, 'Test connection')),
    row('Usage', 'Tokens and latency recorded per model on this machine.',
      h('button.btn.btn-sm.btn-secondary', { type: 'button', onClick: showMetrics }, 'View usage')),"""

    if old_usage_row in content:
        content = content.replace(old_usage_row, new_usage_row)
        with open('app/ui/features/settings.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched settings.js successfully.")
    else:
        print("Could not find usage row in settings.js.")

if __name__ == "__main__":
    main()
