$ErrorActionPreference = "Stop"
$MakeAppxDir = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"
$SignTool = Join-Path $MakeAppxDir "signtool.exe"
$OutputFolder = "C:\Users\maher\Music\KALKI application\microsoft_store\output"
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

Write-Host "Done! The MSIX is now signed for Sandbox testing."
