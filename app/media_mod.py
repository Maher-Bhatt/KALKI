import asyncio

_winrt_available = False
GlobalSystemMediaTransportControlsSessionManager = None

try:
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    _winrt_available = True
except Exception:
    _winrt_available = False

async def _get_manager():
    if not _winrt_available or not GlobalSystemMediaTransportControlsSessionManager:
        return None
    try:
        return await GlobalSystemMediaTransportControlsSessionManager.request_async()
    except Exception:
        return None

def _press_key(key):
    try:
        import pyautogui
        pyautogui.press(key)
        return True
    except Exception:
        return False

def now_playing():
    if not _winrt_available:
        return "Nothing playing"
    try:
        manager = asyncio.run(_get_manager())
        if not manager:
            return "Nothing playing"
        session = manager.get_current_session()
        if not session:
            return "Nothing playing"
            
        async def _get_info(s):
            return await s.try_get_media_properties_async()
            
        props = asyncio.run(_get_info(session))
        title = props.title if props and props.title else "Unknown"
        artist = props.artist if props and props.artist else "Unknown"
        
        info = session.get_playback_info()
        status_num = info.playback_status if info else 0
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"
        
        return f"{title} by {artist} ({status})"
    except Exception as e:
        return "Nothing playing"

def play():
    if _winrt_available:
        try:
            manager = asyncio.run(_get_manager())
            if manager:
                session = manager.get_current_session()
                if session:
                    asyncio.run(session.try_play_async())
                    return "Played."
        except Exception:
            pass
    _press_key('playpause')
    return "Played."

def pause():
    if _winrt_available:
        try:
            manager = asyncio.run(_get_manager())
            if manager:
                session = manager.get_current_session()
                if session:
                    asyncio.run(session.try_pause_async())
                    return "Paused."
        except Exception:
            pass
    _press_key('playpause')
    return "Paused."

def next_track():
    if _winrt_available:
        try:
            manager = asyncio.run(_get_manager())
            if manager:
                session = manager.get_current_session()
                if session:
                    asyncio.run(session.try_skip_next_async())
                    return "Skipped to next track."
        except Exception:
            pass
    _press_key('nexttrack')
    return "Skipped to next track."

def prev_track():
    if _winrt_available:
        try:
            manager = asyncio.run(_get_manager())
            if manager:
                session = manager.get_current_session()
                if session:
                    asyncio.run(session.try_skip_previous_async())
                    return "Skipped to previous track."
        except Exception:
            pass
    _press_key('prevtrack')
    return "Skipped to previous track."

def now_playing_json():
    if not _winrt_available:
        return {"status": "NoMedia", "title": "Nothing playing", "artist": ""}
    try:
        manager = asyncio.run(_get_manager())
        if not manager:
            return {"status": "NoMedia", "title": "Nothing playing", "artist": ""}
        session = manager.get_current_session()
        if not session:
            return {"status": "NoMedia", "title": "Nothing playing", "artist": ""}
            
        async def _get_info(s):
            return await s.try_get_media_properties_async()
            
        props = asyncio.run(_get_info(session))
        title = props.title if props and props.title else "Unknown"
        artist = props.artist if props and props.artist else ""
        
        info = session.get_playback_info()
        status_num = info.playback_status if info else 0
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"
        
        return {"status": status, "title": title, "artist": artist}
    except Exception as e:
        return {"status": "NoMedia", "title": "Nothing playing", "artist": ""}
