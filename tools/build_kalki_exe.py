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
    "--name=KALKI",
    f"--icon={icon_path}",
    f"--version-file={version_info_path}",
    "--specpath=build_tools",
    "--exclude-module=config",
    "--collect-all=webview",
    "--windowed",
    "main_app.py"
]

print("Rebuilding KALKI main executable...")
subprocess.run(cmd, check=True)
dest = os.path.join("dist", "KALKI", "config.example.py")
if os.path.exists("config.example.py"):
    shutil.copy("config.example.py", dest)
print("KALKI main executable rebuild complete!")
