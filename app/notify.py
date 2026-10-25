import os
import sys

def notify_desktop(title: str, message: str):
    """
    Shows a native desktop notification using plyer, if available.
    Degrades silently if unsupported.
    """
    try:
        from plyer import notification
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(sys.executable), "assets", "kalki_icon.ico")),
            os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "assets", "kalki_icon.ico")),
        ]
        icon_path = next((p for p in candidates if os.path.exists(p)), None)
        notification.notify(
            title=title,
            message=message,
            app_name="KALKI",
            app_icon=icon_path,
            timeout=5
        )
    except Exception:
        pass
