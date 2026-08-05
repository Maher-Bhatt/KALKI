import re

with open(r'E:\PROJECT\KALKI-main\app\server.py', 'r', encoding='utf-8') as f:
    code = f.read()

replacement = """  INTELLIGENCE:
  - If a user asks you to scan or search something vaguely (e.g. "search this", "scan screen") WITHOUT specifying a target or site, STOP and ASK the user which specific site or topic they want to search before proceeding.
  - Use the conversation history above — resolve follow-ups and pronouns from"""

code = code.replace("""  INTELLIGENCE:
  - Use the conversation history above — resolve follow-ups and pronouns from""", replacement)

with open(r'E:\PROJECT\KALKI-main\app\server.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("server.py patched for search intelligence")
