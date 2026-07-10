# 🚀 KALKI v1.0.23 — Post-Installation Stability Patch

## 🔥 v1.0.23 Patch Notes

- **Vision Memory OCR Fix:** Added a robust fallback block for `pytesseract` to prevent startup crashes when Tesseract OCR is not installed.
- **PyInstaller Dependency Fix:** Added `spotipy` and `pytesseract` to hidden imports in the build script so compiled `.exe` files include all necessary lazy-loaded modules.
- **Developer Mode Fix:** Fixed `get_exe_path` logic in `main_app.py` to properly map source files instead of executable targets when running unfrozen.
- **Version Clean Bump:** Bumped system-wide to `v1.0.23`.

Installer SHA-256:
E4F0F7E3F30BE4ED4681C7610F0B71C89D960F3DD59824ADC1CAF97858421A5E

