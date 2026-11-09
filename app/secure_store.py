"""The one place KALKI encrypts things on this PC.

Windows uses DPAPI, which ties data to the signed-in user. Elsewhere it uses a random
key held in the OS keychain, or failing that in a private key file.

Reading fails loudly. A caller that gets an empty string for "couldn't decrypt" can
easily save that empty value over the real data, so unprotect() raises instead.
"""

import base64
import hashlib
import os
import socket
import threading
from typing import Optional

try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    win32crypt = None
    HAS_DPAPI = False

_KEYRING_SERVICE = "kalki_store"
_KEYRING_NAME = "local_key"
_key_lock = threading.Lock()


class UnprotectError(Exception):
    """This data can't be decrypted here. Keep it: don't overwrite it."""


def _key_path() -> str:
    from runtime_paths import prepare_runtime
    return os.path.join(prepare_runtime().user_data_dir, "store.key")


def _keyring_key() -> Optional[bytes]:
    try:
        import keyring
        from cryptography.fernet import Fernet
        stored = keyring.get_password(_KEYRING_SERVICE, _KEYRING_NAME)
        if not stored:
            stored = Fernet.generate_key().decode()
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_NAME, stored)
        return stored.encode()
    except Exception:
        return None


def _file_key() -> bytes:
    from cryptography.fernet import Fernet
    path = _key_path()
    if os.path.exists(path):
        with open(path, "rb") as handle:
            return handle.read().strip()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = Fernet.generate_key()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(key)
    return key


def _local_key() -> bytes:
    with _key_lock:
        return _keyring_key() or _file_key()


def protect(text: str) -> str:
    data = str(text).encode("utf-8")
    if HAS_DPAPI:
        blob = win32crypt.CryptProtectData(data, "kalki", None, None, None, 0)
        return "DPAPI:" + base64.b64encode(blob).decode("ascii")
    from cryptography.fernet import Fernet
    return "LOCAL:" + Fernet(_local_key()).encrypt(data).decode("ascii")


def _legacy_machine_key() -> bytes:
    """Old semantic-memory key derived from the computer and user names. Read-only:
    new data never uses it, because anyone can work those names out."""
    machine = os.environ.get("COMPUTERNAME", socket.gethostname()) + "_" + os.environ.get("USERNAME", "kalki")
    return base64.urlsafe_b64encode(hashlib.sha256(machine.encode("utf-8")).digest())


def is_protected(value: str) -> bool:
    return isinstance(value, str) and value.startswith(("DPAPI:", "LOCAL:", "FERNET:", "B64:"))


def unprotect(blob: str) -> str:
    """Decrypt, or raise UnprotectError. Never returns a placeholder."""
    if not is_protected(blob):
        raise UnprotectError("Not encrypted data.")
    try:
        if blob.startswith("DPAPI:"):
            if not HAS_DPAPI:
                raise UnprotectError("Windows encryption isn't available here.")
            raw = base64.b64decode(blob[6:])
            return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1].decode("utf-8")
        if blob.startswith("LOCAL:"):
            from cryptography.fernet import Fernet
            return Fernet(_local_key()).decrypt(blob[6:].encode("ascii")).decode("utf-8")
        if blob.startswith("FERNET:"):
            from cryptography.fernet import Fernet
            return Fernet(_legacy_machine_key()).decrypt(blob[7:].encode("ascii")).decode("utf-8")
        return base64.b64decode(blob[4:]).decode("utf-8")
    except UnprotectError:
        raise
    except Exception as exc:
        raise UnprotectError(f"Couldn't decrypt: {type(exc).__name__}") from exc
