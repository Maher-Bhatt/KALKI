"""Music, WhatsApp and YouTube download quick commands, moved out of handle_local.

Spotify is used when it's connected. Otherwise music controls go to whatever is playing on
Windows. Replies say what really happened: opening a search page isn't "playing".

Each function returns (handled, reply) or None, because some replies come from an
approval, which already returns that pair.
"""

import re
import urllib.parse
from typing import Any, Callable, Dict, Optional, Tuple

import config

Reply = Optional[Tuple[bool, str]]

_PAUSE = ("pause", "pause music", "pause song", "pause spotify", "pause the music")
_RESUME = ("resume", "resume music", "resume song", "play music", "play the music", "play some music", "play any music",
           "play a song", "play the song", "continue music", "continue the music", "play spotify")
_AGAIN = ("play it again", "play it", "play that again")
_NEXT = ("next", "next song", "next track", "skip", "skip song")
_PREVIOUS = ("previous", "previous song", "previous track", "last song", "go back song")
_NOW = ("what's playing", "what is playing", "current song", "now playing", "what song is this")
_SHUFFLE = ("shuffle", "shuffle on", "turn shuffle on")
_GENERIC = ("music", "song", "songs", "track", "tracks", "playlist", "spotify", "something")
_APPLE = re.compile(r"^(?:open|start|use|launch)\s+apple\s+music$|^play\s+(?:.+\s+)?on\s+apple(?:\s+music)?$|^apple\s+music$")
_CONTACTS = ("list contacts", "list my contacts", "show contacts", "show my contacts", "my contacts")


def _done(sentence: str) -> str:
    title = str(getattr(config, "OWNER_TITLE", "") or "").strip()
    return f"{sentence[:-1]}, {title}." if title and sentence.endswith(".") else sentence


def music_command(t: str, deps: Dict[str, Any]) -> Reply:
    """deps: spotify, media, open_url, set_volume, open_apple_music, and optionally
    music_app() -> "spotify" | "apple_music" | "youtube" (which app plays music) and
    apple_music(query) -> reply (opens Apple Music and starts it, or searches it)."""
    spotify, media, open_url = deps["spotify"], deps["media"], deps["open_url"]
    app = deps.get("music_app", lambda: "spotify" if spotify.is_configured() else "youtube")()
    linked = app == "spotify"
    apple = app == "apple_music" and "apple_music" in deps

    def windows(action: Callable[[], str], failed: str) -> Tuple[bool, str]:
        try:
            return True, _done(action())
        except Exception as exc:
            return True, f"{failed} ({exc})"

    if t in _PAUSE:
        return (True, spotify.pause()) if linked else windows(media.pause, "I couldn't pause the music")
    if _APPLE.match(t):
        deps["open_apple_music"]()
        return True, _done("Opening Apple Music.")
    if t in _RESUME:
        if linked:
            return True, spotify.play()
        playing = (media.now_playing_json() or {}) if hasattr(media, "now_playing_json") else {}
        if playing.get("title") and playing.get("title") not in ("Unknown", "Nothing playing"):
            return windows(media.play, "I couldn't resume the music")
        if apple:
            return True, deps["apple_music"](None)
        open_url("https://music.youtube.com")
        return True, "Nothing was playing, so I opened YouTube Music."
    if t in _AGAIN:
        return (True, spotify.retry()) if linked else windows(media.play, "I couldn't play the music")
    if t in _NEXT:
        return (True, spotify.next_track()) if linked else windows(media.next_track, "I couldn't skip the track")
    if t in _PREVIOUS:
        return (True, spotify.prev_track()) if linked else windows(media.prev_track, "I couldn't go back a track")
    if t in _NOW:
        return (True, spotify.now_playing()) if linked else (True, f"Now playing: {media.now_playing()}.")
    if t in _SHUFFLE:
        return (True, spotify.shuffle_on()) if linked else (True, "Shuffle needs Spotify connected in Settings.")

    m = re.match(r"^(?:spotify|music)\s+volume\s+(\d+)$", t)
    if m:
        level = max(0, min(100, int(m.group(1))))
        if linked:
            return True, spotify.set_volume(level)
        return True, f"Volume set to {level}%." if deps["set_volume"](level) else "I couldn't change the volume."

    m = re.match(r"^play\s+(.+?)(?:\s+on\s+spotify)?$", t)
    if m and "youtube" not in t:
        query = m.group(1).strip()
        plain = re.sub(r"^(?:the|some|a|an|any|my)\s+", "", query).strip()
        if linked:
            if plain in _GENERIC:
                return True, spotify.play()
            if plain.replace("-", "").replace(" ", "") == "lofi":
                return True, spotify.play_lofi()
            return True, spotify.play(query)
        if apple:
            return True, deps["apple_music"](None if plain in _GENERIC else query)
        if plain in _GENERIC or plain.replace("-", "").replace(" ", "") == "lofi":
            open_url("https://music.youtube.com")
            return True, "Opened YouTube Music. Connect Spotify in Settings to play songs directly."
        open_url(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return True, f"Opened a YouTube search for '{query}'. Connect Spotify in Settings to play songs directly."
    return None


def whatsapp_command(t: str, raw: str, whatsapp, queue: Callable[[str, Callable[[], Any]], Any]) -> Reply:
    m = re.match(r"^(?:send\s+(?:a\s+)?(?:whatsapp|message|whats\s*app)\s+to\s+|whatsapp\s+|message\s+)"
                 r"([^,]+?)\s+(?:saying|that|to say)\s+(.+)$", t)
    if m:
        name = m.group(1).strip()
        lowered = m.group(2).strip()
        start = t.find(lowered)
        body = raw[start:start + len(lowered)] if start >= 0 else lowered

        def send():
            result = whatsapp.send_message(name, body)
            if result.get("ok"):
                return True, _done(f"WhatsApp sent to {name}.")
            return True, f"WhatsApp didn't send: {result.get('error')}"
        return queue(f"Send this WhatsApp message to {name}: {body}", send)

    m = re.match(r"^add\s+contact\s+(\S+)\s+(?:phone|number)?\s*(\+?\d[\d\s\-]+)$", t)
    if m:
        name, phone = m.group(1), re.sub(r"[\s\-]", "", m.group(2))
        whatsapp.add_contact(name, phone)
        return True, f"Contact {name} saved."
    if t in _CONTACTS:
        contacts = whatsapp.list_contacts()
        if not contacts:
            return True, "No contacts yet."
        return True, f"{len(contacts)} contacts: " + ", ".join(contacts.keys())
    return None


def youtube_command(t: str, raw: str, ytdl, speak: Callable[[str], Any]) -> Reply:
    m = re.search(r"download\s+(?:this\s+)?(?:youtube\s+)?(?:video|audio|song|track)(?:\s+from)?\s+(\S+)", raw, re.IGNORECASE)
    if not m:
        return None
    audio_only = any(w in t for w in ("audio", "song", "music", "mp3"))
    speak("Downloading. This may take a moment.")
    result = ytdl.download(m.group(1).strip(), audio_only=audio_only)
    if result.get("ok"):
        where = result.get("path") or result.get("file") or "your Downloads folder"
        return True, _done(f"Download complete. Saved to {where}.")
    return True, f"The download didn't work: {result.get('error', 'unknown error')}"
