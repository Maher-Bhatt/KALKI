# KALKI — Microsoft Store Build

This directory contains everything needed to build and submit KALKI to the Microsoft Store.

## Files

| File | Purpose |
|------|---------|
| `AppxManifest.xml` | MSIX package manifest (identity, permissions, visual assets) |
| `build_msix.ps1` | PowerShell script to compile the MSIX package |
| `package_root/` | (Generated) Flat directory layout used by `makeappx.exe` |

## Prerequisites

1. **Windows 10/11 SDK** — Provides `makeappx.exe`
2. **Python 3.x + PyInstaller** — Compiles .py scripts into .exe
3. **Pillow** (`pip install Pillow`) — Generates Store visual assets from `kalki_logo.png`

## How to Build

```powershell
# From the project root:
powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1
```

The output file will be: `Output/KALKI_Store.msix`

## ⚠️ Before Building

You **must** update `AppxManifest.xml` with your real Partner Center identity values:

1. Go to [Partner Center](https://partner.microsoft.com/) → Apps and games → Kalki → Product Identity
2. Copy:
   - **Package/Identity/Name** → Replace `PLACEHOLDER_PACKAGE_IDENTITY_NAME`
   - **Package/Identity/Publisher** → Replace `PLACEHOLDER_PUBLISHER_ID`
   - **Package/Properties/PublisherDisplayName** → Replace `PLACEHOLDER_PUBLISHER_DISPLAY_NAME`

## Submitting to the Store

1. Build the `.msix` using the script above.
2. Go to Partner Center → Apps and games → Kalki → Start submission.
3. Under **Packages**, upload `Output/KALKI_Store.msix`.
4. Fill in Store listing details (description, screenshots, pricing).
5. Submit for certification review (usually takes 1–3 business days).
