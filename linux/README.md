# KALKI AI Assistant — Linux Deployment & User Guide

Welcome to the official Linux documentation for **KALKI AI Assistant v1.4.0**.

---

## 🐧 Supported Linux Distributions
KALKI has been validated across standard modern 64-bit Linux distributions:
- **Ubuntu**: 20.04 LTS, 22.04 LTS, 24.04 LTS
- **Debian**: 11 (Bullseye), 12 (Bookworm)
- **Fedora**: 38, 39, 40, 41
- **Arch Linux & Manjaro**
- **Linux Mint / Pop!_OS / elementary OS**

---

## 📦 System Dependencies

KALKI operates with minimal external dependencies. For full voice synthesis, microphone capture, and media playback:

### Debian / Ubuntu / Mint / Pop!_OS
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg espeak-ng portaudio19-dev python3-tk
```

### Fedora / RHEL
```bash
sudo dnf install -y python3 python3-pip ffmpeg espeak-ng portaudio-devel python3-tkinter
```

### Arch Linux / Manjaro
```bash
sudo pacman -S --needed python python-pip ffmpeg espeak-ng portaudio tk
```

---

## 🚀 Installation Methods

### Method 1: Self-Extracting 1-Click Installer (Recommended)
Download `Output/linux/KALKI_Ubuntu_Installer_v1.4.0.sh` and run:
```bash
chmod +x KALKI_Ubuntu_Installer_v1.4.0.sh
./KALKI_Ubuntu_Installer_v1.4.0.sh
```
This automatically extracts KALKI, provisions a dedicated Python virtual environment under `~/.local/share/kalki/venv`, registers a desktop application menu entry, and adds the `kalki` CLI command to `~/.local/bin`.

### Method 2: Standard Archive Installation
```bash
tar -xzf KALKI_v1.4.0_Linux.tar.gz
cd KALKI-v1.4.0-linux
chmod +x install.sh
./install.sh
```

---

## 🖥️ Running KALKI on Linux

Once installed, KALKI can be launched from:
1. **Desktop App Menu**: Search for "KALKI" in GNOME, KDE Plasma, or XFCE.
2. **Terminal Command**:
   ```bash
   kalki
   ```
   *(Ensure `~/.local/bin` is in your `$PATH`)*
3. **Direct Binary / Script**:
   ```bash
   ~/.local/share/kalki/venv/bin/python ~/.local/share/kalki/app/linux_launcher.py
   ```

---

## 🛠️ Architecture & Security
- **Daemon Architecture**: `linux_launcher.py` supervises the local backend (`server.py`) and audio listener (`listener.py`), auto-restarting services on unexpected termination.
- **Loopback Security**: The internal HTTP service strictly binds to loopback (`127.0.0.1:8888`) and requires authentication tokens stored in `~/.local/share/KALKI/data/api_token.txt`.
- **Browser & UI**: Launches the dashboard in your system's default browser or hardware-accelerated WebKit window.
