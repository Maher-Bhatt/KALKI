# 🚀 KALKI v1.0.23 — Post-Installation Stability Patch

## 🔥 v1.0.23 Patch Notes

- **Vision Memory OCR Fix:** Added a robust fallback block for `pytesseract` to prevent startup crashes when Tesseract OCR is not installed.
- **PyInstaller Dependency Fix:** Added `spotipy` and `pytesseract` to hidden imports in the build script so compiled `.exe` files include all necessary lazy-loaded modules.
- **Developer Mode Fix:** Fixed `get_exe_path` logic in `main_app.py` to properly map source files instead of executable targets when running unfrozen.
- **Version Clean Bump:** Bumped system-wide to `v1.0.23`.

Installer SHA-256:
317C924C95EA65FAEECDD035272666563163A6459E2629027DEBCC260255CCF0

