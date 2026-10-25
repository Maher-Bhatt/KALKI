"""Boot the real server in isolation and probe every endpoint the UI touches at launch."""
import json, os, sys, tempfile, threading, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
home = tempfile.mkdtemp(prefix="kalki_probe_")
os.environ["HOME"] = home; os.environ["APPDATA"] = home; os.environ["USERPROFILE"] = home
os.environ["KALKI_TEST"] = "1"
sys.path.insert(0, APP); os.chdir(APP)

import config
PORT = 10011; config.PORT = PORT
import server
rs = server.runtime_security
H = {rs.TOKEN_HEADER: rs.get_api_token(), "Content-Type": "application/json"}
threading.Thread(target=server.main, daemon=True).start()
for _ in range(80):
    time.sleep(.5)
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/api/health"), timeout=1); break
    except Exception:
        pass

def call(m, p, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{p}", data=data, headers=H, method=m)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", "replace"); code = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace"); code = e.code
    except Exception as e:
        return 0, str(e)
    return code, raw[:160]

probes = [("GET", l.split(" ", 1)[1], None) for l in open(os.path.join(ROOT, "tools", "_paths.txt")).read().splitlines()
          if l.startswith("GET ") and "settings/test" not in l and "clipboard" not in l and "support" not in l]
probes += [
    ("POST", "/api/tasks/list", {"all": False}), ("POST", "/api/reminders/list", {}),
    ("POST", "/api/notes/list", {"n": 6}), ("POST", "/api/calendar/today", {}),
    ("POST", "/api/media/now_json", {}),
]
for m, p, b in probes:
    code, raw = call(m, p, b)
    flag = "OK  " if code == 200 and '"ok": false' not in raw and '"ok":false' not in raw else "BAD "
    print(f"{flag}{code} {m:4s} {p:26s} {raw[:150]!r}", flush=True)
sys.stdout.flush()
os._exit(0)
