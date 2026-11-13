"""Backup and restore routes, moved out of server.py.

A backup is one zip of the database and KALKI's settings files. Restore checks the
database first, so a bad backup restores nothing, and keeps a copy of every file it
replaces.
"""

import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, Tuple

import db
import semantic_memory

Result = Tuple[Dict[str, Any], int]

MAX_FILE_BYTES = 20 * 1024 * 1024

# Files in the profile folder, and files in its data folder.
PROFILE_FILES = ("user_config.json", "secure_api_vault.enc", "vault_integrity.sha256", "ai_usage.json",
                 "semantic_memory.json")
DATA_FILES = ("productivity.json", "memory.json", "history.json")

_config: Dict[str, Any] = {"profile_dir": None, "data_dir": None}


def configure(profile_dir: str, data_dir: str) -> None:
    _config.update(profile_dir=profile_dir, data_dir=data_dir)


def _target(name: str) -> str:
    folder = _config["data_dir"] if name in DATA_FILES else _config["profile_dir"]
    return os.path.join(folder, name)


def create(body: Dict[str, Any]) -> Result:
    backups = os.path.join(_config["profile_dir"], "backups")
    os.makedirs(backups, exist_ok=True)
    path = os.path.join(backups, f"kalki_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    try:
        with tempfile.TemporaryDirectory() as work:
            snapshot = os.path.join(work, "kalki.db")
            db.backup_to(snapshot)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name in ("user_config.json", "secure_api_vault.enc", "vault_integrity.sha256", "ai_usage.json",
                             "productivity.json"):
                    source = _target(name)
                    if os.path.exists(source):
                        archive.write(source, name)
                archive.write(snapshot, "kalki.db")
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 200
    return {"ok": True, "file": path}, 200


def _replace_file(target: str, data: bytes, stamp: str) -> None:
    """Keep a copy of what's there, then swap the new file in whole."""
    if os.path.exists(target):
        shutil.copy2(target, f"{target}.before-restore.{stamp}")
    temporary = f"{target}.restoring"
    with open(temporary, "wb") as out:
        out.write(data)
    os.replace(temporary, target)


def restore(body: Dict[str, Any]) -> Result:
    path = str(body.get("path") or body.get("filepath") or body.get("filePath") or "").strip()
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "Choose a backup file that exists."}, 400
    allowed = set(PROFILE_FILES) | set(DATA_FILES)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = {os.path.basename(n) for n in archive.namelist()}
            # The database first: if it's bad, nothing else is touched.
            if "kalki.db" in names:
                with tempfile.TemporaryDirectory() as work:
                    db.restore_from(archive.extract("kalki.db", work))
            for member in archive.infolist():
                name = os.path.basename(member.filename)
                if name not in allowed or member.file_size > MAX_FILE_BYTES:
                    continue
                with archive.open(member) as source:
                    _replace_file(_target(name), source.read(), stamp)
            if "kalki.db" not in names:
                db.reimport_legacy([k for k, f in (("memory", "memory.json"), ("history", "history.json")) if f in names],
                                   _config["data_dir"])
                if "semantic_memory.json" in names:
                    semantic_memory.memory.reimport_legacy()
        semantic_memory.memory.reload()
    except db.StoreError as exc:
        return {"ok": False, "error": str(exc)}, 400
    except zipfile.BadZipFile:
        return {"ok": False, "error": "That file isn't a KALKI backup."}, 400
    except Exception as exc:
        return {"ok": False, "error": str(exc)}, 500
    return {"ok": True, "message": "Restore successful."}, 200


POST_ROUTES = {
    "/api/backup/create": create,
    "/api/backup/restore": restore,
}
