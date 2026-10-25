# KALKI AI Assistant — macOS Deployment & User Guide

Welcome to the official macOS documentation for **KALKI AI Assistant v1.4.0**.

---

## 🍏 Target Platforms & Compatibility
- **Architectures**: Apple Silicon (M1, M2, M3, M4) & Intel (x86_64)
- **Supported macOS Versions**:
  - macOS 15 (Sequoia)
  - macOS 14 (Sonoma)
  - macOS 13 (Ventura)
  - macOS 12 (Monterey)
  - macOS 11 (Big Sur)

---

## 📦 Prerequisites

### 1. Python 3 (3.10, 3.11, 3.12, or 3.13)
macOS comes with Python command line tools or you can install standard Python via Homebrew:
```bash
brew install python@3.12
```

### 2. Optional Audio Utilities (Homebrew)
For enhanced microphone input and audio streaming:
```bash
brew install ffmpeg portaudio
```

---

## 🚀 Installation & Setup

### Method 1: Automated 1-Click Installer
From terminal, navigate to the extracted release directory or run:
```bash
chmod +x install.sh
./install.sh
```

The installer will:
1. Copy the application to `~/Library/Application Support/KALKI`.
2. Provision an isolated virtual environment with all macOS-compatible dependencies (`pywebview`, `edge-tts`, `cryptography`, etc.).
3. Generate a standard native macOS Application bundle at `~/Applications/KALKI.app`.
4. Register the `kalki` CLI command in `~/.local/bin`.

---

## 🖥️ Running KALKI on macOS

1. **Spotlight / Launchpad / Applications**:
   - Open `~/Applications/KALKI.app`.
   - On first launch, macOS will prompt for Microphone access if voice wake-word listening is enabled.
2. **Terminal**:
   ```bash
   kalki
   ```
3. **Direct Python Runner**:
   ```bash
   ~/Library/Application\ Support/KALKI/venv/bin/python ~/Library/Application\ Support/KALKI/app/../mac/mac_launcher.py
   ```

---

## 🎵 Apple Music & macOS Integrations
- **Apple Music Control**: Native AppleScript (`osascript`) controls allow you to speak or type commands like:
  - *"Play some music"*
  - *"Pause music"*
  - *"Next track"*
  - KALKI automatically bridges to the native macOS Music app.
- **Natural Voice Synthesis**: Uses Edge TTS (`en-US-AndrewMultilingualNeural`) with instant fallback to built-in high quality macOS speech voices (`say -v Samantha` or `Alex`) if offline.
- **Native Notifications**: System alerts and reminders appear directly in the macOS Notification Center.
