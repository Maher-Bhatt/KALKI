#!/usr/bin/env bash
# ==============================================================================
# KALKI AI Assistant — macOS Installer & App Bundle Creator (v1.4.0)
# Supports Apple Silicon (M1/M2/M3/M4) & Intel Macs (macOS Sequoia, Sonoma, Ventura)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
if [[ ! -d "$ROOT/app" && -d "$SCRIPT_DIR/../app" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
APP_DIR="$ROOT/app"

APP_SUPPORT="$HOME/Library/Application Support/KALKI"
VENV_DIR="$APP_SUPPORT/venv"
BIN_DIR="$HOME/.local/bin"
APP_BUNDLE="$HOME/Applications/KALKI.app"

echo "========================================================"
echo "  KALKI AI Assistant — macOS Installation Wizard"
echo "========================================================"
echo "Source: $ROOT"
echo "Target: $APP_SUPPORT"
echo ""

# Verify Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3 was not found." >&2
  echo "Please install Python 3 via Homebrew: 'brew install python@3.12'" >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
ARCH="$(uname -m)"
echo "Detected macOS architecture: $ARCH ($PY_VER)"

# Optional Homebrew dependency hints
if command -v brew >/dev/null 2>&1; then
  echo "Homebrew detected. Checking optional multimedia tools..."
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Tip: Run 'brew install ffmpeg portaudio' for optimal microphone and audio support."
  fi
fi

mkdir -p "$APP_SUPPORT" "$BIN_DIR" "$HOME/Applications"

# Copy application files
if [[ "$ROOT" != "$APP_SUPPORT" ]]; then
  echo "Copying KALKI files to $APP_SUPPORT..."
  cp -a "$APP_DIR" "$APP_SUPPORT/"
  if [[ -d "$ROOT/assets" ]]; then
    cp -a "$ROOT/assets" "$APP_SUPPORT/"
  fi
  APP_DIR="$APP_SUPPORT/app"
fi

# Create dedicated virtual environment
echo "Setting up Python virtual environment in $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing macOS-compatible Python dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
if [[ -f "$APP_DIR/requirements-mac.txt" ]]; then
  "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements-mac.txt"
elif [[ -f "$APP_DIR/requirements-linux.txt" ]]; then
  "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements-linux.txt"
fi

# Ensure default config exists
if [[ ! -f "$APP_DIR/config.py" && -f "$APP_DIR/config.example.py" ]]; then
  cp "$APP_DIR/config.example.py" "$APP_DIR/config.py"
  echo "Created default config.py from template."
fi

# Create CLI executable wrapper in ~/.local/bin/kalki
LAUNCHER_WRAPPER="$BIN_DIR/kalki"
cat > "$LAUNCHER_WRAPPER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$ROOT/mac/mac_launcher.py" "\$@"
EOF
chmod +x "$LAUNCHER_WRAPPER"

# Assemble native macOS .app bundle
echo "Creating macOS Application Bundle: $APP_BUNDLE..."
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>kalki_mac</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.kalki.assistant</string>
    <key>CFBundleName</key>
    <string>KALKI</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.4.0</string>
    <key>CFBundleVersion</key>
    <string>1.4.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>KALKI requires microphone access for voice conversations and voice command recognition.</string>
</dict>
</plist>
EOF

cat > "$APP_BUNDLE/Contents/MacOS/kalki_mac" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$APP_DIR/../mac/mac_launcher.py"
EOF
chmod +x "$APP_BUNDLE/Contents/MacOS/kalki_mac"

echo ""
echo "========================================================"
echo "  KALKI macOS Installation Successful!"
echo "========================================================"
echo "You can launch KALKI in any of the following ways:"
echo "  1. Open ~/Applications/KALKI.app or Launchpad"
echo "  2. Terminal command: kalki (ensure ~/.local/bin is in PATH)"
echo "  3. Direct script: $VENV_DIR/bin/python $ROOT/mac/mac_launcher.py"
echo ""
