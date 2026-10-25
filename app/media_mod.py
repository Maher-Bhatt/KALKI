import asyncio
import base64
import json
import threading
import urllib.parse
import urllib.request

_art_cache = {}
_art_lock = threading.Lock()

_winrt_available = False
GlobalSystemMediaTransportControlsSessionManager = None
winrt_streams = None

try:
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    _winrt_available = True
except Exception:
    _winrt_available = False

try:
    import winrt.windows.storage.streams as winrt_streams
except Exception:
    winrt_streams = None

_loop = None
_loop_lock = threading.Lock()


def _get_loop():
    """Return or create a reusable event loop for WinRT async calls."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(_loop)
        except Exception:
            pass
    return _loop


def _run_coro(coro):
    """Run a coroutine on the reusable event loop with proper exception recovery."""
    global _loop
    _init_com()
    with _loop_lock:
        loop = _get_loop()
        try:
            return loop.run_until_complete(coro)
        except Exception:
            # If the loop crashed or became invalid, recreate it
            try:
                if loop and not loop.is_closed():
                    loop.close()
            except Exception:
                pass
            _loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(_loop)
            except Exception:
                pass
            raise


async def _get_manager():
    if not _winrt_available or not GlobalSystemMediaTransportControlsSessionManager:
        return None
    try:
        return await asyncio.wait_for(
            GlobalSystemMediaTransportControlsSessionManager.request_async(),
            timeout=1.0,
        )
    except Exception:
        return None


def _init_com():
    try:
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    except Exception:
        pass


def _press_key(key):
    try:
        import pyautogui
        pyautogui.press(key)
        return True
    except Exception:
        return False


def _clean_source(aumid: str, title: str = "", artist: str = "") -> str:
    if not aumid:
        return ""
    low = aumid.lower()
    t_low = f"{title} {artist}".lower()

    if "spotify" in low:
        return "Spotify"
    if "itunes" in low:
        return "iTunes"
    if "applemusic" in low or "apple music" in low or "apple" in low:
        return "Apple Music"
    if any(k in low for k in ["zunemusic", "wmplayer", "windowsmediaplayer", "media player"]):
        return "Windows Media Player"
    if "tidal" in low:
        return "TIDAL"
    if "deezer" in low:
        return "Deezer"
    if "amazon" in low:
        return "Amazon Music"
    if "vlc" in low:
        return "VLC"
    if "foobar" in low:
        return "foobar2000"

    browsers = ["chrome", "msedge", "edge", "firefox", "brave", "opera", "vivaldi", "arc"]
    if any(b in low for b in browsers):
        if "music.youtube" in low or "youtube music" in t_low:
            return "YouTube Music"
        return "YouTube in browser"

    if "youtube" in low or "youtube" in t_low:
        return "YouTube"

    try:
        part = aumid.split("!")[0].split("\\")[-1].split("/")[-1].split(".exe")[0]
        name = part.split(".")[-1] if "." in part else part
        return name if name and len(name) > 1 else "Media"
    except Exception:
        return "Media"


def _fetch_online_artwork(title: str, artist: str = "") -> str:
    """Look up iTunes Search API for song artwork with high-res replacement and caching."""
    if not title or title.strip().lower() in ("", "unknown", "nothing playing", "no media"):
        return None
    
    t = title.strip()
    a = (artist or "").strip()
    cache_key = f"{t.lower()}::{a.lower()}"
    with _art_lock:
        if cache_key in _art_cache:
            return _art_cache[cache_key]

    query = f"{t} {a}".strip() if a else t
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
    art_b64 = None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KALKI/2.0"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                results = data.get("results") or []
                if results and isinstance(results, list):
                    first = results[0]
                    raw_art = first.get("artworkUrl100") or first.get("artworkUrl60")
                    if raw_art:
                        art_url = raw_art.replace("100x100", "300x300").replace("60x60", "300x300")
                        try:
                            img_req = urllib.request.Request(art_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(img_req, timeout=2.5) as img_resp:
                                if img_resp.status == 200:
                                    img_bytes = img_resp.read()
                                    art_b64 = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('ascii')}"
                        except Exception:
                            art_b64 = art_url
    except Exception:
        art_b64 = None

    with _art_lock:
        _art_cache[cache_key] = art_b64
    return art_b64


async def _read_thumbnail(thumb_obj):
    if not winrt_streams or not thumb_obj:
        return None
    try:
        stream = None
        if hasattr(thumb_obj, "open_read_async"):
            stream = await asyncio.wait_for(thumb_obj.open_read_async(), timeout=1.0)
        elif hasattr(thumb_obj, "size"):
            stream = thumb_obj

        # Increased limit from 50KB to 1024*1024 (1MB) to support crisp modern album art
        if not stream or stream.size == 0 or stream.size > 1024 * 1024:
            return None

        reader = winrt_streams.DataReader(stream)
        loaded = await asyncio.wait_for(reader.load_async(stream.size), timeout=1.0)
        if loaded == 0:
            return None

        buf = bytearray(loaded)
        reader.read_bytes(buf)
        raw = bytes(buf)
        if not raw:
            return None

        if raw.startswith(b"\x89PNG"):
            mime = "image/png"
        elif raw.startswith(b"GIF8"):
            mime = "image/gif"
        elif raw.startswith(b"RIFF") and b"WEBP" in raw[:16]:
            mime = "image/webp"
        else:
            mime = "image/jpeg"

        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


async def _async_get_all_info():
    """Single coroutine to retrieve manager, session, media properties, and thumbnail."""
    manager = await _get_manager()
    if not manager:
        return None, None, None, None
    session = manager.get_current_session()
    if not session:
        return None, None, None, None

    props = None
    try:
        props = await asyncio.wait_for(session.try_get_media_properties_async(), timeout=1.0)
    except Exception:
        props = None

    thumb = None
    if props and getattr(props, "thumbnail", None):
        thumb = await _read_thumbnail(props.thumbnail)
    if not thumb and props and props.title and props.title != "Unknown":
        thumb = _fetch_online_artwork(props.title, getattr(props, "artist", "") or "")

    return manager, session, props, thumb


def now_playing():
    if not _winrt_available:
        return "Nothing playing"
    try:
        _, session, props, _ = _run_coro(_async_get_all_info())
        if not session:
            return "Nothing playing"
        title = props.title if props and props.title else "Unknown"
        artist = props.artist if props and props.artist else "Unknown"
        info = session.get_playback_info()
        status_num = info.playback_status if info else 0
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"
        return f"{title} by {artist} ({status})"
    except Exception:
        return "Nothing playing"


async def _async_action(action_name: str):
    manager = await _get_manager()
    if not manager:
        return False
    session = manager.get_current_session()
    if not session:
        return False
    if action_name == "play":
        await asyncio.wait_for(session.try_play_async(), timeout=1.0)
    elif action_name == "pause":
        await asyncio.wait_for(session.try_pause_async(), timeout=1.0)
    elif action_name == "next":
        await asyncio.wait_for(session.try_skip_next_async(), timeout=1.0)
    elif action_name == "prev":
        await asyncio.wait_for(session.try_skip_previous_async(), timeout=1.0)
    return True


def play():
    if _winrt_available:
        try:
            if _run_coro(_async_action("play")):
                return "Played."
        except Exception:
            pass
    _press_key("playpause")
    return "Played."


def pause():
    if _winrt_available:
        try:
            if _run_coro(_async_action("pause")):
                return "Paused."
        except Exception:
            pass
    _press_key("playpause")
    return "Paused."


def next_track():
    if _winrt_available:
        try:
            if _run_coro(_async_action("next")):
                return "Skipped to next track."
        except Exception:
            pass
    _press_key("nexttrack")
    return "Skipped to next track."


def prev_track():
    if _winrt_available:
        try:
            if _run_coro(_async_action("prev")):
                return "Skipped to previous track."
        except Exception:
            pass
    _press_key("prevtrack")
    return "Skipped to previous track."


def now_playing_json():
    empty_res = {
        "ok": True,
        "status": "NoMedia",
        "title": "Nothing playing",
        "artist": "",
        "thumbnail": None,
        "source": "",
        "position": 0.0,
        "duration": 0.0,
        "reply": "Nothing playing",
    }
    if not _winrt_available:
        return empty_res
    try:
        _, session, props, thumbnail = _run_coro(_async_get_all_info())
        if not session:
            return empty_res

        title = props.title if props and props.title else "Unknown"
        artist = props.artist if props and props.artist else ""

        aumid = getattr(session, "source_app_user_model_id", "") or ""
        source = _clean_source(aumid, title, artist)

        # Fallback to online artwork if WinRT had no thumbnail or failed to read
        if not thumbnail and title and title.strip().lower() not in ("unknown", "nothing playing", "no media"):
            thumbnail = _fetch_online_artwork(title, artist)

        position = 0.0
        duration = 0.0
        try:
            tl = session.get_timeline_properties()
            if tl:
                def _to_sec(val):
                    if val is None:
                        return 0.0
                    if hasattr(val, "total_seconds"):
                        return float(val.total_seconds())
                    if isinstance(val, (int, float)):
                        return float(val)
                    return 0.0

                position = round(_to_sec(getattr(tl, "position", None)), 1)
                duration = round(_to_sec(getattr(tl, "end_time", None)), 1)
                if duration <= 0:
                    duration = round(_to_sec(getattr(tl, "max_seek_time", None)), 1)
        except Exception:
            pass

        info = session.get_playback_info()
        status_num = info.playback_status if info else 0
        status = "Playing" if status_num == 4 else "Paused" if status_num == 5 else "Stopped"

        reply = f"{title} by {artist} ({status})" if artist else f"{title} ({status})"

        return {
            "ok": True,
            "status": status,
            "title": title,
            "artist": artist,
            "thumbnail": thumbnail,
            "source": source,
            "position": position,
            "duration": duration,
            "reply": reply,
        }
    except Exception:
        return empty_res
