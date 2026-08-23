#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.3.0"
OUT_DIR="${1:-$ROOT/output/linux-v$VERSION}"
STAGE="$OUT_DIR/KALKI-v$VERSION-linux"
ARCHIVE="$OUT_DIR/KALKI_v${VERSION}_Linux.tar.gz"
CHECKSUMS="$OUT_DIR/SHA256SUMS.txt"

rm -rf "$STAGE"
mkdir -p "$STAGE/app" "$STAGE/assets" "$OUT_DIR"

# Copy maintained runtime files while excluding Windows build output and mutable data.
tar -C "$ROOT" \
  --exclude='*/__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
  --exclude='*.pfx' --exclude='*.cer' --exclude='*.pem' --exclude='*.key' \
  --exclude='*.log' --exclude='*.bak' --exclude='*.tmp' \
  --exclude='app/dist' --exclude='app/build' --exclude='app/.build_packages' \
  --exclude='app/.build-venv' --exclude='app/data' --exclude='app/msix_staging' \
  -cf - app | tar -C "$STAGE" -xf -
if [[ -d "$ROOT/assets" ]]; then
  tar -C "$ROOT" -cf - assets | tar -C "$STAGE" -xf -
fi
cp "$ROOT/README.md" "$ROOT/LICENSE" "$ROOT/TERMS.md" "$ROOT/CHANGES.md" "$STAGE/" 2>/dev/null || true
cp "$ROOT/release_notes.md" "$STAGE/" 2>/dev/null || true
cp "$ROOT/linux/install.sh" "$STAGE/"

cat > "$STAGE/README-LINUX.md" <<EOF
# KALKI $VERSION for Linux

Run \`./install.sh\` from this directory. The installer creates a private Python
virtual environment under \`~/.local/share/kalki/venv\`, installs Linux-safe
requirements, and registers a desktop entry. The launcher uses the default
browser for the dashboard, keeps state under the XDG user-data directory, and
starts the local server and listener as supervised child processes.

Linux TTS uses Edge neural speech when available, then an installed local
\`espeak-ng\`/\`espeak\` fallback. Install \`ffmpeg\`, \`mpv\`, or \`mpg123\` for MP3
playback. Microphone wake-word support is optional and may require \`portaudio19-dev\`
plus PyAudio on Debian/Ubuntu.
EOF
chmod +x "$STAGE/install.sh" "$STAGE/app/linux_launcher.py"

rm -f "$ARCHIVE"
tar -czf "$ARCHIVE" -C "$OUT_DIR" "KALKI-v$VERSION-linux"
sha256sum "$ARCHIVE" > "$CHECKSUMS"
printf 'Linux release created:\n  %s\n  %s\n' "$ARCHIVE" "$CHECKSUMS"
