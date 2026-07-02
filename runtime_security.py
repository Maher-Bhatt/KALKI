"""Local authentication helpers for the KALKI server and listener."""

import hmac
import os
import secrets
import subprocess
import sys


BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
TOKEN_PATH = os.path.join(BASE_DIR, "data", "api_token.txt")
TOKEN_HEADER = "X-KALKI-Token"
TOKEN_COOKIE = "kalki_session"


def _restrict_file(path):
    """Best-effort ACL: current Windows user and SYSTEM only."""
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return
    user = os.environ.get("USERNAME")
    if not user:
        return
    try:
        subprocess.run(
            [
                "icacls",
                path,
                "/inheritance:r",
                "/grant:r",
                f"{user}:(R,W)",
                "/grant:r",
                "SYSTEM:(F)",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def get_api_token():
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    try:
        with open(TOKEN_PATH, "r", encoding="ascii") as f:
            token = f.read().strip()
        if len(token) >= 32:
            return token
    except OSError:
        pass

    token = secrets.token_urlsafe(48)
    tmp = TOKEN_PATH + ".tmp"
    with open(tmp, "w", encoding="ascii") as f:
        f.write(token)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, TOKEN_PATH)
    _restrict_file(TOKEN_PATH)
    return token


def token_matches(candidate):
    return isinstance(candidate, str) and hmac.compare_digest(
        candidate, get_api_token()
    )

