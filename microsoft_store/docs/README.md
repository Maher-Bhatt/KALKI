# KALKI — Microsoft Store Build System

## Overview

This directory contains the complete Microsoft Store MSIX build pipeline for KALKI.
It produces a `.msix` package ready for upload to Microsoft Partner Center.

## Directory Structure

```
microsoft_store/
├── AppxManifest.xml          # MSIX package manifest (identity, permissions, visuals)
├── build_msix.ps1            # Master pipeline script (runs all steps)
│
├── packaging/
│   ├── VFS/                  # Virtual File System (reserved for Store sandboxing)
│   ├── AppFiles/             # (Generated) Flat package layout for makeappx.exe
│   └── store_build.txt       # Marker file that disables the GitHub auto-updater
│
├── assets/                   # Store visual assets (logos, tiles, splash screen)
│   ├── StoreLogo.png         # 50x50
│   ├── Square44x44Logo.png   # 44x44 + target sizes
│   ├── Square71x71Logo.png   # 71x71
│   ├── Square150x150Logo.png # 150x150
│   ├── Wide310x150Logo.png   # 310x150
│   ├── SplashScreen.png      # 620x300
│   └── ...                   # Additional target sizes
│
├── scripts/
│   ├── build.ps1             # Step 1: PyInstaller compilation
│   ├── package.ps1           # Step 2: MSIX layout assembly + makeappx
│   ├── sign.ps1              # Step 3: Self-signed cert for local testing
│   └── validate.ps1          # Step 4: Package validation
│
├── docs/
│   ├── README.md             # This file
│   ├── StoreChecklist.md     # Pre-submission checklist
│   └── Submission.md         # Step-by-step submission guide
│
└── output/
    ├── KALKI.msix            # (Generated) Final MSIX package
    └── logs/                 # Build and validation logs
```

## Build Pipeline

```
Python Source  →  PyInstaller  →  Windows EXE
    →  Create MSIX Layout  →  Generate AppxManifest
    →  Package MSIX  →  Validate Package
    →  Upload to Microsoft Store
```

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.x | Source language | python.org |
| PyInstaller | .py → .exe compiler | `pip install pyinstaller` |
| Pillow | Asset generation | `pip install Pillow` |
| Windows 10/11 SDK | `makeappx.exe`, `signtool.exe` | Visual Studio Installer |
| Inno Setup 6 | .exe installer (for non-Store releases) | jrsoftware.org |

## Quick Start

### Full build (from scratch):
```powershell
powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1
```

### Skip PyInstaller (reuse existing dist/):
```powershell
powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1 -SkipBuild
```

### Build + Sign for local sideload testing:
```powershell
powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1 -SkipBuild -Sign
```

### Run individual steps:
```powershell
powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\build.ps1
powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\package.ps1
powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\sign.ps1
powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\validate.ps1
```

### Regenerate Store assets:
```powershell
py microsoft_store\generate_assets.py
```

## Configuration

### Partner Center Product Identity

Before building a Store-submittable MSIX, update `AppxManifest.xml` with your real values from
Partner Center → Apps and games → Kalki → Product Identity:

| Manifest Field | Partner Center Field |
|---|---|
| `Identity Name="..."` | Package/Identity/Name |
| `Identity Publisher="..."` | Package/Identity/Publisher |
| `PublisherDisplayName` | Publisher display name |

### Auto-Updater Behavior

| Build Type | `store_build.txt` Present? | Auto-Updater |
|---|---|---|
| Normal `.exe` installer | No | Enabled (checks GitHub releases) |
| Microsoft Store `.msix` | Yes | Disabled (Store manages updates) |

## Dual Release Strategy

KALKI maintains two parallel release channels:

| Channel | Format | Update Method | Output |
|---|---|---|---|
| GitHub / Direct | `KALKI_Setup.exe` | Built-in auto-updater | `Output/KALKI_Setup.exe` |
| Microsoft Store | `KALKI.msix` | Windows Store | `microsoft_store/output/KALKI.msix` |

Both use the same source code. The only difference is the presence of `store_build.txt` in the Store build.
