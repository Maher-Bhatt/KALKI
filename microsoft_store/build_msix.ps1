<#
.SYNOPSIS
    Build KALKI into an MSIX package for Microsoft Store submission.

.DESCRIPTION
    This script:
    1. Runs PyInstaller to freeze all Python scripts into dist/ folders.
    2. Assembles a flat package layout in microsoft_store/package_root/.
    3. Generates required Store visual assets from the KALKI logo.
    4. Copies AppxManifest.xml into the package root.
    5. Marks this as a Store build (disables auto-updater).
    6. Runs makeappx.exe to produce Output/KALKI_Store.msix.

.NOTES
    Run from the project root: powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1
#>

param(
    [switch]$SkipPyInstaller  # Use -SkipPyInstaller if dist/ is already built
)

$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────
$ProjectRoot   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$AppDir        = Join-Path $ProjectRoot "app"
$StoreDir      = Join-Path $ProjectRoot "microsoft_store"
$PackageRoot   = Join-Path $StoreDir "package_root"
$AssetsOut     = Join-Path $PackageRoot "Assets"
$OutputDir     = Join-Path $ProjectRoot "Output"
$DistDir       = Join-Path $AppDir "dist"
$SourceLogo    = Join-Path $ProjectRoot "assets\kalki_logo.png"
$SourceIcon    = Join-Path $ProjectRoot "assets\kalki_icon.ico"

# makeappx.exe from Windows SDK
$MakeAppx = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"
if (-not (Test-Path $MakeAppx)) {
    Write-Error "makeappx.exe not found at $MakeAppx. Please install Windows 10/11 SDK."
    exit 1
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  KALKI — Microsoft Store MSIX Builder" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# ── Step 1: Build with PyInstaller (reuse existing build_installer.py logic) ──
if (-not $SkipPyInstaller) {
    Write-Host "[1/6] Building executables with PyInstaller..." -ForegroundColor Yellow
    Push-Location (Join-Path $AppDir "build_tools")
    py build_installer.py
    Pop-Location
    # The Inno Setup step will fail or succeed — we don't care, we only need dist/
    Write-Host "[1/6] PyInstaller build complete.`n" -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping PyInstaller (using existing dist/).`n" -ForegroundColor DarkGray
}

# ── Step 2: Clean and create package layout ──
Write-Host "[2/6] Assembling MSIX package layout..." -ForegroundColor Yellow
if (Test-Path $PackageRoot) {
    Remove-Item -Recurse -Force $PackageRoot
}
New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $AssetsOut -Force | Out-Null

# Copy all dist/ subfolders (each PyInstaller target) flat into package root
$distFolders = @("KALKI", "KALKI_Server", "KALKI_Listener", "KALKI_Setup_Wizard", "KALKI_Setup_Google", "KALKI_Setup_Spotify")
foreach ($folder in $distFolders) {
    $src = Join-Path $DistDir $folder
    if (Test-Path $src) {
        Write-Host "   Copying $folder..." -ForegroundColor DarkGray
        Copy-Item -Path "$src\*" -Destination $PackageRoot -Recurse -Force
    } else {
        Write-Warning "   dist/$folder not found — skipping."
    }
}

# Copy browsers
$browsersDir = Join-Path $ProjectRoot "browsers"
if (Test-Path $browsersDir) {
    Write-Host "   Copying browsers..." -ForegroundColor DarkGray
    $destBrowsers = Join-Path $PackageRoot "browsers"
    Copy-Item -Path $browsersDir -Destination $destBrowsers -Recurse -Force
}

# Copy assets
$assetsDir = Join-Path $ProjectRoot "assets"
if (Test-Path $assetsDir) {
    Write-Host "   Copying assets..." -ForegroundColor DarkGray
    $destAssets = Join-Path $PackageRoot "assets"
    New-Item -ItemType Directory -Path $destAssets -Force | Out-Null
    Copy-Item -Path "$assetsDir\*" -Destination $destAssets -Recurse -Force
}

# Copy web files
foreach ($webFile in @("index.html", "manifest.json", "service-worker.js", "config.example.py")) {
    $src = Join-Path $AppDir $webFile
    if (Test-Path $src) {
        Copy-Item $src -Destination $PackageRoot -Force
    }
}

# Copy LICENSE and TERMS
foreach ($docFile in @("LICENSE", "TERMS.md")) {
    $src = Join-Path $ProjectRoot $docFile
    if (Test-Path $src) {
        Copy-Item $src -Destination $PackageRoot -Force
    }
}

# Create data directory
New-Item -ItemType Directory -Path (Join-Path $PackageRoot "data") -Force | Out-Null

Write-Host "[2/6] Package layout assembled.`n" -ForegroundColor Green

# ── Step 3: Create Store build marker (disables auto-updater) ──
Write-Host "[3/6] Creating Store build marker..." -ForegroundColor Yellow
Set-Content -Path (Join-Path $PackageRoot "store_build.txt") -Value "This file indicates a Microsoft Store build. Auto-updater is disabled."
Write-Host "[3/6] Store marker created.`n" -ForegroundColor Green

# ── Step 4: Generate required MSIX visual assets ──
Write-Host "[4/6] Generating Store visual assets..." -ForegroundColor Yellow

# Use Python + Pillow to resize the logo into all required MSIX asset sizes
$assetScript = @"
from PIL import Image
import os, sys

src = sys.argv[1]
out = sys.argv[2]

img = Image.open(src).convert("RGBA")

sizes = {
    "StoreLogo.png": (50, 50),
    "Square44x44Logo.png": (44, 44),
    "Square71x71Logo.png": (71, 71),
    "Square150x150Logo.png": (150, 150),
    "Wide310x150Logo.png": (310, 150),
    "SplashScreen.png": (620, 300),
    "Square44x44Logo.targetsize-24_altform-unplated.png": (24, 24),
    "Square44x44Logo.targetsize-32_altform-unplated.png": (32, 32),
    "Square44x44Logo.targetsize-48_altform-unplated.png": (48, 48),
    "Square44x44Logo.targetsize-256_altform-unplated.png": (256, 256),
}

for name, (w, h) in sizes.items():
    resized = img.resize((w, h), Image.LANCZOS)
    out_path = os.path.join(out, name)
    resized.save(out_path, "PNG")
    print(f"   Generated {name} ({w}x{h})")
"@

$assetScriptPath = Join-Path $StoreDir "_gen_assets.py"
Set-Content -Path $assetScriptPath -Value $assetScript -Encoding UTF8

py $assetScriptPath $SourceLogo $AssetsOut

Remove-Item $assetScriptPath -Force -ErrorAction SilentlyContinue

Write-Host "[4/6] Visual assets generated.`n" -ForegroundColor Green

# ── Step 5: Copy AppxManifest.xml ──
Write-Host "[5/6] Copying AppxManifest.xml..." -ForegroundColor Yellow
$manifestSrc = Join-Path $StoreDir "AppxManifest.xml"
Copy-Item $manifestSrc -Destination $PackageRoot -Force
Write-Host "[5/6] Manifest copied.`n" -ForegroundColor Green

# ── Step 6: Build the MSIX package ──
Write-Host "[6/6] Building MSIX package..." -ForegroundColor Yellow
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$msixPath = Join-Path $OutputDir "KALKI_Store.msix"
if (Test-Path $msixPath) {
    Remove-Item $msixPath -Force
}

& $MakeAppx pack /d $PackageRoot /p $msixPath /l /o

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================" -ForegroundColor Green
    Write-Host "  SUCCESS! MSIX package created:" -ForegroundColor Green
    Write-Host "  $msixPath" -ForegroundColor White
    Write-Host "============================================`n" -ForegroundColor Green

    $hash = (Get-FileHash -Path $msixPath -Algorithm SHA256).Hash
    Write-Host "SHA-256: $hash" -ForegroundColor Cyan
} else {
    Write-Error "makeappx.exe failed with exit code $LASTEXITCODE"
    exit 1
}
