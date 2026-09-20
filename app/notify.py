import os

def notify_desktop(title: str, message: str):
    """
    Shows a native desktop notification using plyer, if available.
    Degrades silently if unsupported.
    """
    try:
        from plyer import notification
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "kalki_icon.ico"))
        notification.notify(
            title=title,
            message=message,
            app_name="KALKI",
            app_icon=icon_path if os.path.exists(icon_path) else None,
            timeout=5
        )
    except Exception:
        pass
