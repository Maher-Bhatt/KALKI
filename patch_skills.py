import os

server_path = "e:/KALKI-main/app/server.py"
with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace toggle endpoint to actually save to config
toggle_old = """        if path == "/api/skills/toggle":
            skill_id = body.get("id")
            enabled = bool(body.get("enabled"))
            # In a real app we'd save this to config
            self._json({"ok": True})
            return"""

toggle_new = """        if path == "/api/skills/toggle":
            skill_id = body.get("id")
            enabled = bool(body.get("enabled"))
            setattr(config, f"SKILL_{skill_id.upper()}_ENABLED", enabled)
            self._json({"ok": True})
            return"""

content = content.replace(toggle_old, toggle_new)

# Add check in tool executor
tool_exec_old = """    try:
        if tool_name == "search_web":"""
        
tool_exec_new = """    try:
        skill_map = {
            "search_web": "search",
            "get_calendar_events": "calendar",
            "create_calendar_event": "calendar",
            "delete_calendar_event": "calendar",
            "play_music": "spotify",
            "github": "github"
        }
        mapped = skill_map.get(tool_name)
        if mapped and not getattr(config, f"SKILL_{mapped.upper()}_ENABLED", True):
            return f"Error: The {mapped} skill is currently disabled. Ask the user to enable it."
            
        if tool_name == "search_web":"""

content = content.replace(tool_exec_old, tool_exec_new)

with open(server_path, "w", encoding="utf-8") as f:
    f.write(content)
