import asyncio
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

async def _get_manager():
    return await GlobalSystemMediaTransportControlsSessionManager.request_async()

def now_playing():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if not session:
            return "Nothing playing"
            
        async def _get_info(s):
            return await s.try_get_media_properties_async()
            
        props = asyncio.run(_get_info(session))
        title = props.title if props.title else "Unknown"
        artist = props.artist if props.artist else "Unknown"
        
        info = session.get_playback_info()
        status_num = info.playback_status
        # 0: Closed, 1: Opened, 2: Changing, 3: Stopped, 4: Playing, 5: Paused
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"
        
        app = session.source_app_user_model_id or "Unknown App"
        
        return f"{title} by {artist} ({status})"
    except Exception as e:
        return f"Error: {e}"

def play():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if session:
            asyncio.run(session.try_play_async())
            return "Played."
        return "No active media session."
    except Exception as e:
        return f"Error: {e}"

def pause():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if session:
            asyncio.run(session.try_pause_async())
            return "Paused."
        return "No active media session."
    except Exception as e:
        return f"Error: {e}"

def next_track():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if session:
            asyncio.run(session.try_skip_next_async())
            return "Skipped to next track."
        return "No active media session."
    except Exception as e:
        return f"Error: {e}"

def prev_track():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if session:
            asyncio.run(session.try_skip_previous_async())
            return "Skipped to previous track."
        return "No active media session."
    except Exception as e:
        return f"Error: {e}"

def now_playing_json():
    try:
        manager = asyncio.run(_get_manager())
        session = manager.get_current_session()
        if not session:
            return {"status": "NoMedia", "title": "Nothing playing", "artist": ""}
            
        async def _get_info(s):
            return await s.try_get_media_properties_async()
            
        props = asyncio.run(_get_info(session))
        title = props.title if props.title else "Unknown"
        artist = props.artist if props.artist else ""
        
        info = session.get_playback_info()
        status_num = info.playback_status
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"
        
        return {"status": status, "title": title, "artist": artist}
    except Exception as e:
        return {"status": "Error", "title": "Error", "artist": str(e)}
