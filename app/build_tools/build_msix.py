import os
import shutil
import subprocess
import glob
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Configuration
APP_NAME = "KALKI"
APP_VERSION = "1.2.6.0" # Must be X.X.X.X
PUBLISHER_NAME = "CN=KALKI_Developer"
PUBLISHER_DISPLAY_NAME = "KALKI Developer"
APP_DESCRIPTION = "Advanced AI Assistant"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dist", "KALKI")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "Output")
MSIX_STAGING = os.path.join(BASE_DIR, "build", "msix_staging")
ASSETS_SRC_ICON = os.path.join(os.path.dirname(BASE_DIR), "assets", "kalki_logo.png")

# Certificate Info
CERT_NAME = "KALKI_Dev_Cert.pfx"
CERT_PASS = "kalkipass"

def find_sdk_tool(tool_name):
    # Find Windows 10 SDK path
    base_path = r"C:\Program Files (x86)\Windows Kits\10\bin"
    if not os.path.exists(base_path):
        return None
    # Find newest version
    versions = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    if not versions:
        return None
    versions.sort(reverse=True)
    
    # Prefer x64
    for v in versions:
        arch_path = os.path.join(base_path, v, "x64", tool_name)
        if os.path.exists(arch_path):
            return arch_path
            
    # Fallback to arm64 or x86
    for v in versions:
        for arch in ["arm64", "x86"]:
            arch_path = os.path.join(base_path, v, arch, tool_name)
            if os.path.exists(arch_path):
                return arch_path
    return None

def build_manifest():
    print("Generating AppxManifest.xml...")
    
    Package = Element("Package", {
        "xmlns": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        "xmlns:uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
        "xmlns:rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
    })
    
    Identity = SubElement(Package, "Identity", {
        "Name": APP_NAME,
        "ProcessorArchitecture": "x64",
        "Publisher": PUBLISHER_NAME,
        "Version": APP_VERSION
    })
    
    Properties = SubElement(Package, "Properties")
    SubElement(Properties, "DisplayName").text = APP_NAME
    SubElement(Properties, "PublisherDisplayName").text = PUBLISHER_DISPLAY_NAME
    SubElement(Properties, "Description").text = APP_DESCRIPTION
    SubElement(Properties, "Logo").text = r"Assets\StoreLogo.png"
    
    Resources = SubElement(Package, "Resources")
    SubElement(Resources, "Resource", {"Language": "en-us"})
    
    Dependencies = SubElement(Package, "Dependencies")
    SubElement(Dependencies, "TargetDeviceFamily", {
        "Name": "Windows.Desktop",
        "MinVersion": "10.0.17763.0",
        "MaxVersionTested": "10.0.22000.0"
    })
    
    Capabilities = SubElement(Package, "Capabilities")
    SubElement(Capabilities, "rescap:Capability", {"Name": "runFullTrust"})
    SubElement(Capabilities, "Capability", {"Name": "internetClient"})
    SubElement(Capabilities, "Capability", {"Name": "privateNetworkClientServer"})
    
    Applications = SubElement(Package, "Applications")
    Application = SubElement(Applications, "Application", {
        "Id": APP_NAME,
        "Executable": f"{APP_NAME}.exe",
        "EntryPoint": "Windows.FullTrustApplication"
    })
    
    VisualElements = SubElement(Application, "uap:VisualElements", {
        "DisplayName": APP_NAME,
        "Description": APP_DESCRIPTION,
        "BackgroundColor": "transparent",
        "Square150x150Logo": r"Assets\Square150x150Logo.png",
        "Square44x44Logo": r"Assets\Square44x44Logo.png"
    })
    SubElement(VisualElements, "uap:DefaultTile", {"Wide310x150Logo": r"Assets\Wide310x150Logo.png"})
    SubElement(VisualElements, "uap:SplashScreen", {"Image": r"Assets\SplashScreen.png"})
    
    xml_str = minidom.parseString(tostring(Package)).toprettyxml(indent="  ")
    with open(os.path.join(MSIX_STAGING, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(xml_str)

def create_assets():
    print("Creating Assets...")
    assets_dir = os.path.join(MSIX_STAGING, "Assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    try:
        from PIL import Image
        img = Image.open(ASSETS_SRC_ICON)
        img.resize((150, 150)).save(os.path.join(assets_dir, "Square150x150Logo.png"))
        img.resize((44, 44)).save(os.path.join(assets_dir, "Square44x44Logo.png"))
        img.resize((50, 50)).save(os.path.join(assets_dir, "StoreLogo.png"))
        img.resize((620, 300)).save(os.path.join(assets_dir, "SplashScreen.png"))
        img.resize((310, 150)).save(os.path.join(assets_dir, "Wide310x150Logo.png"))
    except ImportError:
        print("Pillow not installed, using raw copies (may cause store rejection).")
        shutil.copy(ASSETS_SRC_ICON, os.path.join(assets_dir, "Square150x150Logo.png"))
        shutil.copy(ASSETS_SRC_ICON, os.path.join(assets_dir, "Square44x44Logo.png"))
        shutil.copy(ASSETS_SRC_ICON, os.path.join(assets_dir, "StoreLogo.png"))
        shutil.copy(ASSETS_SRC_ICON, os.path.join(assets_dir, "SplashScreen.png"))
        shutil.copy(ASSETS_SRC_ICON, os.path.join(assets_dir, "Wide310x150Logo.png"))

def build_msix():
    makeappx = find_sdk_tool("makeappx.exe")
    signtool = find_sdk_tool("signtool.exe")
    
    if not makeappx or not signtool:
        print("Error: Windows 10 SDK (makeappx.exe, signtool.exe) not found!")
        print("Please install Windows 10 SDK.")
        return False
        
    print(f"Found makeappx: {makeappx}")
    print(f"Found signtool: {signtool}")

    print("Cleaning staging directory...")
    if os.path.exists(MSIX_STAGING):
        shutil.rmtree(MSIX_STAGING)
    os.makedirs(MSIX_STAGING)
    
    print("Copying compiled binaries...")
    if not os.path.exists(DIST_DIR):
        print(f"Error: {DIST_DIR} not found. Please run PyInstaller first.")
        return False
        
    for item in os.listdir(DIST_DIR):
        s = os.path.join(DIST_DIR, item)
        d = os.path.join(MSIX_STAGING, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
            
    build_manifest()
    create_assets()
    
    print("Packing MSIX...")
    msix_out = os.path.join(OUTPUT_DIR, f"{APP_NAME}_v1.2.6.msix")
    if os.path.exists(msix_out):
        os.remove(msix_out)
        
    subprocess.run([makeappx, "pack", "/d", MSIX_STAGING, "/p", msix_out, "/o"], check=True)
    
    cert_path = os.path.join(BASE_DIR, "build_tools", CERT_NAME)
    if not os.path.exists(cert_path):
        print("Generating self-signed certificate for local testing...")
        ps_cmd = f'''
        $cert = New-SelfSignedCertificate -Type Custom -Subject "{PUBLISHER_NAME}" -KeyUsage DigitalSignature -FriendlyName "KALKI Dev Cert" -CertStoreLocation "Cert:\\CurrentUser\\My" -TextExtension @("2.5.29.37={{text}}1.3.6.1.5.5.7.3.3", "2.5.29.19={{text}}")
        $pwd = ConvertTo-SecureString -String "{CERT_PASS}" -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath "{cert_path}" -Password $pwd
        '''
        subprocess.run(["powershell", "-Command", ps_cmd], check=True)
        
    print("Signing MSIX...")
    subprocess.run([signtool, "sign", "/fd", "SHA256", "/a", "/f", cert_path, "/p", CERT_PASS, msix_out], check=True)
    
    print(f"\\nSUCCESS! MSIX generated at: {msix_out}")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    build_msix()
