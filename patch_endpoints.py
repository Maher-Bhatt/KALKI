import re
import sys

def main():
    with open('app/ui/api/endpoints.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # Patch system.status
    old_status = "status: (signal) => get('/api/status', { signal, timeout: 8000 }),"
    new_status = "status: (hidden) => get(hidden ? '/api/status?hidden=1' : '/api/status', { timeout: 8000 }),"

    if old_status in content:
        content = content.replace(old_status, new_status)
    else:
        print("Could not find system.status in endpoints.js")

    # Add oversight endpoints
    if "export const oversight" not in content:
        oversight_code = """
/* ── Oversight ────────────────────────────────────────────────────────── */
export const oversight = {
  status: () => get('/api/oversight/status'),
  watchdogAdd: (url, label) => post('/api/oversight/watchdog/add', { url, label }),
  watchdogRemove: (url) => post('/api/oversight/watchdog/remove', { url }),
  watchdogCheck: (url) => post('/api/oversight/watchdog/check', { url }),
};
"""
        content += oversight_code

    with open('app/ui/api/endpoints.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("endpoints.js patched.")

if __name__ == "__main__":
    main()
