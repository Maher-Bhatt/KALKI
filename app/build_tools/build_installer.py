import os

import subprocess
import sys
from pathlib import Path

try:
    from version import APP_VERSION
except ImportError:
    APP_VERSION = "1.3.5"


VERSION_PARTS = tuple(int(part) for part in APP_VERSION.split(".")) + (0,)

def run_cmd(cmd):
    """Run a build command without breaking paths that contain spaces."""
    print("Running:", " ".join(f'"{part}"' if " " in str(part) else str(part) for part in cmd))
    env = os.environ.copy()

    # ``pip install --target`` does not process pywin32.pth automatically.
    # Without these paths, PyInstaller cannot import pythoncom/pywintypes and
    # aborts while packaging server.py. A normal site-packages installation is
    # unaffected because Python has already processed its .pth file.
    pywin32_roots = [
        path for path in sys.path
        if os.path.isfile(os.path.join(path, "pywin32.pth"))
    ]
    if pywin32_roots:
        extra_paths = []
        for root in pywin32_roots:
            extra_paths.extend([
                root,
                os.path.join(root, "win32"),
                os.path.join(root, "win32", "lib"),
                os.path.join(root, "pywin32_system32"),
            ])
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(extra_paths + ([existing] if existing else []))

    subprocess.run(cmd, check=True, env=env)


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller is already available.")
    except ImportError:
        print("Installing PyInstaller...")
        run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"])

def main():
    # Change to root directory since build_installer.py is in build_tools/
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    ensure_pyinstaller()

    # Generate Version Info File for Windows executable metadata
    version_info_path = os.path.abspath(os.path.join("build_tools", "file_version_info.txt"))
    with open(version_info_path, "w", encoding="utf-8") as f:
        f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_PARTS},
    prodvers={VERSION_PARTS},
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
        StringStruct('FileVersion', '{APP_VERSION}'),
        StringStruct('InternalName', 'kalki_assistant'),
        StringStruct('LegalCopyright', '© 2026 KALKI Technologies. All rights reserved.'),
        StringStruct('OriginalFilename', 'KALKI.exe'),
        StringStruct('ProductName', 'KALKI AI Assistant'),
        StringStruct('ProductVersion', '{APP_VERSION}')])
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
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--clean",
            f"--name={name}",
            f"--icon={os.path.abspath('../assets/kalki_icon.ico')}",
            f"--version-file={version_info_path}",
            "--specpath=build_tools",
            # User settings and API keys must never be frozen into a release.
            # runtime_paths.py provisions config.py from the packaged example
            # (or the user's writable AppData directory) on first launch.
            "--exclude-module=config",
        ]
        
        if windowed:
            if script == "main_app.py":
                cmd.append("--collect-all=webview")
            cmd.append("--windowed")
        if script == "kalki_setup_wizard.py":
            cmd.append("--collect-all=customtkinter")
            cmd.append("--collect-all=pystray")
        
        if script == "server.py":
            cmd.append("--hidden-import=pytesseract")
            cmd.append("--hidden-import=spotipy")
            
        if script == "listener.py":
            cmd.append("--hidden-import=pyaudio")
            cmd.append("--collect-all=speech_recognition")
            
        cmd.append(script)
        run_cmd(cmd)
        
    # Copy config.example.py to build dist folders
    import shutil
    for folder in [
        "KALKI", "KALKI_Setup_Wizard", "KALKI_Server", "KALKI_Listener",
        "KALKI_Setup_Google", "KALKI_Setup_Spotify",
    ]:
        dest = os.path.join("dist", folder, "config.example.py")
        if os.path.exists(os.path.join("dist", folder)):
            shutil.copy("config.example.py", dest)
            print(f"Copied config.example.py to {dest}")
        
    print("\n--- Compiling Inno Setup Installer ---")
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Antigravity IDE", "resources", "app", "node_modules", "innosetup", "bin", "ISCC.exe"),
    ]
    inno_compiler = None
    for p in inno_paths:
        if os.path.exists(p):
            inno_compiler = p
            break
    if inno_compiler:
        run_cmd([inno_compiler, "build_tools\\installer.iss"])
        print("\nSUCCESS! Installer is in the Output folder.")
    else:
        # The GitHub release path remains usable without Inno Setup: the
        # onedir bundles under dist/ are still valid portable artifacts.
        print("\nWARNING: Inno Setup compiler not found; portable bundles remain in dist/.")
        print("Install Inno Setup 6 to generate the optional single-file installer.")

if __name__ == "__main__":
    main()
