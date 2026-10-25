import os

path = "app/main_app.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Enable --disable-gpu in main_app.py
old_gpu = '''    # Prefer a conservative WebView2 renderer for packaged Windows builds.
    # KALKI is intentionally CSS-only now; disabling GPU compositing avoids
    # driver-specific WebView hangs after first paint while preserving the
    # full dashboard interaction model.
    if sys.platform == "win32":
        pass'''

new_gpu = '''    # Prefer a conservative WebView2 renderer for packaged Windows builds.
    # KALKI is intentionally CSS-only now; disabling GPU compositing avoids
    # driver-specific WebView hangs after first paint while preserving the
    # full dashboard interaction model.
    if sys.platform == "win32":
        extra_args = "--disable-gpu"
        existing_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "").strip()
        if extra_args not in existing_args:
            os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (existing_args + " " + extra_args).strip()'''

if old_gpu in c:
    c = c.replace(old_gpu, new_gpu, 1)
    print("Patched main_app.py: enabled --disable-gpu")
else:
    print("Warning: old_gpu not found")

# 2. Server wait timeout
old_wait = '''    start_services()
    if server_ready is not None:
        server_ready.wait(timeout=3.0)'''

new_wait = '''    start_services()
    if server_ready is not None:
        server_ready.wait(timeout=10.0)'''

if old_wait in c:
    c = c.replace(old_wait, new_wait, 1)
    print("Patched main_app.py: server_ready.wait(timeout=10.0)")
else:
    print("Warning: old_wait not found")

# 3. on_closing return True
old_closing = '''    import threading
    threading.Thread(target=do_cleanup, daemon=True).start()
    return False'''

new_closing = '''    import threading
    threading.Thread(target=do_cleanup, daemon=True).start()
    return True'''

if old_closing in c:
    c = c.replace(old_closing, new_closing, 1)
    print("Patched main_app.py: on_closing returns True")
else:
    print("Warning: old_closing not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Saved app/main_app.py successfully!")
