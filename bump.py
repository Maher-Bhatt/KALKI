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
        content = content.replace('1.0.22', '1.0.23')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Bumped {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")

# Special handling for release_notes.md
with open('release_notes.md', 'w', encoding='utf-8') as file:
    file.write("""# 🚀 KALKI v1.0.23 — Post-Installation Stability Patch

## 🔥 v1.0.23 Patch Notes

- **Vision Memory OCR Fix:** Added a robust fallback block for `pytesseract` to prevent startup crashes when Tesseract OCR is not installed.
- **PyInstaller Dependency Fix:** Added `spotipy` and `pytesseract` to hidden imports in the build script so compiled `.exe` files include all necessary lazy-loaded modules.
- **Developer Mode Fix:** Fixed `get_exe_path` logic in `main_app.py` to properly map source files instead of executable targets when running unfrozen.
- **Version Clean Bump:** Bumped system-wide to `v1.0.23`.
""")
print("Updated release_notes.md")
