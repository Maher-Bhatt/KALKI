import re
import sys

def main():
    with open('app/server.py', 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        (r'speak\(f"Critical battery, \{config\.OWNER_TITLE\}\. "\s*f"\{pct\} percent\. Plug in immediately\."\)',
         r'speak(f"Critical battery, {config.OWNER_TITLE}. {pct} percent. Plug in immediately."); import oversight, notify; oversight.record_alert("battery", f"Critical battery: {pct}%", "critical"); notify.notify_desktop("Battery Critical", f"Critical battery: {pct}%") if STATE.get("frontend_hidden", False) else None'),
         
        (r'speak\(f"Reminder, \{config\.OWNER_TITLE\}\. "\s*f"\{title\} starts in \{mins\} minute"\s*f"\{\'s\' if mins != 1 else \'\'\}\.", is_notification=True\)',
         r'speak(f"Reminder, {config.OWNER_TITLE}. {title} starts in {mins} minute{\'s\' if mins != 1 else \'\'}.", is_notification=True); import oversight, notify; oversight.record_alert("calendar", f"Event \'{title}\' starts in {mins} min", "info"); notify.notify_desktop("Calendar", f"Event \'{title}\' starts in {mins} min") if STATE.get("frontend_hidden", False) else None'),
         
        (r'speak\(f"Heads up, \{config\.OWNER_TITLE\}\. \{r\[\'host\'\]\} "\s*f"SSL certificate expires in \{cd\} days\.", is_notification=True\)',
         r'speak(f"Heads up, {config.OWNER_TITLE}. {r[\'host\']} SSL certificate expires in {cd} days.", is_notification=True); import oversight, notify; oversight.record_alert("cert-expiring", f"{r[\'host\']} SSL expires in {cd} days", "warning"); notify.notify_desktop("SSL Expiry", f"{r[\'host\']} SSL expires in {cd} days") if STATE.get("frontend_hidden", False) else None')
    ]

    for pat, repl in replacements:
        content, count = re.subn(pat, repl, content)
        if count == 0:
            print(f"Failed to replace: {pat}")
        else:
            print(f"Replaced {count} occurrences of {pat}")

    with open('app/server.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    main()
