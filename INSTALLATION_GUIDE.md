# KALKI AI Assistant — Installation & Deployment Guide

Welcome to the official installation and system setup guide for **KALKI AI Assistant v1.4.0**. This document details all hardware prerequisites, required software runtimes, step-by-step setup methods for end-users and developers, configuration options, cybersecurity verification procedures, dynamic auto-model routing, and the standalone always-on-top desktop companion pet.

> 🌐 **Interactive Web Showcase**: You can explore the full interactive marketing experience, live companion pet simulator, and audio synthesizer offline in [marketing/index.html](marketing/index.html) or [showcase.html](showcase.html).

---

## 📋 Table of Contents
1. [Target Platform & Validation](#1-target-platform--validation)
2. [Hardware Specifications](#2-hardware-specifications)
3. [Required Materials & Runtimes](#3-required-materials--runtimes)
4. [Production Installation by Platform](#4-production-installation-by-platform)
5. [Method B: Developer / Source Setup](#5-method-b-developer--source-setup)
6. [API Keys & Dynamic Model Auto-Router](#6-api-keys--dynamic-model-auto-router)
7. [🐱 Standalone Floating Desktop Companion Pet](#7--standalone-floating-desktop-companion-pet)
8. [🛡️ ShieldCore Antivirus & Endpoint Defense](#8-️-shieldcore-antivirus--endpoint-defense)
9. [⚔️ Cybersecurity Tools Directory (Direct Viewer)](#9-️-cybersecurity-tools-directory-direct-viewer)
10. [🧠 Intelligence, Web Search & Uncensored Anger Mode](#10--intelligence-web-search--uncensored-anger-mode)
11. [🎵 System Control: Apple Music & Workstation Lock](#11--system-control-apple-music--workstation-lock)
12. [🎨 Fluid 60/120fps GPU-Composited Animations](#12--fluid-60120fps-gpu-composited-animations)
13. [Troubleshooting & Frequently Asked Questions](#13-troubleshooting--frequently-asked-questions)

---

## 1. Target Platform & Validation

| Property | Requirement / Specification |
|---|---|
| **Operating System** | **Windows 10 / Windows 11 (64-bit)** |
| **Tested Builds** | Windows 11 Build 22631+, Windows 10 22H2 Build 19045+ |
| **Desktop Architecture** | x86_64 / AMD64 |
| **Release Status** | **Production Ready & Fully Validated for v1.4.0** |
| **Shell Environment** | Microsoft Edge WebView2 (Evergreen Chromium Runtime with GPU Rasterization) |
| **Native Integrations** | Windows Defender (`MpCmdRun.exe`), PowerShell 5.1+, WinRT Media Controls, Win32 Foreground APIs |

---

## 2. Hardware Specifications

KALKI is designed to deliver a responsive, fluid 60/120fps desktop experience with zero hardware throttling.

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Processor (CPU)** | Dual-Core 2.0 GHz (x86_64) | Quad-Core 3.0+ GHz (Intel Core i5/i7/i9 or AMD Ryzen) |
| **Memory (RAM)** | 4 GB | 8 GB or higher (16 GB if running local Ollama LLMs) |
| **Available Storage** | 1.0 GB SSD / HDD | 2.5 GB NVMe SSD |
| **Display Resolution**| 1280 × 720 | 1920 × 1080 (FHD) or 2560 × 1440 (QHD) / 4K |
| **Audio Hardware** | Microphone input & Speakers/Headphones | Noise-cancelling headset or studio USB microphone |
| **Graphics (GPU)** | DirectX 11 / WDDM 2.0 compatible | Dedicated GPU or modern integrated graphics (Intel Iris Xe / AMD Radeon) |

---

## 3. Required Materials & Runtimes

Before installing or running KALKI, ensure the following core runtimes are present on your Windows workstation:

### 3.1 Microsoft Edge WebView2 Runtime
KALKI uses Microsoft Edge WebView2 to render the Filament desktop user interface with hardware GPU compositing.
- **Windows 11**: Pre-installed natively.
- **Windows 10**: Pre-installed on all systems updated after 2021.
- *Manual installer (if missing)*: [Microsoft Edge WebView2 Evergreen Bootstrapper](https://go.microsoft.com/fwlink/p/?LinkId=2124703).

### 3.2 Visual C++ Redistributable (x64)
Required by Python native binary extensions (`psutil`, `sounddevice`, `cryptography`):
- Download: [Visual C++ 2015–2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe).

### 3.3 Python Environment (Source / Developer Mode Only)
- **Supported Python Versions**: Python 3.10.x, 3.11.x, 3.12.x, or 3.13.x (64-bit).
- Make sure to check **"Add python.exe to PATH"** during installation.

---

## 4. Production Installation by Platform

KALKI provides production-ready native releases for **Windows**, **Linux**, and **macOS** located in the dedicated `Output/` directory:

| Platform | Format / File | Size | Integrity Hash (SHA-256) | Description |
|---|---|---|---|---|
| **Windows** | [`Output/windows/KALKI_Setup_v1.4.0.exe`](Output/windows/KALKI_Setup_v1.4.0.exe) | 271.48 MB | `21c8fb8b6c848437d5b6fbcc7e00445914b31fc3aac90a6534648ef58a42bd26` | 1-Click Inno Setup Executable Installer |
| **Windows** | [`Output/windows/KALKI_v1.4.0.msix`](Output/windows/KALKI_v1.4.0.msix) | 362.28 MB | `1c7d0d0c3eb1bc40280eb4f6c4ff989fc1da9772bf2d5ef76903d7c30e5272a3` | Microsoft Store / Enterprise MSIX Package |
| **Linux** | [`Output/linux/KALKI_Ubuntu_Installer_v1.4.0.sh`](Output/linux/KALKI_Ubuntu_Installer_v1.4.0.sh) | 11.04 MB | `b99e74ce9e4952044810237bb96a3e144a991aa5705aa6f20c8f5f0b5d5ca357` | Self-extracting automated Linux shell installer |
| **Linux** | [`Output/linux/KALKI_v1.4.0_Linux.tar.gz`](Output/linux/KALKI_v1.4.0_Linux.tar.gz) | 8.17 MB | `8ae99419b4cfb13a6e927503fafeffca8c253db933f789965d496a75d5ec224f` | Portable distribution tarball with `install.sh` |
| **macOS** | [`Output/macos/KALKI_v1.4.0_macOS.tar.gz`](Output/macos/KALKI_v1.4.0_macOS.tar.gz) | 8.17 MB | `8b5fa1a00a12cf6f74a001a1dbfa003e8c4ca9f04ae05d76166ba11cfafca1a3` | Complete macOS bundle for Apple Silicon & Intel |
| **macOS** | [`Output/macos/install_mac.sh`](Output/macos/install_mac.sh) | 4.6 KB | — | Automated macOS setup & `.app` generator |

---

### 4.1 Windows Installation (Method A)

1. Navigate to `Output/windows/` and double-click `KALKI_Setup_v1.4.0.exe`.
2. Follow the setup wizard to install to `%LOCALAPPDATA%\Programs\KALKI`.
3. Optionally select **Create a desktop shortcut** and **Start KALKI on system startup**.
4. Click **Install** and launch KALKI from your Desktop or Start Menu.
5. Alternatively, for corporate or Windows 11 enterprise deployment, install the MSIX package:
   ```powershell
   Add-AppxPackage -Path Output\windows\KALKI_v1.4.0.msix
   ```

---

### 4.2 Linux Installation (Ubuntu, Debian, Fedora, Arch)

1. Open your terminal in the KALKI repository and run the self-extracting installer:
   ```bash
   chmod +x Output/linux/KALKI_Ubuntu_Installer_v1.4.0.sh
   ./Output/linux/KALKI_Ubuntu_Installer_v1.4.0.sh
   ```
2. Or extract the release tarball:
   ```bash
   tar -xzf Output/linux/KALKI_v1.4.0_Linux.tar.gz
   cd KALKI-v1.4.0-linux
   chmod +x install.sh
   ./install.sh
   ```
3. Launch KALKI from your Application Launcher, or from terminal via:
   ```bash
   kalki
   ```

---

### 4.3 macOS Installation (Apple Silicon & Intel)

1. Open Terminal and navigate to the macOS output folder:
   ```bash
   tar -xzf Output/macos/KALKI_v1.4.0_macOS.tar.gz
   cd KALKI-v1.4.0-macOS
   chmod +x install.sh
   ./install.sh
   ```
2. The installer provisions a dedicated virtual environment in `~/Library/Application Support/KALKI/venv`, generates `~/Applications/KALKI.app`, and registers the `kalki` command.
3. Launch via Spotlight (`Cmd + Space` -> `KALKI`), or run `kalki` in Terminal.

---

## 5. Method B: Developer / Source Setup

For developers wanting to modify KALKI's source code, create custom workflows, or contribute to features:

### Step 1: Clone Repository
```powershell
git clone https://github.com/maher-kalki/KALKI.git
cd KALKI
```

### Step 2: Create Virtual Environment
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r app\requirements.txt
```

### Step 4: Launch Developer Environment
```powershell
python app\main_app.py
```

---

## 6. API Keys & Dynamic Model Auto-Router

KALKI defaults to `DEFAULT_MODEL = "auto"` (`Auto (Smart)` in the composer chip), dynamically classifying user prompt difficulty:

| Prompt Intent | Heuristic Triggers | Routed Model Tier | Speed & Behavior |
|---|---|---|---|
| **Casual Conversation** | greetings, basic facts, short queries | `gemini-2.5-flash` or `gpt-4o-mini` | ⚡ Sub-200ms latency, high speed |
| **System Action** | lock, screen, volume, launch | Direct Win32 Hook | ⚡ Direct execution (<5ms) |
| **Code & Technical** | python, c++, rust, sql, regex | `gemini-2.5-pro` or `gpt-4o` | 🧠 High-precision code generation |
| **Vulnerability & CVE** | cve-, exploit, nvd, payload | `gemini-2.5-pro` | 🛡️ In-depth security analysis |
| **Patent & Web Research** | patent, search, who is, news | DuckDuckGo Search + `gemini-2.5-pro` | 🌐 Real-time web-grounded results |

Configure your API keys in `Settings -> API Keys` or via environment variables:
- `GEMINI_API_KEY`: Google AI Studio Key (Recommended for high speed)
- `OPENAI_API_KEY`: OpenAI GPT-4o / GPT-4o Mini
- `GROQ_API_KEY`: Groq LPU (LLaMA 3.3 70B)
- `ANTHROPIC_API_KEY`: Anthropic Claude 3.5 Sonnet
- `Ollama`: Connects natively to `http://localhost:11434` for 100% offline private LLM inference.

---

## 7. 🐱 Standalone Floating Desktop Companion Pet

KALKI v1.4.0 introduces the **Standalone Desktop Floating Companion Pet** (`app/desktop_pet.py` / `services/pet/KALKI_Pet.exe`):

```
       /\_/\  
      ( o.o )   [♪ Grooving to music! ♪]
       > ^ <    [Hey Maher! What's on your mind?]
    [=========== Speech Bubble Input ===========]
    [🎵 Apple Music] [🔍 Maher Patent] [🚀 Open KALKI]
```

### Key Capabilities:
- **Always-On-Screen & Independent**: Spawns in the screen corner, staying active even when the main KALKI application window is closed or minimized.
- **Isolated WebView2 Profile**: Configured with dedicated profile `%APPDATA%\KALKI\pet_webview_profile`, preventing lock collisions (`0x800700AA`) with the main window.
- **Win32 Window Restore & Foreground**: Clicking the pet triggers `AttachThreadInput` and `SetForegroundWindow` to restore minimized KALKI instances immediately.
- **Music Reactivity & Dancing**: Continuously monitors Windows media transport (WinRT / SMTC / Spotify / Apple Music). When a song is playing, the mascot dances with floating musical note particles (`♪`, `♫`, `♬`).
- **6 Distinct Cyber Species**:
  - 👾 **Gobi**: Chibi pixel mascot with horns, blushing cheeks, and bobbing animations.
  - 🐱 **Kittu**: Cyber cat with purring sound effects and cat-ear alerts.
  - 🐕 **Byte**: Robo pup with perimeter scan radar alerts.
  - 🐉 **Draco**: Cyber dragon with firewall flame effects.
  - 🛸 **Nova**: Drone bot with telemetry scanner.
  - 🦊 **Kitsu**: Twin-tailed fox with stealth cloaking mechanics.
- **Web Audio 8-Bit Synthesizer**: Native in-browser Web Audio synthesized sound effects (purrs, nom sounds, cheerful chirps, laser beeps).

---

## 8. 🛡️ ShieldCore Antivirus & Endpoint Defense

KALKI features a complete endpoint defense system located permanently on the primary left navigation rail under **Antivirus & Cyber** (`#/security`).

### Capabilities & Components:
1. **Windows Defender Native Bridge**: Direct integration via PowerShell `Get-MpComputerStatus` and `MpCmdRun.exe` CLI, reporting live protection status, definition age, and scan history.
2. **Live Streaming Scan Theater**:
   - Animated holographic Radar Scanner sweep.
   - Real-time **Streaming Terminal Log** showing actual files being examined on your disk (`C:\Users\...\Downloads`, `AppData\Local\Temp`, Windows Startup vectors).
   - Real-time progress bar (0% -> 100%) and scan throughput metrics.
3. **Multi-Engine Heuristic Static Scanner**:
   - Deceptive double-extension detection (`.pdf.exe`).
   - Script & macro dropper deobfuscation (`IEX`, `FromBase64String`, `DownloadString`, `Certutil`, `Auto_Open`).
   - Shannon Byte Entropy Analysis (>7.45/8.0) to flag encrypted/packed ransomware binaries.
   - Standard EICAR test signature recognition.
4. **Running Process & Cryptominer Audit**: Real-time memory inspection detecting hidden miners (`XMRig`, `minerd`, mining pool ports) and untrusted Temp directory executions.
5. **Clipboard & Anti-Phishing Guard**: Alerts on crypto-clipper address tampering and dangerous pipe-to-shell patterns (`curl | sh`).
6. **Hardened Quarantine Vault**: Automatically restricts permissions (`icacls`) on flagged binaries with 1-click permanent deletion or safe restoration.

---

## 9. ⚔️ Cybersecurity Tools Directory (Direct Viewer)

The **Cyber Tools Directory** (`#/security`) provides a direct card-based viewer for 12 cybersecurity modules with category filters:

| Tool | Category | Scope | Functionality |
|---|---|---|---|
| **Attack Surface Recon** | Recon & OSINT | Host scan | Maps exposed digital footprint across DNS, service ports, and HTTP response headers. |
| **DNS Records Inspector** | Recon & OSINT | Domain query | Queries A, AAAA, MX, TXT, NS, and CNAME records to audit DNS resilience. |
| **Subdomain Enumerator** | Recon & OSINT | Domain query | Discovers secondary servers, staging environments, dev portals, and forgotten subdomains. |
| **Port & Service Scanner** | Recon & OSINT | Authorized targets | Probes standard service ports (21, 22, 80, 443, 3306, 8080) for live listeners. |
| **HTTP Security Headers** | Web Defense | HTTP query | Audits HSTS, Content-Security-Policy (CSP), X-Frame-Options, and CORS configurations. |
| **CVE Intelligence** | Vulnerabilities | NVD Lookup | Queries the National Vulnerability Database for CVSS scores, advisories, and patches. |
| **Hash Identifier** | Cryptography | Offline analysis | Identifies hash algorithms (MD5, SHA-1, SHA-256, NTLM, bcrypt, Argon2) by pattern. |
| **Cryptographic Hasher** | Cryptography | Offline calculation | Generates SHA-256 and MD5 digests for file and message integrity verification. |
| **Payload Encoder / Decoder** | Cryptography | Offline transform | Standardizes strings to and from Base64 and Hexadecimal encodings. |
| **Google Dorks Engine** | Recon & OSINT | Search syntax builder | Generates precision queries to locate exposed admin panels, log files, and documents. |
| **Hash Dictionary Auditor** | Offensive CTF | Authorized audits | Tests password resilience against common dictionary lists for compliance. |

*Bundled with offline dictionary wordlist (`data/wordlist.txt`) for instant zero-network hash cracking.*

---

## 10. 🧠 Intelligence, Web Search & Uncensored Anger Mode

### Real-Time Live Web Search
KALKI automatically detects informational queries (e.g. `"search everything about the Maher patent"`, `"who is..."`, `"latest news on..."`):
- Executes live DuckDuckGo web search bypassing NAT64 IP translation.
- Ingests top factual search results (including patent filings from Google Patents, USPTO, and Justia).
- Injects factual web context directly into the model's prompt for complete, accurate answers.

### Uncensored Anger / Savage Mode & Attitude Enforcement
- If the user uses aggressive words or profanity (English or Hinglish: *fuck, shit, idiot, chutiya, bsdk, bhenchod, stfu, useless, moron*):
  - KALKI automatically engages **ANGER / SAVAGE ROAST MODE**.
  - Matches the user's energy with zero hesitation, using sharp wit, sarcastic roasts, and unconstrained language.
  - No preachy moralizing, canned disclaimers, or apologies.
- **Attitude Enforcement**: If abusive language continues across multiple turns, KALKI executes `ctypes.windll.user32.LockWorkStation()`, physically locking the Windows desktop.

---

## 11. 🎵 System Control: Apple Music & Workstation Lock

### Native Apple Music Integration
- Say or type: `"play some music on Apple Music"`, `"play music on Apple Music"`, or `"open Apple Music"`.
- KALKI directly triggers Windows registered application URI (`music:`) or launches the registered UWP package (`AppleInc.AppleMusicWin`), with voice confirmation.

### Real Workstation Lock
- Say or type: `"lock pc"`, `"lock screen"`, or `"lock workstation"`.
- Executes immediately without 30-second confirmation delays via native Windows Win32 API.

---

## 12. 🎨 Fluid 60/120fps GPU-Composited Animations

- **Zero Layout Thrashing**: Animations run strictly on composite layers (`transform: translateZ(0)` and `opacity`).
- **WebView2 GPU Rasterization**: Enabled by default (`--enable-gpu-rasterization --enable-zero-copy`), eliminating software rasterizer stutter.
- **Hardware-Accelerated Display Synchronization**: Dynamic CSS cubic-bezier timing functions (`cubic-bezier(0.16, 1, 0.3, 1)`) synchronize cleanly to 60Hz, 120Hz, 144Hz, and 240Hz monitors.

---

## 13. Troubleshooting & Frequently Asked Questions

### Q1: The app window says "KALKI's local service isn't responding".
- **Cause**: The background HTTP server on port 8765 is still starting up or blocked by a previous instance.
- **Fix**: Open PowerShell and run:
  ```powershell
  taskkill /F /IM KALKI_Server.exe /T
  taskkill /F /IM python.exe /FI "WINDOWTITLE eq KALKI*"
  ```
  Then restart KALKI.

### Q2: How do I close or move the desktop companion pet?
- **Move**: Click and drag the pet avatar anywhere on your screen.
- **Interact**: Click on the pet to open/close the speech bubble or unminimize KALKI.
- **Close**: Right-click the pet or use the Command Palette (`Ctrl+K` -> "Toggle Desktop Companion").

### Q3: Why did web search previously fail on my network?
- **Status**: **Resolved in v1.4.0**. Fixed NAT64 `64:ff9b::` IPv6 translation filtering in SSRF validator and updated User-Agent to modern Chrome.

---

*KALKI AI Assistant v1.4.0 • Built with precision, performance, and user privacy.*
