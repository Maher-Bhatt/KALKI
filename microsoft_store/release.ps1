<##
.SYNOPSIS
    Build the KALKI 1.3.4 GitHub and Microsoft Store release artifacts.
.DESCRIPTION
    Runs the reproducible PyInstaller build, creates a portable GitHub ZIP,
    assembles and validates an MSIX, optionally signs it for local sideloading,
    and writes SHA-256 checksums. Microsoft Store production signing is not
    performed by this script.
#>

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipBuild,
    [switch]$SignDevelopment,
    [string]$PythonExe = $env:KALKI_PYTHON
)

$ErrorActionPreference = 'Stop'
$StoreDir = $PSScriptRoot
$ProjectRoot = (Get-Item (Join-Path $StoreDir '..')).FullName
$AppDir = Join-Path $ProjectRoot 'app'
$OutputDir = Join-Path $StoreDir 'output'
$ReleaseDir = Join-Path $OutputDir 'release-v1.3.4'
$GitHubStage = Join-Path $OutputDir 'KALKI_v1.3.4_GitHub'
$GitHubZip = Join-Path $ReleaseDir 'KALKI_v1.3.4_GitHub.zip'
$MsixSource = Join-Path $OutputDir 'KALKI.msix'
$MsixRelease = Join-Path $ReleaseDir 'KALKI_v1.3.4.msix'
$Checksums = Join-Path $ReleaseDir 'SHA256SUMS.txt'

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
if (Test-Path $GitHubStage) { Remove-Item -Recurse -Force $GitHubStage }
New-Item -ItemType Directory -Path $GitHubStage -Force | Out-Null

if (-not $PythonExe) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $PythonExe = $pythonCommand.Source }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    throw "Python was not found. Set KALKI_PYTHON or pass -PythonExe."
}

Write-Host '=== KALKI 1.3.4 Release Pipeline ===' -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Python:  $PythonExe"

if (-not $SkipBuild) {
    $buildArgs = @('-ExecutionPolicy', 'Bypass', '-File', (Join-Path $StoreDir 'scripts\build.ps1'))
    if ($Clean) { $buildArgs += '-Clean' }
    if ($PythonExe) { $buildArgs += @('-PythonExe', $PythonExe) }
    & powershell @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "EXE build failed with exit code $LASTEXITCODE" }
} else {
    Write-Host 'Skipping EXE rebuild; using existing app/dist outputs.' -ForegroundColor DarkYellow
}

$distDir = Join-Path $AppDir 'dist'
$copyMap = [ordered]@{
    'KALKI' = ''
    'KALKI_Setup_Wizard' = 'services\setup_wizard'
    'KALKI_Server' = 'services\server'
    'KALKI_Listener' = 'services\listener'
    'KALKI_Setup_Google' = 'services\setup_google'
    'KALKI_Setup_Spotify' = 'services\setup_spotify'
}
foreach ($name in $copyMap.Keys) {
    $src = Join-Path $distDir $name
    if (-not (Test-Path $src)) { throw "Missing build output: $src" }
    $dest = if ($copyMap[$name]) { Join-Path $GitHubStage $copyMap[$name] } else { $GitHubStage }
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    Copy-Item -Path (Join-Path $src '*') -Destination $dest -Recurse -Force
}

$githubAssets = Join-Path $GitHubStage 'assets'
New-Item -ItemType Directory -Path $githubAssets -Force | Out-Null
$assetSource = Join-Path $ProjectRoot 'assets'
if (Test-Path $assetSource) { Copy-Item (Join-Path $assetSource '*') $githubAssets -Recurse -Force }
$appAssetSource = Join-Path $AppDir 'assets'
if (Test-Path $appAssetSource) { Copy-Item (Join-Path $appAssetSource '*') $githubAssets -Recurse -Force }
foreach ($name in @('index.html','manifest.json','service-worker.js','config.example.py')) {
    $src = Join-Path $AppDir $name
    if (Test-Path $src) { Copy-Item $src $GitHubStage -Force }
}
foreach ($name in @('README.md','LICENSE','TERMS.md','CHANGES.md')) {
    $src = Join-Path $ProjectRoot $name
    if (Test-Path $src) { Copy-Item $src $GitHubStage -Force }
}

$portableReadme = @"
KALKI v1.3.4 — portable Windows package

Run KALKI.exe. Runtime data and API credentials are stored in %APPDATA%\KALKI.
The local API requires its per-installation token; do not expose it or forward
port 8888. Generated host code execution is disabled by default.
"@
Set-Content -Path (Join-Path $GitHubStage 'PORTABLE_README.txt') -Value $portableReadme -Encoding UTF8
if (Test-Path $GitHubZip) { Remove-Item $GitHubZip -Force }
Compress-Archive -Path (Join-Path $GitHubStage '*') -DestinationPath $GitHubZip -CompressionLevel Optimal

& powershell -ExecutionPolicy Bypass -File (Join-Path $StoreDir 'scripts\package.ps1')
if ($LASTEXITCODE -ne 0) { throw "MSIX packaging failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $MsixSource)) { throw "MSIX was not created: $MsixSource" }

if ($SignDevelopment) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $StoreDir 'scripts\sign.ps1') -MsixPath $MsixSource
    if ($LASTEXITCODE -ne 0) { throw "Development signing failed with exit code $LASTEXITCODE" }
}
Copy-Item $MsixSource $MsixRelease -Force

& powershell -ExecutionPolicy Bypass -File (Join-Path $StoreDir 'scripts\validate.ps1')
if ($LASTEXITCODE -ne 0) { throw "MSIX validation failed with exit code $LASTEXITCODE" }

$artifacts = @($GitHubZip, $MsixRelease)
$lines = foreach ($artifact in $artifacts) {
    $hash = (Get-FileHash -Algorithm SHA256 -Path $artifact).Hash
    "{0}  {1}" -f $hash.ToLowerInvariant(), (Split-Path $artifact -Leaf)
}
Set-Content -Path $Checksums -Value $lines -Encoding ASCII

Write-Host ''
Write-Host 'Release artifacts:' -ForegroundColor Green
$artifacts | ForEach-Object { Write-Host "  $_" }
Write-Host "Checksums: $Checksums" -ForegroundColor Green
