"""Runtime locations shared by KALKI's packaged entry points.

Each PyInstaller ``--onedir`` executable needs its own ``_internal`` folder.
The release layout therefore keeps the desktop app at the package root and
places helper executables below ``services/``.  This module gives every entry
point the same reliable way to find the package root, user settings, and the
configuration module in both source and packaged builds.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved paths for the current KALKI process."""

    entry_dir: str
    app_root: str
    user_data_dir: str
    config_path: str
    using_user_config: bool


def _entry_dir() -> str:
    executable_or_file = sys.executable if getattr(sys, "frozen", False) else __file__
    return os.path.dirname(os.path.abspath(executable_or_file))


def _find_app_root(entry_dir: str) -> str:
    """Return the package root when this process is a bundled helper."""

    candidate = entry_dir
    for _ in range(3):
        if os.path.isfile(os.path.join(candidate, "KALKI.exe")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return entry_dir


def prepare_runtime() -> RuntimePaths:
    """Set import paths and provision a writable config file on first run.

    MSIX installs are read-only. In that case ``config.py`` is copied to the
    per-user KALKI directory and that directory is placed before PyInstaller's
    bundled modules, so settings saved by the setup wizard are actually used.
    """

    entry_dir = _entry_dir()
    app_root = _find_app_root(entry_dir)
    user_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI")
    app_config = os.path.join(app_root, "config.py")
    config_example = os.path.join(app_root, "config.example.py")
    user_config = os.path.join(user_data_dir, "config.py")
    using_user_config = False

    if not os.path.exists(app_config) and os.path.exists(config_example):
        try:
            shutil.copy2(config_example, app_config)
        except (OSError, PermissionError):
            using_user_config = True

    if not os.path.exists(app_config):
        using_user_config = True
        os.makedirs(user_data_dir, exist_ok=True)
        if not os.path.exists(user_config) and os.path.exists(config_example):
            shutil.copy2(config_example, user_config)

    os.chdir(app_root)
    for path in (entry_dir, app_root):
        if path not in sys.path:
            sys.path.insert(0, path)
    if using_user_config and os.path.exists(user_config):
        sys.path.insert(0, user_data_dir)

    return RuntimePaths(
        entry_dir=entry_dir,
        app_root=app_root,
        user_data_dir=user_data_dir,
        config_path=user_config if using_user_config else app_config,
        using_user_config=using_user_config,
    )
