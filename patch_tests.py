import os

test_path = "e:/KALKI-main/tests/feature_check.py"
with open(test_path, "r", encoding="utf-8") as f:
    content = f.read()

tests = """
# ---- activity log
c, d = call("POST", "/api/activity/list", {})
check("activity: list returns 200", c == 200, f"{c} {d}")
# It would be empty now, so let's check it doesn't crash.

# ---- approvals
c, d = call("POST", "/api/approvals/list", {})
check("approvals: list returns 200", c == 200, f"{c} {d}")

# ---- briefing
c, d = call("POST", "/api/briefing/get", {})
check("briefing: disabled by default", c == 400, f"{c} {d}", "WARN")

# ---- skills
c, d = call("POST", "/api/skills/list", {})
check("skills: list", c == 200 and "skills" in d, f"{c} {d}")
c, d = call("POST", "/api/skills/toggle", {"id": "calendar", "enabled": False})
check("skills: toggle", c == 200, f"{c} {d}")

# ---- listener state
c, d = call("GET", "/api/status", {})
check("status: includes listenerState", c == 200 and "listenerState" in d, f"{c} {d}")
"""

# Append just before "hard = [r for r in res if not r[1] and r[3] == "HARD"]"
marker = 'hard = [r for r in res if not r[1] and r[3] == "HARD"]'
content = content.replace(marker, tests + "\n" + marker)

with open(test_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated feature_check.py")
