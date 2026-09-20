def main():
    with open('KALKI_FRONTEND_CAPABILITY_MAP.md', 'r', encoding='utf-8') as f:
        content = f.read()

    additions = """

## v2.1.0 Additions
- **Oversight Panel (`app/ui/features/oversight.js`)**: Real-time Shodan/monitoring dashboard with CPU/RAM limits, watched sites (API endpoints added in v2.1.0), and 50-item alert history.
- **Desktop Notifications (`app/notify.py`)**: Native plyer toasts when KALKI is backgrounded.
- **Fallback Chain (`app/server.py`)**: Zero-downtime model fallback with unified errors.
"""
    if "v2.1.0" not in content:
        content += additions
        with open('KALKI_FRONTEND_CAPABILITY_MAP.md', 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == "__main__":
    main()
