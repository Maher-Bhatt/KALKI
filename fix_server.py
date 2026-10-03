import os

server_path = "e:/KALKI-main/app/server.py"
with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\\\\n        if path == \\"/api/recovery/clear\\":", "\\n        if path == \\"/api/recovery/clear\\":")

with open(server_path, "w", encoding="utf-8") as f:
    f.write(content)
