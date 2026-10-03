"""Fails if release version strings drift apart (version.py is the source of truth)."""
import re, sys, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
ver = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', (R/"app/version.py").read_text()).group(1)
checks = {
 "AppxManifest.xml": (R/"microsoft_store/AppxManifest.xml", rf'Version="{re.escape(ver)}\.0"'),
 "installer.iss": (R/"app/build_tools/installer.iss", rf'MyAppVersion "{re.escape(ver)}"'),
 "file_version_info.txt": (R/"app/build_tools/file_version_info.txt", rf"'FileVersion', '{re.escape(ver)}'"),
}
bad = [n for n,(p,rx) in checks.items() if not re.search(rx, p.read_text(encoding="utf-8"))]
print(f"version.py = {ver}")
if bad: print("MISMATCH:", ", ".join(bad)); sys.exit(1)
print("all release files match")
