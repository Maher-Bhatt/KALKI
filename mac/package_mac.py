#!/usr/bin/env python3
"""Cross-platform packaging script for KALKI macOS Release.
Reads APP_VERSION from app/version.py and packages the complete macOS
release tarball, App bundle structure, and SHA-256 telemetry.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Read version
sys.path.insert(0, str(REPO_ROOT / "app"))
try:
    from version import APP_VERSION
except ImportError:
    APP_VERSION = "1.5.0"

OUT_DIR = REPO_ROOT / "Output" / "macos"
STAGE_DIR = OUT_DIR / f"KALKI-v{APP_VERSION}-macOS"
TARBALL_PATH = OUT_DIR / f"KALKI_v{APP_VERSION}_macOS.tar.gz"
CHECKSUMS_PATH = OUT_DIR / "SHA256SUMS.txt"


def clean_stage():
    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)


def copy_runtime_files():
    print(f"Staging KALKI v{APP_VERSION} for macOS...")
    app_stage = STAGE_DIR / "app"
    app_stage.mkdir(parents=True, exist_ok=True)

    # Exclude Windows binaries, venvs, and cache
    ignore_patterns = shutil.ignore_patterns(
        "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        "dist", "build", ".build*", "data", "scans",
        "msix_staging", "*.log", "*.tmp", ".venv*", "venv"
    )

    # Copy app/
    shutil.copytree(REPO_ROOT / "app", app_stage, ignore=ignore_patterns, dirs_exist_ok=True)

    # Copy assets/
    if (REPO_ROOT / "assets").exists():
        shutil.copytree(REPO_ROOT / "assets", STAGE_DIR / "assets", dirs_exist_ok=True)

    # Copy mac scripts
    shutil.copy2(REPO_ROOT / "mac" / "install.sh", STAGE_DIR / "install.sh")
    shutil.copy2(REPO_ROOT / "mac" / "mac_launcher.py", STAGE_DIR / "mac_launcher.py")

    # Copy top-level documentation
    for doc in ["README.md", "INSTALLATION_GUIDE.md", "LICENSE", "TERMS.md", "CHANGES.md", "release_notes.md"]:
        src = REPO_ROOT / doc
        if src.exists():
            shutil.copy2(src, STAGE_DIR / doc)

    # Create README-MACOS.md
    readme_mac = f"""# KALKI AI Assistant v{APP_VERSION} for macOS

## Quick Start
Run the installation wizard:
```bash
chmod +x install.sh
./install.sh
```

## Features
- **Filament Desktop Workspace**: 5 destinations (Ask, Today, Memory, Workbench, Settings) + Antivirus & Cyber direct viewer.
- **Native Cocoa WebKit Shell**: Runs with hardware-accelerated macOS WebKit window.
- **Apple Music Control**: Native AppleScript integration for playback control and status.
- **Natural Neural Speech**: Edge TTS with native macOS `say` fallback (Samantha / Alex / Siri).
- **macOS Notification Center**: Direct integration for system alerts and reminders.

## Requirements
- macOS 11.0 (Big Sur) or newer (macOS Sequoia, Sonoma, Ventura fully supported).
- Apple Silicon (M1/M2/M3/M4) or Intel x86_64.
- Python 3.10+ (`brew install python@3.12`).
"""
    (STAGE_DIR / "README-MACOS.md").write_text(readme_mac, encoding="utf-8")


def create_tarball():
    print(f"Creating archive: {TARBALL_PATH.name}...")
    with tarfile.open(TARBALL_PATH, "w:gz") as tar:
        tar.add(STAGE_DIR, arcname=f"KALKI-v{APP_VERSION}-macOS")
    print(f"macOS Tarball created: {TARBALL_PATH} ({TARBALL_PATH.stat().st_size / (1024*1024):.2f} MB)")


def write_checksums():
    h = hashlib.sha256(TARBALL_PATH.read_bytes()).hexdigest()
    CHECKSUMS_PATH.write_text(f"{h}  {TARBALL_PATH.name}\n", encoding="utf-8")
    print("SHA-256 Checksum written to:", CHECKSUMS_PATH)


def main():
    clean_stage()
    copy_runtime_files()
    create_tarball()
    write_checksums()
    # Also copy install.sh to Output/macos/ for quick standalone fetching
    shutil.copy2(REPO_ROOT / "mac" / "install.sh", OUT_DIR / "install_mac.sh")
    print("\nmacOS package build completed successfully!")


if __name__ == "__main__":
    main()
