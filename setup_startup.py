import os
import sys

startup_dir = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
os.makedirs(startup_dir, exist_ok=True)
vbs_path = os.path.join(startup_dir, 'KalkiStartup.vbs')

vbs_content = '''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "c:\\Jarvis\\START.bat" & Chr(34), 0
Set WshShell = Nothing
'''
with open(vbs_path, 'w', encoding='utf-8') as f:
    f.write(vbs_content)
print(f"Startup script created at {vbs_path}")
