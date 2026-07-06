import os
import subprocess
import sys

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def main():
    # Change to root directory since build_installer.py is in build_tools/
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Installing PyInstaller...")
    run_cmd(f"{sys.executable} -m pip install pyinstaller")

    # Generate Version Info File for Windows executable metadata
    version_info_path = os.path.abspath(os.path.join("build_tools", "file_version_info.txt"))
    with open(version_info_path, "w", encoding="utf-8") as f:
        f.write("""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 18, 0),
    prodvers=(1, 0, 18, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'KALKI Technologies'),
        StringStruct('FileDescription', 'KALKI AI Desktop Assistant'),
        StringStruct('FileVersion', '1.0.18'),
        StringStruct('InternalName', 'kalki_assistant'),
        StringStruct('LegalCopyright', '© 2026 KALKI Technologies. All rights reserved.'),
        StringStruct('OriginalFilename', 'KALKI.exe'),
        StringStruct('ProductName', 'KALKI AI Assistant'),
        StringStruct('ProductVersion', '1.0.18')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)""")

    # The targets
    targets = [
        ("server.py", "KALKI_Server", False),
        ("listener.py", "KALKI_Listener", False),
        ("main_app.py", "KALKI", True),
        ("kalki_setup_wizard.py", "KALKI_Setup_Wizard", True),
        ("setup_google.py", "KALKI_Setup_Google", False),
        ("setup_spotify.py", "KALKI_Setup_Spotify", False)
    ]
    
    for script, name, windowed in targets:
        print(f"\n--- Building {name} ---")
        cmd = [
            f"{sys.executable}", "-m", "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--clean",
            f"--name={name}",
            f"--icon=\"{os.path.abspath('../assets/kalki_icon.ico')}\"",
            f"--version-file=\"{version_info_path}\"",
            "--specpath=build_tools",
        ]
        
        if windowed:
            if script == "main_app.py":
                cmd.append("--collect-all=webview")
            cmd.append("--windowed")
        if script == "kalki_setup_wizard.py":
            cmd.append("--collect-all=customtkinter")
            cmd.append("--collect-all=pystray")
        
        if script == "listener.py":
            cmd.append("--hidden-import=pyaudio")
            cmd.append("--collect-all=speech_recognition")
            
        cmd.append(script)
        run_cmd(" ".join(cmd))
        
    # Copy config.example.py to build dist folders
    import shutil
    for folder in ["KALKI", "KALKI_Setup_Wizard", "KALKI_Server", "KALKI_Listener"]:
        dest = os.path.join("dist", folder, "config.example.py")
        if os.path.exists(os.path.join("dist", folder)):
            shutil.copy("config.example.py", dest)
            print(f"Copied config.example.py to {dest}")
        
    print("\n--- Compiling Inno Setup Installer ---")
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    inno_compiler = None
    for p in inno_paths:
        if os.path.exists(p):
            inno_compiler = p
            break
    if inno_compiler:
        run_cmd(f'"{inno_compiler}" build_tools\\installer.iss')
        print("\nSUCCESS! Installer is in the Output folder.")
    else:
        print(f"\nWARNING: Inno Setup compiler not found.")
        print("Please download and install Inno Setup from https://jrsoftware.org/isinfo.php")
        print("Then run 'ISCC.exe build_tools\\installer.iss' manually.")

if __name__ == "__main__":
    main()
