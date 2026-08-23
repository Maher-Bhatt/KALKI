"""GitHub integration used by KALKI's local command and dashboard layers.

The module keeps the public string-returning helpers used by the voice router,
while exposing structured helpers for UI and future automation. Tokens are only
read from the encrypted/config-backed settings layer and are never returned to
callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

import config

API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
USER_AGENT = "KALKI-AI-Assistant/1.3.0"
_PLACEHOLDERS = {"", "your_personal_access_token", "PASTE_YOUR_GITHUB_TOKEN_HERE"}


@dataclass
class GitHubResponse:
    status: int
    data: Any = None
    headers: dict[str, str] | None = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _token() -> str:
    return str(getattr(config, "GITHUB_TOKEN", "") or "").strip()


def is_configured() -> bool:
    token = _token()
    return bool(token and token not in _PLACEHOLDERS and not token.startswith("PASTE_"))


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }


def _request(path: str, *, params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None, timeout: float = 10) -> GitHubResponse:
    try:
        response = requests.get(
            f"{API_ROOT}{path}",
            headers={**_headers(), **(headers or {})},
            params=params,
            timeout=timeout,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = None
        return GitHubResponse(response.status_code, payload, dict(response.headers))
    except requests.RequestException as exc:
        return GitHubResponse(0, error=str(exc))


def _error_message(response: GitHubResponse, resource: str = "GitHub") -> str:
    if response.status == 0:
        return f"Could not reach GitHub: {response.error}"
    if response.status == 401:
        return "GitHub token is invalid or expired."
    if response.status == 403:
        remaining = (response.headers or {}).get("X-RateLimit-Remaining")
        if remaining == "0":
            return "GitHub rate limit reached. Try again after the reset window."
        return "GitHub denied this request. Check token permissions or organization access."
    if response.status == 404:
        return f"{resource} was not found or is not visible to this token."
    message = ""
    if isinstance(response.data, dict):
        message = str(response.data.get("message") or "").strip()
    return f"GitHub returned an error ({response.status})" + (f": {message}" if message else ".")


_NOTIFICATION_HEADERS: dict[str, str] = {}
_NOTIFICATION_CACHE: list[dict[str, Any]] = []


def get_notifications(limit: int = 5, *, force: bool = False) -> dict[str, Any]:
    """Return unread notification threads with conditional polling support."""
    global _NOTIFICATION_CACHE, _NOTIFICATION_HEADERS
    if not is_configured():
        return {"ok": False, "configured": False, "error": "GitHub is not configured."}

    limit = max(1, min(int(limit or 5), 50))
    conditional: dict[str, str] = {}
    if not force:
        last_modified = _NOTIFICATION_HEADERS.get("Last-Modified")
        if last_modified:
            conditional["If-Modified-Since"] = last_modified
    response = _request(
        "/notifications",
        params={"all": "false", "participating": "false", "per_page": limit},
        headers=conditional,
    )
    if response.status == 304:
        return {
            "ok": True,
            "configured": True,
            "notModified": True,
            "notifications": list(_NOTIFICATION_CACHE),
            "count": len(_NOTIFICATION_CACHE),
            "pollInterval": _poll_interval(),
        }
    if not response.ok or not isinstance(response.data, list):
        return {"ok": False, "configured": True, "error": _error_message(response), "status": response.status}

    _NOTIFICATION_CACHE = response.data
    _NOTIFICATION_HEADERS = response.headers or {}
    return {
        "ok": True,
        "configured": True,
        "notModified": False,
        "notifications": list(response.data),
        "count": len(response.data),
        "pollInterval": _poll_interval(),
    }


def _poll_interval() -> int:
    try:
        return max(60, int(_NOTIFICATION_HEADERS.get("X-Poll-Interval", "60")))
    except (TypeError, ValueError):
        return 60


def check_notifications(limit: int = 5) -> str:
    """Fetch unread notifications and return a voice-friendly summary."""
    result = get_notifications(limit)
    if not result.get("ok"):
        return str(result.get("error") or "GitHub notifications are unavailable.")
    notifications = result.get("notifications") or []
    if not notifications:
        return "No new GitHub notifications, Sir."
    summary_parts = []
    for item in notifications[:limit]:
        repository = item.get("repository") or {}
        subject = item.get("subject") or {}
        repo = repository.get("full_name") or repository.get("name") or "a repository"
        title = subject.get("title") or "an update"
        summary_parts.append(f"In {repo}: {title}")
    count = len(notifications)
    noun = "notification" if count == 1 else "notifications"
    text = f"You have {count} unread GitHub {noun}. " + ". ".join(summary_parts)
    return text[:600]


def get_authenticated_user() -> dict[str, Any]:
    """Return the authenticated user profile without exposing credentials."""
    if not is_configured():
        return {"ok": False, "configured": False, "error": "GitHub is not configured."}
    response = _request("/user")
    if not response.ok or not isinstance(response.data, dict):
        return {"ok": False, "configured": True, "error": _error_message(response, "GitHub user"), "status": response.status}
    return {"ok": True, "configured": True, "user": response.data}


def get_rate_limit() -> dict[str, Any]:
    """Return the current REST-core rate-limit bucket."""
    if not is_configured():
        return {"ok": False, "configured": False, "error": "GitHub is not configured."}
    response = _request("/rate_limit")
    if not response.ok or not isinstance(response.data, dict):
        return {"ok": False, "configured": True, "error": _error_message(response, "GitHub rate limit"), "status": response.status}
    return {"ok": True, "configured": True, "rate": response.data.get("rate", {})}


def get_repo_stats(username: str) -> str:
    """Fetch all public repositories for a user and summarize stars/forks."""
    username = (username or "").strip()
    if not username:
        return "Please provide a GitHub username."
    if not is_configured():
        return "GitHub is not configured."

    repos: list[dict[str, Any]] = []
    page = 1
    while page <= 100:
        response = _request(
            f"/users/{requests.utils.quote(username, safe='')}/repos",
            params={"type": "owner", "per_page": 100, "page": page, "sort": "updated"},
        )
        if not response.ok or not isinstance(response.data, list):
            return _error_message(response, f"Repositories for {username}")
        repos.extend(item for item in response.data if isinstance(item, dict))
        if len(response.data) < 100 or "rel=\"next\"" not in (response.headers or {}).get("Link", ""):
            break
        page += 1

    total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    total_forks = sum(int(repo.get("forks_count") or 0) for repo in repos)
    return (
        f"User {username} has {total_stars} total stars and {total_forks} forks "
        f"across {len(repos)} public repositories."
    )
