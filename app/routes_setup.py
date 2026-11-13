"""First-run and connection setup routes, moved out of server.py."""

import json
import os
import threading
import urllib.request
from contextlib import nullcontext
from typing import Any, Callable, Dict, Tuple

import config
import gcal
import routes_settings
import spotify_mod

Result = Tuple[Dict[str, Any], int]

_config: Dict[str, Any] = {"ask": None, "busy": nullcontext, "log": print}


def configure(ask: Callable[[list], str], busy: Callable[[], Any], log: Callable[[str], None]) -> None:
    """`ask` sends one question to the AI. `busy` marks KALKI as working while it runs."""
    _config.update(ask=ask, busy=busy, log=log)


def find_ollama(body: Dict[str, Any]) -> Result:
    """Is Ollama running here, and with which models? Only ever asks this PC."""
    base = str(getattr(config, "OLLAMA_URL", "") or "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=1.5) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (OSError, ValueError):
        return {"ok": True, "running": False, "models": []}, 200
    return {"ok": True, "running": True, "models": [str(m.get("name", "")) for m in models if isinstance(m, dict)][:20]}, 200


def test_ai(body: Dict[str, Any]) -> Result:
    """A real question, so the answer proves the whole path works."""
    try:
        with _config["busy"]():
            reply = _config["ask"]([{"role": "user", "content": "Say hello in one short sentence."}])
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}, 200
    text = str(reply or "")
    return {"ok": bool(text.strip()), "reply": text[:500]}, 200


def _in_background(name: str, work: Callable[[], None]) -> None:
    def run():
        try:
            work()
            _config["log"](f"{name} setup finished.")
        except Exception as exc:
            _config["log"](f"{name} setup didn't finish: {exc}")
    threading.Thread(target=run, daemon=True).start()


def setup_tool(body: Dict[str, Any]) -> Result:
    tool = body.get("tool")
    if tool == "google":
        _in_background("Google", lambda: gcal._get_creds(interactive=True))
    elif tool == "spotify":
        _in_background("Spotify", lambda: spotify_mod._client(interactive=True))
    elif tool == "reconnect_spotify":
        def reconnect():
            if spotify_mod.CACHE_PATH and os.path.exists(spotify_mod.CACHE_PATH):
                os.remove(spotify_mod.CACHE_PATH)
            spotify_mod._client(interactive=True)
        _in_background("Spotify", reconnect)
    else:
        return {"ok": False, "error": "Unknown tool."}, 400
    return {"ok": True, "secretStatus": routes_settings.secret_status()}, 200


POST_ROUTES = {
    "/api/setup/ollama": find_ollama,
    "/api/setup/test_ai": test_ai,
    "/api/setup/tool": setup_tool,
}
