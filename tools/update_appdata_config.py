import os
import re

path = os.path.expandvars(r"%APPDATA%\KALKI\config.py")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    c = re.sub(r'TTS_VOICE\s*=\s*["\'].*?["\']', 'TTS_VOICE = "en-US-AndrewMultilingualNeural"', c)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated APPDATA/KALKI/config.py: TTS_VOICE = en-US-AndrewMultilingualNeural")
else:
    print("APPDATA/KALKI/config.py does not exist")
