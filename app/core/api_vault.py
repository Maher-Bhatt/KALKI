"""Encrypted storage for KALKI's own API keys and tokens."""

import base64
import hashlib
import json
import os
import sys
import threading
from typing import Dict, List

import secure_store

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    keyring = None
    HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

_lock = threading.RLock()
if os.name == "nt":
    _vault_base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
elif sys.platform == "darwin":
    _vault_base = os.path.expanduser("~/Library/Application Support")
else:
    _vault_base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
VAULT_DIR = os.path.join(_vault_base, "KALKI")
VAULT_FILE = os.path.join(VAULT_DIR, "secure_api_vault.enc")
INTEGRITY_FILE = os.path.join(VAULT_DIR, "vault_integrity.sha256")

_SECRET_WORDS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CLIENT_ID")
_PLACEHOLDERS = ("PASTE_", "YOUR_", "your_")
_EXPORT_ITERATIONS = 600_000


def _decrypt_val(stored: str) -> str:
    """Decrypt one stored value. Raises UnprotectError if it can't be read."""
    if stored.startswith("KEYRING:"):  # older macOS/Linux entries
        value = keyring.get_password("kalki_vault", stored[8:]) if HAS_KEYRING else None
        if value:
            return value
        raise secure_store.UnprotectError("Not in the OS keychain.")
    return secure_store.unprotect(stored)


def _load_vault() -> Dict[str, str]:
    if not os.path.exists(VAULT_FILE):
        return {}
    with open(VAULT_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_vault(data: Dict[str, str]) -> None:
    """Write atomically. Errors reach the caller, so "saved" is always true."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    tmp = VAULT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, VAULT_FILE)
    with open(VAULT_FILE, "rb") as handle:
        checksum = hashlib.sha256(handle.read()).hexdigest()
    with open(INTEGRITY_FILE, "w", encoding="utf-8") as handle:
        handle.write(checksum)


def get_secret(key: str, default: str = "") -> str:
    with _lock:
        stored = _load_vault().get(key.upper())
        if not stored:
            return default
        try:
            return _decrypt_val(stored) or default
        except secure_store.UnprotectError:
            return default


def set_secret(key: str, value: str) -> None:
    with _lock:
        data = _load_vault()
        data[key.upper()] = secure_store.protect(value)
        _save_vault(data)


def list_secrets() -> Dict[str, str]:
    """Every value that can be decrypted here. Others stay stored, untouched."""
    with _lock:
        decrypted = {}
        for key, stored in _load_vault().items():
            try:
                value = _decrypt_val(stored)
            except secure_store.UnprotectError:
                continue
            if value:
                decrypted[key] = value
        return decrypted


def unreadable_keys() -> List[str]:
    """Names of stored secrets that can't be decrypted on this PC or account."""
    with _lock:
        names = []
        for key, stored in _load_vault().items():
            try:
                _decrypt_val(stored)
            except secure_store.UnprotectError:
                names.append(key)
        return names


def verify_integrity() -> bool:
    """Check the vault file against its saved checksum."""
    if not os.path.exists(VAULT_FILE):
        return True
    if not os.path.exists(INTEGRITY_FILE):
        return False
    try:
        with open(VAULT_FILE, "rb") as handle:
            current = hashlib.sha256(handle.read()).hexdigest()
        with open(INTEGRITY_FILE, "r", encoding="utf-8") as handle:
            return current == handle.read().strip()
    except OSError:
        return False


def _export_key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _old_export_key(password: str, salt: bytes) -> bytes:
    """Exports made before PBKDF2 used one round of SHA-256. Read-only."""
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode("utf-8") + salt).digest())


def export_vault(filepath: str, password: str) -> bool:
    """Write every readable secret to a password-protected file."""
    if not HAS_CRYPTO or not password:
        return False
    try:
        salt = os.urandom(16)
        token = Fernet(_export_key(password, salt, _EXPORT_ITERATIONS)).encrypt(
            json.dumps(list_secrets()).encode("utf-8"))
        payload = {"kdf": "pbkdf2-sha256", "iterations": _EXPORT_ITERATIONS,
                   "salt": base64.b64encode(salt).decode(), "ciphertext": token.decode()}
        with open(filepath, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        return True
    except (OSError, ValueError):
        return False


def import_vault(filepath: str, password: str) -> bool:
    """Read a password-protected export and store its secrets on this PC."""
    if not HAS_CRYPTO or not password:
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        salt = base64.b64decode(payload["salt"])
        if payload.get("kdf") == "pbkdf2-sha256":
            key = _export_key(password, salt, int(payload["iterations"]))
        else:
            key = _old_export_key(password, salt)
        secrets = json.loads(Fernet(key).decrypt(payload["ciphertext"].encode()).decode("utf-8"))
        with _lock:
            for name, value in secrets.items():
                set_secret(name, value)
        return True
    except Exception:
        return False


def _is_real_secret(name: str, value) -> bool:
    return (isinstance(value, str) and bool(value.strip())
            and any(word in name.upper() for word in _SECRET_WORDS)
            and not value.startswith(_PLACEHOLDERS))


def migrate_settings_to_vault(user_config_path: str) -> None:
    """Move secrets out of plain-text settings. A value is only removed from the
    settings file after it has been read back from the vault correctly."""
    if not os.path.exists(user_config_path):
        return
    try:
        with open(user_config_path, "r", encoding="utf-8-sig") as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            return
        moved = []
        for name, value in config.items():
            if not _is_real_secret(name, value):
                continue
            if not get_secret(name):
                set_secret(name, value)
            if get_secret(name):
                moved.append(name)
        if moved:
            for name in moved:
                del config[name]
            tmp = user_config_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, user_config_path)
    except (OSError, ValueError):
        # Settings stay as they were, and this runs again next start.
        pass
