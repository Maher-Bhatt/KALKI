import os

files = [
    'CHANGES.md', 'README.md', 'app/build_tools/build_installer.py', 
    'app/build_tools/file_version_info.txt', 'app/build_tools/installer.iss', 
    'app/config.example.py', 'app/core/updater.py', 'app/index.html', 
    'app/server.py', 'app/service-worker.js'
]

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        content = content.replace('1.0.23', '1.0.24')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Bumped {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")

# Append to release_notes.md
with open('release_notes.md', 'w', encoding='utf-8') as file:
    file.write("""# 🚀 KALKI v1.0.24 — Hotfix for TTS SSL Connection Error

## 🔥 v1.0.24 Patch Notes

- **Edge-TTS SSL Fix:** Added a global SSL monkeypatch to bypass `[SSL: CERTIFICATE_VERIFY_FAILED]` errors which prevented the Edge-TTS neural voice from rendering audio on restrictive networks or missing `certifi` bundles.
- **Version Clean Bump:** Bumped system-wide to `v1.0.24`.
""")
print("Updated release_notes.md")
