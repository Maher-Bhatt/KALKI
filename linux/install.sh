#!/usr/bin/env bash
# ==============================================================================
# KALKI AI Assistant — Linux Installer & Desktop Setup (v1.4.0)
# Supports Ubuntu, Debian, Fedora, Arch, Linux Mint, Pop!_OS
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
if [[ ! -d "$ROOT/app" && -d "$SCRIPT_DIR/../app" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
APP_DIR="$ROOT/app"
INSTALL_DIR="${KALKI_INSTALL_DIR:-$HOME/.local/share/kalki}"
VENV_DIR="$INSTALL_DIR/venv"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/kalki.desktop"
BIN_DIR="$HOME/.local/bin"

echo "========================================================"
echo "  KALKI AI Assistant — Linux Installation Wizard"
echo "========================================================"
echo "Source: $ROOT"
echo "Target: $INSTALL_DIR"
echo ""

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3 is required. Please install python3 (>=3.10) using your package manager." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Found Python $PY_VER"

# Detect package manager and recommend system dependencies
if command -v apt-get >/dev/null 2>&1; then
  echo "Note: On Debian/Ubuntu, recommended audio/speech packages can be installed via:"
  echo "  sudo apt-get install -y ffmpeg espeak-ng portaudio19-dev python3-tk"
elif command -v dnf >/dev/null 2>&1; then
  echo "Note: On Fedora/RHEL, recommended packages can be installed via:"
  echo "  sudo dnf install -y ffmpeg espeak-ng portaudio-devel python3-tkinter"
elif command -v pacman >/dev/null 2>&1; then
  echo "Note: On Arch Linux, recommended packages can be installed via:"
  echo "  sudo pacman -S --needed ffmpeg espeak-ng portaudio tk"
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"

# Copy files if installing from tarball
if [[ "$ROOT" != "$INSTALL_DIR" ]]; then
  echo "Copying KALKI application files to $INSTALL_DIR..."
  cp -a "$APP_DIR" "$INSTALL_DIR/"
  if [[ -d "$ROOT/assets" ]]; then
    cp -a "$ROOT/assets" "$INSTALL_DIR/"
  fi
  APP_DIR="$INSTALL_DIR/app"
fi

echo "Creating dedicated Python virtual environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing required Python dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools
if [[ -f "$APP_DIR/requirements-linux.txt" ]]; then
  "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements-linux.txt"
fi

# Ensure default config exists
if [[ ! -f "$APP_DIR/config.py" && -f "$APP_DIR/config.example.py" ]]; then
  cp "$APP_DIR/config.example.py" "$APP_DIR/config.py"
  echo "Created default config.py from template."
fi

# Create desktop launcher script
LAUNCHER_WRAPPER="$BIN_DIR/kalki"
cat > "$LAUNCHER_WRAPPER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/linux_launcher.py" "\$@"
EOF
chmod +x "$LAUNCHER_WRAPPER"

# Create XDG Desktop Entry
ICON_PATH="$INSTALL_DIR/assets/kalki_icon.ico"
if [[ -f "$INSTALL_DIR/assets/kalki_logo.png" ]]; then
  ICON_PATH="$INSTALL_DIR/assets/kalki_logo.png"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=KALKI AI Assistant
Comment=Local-first AI Desktop Assistant & Intelligence Companion
Exec=$LAUNCHER_WRAPPER
Icon=$ICON_PATH
Path=$APP_DIR
Terminal=false
Categories=Utility;AudioVideo;Office;Development;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo ""
echo "========================================================"
echo "  KALKI Installation Successful!"
echo "========================================================"
echo "You can launch KALKI in any of the following ways:"
echo "  1. From your Application Menu (search 'KALKI')"
echo "  2. From terminal: $LAUNCHER_WRAPPER (ensure ~/.local/bin is in PATH)"
echo "  3. Directly: $VENV_DIR/bin/python $APP_DIR/linux_launcher.py"
echo ""
