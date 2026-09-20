import sys

def main():
    with open('app/server.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. Inject GET route and hidden handling
    get_index = -1
    for i, line in enumerate(lines):
        if 'if path == "/api/status":' in line:
            get_index = i
            break
            
    if get_index != -1:
        get_code = """
        if path == "/api/oversight/status":
            import oversight
            import watchdog
            self._json({
                "ok": True,
                "alerts": oversight.recent_alerts(),
                "watchedSites": watchdog.list_sites(),
                "thresholds": {
                    "cpu": getattr(config, "CPU_HIGH_PCT", 85),
                    "ram": getattr(config, "RAM_HIGH_PCT", 85),
                    "disk_gb": getattr(config, "DISK_LOW_GB", 5),
                    "battery_low": getattr(config, "BATTERY_LOW_PCT", 20)
                }
            })
            return

"""
        lines.insert(get_index, get_code)
        
        # update get_index since we inserted
        get_index += 1 
        
        hidden_code = """            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            hidden = qs.get("hidden", ["0"])[0] == "1"
            STATE["frontend_hidden"] = hidden
"""
        lines.insert(get_index + 1, hidden_code)
    else:
        print("Could not find /api/status GET route")
        sys.exit(1)

    # 2. Inject POST routes
    post_index = -1
    for i, line in enumerate(lines):
        if 'if path == "/api/chat":' in line:
            post_index = i
            break

    if post_index != -1:
        post_code = """
        if path == "/api/oversight/watchdog/add":
            import watchdog
            url = data.get("url", "")
            label = data.get("label", url)
            watchdog.add_site(url, label)
            self._json({"ok": True})
            return

        if path == "/api/oversight/watchdog/remove":
            import watchdog
            url = data.get("url", "")
            watchdog.remove_site(url)
            self._json({"ok": True})
            return

        if path == "/api/oversight/watchdog/check":
            import watchdog
            url = data.get("url", "")
            res = watchdog.check_site(url)
            self._json({"ok": True, "result": res})
            return

"""
        lines.insert(post_index, post_code)
    else:
        print("Could not find /api/chat POST route")
        sys.exit(1)

    with open('app/server.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print("Routes injected successfully.")

if __name__ == "__main__":
    main()
