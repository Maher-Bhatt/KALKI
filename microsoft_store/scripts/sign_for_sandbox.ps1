$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot = (Get-Item (Split-Path -Parent (Split-Path -Parent $ScriptDir))).FullName
$StoreDir = Join-Path $ProjectRoot "microsoft_store"
$OutputFolder = Join-Path $StoreDir "output"

$SignTool = (Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
if (-not $SignTool) {
    $SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
}

$MsixPath = Join-Path $OutputFolder "KALKI.msix"
$CertPath = Join-Path $OutputFolder "KalkiTestCert.pfx"
$CerPath = Join-Path $OutputFolder "KalkiTestCert.cer"

Write-Host "Generating Self-Signed Certificate for Local Testing..."
$cert = New-SelfSignedCertificate -Type Custom -Subject "CN=5077752A-5182-4523-A5DB-4EBB2626926D" -KeyUsage DigitalSignature -FriendlyName "KALKI Sandbox Test Cert" -CertStoreLocation "Cert:\CurrentUser\My" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

$password = ConvertTo-SecureString -String "testpassword" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $CertPath -Password $password | Out-Null
Export-Certificate -Cert $cert -FilePath $CerPath | Out-Null

Write-Host "Signing KALKI.msix with SignTool..."
& $SignTool sign /fd SHA256 /a /f $CertPath /p "testpassword" $MsixPath

# Generate the WSB config dynamically using the correct absolute host folder path
$wsbTemplatePath = Join-Path $StoreDir "test_kalki_sandbox.wsb"
$wsbContent = @"
<Configuration>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$OutputFolder</HostFolder>
      <SandboxFolder>C:\kalki_test</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -ExecutionPolicy Bypass -WindowStyle Maximized -Command "Write-Host 'Installing KALKI Certificate...'; Import-Certificate -FilePath C:\kalki_test\KalkiTestCert.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople; Write-Host 'Installing KALKI Package (v1.2.1)...'; Add-AppxPackage -Path C:\kalki_test\KALKI.msix; Write-Host 'Installation Complete! Launching KALKI...'; Start-Sleep -Seconds 2; Start-Process shell:AppsFolder\MaherBhatt.Kalki_pwae4j5tndj8e!App"</Command>
  </LogonCommand>
</Configuration>
"@
Set-Content -Path $wsbTemplatePath -Value $wsbContent

Write-Host "Done! The MSIX is now signed for Sandbox testing, and test_kalki_sandbox.wsb has been generated."
