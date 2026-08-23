#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
if [[ ! -d "$ROOT/app" && -d "$SCRIPT_DIR/../app" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
APP_DIR="$ROOT/app"
VENV_DIR="${KALKI_VENV_DIR:-$HOME/.local/share/kalki/venv}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/kalki.desktop"

command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 1; }
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -r "$APP_DIR/requirements-linux.txt"

mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=KALKI AI Assistant
Comment=Indian intelligence companion
Exec=$VENV_DIR/bin/python $APP_DIR/linux_launcher.py
Path=$APP_DIR
Terminal=false
Categories=Utility;Office;
EOF
chmod +x "$APP_DIR/linux_launcher.py" "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
printf '\nKALKI Linux installation complete.\nRun: %q\n' "$VENV_DIR/bin/python $APP_DIR/linux_launcher.py"
