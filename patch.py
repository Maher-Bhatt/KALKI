import re
import sys

def main():
    with open('app/server.py', 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        (r'speak\(f"Reminder, \{config\.OWNER_TITLE\}: \{r\[\'text\'\]\}"\)',
         r'speak(f"Reminder, {config.OWNER_TITLE}: {r[\'text\']}"); import oversight, notify; oversight.record_alert("reminder", r[\'text\'], "info"); notify.notify_desktop("Reminder", r[\'text\']) if STATE.get("frontend_hidden", False) else None'),
        
        (r'speak\(f"Internet connection restored, \{config\.OWNER_TITLE\}\."\)',
         r'speak(f"Internet connection restored, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("network", "Internet connection restored", "info"); notify.notify_desktop("Network", "Internet connection restored") if STATE.get("frontend_hidden", False) else None'),
         
        (r'speak\(f"Internet connection lost, \{config\.OWNER_TITLE\}\."\)',
         r'speak(f"Internet connection lost, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("network", "Internet connection lost", "warning"); notify.notify_desktop("Network", "Internet connection lost") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Charging started\. Estimated time to full is \{mins\} minutes\."\)',
         r'speak(f"Charging started. Estimated time to full is {mins} minutes."); import oversight, notify; oversight.record_alert("battery", f"Charging started. {mins}m to full.", "info"); notify.notify_desktop("Battery", f"Charging started. {mins}m to full.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\("Charging started\."\)',
         r'speak("Charging started."); import oversight, notify; oversight.record_alert("battery", "Charging started.", "info"); notify.notify_desktop("Battery", "Charging started.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\("Power connected\. Battery is already fully charged\."\)',
         r'speak("Power connected. Battery is already fully charged."); import oversight, notify; oversight.record_alert("battery", "Power connected. Battery full.", "info"); notify.notify_desktop("Battery", "Power connected. Battery full.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\("Running on battery power\."\)',
         r'speak("Running on battery power."); import oversight, notify; oversight.record_alert("battery", "Running on battery power.", "info"); notify.notify_desktop("Battery", "Running on battery power.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\("Battery is fully charged\. You may disconnect the power\."\)',
         r'speak("Battery is fully charged. You may disconnect the power."); import oversight, notify; oversight.record_alert("battery", "Battery is fully charged.", "info"); notify.notify_desktop("Battery", "Battery is fully charged.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Warning! Battery at \{pct\} percent\. System will shut down soon\."\)',
         r'speak(f"Warning! Battery at {pct} percent. System will shut down soon."); import oversight, notify; oversight.record_alert("battery", f"Battery at {pct}%. Shutting down soon.", "critical"); notify.notify_desktop("Battery Critical", f"Battery at {pct}%. Shutting down soon.") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Critical battery, \{config\.OWNER_TITLE\}\. "\\n\s*f"\{pct\} percent\. Plug in immediately\."\)',
         r'speak(f"Critical battery, {config.OWNER_TITLE}. {pct} percent. Plug in immediately."); import oversight, notify; oversight.record_alert("battery", f"Critical battery: {pct}%", "critical"); notify.notify_desktop("Battery Critical", f"Critical battery: {pct}%") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Battery is at \{pct\} percent, \{config\.OWNER_TITLE\}\."\)',
         r'speak(f"Battery is at {pct} percent, {config.OWNER_TITLE}."); import oversight, notify; oversight.record_alert("battery", f"Battery low: {pct}%", "warning"); notify.notify_desktop("Battery Low", f"Battery low: {pct}%") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Battery is at half capacity, \{pct\} percent\."\)',
         r'speak(f"Battery is at half capacity, {pct} percent."); import oversight, notify; oversight.record_alert("battery", f"Battery at {pct}%", "info"); notify.notify_desktop("Battery", f"Battery at {pct}%") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Warning: Local disk space is critically low\. Only \{int\(free_gb\)\} gigabytes remaining\."\)',
         r'speak(f"Warning: Local disk space is critically low. Only {int(free_gb)} gigabytes remaining."); import oversight, notify; oversight.record_alert("disk", f"Low disk space: {int(free_gb)} GB remaining", "critical"); notify.notify_desktop("Disk Space", f"Low disk space: {int(free_gb)} GB remaining") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Suspicious activity detected\. Memory usage is abnormally high at \{int\(ram\)\} percent\."\)',
         r'speak(f"Suspicious activity detected. Memory usage is abnormally high at {int(ram)} percent."); import oversight, notify; oversight.record_alert("ram", f"High memory usage: {int(ram)}%", "warning"); notify.notify_desktop("Memory Usage", f"High memory usage: {int(ram)}%") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Suspicious activity detected on your computer, \{config\.OWNER_TITLE\}\. CPU is sustained at \{int\(cpu\)\} percent\."\)',
         r'speak(f"Suspicious activity detected on your computer, {config.OWNER_TITLE}. CPU is sustained at {int(cpu)} percent."); import oversight, notify; oversight.record_alert("cpu", f"High CPU usage: {int(cpu)}%", "warning"); notify.notify_desktop("CPU Usage", f"High CPU usage: {int(cpu)}%") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Excuse me Sir, you have a new important email from \{short_from\} about \{short_subj\}\."\)',
         r'speak(f"Excuse me Sir, you have a new important email from {short_from} about {short_subj}."); import oversight, notify; oversight.record_alert("email", f"Important email from {short_from}", "info"); notify.notify_desktop("Email", f"Important email from {short_from}") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Excuse me Sir, you have \{new_count\} new important emails, including one from \{short_from\}\."\)',
         r'speak(f"Excuse me Sir, you have {new_count} new important emails, including one from {short_from}."); import oversight, notify; oversight.record_alert("email", f"{new_count} new important emails", "info"); notify.notify_desktop("Email", f"{new_count} new important emails") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Sir, you have \{count - last_github_count\} new GitHub notifications\."\)',
         r'speak(f"Sir, you have {count - last_github_count} new GitHub notifications."); import oversight, notify; oversight.record_alert("github", f"{count - last_github_count} new GitHub notifications", "info"); notify.notify_desktop("GitHub", f"{count - last_github_count} new GitHub notifications") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Reminder, \{config\.OWNER_TITLE\}\. "\\n\s*f"\{title\} starts in \{mins\} minute"\\n\s*f"\{\'s\' if mins != 1 else \'\'\}\.", is_notification=True\)',
         r'speak(f"Reminder, {config.OWNER_TITLE}. {title} starts in {mins} minute{\'s\' if mins != 1 else \'\'}.", is_notification=True); import oversight, notify; oversight.record_alert("calendar", f"Event \'{title}\' starts in {mins} min", "info"); notify.notify_desktop("Calendar", f"Event \'{title}\' starts in {mins} min") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Alert, \{config\.OWNER_TITLE\}\. \{r\[\'host\'\]\} is down\.", is_notification=True\)',
         r'speak(f"Alert, {config.OWNER_TITLE}. {r[\'host\']} is down.", is_notification=True); import oversight, notify; oversight.record_alert("site-down", f"{r[\'host\']} is down", "critical"); notify.notify_desktop("Site Down", f"{r[\'host\']} is down") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"\{r\[\'host\'\]\} is back up, \{config\.OWNER_TITLE\}\.", is_notification=True\)',
         r'speak(f"{r[\'host\']} is back up, {config.OWNER_TITLE}.", is_notification=True); import oversight, notify; oversight.record_alert("site-down", f"{r[\'host\']} is back up", "info"); notify.notify_desktop("Site Recovered", f"{r[\'host\']} is back up") if STATE.get("frontend_hidden", False) else None'),

        (r'speak\(f"Heads up, \{config\.OWNER_TITLE\}\. \{r\[\'host\'\]\} "\\n\s*f"SSL certificate expires in \{cd\} days\.", is_notification=True\)',
         r'speak(f"Heads up, {config.OWNER_TITLE}. {r[\'host\']} SSL certificate expires in {cd} days.", is_notification=True); import oversight, notify; oversight.record_alert("cert-expiring", f"{r[\'host\']} SSL expires in {cd} days", "warning"); notify.notify_desktop("SSL Expiry", f"{r[\'host\']} SSL expires in {cd} days") if STATE.get("frontend_hidden", False) else None'),
    ]

    for pat, repl in replacements:
        content, count = re.subn(pat, repl, content)
        if count == 0:
            print(f"Failed to replace: {pat}")

    with open('app/server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replacement complete!")

if __name__ == "__main__":
    main()
