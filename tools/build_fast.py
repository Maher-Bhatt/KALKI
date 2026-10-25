import os, sys, subprocess, shutil

app_dir = os.path.abspath("app")
os.chdir(app_dir)

version_info_path = os.path.abspath(os.path.join("build_tools", "file_version_info.txt"))
icon_path = os.path.abspath(os.path.join("..", "assets", "kalki_icon.ico"))

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--clean",
    "--name=KALKI_Server",
    f"--icon={icon_path}",
    f"--version-file={version_info_path}",
    "--specpath=build_tools",
    "--exclude-module=config",
    "--hidden-import=pytesseract",
    "--hidden-import=spotipy",
    "--hidden-import=plyer",
    "--hidden-import=media_mod",
    "--hidden-import=antivirus",
    "server.py"
]

print("Rebuilding KALKI_Server...")
subprocess.run(cmd, check=True)
dest = os.path.join("dist", "KALKI_Server", "config.example.py")
if os.path.exists("config.example.py"):
    shutil.copy("config.example.py", dest)
print("KALKI_Server rebuild complete!")
