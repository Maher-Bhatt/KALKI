<#
.SYNOPSIS
    Step 3 of 4 (Optional): Sign the MSIX for local sideload testing.

.DESCRIPTION
    Creates a self-signed development certificate and signs the MSIX package.
    This is ONLY needed for local testing/sideloading.
    The Microsoft Store will re-sign the package with its own certificate upon submission.

.NOTES
    Run from project root (elevated PowerShell):
    powershell -ExecutionPolicy Bypass -File microsoft_store\scripts\sign.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Item (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))).FullName
$StoreDir    = Join-Path $ProjectRoot "microsoft_store"
$OutputDir   = Join-Path $StoreDir "output"
$MsixPath    = Join-Path $OutputDir "KALKI.msix"
$CertDir     = Join-Path $StoreDir "packaging"
$PfxPath     = Join-Path $CertDir "KALKI_Dev.pfx"
$LogDir      = Join-Path $OutputDir "logs"

# SignTool from Windows SDK
$SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "sign_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "============================================"
Log "  KALKI Store Build — Step 3: Sign (Dev)"
Log "============================================"

if (-not (Test-Path $MsixPath)) {
    Log "ERROR: KALKI.msix not found. Run package.ps1 first."
    exit 1
}

if (-not (Test-Path $SignTool)) {
    Log "ERROR: signtool.exe not found. Install Windows 10/11 SDK."
    exit 1
}

# Read the Publisher from AppxManifest.xml
[xml]$manifest = Get-Content (Join-Path $StoreDir "AppxManifest.xml")
$publisher = $manifest.Package.Identity.Publisher

if ($publisher -match "PLACEHOLDER") {
    Log "WARNING: Publisher is still a placeholder. Using dev publisher for local testing."
    $publisher = "CN=KALKI-Dev"
}

# Create self-signed certificate if it doesn't exist
if (-not (Test-Path $PfxPath)) {
    Log "Creating self-signed dev certificate..."
    Log "  Subject: $publisher"

    $cert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $publisher `
        -KeyUsage DigitalSignature `
        -FriendlyName "KALKI Dev Signing Certificate" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

    $password = ConvertTo-SecureString -String "kalki_dev_2026" -Force -AsPlainText
    Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" -FilePath $PfxPath -Password $password | Out-Null

    Log "Certificate exported to: $PfxPath"
    Log "Password: kalki_dev_2026"

    # Also install the cert to Trusted People for sideloading
    Log "Installing certificate to Trusted People store..."
    Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" -Password $password | Out-Null
} else {
    Log "Using existing dev certificate: $PfxPath"
}

# Sign the MSIX
Log "Signing MSIX package..."
$password = ConvertTo-SecureString -String "kalki_dev_2026" -Force -AsPlainText

& $SignTool sign /fd SHA256 /a /f $PfxPath /p "kalki_dev_2026" $MsixPath 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -eq 0) {
    Log ""
    Log "============================================"
    Log "  SUCCESS! MSIX signed for local testing."
    Log "============================================"
    Log ""
    Log "To sideload on this machine:"
    Log "  1. Enable Developer Mode in Windows Settings"
    Log "  2. Double-click: $MsixPath"
    Log "  3. Click 'Install'"
    Log ""
    Log "NOTE: For Microsoft Store submission, do NOT sign the package."
    Log "      The Store will sign it with its own certificate."
} else {
    Log "ERROR: signtool.exe failed with exit code $LASTEXITCODE"
    exit 1
}
