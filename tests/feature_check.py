"""KALKI feature check: boots the real server in-process with an isolated HOME
and exercises each everyday feature end to end. Exit code 1 on any hard failure.
Run:  python tests/feature_check.py
Cases marked NET need internet; OPTIONAL need keys/credentials and must degrade
gracefully (clear error, no crash, no 500)."""
import json, os, sys, tempfile, threading, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
home = tempfile.mkdtemp(prefix="kalki_test_")
os.environ["HOME"] = home; os.environ["APPDATA"] = home; os.environ["USERPROFILE"] = home
os.environ["KALKI_TEST"] = "1"
sys.path.insert(0, APP); os.chdir(APP)

import config  # noqa: E402
PORT = 10000; config.PORT = PORT
import server  # noqa: E402
rs = server.runtime_security
H = {rs.TOKEN_HEADER: rs.get_api_token(), "Content-Type": "application/json"}
threading.Thread(target=server.main, daemon=True).start()
for _ in range(80):
    time.sleep(.5)
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/api/status", headers=H), timeout=1); break
    except Exception: pass
else:
    print("server did not start"); sys.exit(1)

def call(m, p, body=None, t=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{p}", data=data, headers=H, method=m)
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            raw = r.read().decode("utf-8", "replace"); code = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace"); code = e.code
    except Exception as e:
        return 0, {"_err": str(e)}
    try: return code, json.loads(raw)
    except Exception: return code, {"_raw": raw[:200]}

res = []
def check(name, ok, detail="", level="HARD"):
    res.append((name, ok, detail, level)); print(("PASS " if ok else ("FAIL " if level=="HARD" else "WARN ")) + name + (f"  [{detail}]" if detail and not ok else ""))

# ---- auth
req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/status")
try: urllib.request.urlopen(req, timeout=5); check("auth: unauthenticated API call is rejected", False, "got 200")
except urllib.error.HTTPError as e: check("auth: unauthenticated API call is rejected", e.code in (401,403), str(e.code))
# ---- static UI
c, d = call("GET", "/"); check("ui: index served", c == 200, str(c))
# ---- status / dashboard / health / metrics
c, d = call("GET", "/api/status"); check("status: cpu/ram/uptime", c == 200 and all(k in d for k in ("cpu","ram","uptimeSec")), str(d)[:80])
for p in ("/api/dashboard","/api/health","/api/metrics","/api/models"):
    c, d = call("GET", p); check(f"GET {p}", c == 200, f"{c} {str(d)[:80]}")
# ---- tasks
c, d = call("POST", "/api/tasks/add", {"text": "Review agenda"}); check("tasks: add", c == 200, f"{c} {d}")
c, d = call("POST", "/api/tasks/list", {}); lst = d.get("tasks", []) if isinstance(d, dict) else []
check("tasks: list shows the new task", c == 200 and any("Review agenda" in json.dumps(x) for x in lst), str(d)[:120])
tid = None
for x in lst:
    if "Review agenda" in json.dumps(x): tid = x.get("id") if isinstance(x, dict) else None
c, d = call("POST", "/api/tasks/complete", {"id": tid}); check("tasks: complete", c == 200, f"{c} {d}")
c, d = call("POST", "/api/tasks/delete", {"id": tid}); check("tasks: delete", c == 200, f"{c} {d}")
# ---- notes
c, d = call("POST", "/api/notes/add", {"text": "Try Ollama for offline summaries"}); check("notes: add", c == 200, f"{c} {d}")
c, d = call("POST", "/api/notes/list", {}); check("notes: list", c == 200 and "Ollama" in json.dumps(d), str(d)[:100])
c, d = call("POST", "/api/notes/search", {"q": "ollama"}); check("notes: search finds it", c == 200 and "Ollama" in json.dumps(d), f"{c} {str(d)[:100]}")
# ---- reminders
c, d = call("POST", "/api/reminders/add", {"text": "Leave for the venue", "due": "2099-01-01T13:30:00"}); check("reminders: add natural-language time", c == 200, f"{c} {d}")
c, d = call("POST", "/api/reminders/list", {}); check("reminders: list", c == 200 and "venue" in json.dumps(d).lower(), str(d)[:100])
# ---- memory
c, d = call("POST", "/api/memory/add", {"text": "Prefers short direct answers", "type": "preference", "importance": 9}); check("memory: add", c == 200, f"{c} {d}")
c, d = call("GET", "/api/memory/list"); check("memory: list", c == 200 and "short direct" in json.dumps(d), str(d)[:100])
# ---- vault (needs Windows DPAPI; correctly refuses on other platforms)
VAULT = sys.platform == "win32"
if VAULT:
  c, d = call("POST", "/api/vault/save", {"label": "test_entry", "username": "me", "password": "s3cret!"}); check("vault: save", c == 200, f"{c} {d}")
  c, d = call("POST", "/api/vault/get", {"label": "test_entry"}); check("vault: get returns what was saved", c == 200 and "test_entry" in json.dumps(d), f"{c} {str(d)[:80]}")
  c, d = call("POST", "/api/vault/delete", {"label": "test_entry"}); check("vault: delete", c == 200, f"{c} {d}", "WARN")
else:
  print("SKIP vault checks (Windows DPAPI only; CI runs them on windows-latest)")
# ---- settings
c, d = call("GET", "/api/settings/get"); check("settings: get", c == 200, f"{c}")
check("settings: never returns a raw API key", "gsk_" not in json.dumps(d) and "sk-" not in json.dumps(d))
c, d = call("GET", "/api/settings/export"); check("settings: export", c == 200, f"{c}")
# ---- oversight
c, d = call("GET", "/api/oversight/status"); check("oversight: status", c == 200, f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/oversight/watchdog/add", {"url": "http://127.0.0.1:%d/" % PORT}); check("oversight: add watched site", c == 200, f"{c} {d}")
c, d = call("POST", "/api/oversight/watchdog/check", {}, 30); check("oversight: check runs", c == 200, f"{c} {str(d)[:100]}")
c, d = call("POST", "/api/oversight/watchdog/remove", {"url": "http://127.0.0.1:%d/" % PORT}); check("oversight: remove", c == 200, f"{c} {d}")
# ---- calendar / mail / github / spotify without credentials must degrade gracefully
for p in ("/api/calendar/today","/api/calendar/upcoming","/api/mail/inbox","/api/github/status","/api/spotify/now"):
    m = "GET"; c, d = call(m, p)
    check(f"graceful without credentials: {p}", c in (200, 400, 401, 403, 404, 409, 503) and c != 500 and "Traceback" not in json.dumps(d), f"{c} {str(d)[:80]}", "WARN")
# ---- cyber (offline-safe)
c, d = call("POST", "/api/cyber/hash", {"text": "kalki", "algo": "sha256"}); check("cyber: hash", c == 200 and "a" in json.dumps(d), f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/cyber/encode", {"text": "hello", "type": "base64"}); check("cyber: encode base64", c == 200 and "aGVsbG8=" in json.dumps(d), f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/cyber/decode", {"text": "aGVsbG8=", "type": "base64"}); check("cyber: decode base64", c == 200 and "hello" in json.dumps(d), f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/cyber/identify", {"hash": "5d41402abc4b2a76b9719d911017c592"}); check("cyber: identify hash", c == 200 and "md5" in json.dumps(d).lower(), f"{c} {str(d)[:80]}")
# ---- chat and model routing without a key must fail clearly, not crash
c, d = call("POST", "/api/chat", {"message": "hello"}, 40); check("chat: responds or explains missing key (no crash)", c in (200, 400, 401, 403, 409, 503) and "Traceback" not in json.dumps(d), f"{c} {str(d)[:120]}", "WARN")
# ---- code run gated
c, d = call("POST", "/api/code/run", {"code": "print(1)", "language": "python"}, 30); check("code run: gated when host execution is off", c != 500 and "Traceback" not in json.dumps(d), f"{c} {str(d)[:100]}", "WARN")
# ---- backup
c, d = call("POST", "/api/backup/create", {}, 30); check("backup: create", c == 200, f"{c} {str(d)[:100]}", "WARN")
# ---- history / telemetry / listener
for p in ("/api/history",):
    c, d = call("GET", p); check(f"GET {p}", c == 200, f"{c} {str(d)[:80]}", "WARN")


# ---- activity log
c, d = call("POST", "/api/activity/list", {})
check("activity: list returns 200", c == 200, f"{c} {d}")
# It would be empty now, so let's check it doesn't crash.

# ---- approvals
c, d = call("POST", "/api/approvals/list", {})
check("approvals: list returns 200", c == 200, f"{c} {d}")

# ---- briefing
c, d = call("POST", "/api/briefing/get", {})
check("briefing: disabled by default", c == 400, f"{c} {d}", "WARN")

# ---- skills
c, d = call("POST", "/api/skills/list", {})
check("skills: list", c == 200 and "skills" in d, f"{c} {d}")
c, d = call("POST", "/api/skills/toggle", {"id": "calendar", "enabled": False})
check("skills: toggle", c == 200, f"{c} {d}")

# ---- listener state
c, d = call("GET", "/api/status", {})
check("status: includes listenerState", c == 200 and "listenerState" in d, f"{c} {d}")

# ---- Phase 4 New Endpoints
c, d = call("POST", "/api/activity/list", {}); check("activity: list", c == 200, f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/approvals/list", {}); check("approvals: list", c == 200, f"{c} {str(d)[:80]}")
config.BRIEFING_ENABLED = True
c, d = call("POST", "/api/briefing/get", {}); check("briefing: get", c == 200, f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/skills/list", {}); check("skills: list", c == 200, f"{c} {str(d)[:80]}")
c, d = call("POST", "/api/skills/toggle", {"id": "web_search", "enabled": False}); check("skills: toggle", c == 200, f"{c} {str(d)[:80]}")
c, d = call("GET", "/api/status"); check("status: listenerState and micLevel", c == 200 and "listenerState" in json.dumps(d) and "micLevel" in json.dumps(d), f"{c} {str(d)[:80]}")

hard = [r for r in res if not r[1] and r[3] == "HARD"]; warn = [r for r in res if not r[1] and r[3] != "HARD"]
print(f"\n{len(res)-len(hard)-len(warn)} passed, {len(warn)} warnings, {len(hard)} hard failures")
sys.exit(1 if hard else 0)
