<#
.SYNOPSIS
    Step 4 of 4: Validate the MSIX package before Store submission.
#>
$ErrorActionPreference = "Stop"
$ScriptDir    = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot  = (Get-Item (Split-Path -Parent (Split-Path -Parent $ScriptDir))).FullName
$StoreDir    = Join-Path $ProjectRoot "microsoft_store"
$OutputDir   = Join-Path $StoreDir "output"
$MsixPath    = Join-Path $OutputDir "KALKI.msix"
$LogDir      = Join-Path $OutputDir "logs"
$UnpackDir   = Join-Path $OutputDir "_validation_unpack"

$MakeAppx = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "validate_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

$errors   = @()
$warnings = @()
$passed   = @()

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Pass($msg) { $script:passed += $msg; Log ("  PASS: " + $msg) }
function Warn($msg) { $script:warnings += $msg; Log ("  WARN: " + $msg) }
function Fail($msg) { $script:errors += $msg; Log ("  FAIL: " + $msg) }

Log "============================================"
Log "  KALKI Store Build -- Step 4: Validate"
Log "============================================"

Log ""
Log "[Check 1] MSIX package exists..."
if (Test-Path $MsixPath) {
    $size = [math]::Round((Get-Item $MsixPath).Length / 1MB, 2)
    $hash = (Get-FileHash -Path $MsixPath -Algorithm SHA256).Hash
    Pass ("KALKI.msix found (" + $size + " MB)")
    Log ("         SHA-256: " + $hash)
} else {
    Fail "KALKI.msix not found at $MsixPath"
    Log "Run package.ps1 first."
    exit 1
}

Log ""
Log "[Check 2] Unpacking MSIX to verify integrity..."
if (Test-Path $UnpackDir) {
    Remove-Item -Recurse -Force $UnpackDir
}
try {
    & $MakeAppx unpack /p $MsixPath /d $UnpackDir /o 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Pass "MSIX unpacked successfully"
    } else {
        Fail ("makeappx unpack failed (exit code " + $LASTEXITCODE + ")")
    }
} catch {
    Fail ("makeappx unpack threw an exception: " + $_)
}

Log ""
Log "[Check 3] Validating AppxManifest.xml..."
$manifestPath = Join-Path $UnpackDir "AppxManifest.xml"
if (Test-Path $manifestPath) {
    [xml]$manifest = Get-Content $manifestPath
    $identity = $manifest.Package.Identity

    if ($identity.Name -match "PLACEHOLDER") {
        Fail "Identity Name is still a placeholder"
    } else {
        Pass ("Identity Name: " + $identity.Name)
    }

    if ($identity.Publisher -match "PLACEHOLDER") {
        Fail "Identity Publisher is still a placeholder"
    } else {
        Pass ("Identity Publisher: " + $identity.Publisher)
    }

    $pubDisplayName = $manifest.Package.Properties.PublisherDisplayName
    if ($pubDisplayName -match "PLACEHOLDER") {
        Fail "PublisherDisplayName is still a placeholder"
    } else {
        Pass ("PublisherDisplayName: " + $pubDisplayName)
    }

    if ($identity.Version -match "^\d+\.\d+\.\d+\.\d+$") {
        Pass ("Version format valid: " + $identity.Version)
    } else {
        Fail ("Version format invalid: " + $identity.Version + " (must be X.X.X.X)")
    }

    if ($identity.ProcessorArchitecture -eq "x64") {
        Pass "Architecture: x64"
    } else {
        Warn ("Architecture is '" + $identity.ProcessorArchitecture + "' (expected x64)")
    }
} else {
    Fail "AppxManifest.xml not found in package"
}

Log ""
Log "[Check 4] Checking required visual assets..."
$requiredAssets = @(
    "StoreLogo.png",
    "Square44x44Logo.png",
    "Square71x71Logo.png",
    "Square150x150Logo.png",
    "Wide310x150Logo.png",
    "SplashScreen.png"
)

$assetsDir = Join-Path $UnpackDir "Assets"
foreach ($asset in $requiredAssets) {
    $assetPath = Join-Path $assetsDir $asset
    if (Test-Path $assetPath) {
        $sz = (Get-Item $assetPath).Length
        Pass ($asset + " (" + $sz + " bytes)")
    } else {
        Fail ("Missing required asset: " + $asset)
    }
}

Log ""
Log "[Check 5] Checking entry point executable..."
$exePath = Join-Path $UnpackDir "KALKI.exe"
if (Test-Path $exePath) {
    Pass "KALKI.exe found in package root"
} else {
    Fail "KALKI.exe not found in package root"
}

Log ""
Log "[Check 6] Checking store_build.txt marker..."
$markerPath = Join-Path $UnpackDir "store_build.txt"
if (Test-Path $markerPath) {
    Pass "store_build.txt present (auto-updater will be disabled)"
} else {
    Warn "store_build.txt missing -- auto-updater may conflict with Store updates"
}

Log ""
Log "[Check 7] Package size check..."
if ($size -lt 2048) {
    Pass ("Package size (" + $size + " MB) is under 2 GB Store limit")
} else {
    Fail ("Package size (" + $size + " MB) exceeds 2 GB Store limit")
}

if (Test-Path $UnpackDir) {
    Remove-Item -Recurse -Force $UnpackDir -ErrorAction SilentlyContinue
}

Log ""
Log "============================================"
Log "  VALIDATION SUMMARY"
Log "============================================"
Log ("  Passed:   " + $passed.Count)
Log ("  Warnings: " + $warnings.Count)
Log ("  Errors:   " + $errors.Count)
Log ""

if ($errors.Count -gt 0) {
    Log "ERRORS:"
    foreach ($e in $errors) { Log ("  - " + $e) }
    Log ""
    Log "RESULT: FAILED -- Fix errors before Store submission."
    exit 1
} elseif ($warnings.Count -gt 0) {
    Log "WARNINGS:"
    foreach ($w in $warnings) { Log ("  - " + $w) }
    Log ""
    Log "RESULT: PASSED with warnings."
} else {
    Log "RESULT: ALL CHECKS PASSED"
    Log ""
    Log "Your MSIX is ready for Microsoft Store submission!"
    Log ("Upload " + $MsixPath + " to Partner Center.")
}
