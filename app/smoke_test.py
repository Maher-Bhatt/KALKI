"""
Run before packaging any release. Boots the real server module in-process
and hits its two most basic endpoints. Exits non-zero on any failure so it
can gate a build script.
"""
import sys
import threading
import time
import urllib.request
import json

def main():
    # Make sure we use the configured port
    try:
        import config
        port = config.PORT
    except ImportError:
        port = 8888

    import server  # importing this alone will surface any broken top-level import

    t = threading.Thread(target=server.main, daemon=True)
    t.start()
    time.sleep(2)

    failures = []
    for path, required_keys in [
        ("/api/status", ["uptimeSec", "cpu", "ram"]),
        ("/api/models", None),
    ]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
                if required_keys:
                    missing = [k for k in required_keys if k not in data]
                    if missing:
                        failures.append(f"{path}: missing keys {missing}")
        except Exception as e:
            failures.append(f"{path}: {e}")

    if failures:
        print("SMOKE TEST FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("SMOKE TEST PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
