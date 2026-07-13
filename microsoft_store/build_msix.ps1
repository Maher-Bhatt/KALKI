<#
.SYNOPSIS
    Master build script -- runs the full MSIX pipeline end-to-end.
#>
param(
    [switch]$SkipBuild,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).FullName
$ScriptsDir  = Join-Path $ProjectRoot "scripts"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KALKI -- Microsoft Store MSIX Build Pipeline" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Pipeline:"
Write-Host "    Python Source -> PyInstaller -> Windows EXE" -ForegroundColor DarkGray
Write-Host "    -> Create MSIX Layout -> Generate AppxManifest" -ForegroundColor DarkGray
Write-Host "    -> Package MSIX -> Validate Package" -ForegroundColor DarkGray
Write-Host ""

$startTime = Get-Date

if (-not $SkipBuild) {
    Write-Host "Pipeline 1 of 4: Building executables..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "build.ps1")
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Host "WARNING: Build step had issues (may be non-critical)" -ForegroundColor DarkYellow
    }
    Write-Host ""
} else {
    Write-Host "Pipeline 1 of 4: Skipped (using existing dist/)." -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host "Pipeline 2 of 4: Assembling MSIX package..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "package.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Package step failed." -ForegroundColor Red
    exit 1
}
Write-Host ""

if ($Sign) {
    Write-Host "Pipeline 3 of 4: Signing for local testing..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "sign.ps1")
    Write-Host ""
} else {
    Write-Host "Pipeline 3 of 4: Skipped signing (use -Sign for local sideload testing)." -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host "Pipeline 4 of 4: Validating package..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File (Join-Path $ScriptsDir "validate.ps1")
Write-Host ""

$elapsed = (Get-Date) - $startTime
Write-Host "========================================================" -ForegroundColor Green
Write-Host ("  Pipeline complete in " + [math]::Round($elapsed.TotalMinutes, 1) + " minutes.") -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
