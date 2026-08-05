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
        
        # Check if the configured port is already occupied (e.g. production KALKI running)
        import socket
        port_in_use = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                port_in_use = True
                
        if port_in_use:
            print(f"[SMOKE TEST] Port {port} is already in use by another instance.")
            print("Switching smoke test port to 9999 to verify this build without stale masking.")
            config.PORT = 9999
            port = 9999
    except ImportError:
        port = 8888

    import server  # importing this alone will surface any broken top-level import

    t = threading.Thread(target=server.main, daemon=True)
    t.start()
    
    # This is a release gate: continuing after a failed startup can mask a
    # broken build.
    print(f"[SMOKE TEST] Waiting for server on port {port} to start accepting connections...")
    server_started = False
    for _ in range(60):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1) as r:
                if r.status == 200:
                    server_started = True
                    break
        except Exception:
            pass

    if not server_started:
        print(f"[SMOKE TEST] FAILED: Server on port {port} did not respond within 30 seconds.")
        sys.exit(1)

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
