def main():
    with open('CHANGES.md', 'r', encoding='utf-8') as f:
        content = f.read()

    changes = """# KALKI Change History

## v2.1.0 — Oversight, Presence & Background Notifications

**Release date:** Unreleased

This release adds comprehensive background monitoring and deepens the system integration without touching the core routing or frontend architecture established in v2.0.0.

- **System Oversight panel.** Added a new 'Oversight' destination to the navigation rail, surfacing live machine telemetry, watched websites, threshold configurations, and a 50-item rolling alert history.
- **Background API reliability.** The backend now implements a robust 1-step fallback for AI requests. If the primary provider fails, KALKI transparently tries the next configured provider (e.g. Gemini or Ollama) before surfacing an error to the user, ensuring uninterrupted service. Added a 'Test connection' button in Settings to verify API keys.
- **Native OS Notifications.** Background loops (alerts, watchdogs, reminders) now generate native Windows toast notifications using `plyer` when KALKI is running hidden in the background, in addition to spoken alerts.
- **Hidden state optimization.** The frontend status loop now correctly detects when the window is hidden (`document.hidden`) and throttles polling to 30s while maintaining background notification capability.
"""

    if "# KALKI Change History" in content:
        content = content.replace("# KALKI Change History", changes)
        with open('CHANGES.md', 'w', encoding='utf-8') as f:
            f.write(content)
        print("CHANGES.md updated")

if __name__ == "__main__":
    main()
