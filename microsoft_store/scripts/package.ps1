<#
.SYNOPSIS
    Step 2 of 4: Assemble the MSIX package layout from PyInstaller dist output.
.DESCRIPTION
    Takes the compiled executables from app/dist/ and assembles them into
    the flat MSIX package layout required by makeappx.exe.
#>

$ErrorActionPreference = "Stop"
$ScriptDir    = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot  = (Get-Item (Split-Path -Parent (Split-Path -Parent $ScriptDir))).FullName
$AppDir       = Join-Path $ProjectRoot "app"
$DistDir      = Join-Path $AppDir "dist"
$StoreDir     = Join-Path $ProjectRoot "microsoft_store"
$PackageRoot  = Join-Path $StoreDir "packaging\AppFiles"
$AssetsOut    = Join-Path $PackageRoot "Assets"
$StoreAssets  = Join-Path $StoreDir "assets"
$OutputDir    = Join-Path $StoreDir "output"
$LogDir       = Join-Path $OutputDir "logs"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "package_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

$MakeAppx = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "============================================"
Log "  KALKI Store Build -- Step 2: Package MSIX"
Log "============================================"

if (-not (Test-Path $MakeAppx)) {
    Log "ERROR: makeappx.exe not found. Install Windows 10/11 SDK."
    exit 1
}

if (-not (Test-Path $DistDir)) {
    Log "ERROR: dist/ not found. Run build.ps1 first."
    exit 1
}

if (Test-Path $PackageRoot) {
    Log "Cleaning previous package layout..."
    Remove-Item -Recurse -Force $PackageRoot
}
New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $AssetsOut -Force | Out-Null

Log "Copying PyInstaller output..."
$distFolders = @("KALKI", "KALKI_Server", "KALKI_Listener", "KALKI_Setup_Wizard", "KALKI_Setup_Google", "KALKI_Setup_Spotify")
foreach ($folder in $distFolders) {
    $src = Join-Path $DistDir $folder
    if (Test-Path $src) {
        Log "  Copying $folder..."
        Copy-Item -Path "$src\*" -Destination $PackageRoot -Recurse -Force
    } else {
        Log "  WARNING: dist/$folder not found, skipping."
    }
}

$browsersDir = Join-Path $ProjectRoot "browsers"
if (Test-Path $browsersDir) {
    Log "Copying browsers..."
    Copy-Item -Path $browsersDir -Destination (Join-Path $PackageRoot "browsers") -Recurse -Force
}

$appAssets = Join-Path $ProjectRoot "assets"
if (Test-Path $appAssets) {
    Log "Copying app assets..."
    $destAssets = Join-Path $PackageRoot "assets"
    New-Item -ItemType Directory -Path $destAssets -Force | Out-Null
    Copy-Item -Path "$appAssets\*" -Destination $destAssets -Recurse -Force
}

Log "Copying web files..."
foreach ($webFile in @("index.html", "manifest.json", "service-worker.js", "config.example.py")) {
    $src = Join-Path $AppDir $webFile
    if (Test-Path $src) {
        Copy-Item $src -Destination $PackageRoot -Force
    }
}

foreach ($docFile in @("LICENSE", "TERMS.md")) {
    $src = Join-Path $ProjectRoot $docFile
    if (Test-Path $src) {
        Copy-Item $src -Destination $PackageRoot -Force
    }
}

New-Item -ItemType Directory -Path (Join-Path $PackageRoot "data") -Force | Out-Null

Log "Copying store_build.txt marker..."
$markerSrc = Join-Path $StoreDir "packaging\store_build.txt"
Copy-Item $markerSrc -Destination $PackageRoot -Force

Log "Copying Store visual assets..."
if (Test-Path $StoreAssets) {
    Copy-Item -Path "$StoreAssets\*" -Destination $AssetsOut -Recurse -Force
} else {
    Log "WARNING: microsoft_store/assets/ not found. Run generate_assets.py first."
}

Log "Copying AppxManifest.xml..."
$manifestSrc = Join-Path $StoreDir "AppxManifest.xml"
Copy-Item $manifestSrc -Destination $PackageRoot -Force

$manifestContent = Get-Content (Join-Path $PackageRoot "AppxManifest.xml") -Raw
if ($manifestContent -match "PLACEHOLDER") {
    Log ""
    Log "WARNING: AppxManifest.xml still contains PLACEHOLDER values!"
    Log "The MSIX will be built but will NOT pass Store validation."
    Log "Update microsoft_store/AppxManifest.xml with your Partner Center Product Identity."
    Log ""
}

Log "Building MSIX package..."
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$msixPath = Join-Path $OutputDir "KALKI.msix"
if (Test-Path $msixPath) {
    Remove-Item $msixPath -Force
}

& $MakeAppx pack /d $PackageRoot /p $msixPath /l /o 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -eq 0) {
    $hash = (Get-FileHash -Path $msixPath -Algorithm SHA256).Hash
    $size = [math]::Round((Get-Item $msixPath).Length / 1MB, 2)

    Log ""
    Log "============================================"
    Log "  SUCCESS! MSIX package created."
    Log "============================================"
    Log "  Path: $msixPath"
    Log "  Size: $size MB"
    Log "  SHA-256: $hash"
    Log ""
    Log "Next: Run validate.ps1 to check the package."
} else {
    Log "ERROR: makeappx.exe failed with exit code $LASTEXITCODE"
    exit 1
}
