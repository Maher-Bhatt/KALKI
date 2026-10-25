#!/usr/bin/env python3
"""Cross-platform packaging script for KALKI Linux Release.
Reads APP_VERSION from app/version.py and builds tar.gz bundle,
self-extracting bash installer, and SHA-256 telemetry.
"""
from __future__ import annotations

import base64
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
    APP_VERSION = "1.4.0"

OUT_DIR = REPO_ROOT / "Output" / "linux"
STAGE_DIR = OUT_DIR / f"KALKI-v{APP_VERSION}-linux"
TARBALL_PATH = OUT_DIR / f"KALKI_v{APP_VERSION}_Linux.tar.gz"
INSTALLER_PATH = OUT_DIR / f"KALKI_Ubuntu_Installer_v{APP_VERSION}.sh"
CHECKSUMS_PATH = OUT_DIR / "SHA256SUMS.txt"


def clean_stage():
    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)


def copy_runtime_files():
    print(f"Staging KALKI v{APP_VERSION} for Linux...")
    app_stage = STAGE_DIR / "app"
    app_stage.mkdir(parents=True, exist_ok=True)

    # Exclude build artifacts, virtualenvs, and data
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

    # Copy linux scripts
    shutil.copy2(REPO_ROOT / "linux" / "install.sh", STAGE_DIR / "install.sh")
    shutil.copy2(REPO_ROOT / "linux" / "kalki.desktop", STAGE_DIR / "kalki.desktop")

    # Copy top-level documentation
    for doc in ["README.md", "INSTALLATION_GUIDE.md", "LICENSE", "TERMS.md", "CHANGES.md", "release_notes.md"]:
        src = REPO_ROOT / doc
        if src.exists():
            shutil.copy2(src, STAGE_DIR / doc)

    # Create README-LINUX.md inside stage
    readme_linux = f"""# KALKI AI Assistant v{APP_VERSION} for Linux

## Quick Start
Run the automated installation script:
```bash
chmod +x install.sh
./install.sh
```

## Features
- **Filament Desktop Workspace**: 5 destinations (Ask, Today, Memory, Workbench, Settings) + Antivirus & Cyber direct viewer.
- **Natural Neural TTS**: Edge TTS synthesis with local espeak-ng / ffmpeg fallback.
- **Offline / Local First**: Loopback HTTP service with loopback auth tokens and local encrypted vault.
- **Desktop & CLI Launchers**: Registers `kalki` in `~/.local/bin` and adds a system desktop shortcut.

## Requirements
- Python 3.10+ (`python3`, `python3-venv`)
- Optional system packages for voice: `ffmpeg`, `espeak-ng`, `portaudio19-dev`
"""
    (STAGE_DIR / "README-LINUX.md").write_text(readme_linux, encoding="utf-8")


def create_tarball():
    print(f"Creating archive: {TARBALL_PATH.name}...")
    with tarfile.open(TARBALL_PATH, "w:gz") as tar:
        tar.add(STAGE_DIR, arcname=f"KALKI-v{APP_VERSION}-linux")
    print(f"Tarball created: {TARBALL_PATH} ({TARBALL_PATH.stat().st_size / (1024*1024):.2f} MB)")


def create_self_extracting_installer():
    print(f"Generating self-extracting installer: {INSTALLER_PATH.name}...")
    tar_bytes = TARBALL_PATH.read_bytes()
    b64_payload = base64.b64encode(tar_bytes).decode("ascii")

    header = f"""#!/usr/bin/env bash
# ==============================================================================
# Self-Extracting Linux Installer for KALKI AI Assistant v{APP_VERSION}
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${{KALKI_INSTALL_DIR:-$HOME/.local/share/kalki}}"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
TMP_DIR="$(mktemp -d "${{TMPDIR:-/tmp}}/kalki-linux.XXXXXX")"
cleanup() {{ rm -rf "$TMP_DIR"; }}
trap cleanup EXIT

command -v base64 >/dev/null 2>&1 || {{ echo "Error: base64 utility is required." >&2; exit 1; }}
command -v tar >/dev/null 2>&1 || {{ echo "Error: tar utility is required." >&2; exit 1; }}

echo "========================================================"
echo "  Unpacking KALKI AI Assistant v{APP_VERSION}..."
echo "========================================================"

marker_line="$(grep -n '^__KALKI_LINUX_PAYLOAD_BELOW__$' "$SELF" | tail -n 1 | cut -d: -f1)"
if [[ -z "$marker_line" ]]; then
  echo "Error: Corrupted installer payload." >&2
  exit 1
fi

tail -n +$((marker_line + 1)) "$SELF" | base64 -d > "$TMP_DIR/kalki-linux.tar.gz"
mkdir -p "$TMP_DIR/extracted"
tar -xzf "$TMP_DIR/kalki-linux.tar.gz" -C "$TMP_DIR/extracted"

payload_dir="$(find "$TMP_DIR/extracted" -mindepth 1 -maxdepth 1 -type d -name 'KALKI-v*-linux' -print -quit)"
if [[ -z "$payload_dir" ]]; then
  echo "Error: Payload directory missing." >&2
  exit 1
fi

echo "Running installation..."
chmod +x "$payload_dir/install.sh"
KALKI_INSTALL_DIR="$INSTALL_DIR" "$payload_dir/install.sh"

exit 0

__KALKI_LINUX_PAYLOAD_BELOW__
"""
    with open(INSTALLER_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        # Write base64 in 76-char wrapped chunks
        chunk_size = 76
        for i in range(0, len(b64_payload), chunk_size):
            f.write(b64_payload[i:i + chunk_size] + "\n")

    print(f"Self-extracting installer generated: {INSTALLER_PATH} ({INSTALLER_PATH.stat().st_size / (1024*1024):.2f} MB)")


def write_checksums():
    hashes = []
    for p in [TARBALL_PATH, INSTALLER_PATH]:
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            hashes.append(f"{h}  {p.name}")
    CHECKSUMS_PATH.write_text("\n".join(hashes) + "\n", encoding="utf-8")
    print("SHA-256 Checksums written to:", CHECKSUMS_PATH)


def main():
    clean_stage()
    copy_runtime_files()
    create_tarball()
    create_self_extracting_installer()
    write_checksums()
    print("\nLinux package build completed successfully!")


if __name__ == "__main__":
    main()
