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
            f"--icon=assets/kalki_icon.ico",
            "--specpath=build_tools",
        ]
        
        if windowed:
            if script == "main_app.py":
                cmd.append("--collect-all=webview")
            cmd.append("--windowed")
        if script == "kalki_setup_wizard.py":
            cmd.append("--collect-all=customtkinter")
            cmd.append("--collect-all=pystray")
            
        cmd.append(script)
        run_cmd(" ".join(cmd))
        
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
