#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT/output/linux-v1.3.0}"
ARCHIVE="$OUT_DIR/KALKI_v1.3.0_Linux.tar.gz"
INSTALLER="$OUT_DIR/KALKI_Ubuntu_Installer_v1.3.0.sh"

mkdir -p "$OUT_DIR"
if [[ ! -f "$ARCHIVE" ]]; then
  "$ROOT/linux/package_linux.sh" "$OUT_DIR"
fi

cat > "$INSTALLER" <<'INSTALLER_HEADER'
#!/usr/bin/env bash
set -Eeuo pipefail

# KALKI Ubuntu installer and launcher. It is self-contained: the compressed
# Linux release is base64-encoded below the marker at the end of this file.
INSTALL_DIR="${KALKI_INSTALL_DIR:-$HOME/.local/share/kalki/releases/v1.3.0}"
VENV_DIR="${KALKI_VENV_DIR:-$HOME/.local/share/kalki/venv}"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kalki-ubuntu.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

command -v base64 >/dev/null 2>&1 || { echo "KALKI requires the base64 utility." >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo "KALKI requires tar." >&2; exit 1; }

marker_line="$(grep -n '^__KALKI_PAYLOAD_BELOW__$' "$SELF" | tail -n 1 | cut -d: -f1)"
[[ -n "$marker_line" ]] || { echo "KALKI installer payload marker is missing." >&2; exit 1; }
tail -n +$((marker_line + 1)) "$SELF" | base64 -d > "$TMP_DIR/kalki-linux.tar.gz"
mkdir -p "$TMP_DIR/release"
tar -xzf "$TMP_DIR/kalki-linux.tar.gz" -C "$TMP_DIR/release"
release_dir="$(find "$TMP_DIR/release" -mindepth 1 -maxdepth 1 -type d -name 'KALKI-v*-linux' -print -quit)"
[[ -n "$release_dir" ]] || { echo "KALKI release payload is invalid." >&2; exit 1; }

mkdir -p "$INSTALL_DIR"
cp -a "$release_dir"/. "$INSTALL_DIR"/
chmod +x "$INSTALL_DIR/install.sh" "$INSTALL_DIR/app/linux_launcher.py"
KALKI_VENV_DIR="$VENV_DIR" "$INSTALL_DIR/install.sh"

echo "KALKI installed to $INSTALL_DIR"
echo "Launching the dashboard. Press Ctrl+C to stop the local assistant."
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/app/linux_launcher.py"

__KALKI_PAYLOAD_BELOW__
INSTALLER_HEADER

base64 -w 0 "$ARCHIVE" >> "$INSTALLER"
printf '\n' >> "$INSTALLER"
chmod +x "$INSTALLER"
printf 'Ubuntu installer created:\n  %s\n' "$INSTALLER"
