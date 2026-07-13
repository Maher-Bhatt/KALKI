<#
.SYNOPSIS
    Step 1 of 4: Build KALKI executables using PyInstaller.

.DESCRIPTION
    Compiles all Python source files into standalone Windows executables
    using PyInstaller. Output goes to app/dist/.

.NOTES
    Run from project root:
    powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\build.ps1
#>

param(
    [switch]$Clean  # Force clean rebuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Item (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))).FullName
$AppDir      = Join-Path $ProjectRoot "app"
$BuildTools  = Join-Path $AppDir "build_tools"
$DistDir     = Join-Path $AppDir "dist"
$LogDir      = Join-Path $ProjectRoot "microsoft_store\output\logs"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "build_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "============================================"
Log "  KALKI Store Build - Step 1: PyInstaller"
Log "============================================"
Log "Project root: $ProjectRoot"
Log "Log file: $LogFile"

# Clean if requested
if ($Clean -and (Test-Path $DistDir)) {
    Log "Cleaning dist/ directory..."
    Remove-Item -Recurse -Force $DistDir
}

# Run PyInstaller via the existing build script
Log "Running build_installer.py..."
Push-Location $BuildTools
try {
    py build_installer.py 2>&1 | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        # build_installer.py may fail at the Inno Setup step — that's OK for Store builds
        Log "WARNING: build_installer.py exited with code $LASTEXITCODE (Inno Setup step may have failed — acceptable for Store builds)"
    }
} finally {
    Pop-Location
}

# Verify critical dist folders exist
$required = @("KALKI", "KALKI_Server", "KALKI_Listener", "KALKI_Setup_Wizard")
$missing = @()
foreach ($folder in $required) {
    $p = Join-Path $DistDir $folder
    if (-not (Test-Path $p)) {
        $missing += $folder
    }
}

if ($missing.Count -gt 0) {
    $missingString = $missing -join ', '
    Log "ERROR: Missing required dist folders: $missingString"
    exit 1
}

Log ""
Log "Build complete. All required executables are in: $DistDir"
Log "Proceed to: microsoft_store\scripts\package.ps1"
