import os
import sys
import json
import base64
import hashlib
import threading
from typing import Dict, Any, Optional

try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet
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
MASTER_KEY_FILE = os.path.join(VAULT_DIR, "vault_master.key")
INTEGRITY_FILE = os.path.join(VAULT_DIR, "vault_integrity.sha256")

_master_password: Optional[str] = None


def set_master_password(password: str) -> None:
    """Sets the master password for the local AES-256 fallback encryption."""
    global _master_password
    _master_password = password


def _derive_fernet_key(salt: bytes, password: str) -> bytes:
    """Derive a Fernet key from a per-entry random salt and master password."""
    if not password:
        raise ValueError("vault master password is required")
    hasher = hashlib.sha256()
    hasher.update(password.encode("utf-8") + salt)
    return base64.urlsafe_b64encode(hasher.digest())


def _encrypt_val(val: Any) -> str:
    """Encrypts a value using DPAPI on Windows, keyring on Mac/Linux, or Fernet fallback."""
    if val is None:
        return ""
    val_str = str(val)
    if not val_str:
        return ""

    # 1. Try DPAPI first (Windows)
    if HAS_DPAPI:
        try:
            blob = win32crypt.CryptProtectData(val.encode("utf-8"), "kalki-api-vault", None, None, None, 0)
            return "DPAPI:" + base64.b64encode(blob).decode()
        except Exception:
            pass

    # 2. Try keyring (macOS/Linux)
    if HAS_KEYRING:
        try:
            # We store random token names to fetch from OS store
            token_id = hashlib.sha1(val.encode()).hexdigest()[:16]
            keyring.set_password("kalki_vault", token_id, val)
            return f"KEYRING:{token_id}"
        except Exception:
            pass

    # 3. Password-based fallback requires an explicit master password and a
    # fresh random salt for every value. Never silently store plaintext.
    if HAS_CRYPTO and _master_password:
        try:
            salt = os.urandom(16)
            key = _derive_fernet_key(salt, _master_password)
            encrypted = Fernet(key).encrypt(val.encode("utf-8"))
            return "FERNET:" + base64.b64encode(salt).decode() + ":" + encrypted.decode()
        except Exception:
            pass

    raise RuntimeError("secure vault storage is unavailable; refusing to store secret")


def _decrypt_val(enc_str: str) -> str:
    """Decrypts a value."""
    if not enc_str:
        return ""

    if enc_str.startswith("DPAPI:") and HAS_DPAPI:
        try:
            raw = base64.b64decode(enc_str[6:])
            return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1].decode("utf-8")
        except Exception:
            pass

    if enc_str.startswith("KEYRING:") and HAS_KEYRING:
        try:
            token_id = enc_str[8:]
            val = keyring.get_password("kalki_vault", token_id)
            if val:
                return val
        except Exception:
            pass

    if enc_str.startswith("FERNET:") and HAS_CRYPTO and _master_password:
        try:
            _, salt_b64, ciphertext = enc_str.split(":", 2)
            salt = base64.b64decode(salt_b64)
            key = _derive_fernet_key(salt, _master_password)
            return Fernet(key).decrypt(ciphertext.encode()).decode("utf-8")
        except Exception:
            pass

    # Legacy AES entries can be read only when the user supplied the old
    # master password; new writes never use this deterministic format.
    if enc_str.startswith("AES:") and HAS_CRYPTO and _master_password:
        try:
            key = _derive_fernet_key(b"kalki_default_salt_123", _master_password)
            return Fernet(key).decrypt(enc_str[4:].encode()).decode("utf-8")
        except Exception:
            pass

    # Plaintext legacy values are intentionally not returned.
    if enc_str.startswith("PLAIN:"):
        return ""

    return ""


def _load_vault() -> Dict[str, str]:
    """Load and return the raw encrypted vault dictionary."""
    if not os.path.exists(VAULT_FILE):
        return {}
    try:
        with open(VAULT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_vault(data: Dict[str, str]) -> None:
    """Save the encrypted vault dictionary and update integrity checksum."""
    os.makedirs(VAULT_DIR, exist_ok=True)
    tmp = VAULT_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, VAULT_FILE)
        
        # Write integrity checksum
        with open(VAULT_FILE, "rb") as rb:
            sha = hashlib.sha256(rb.read()).hexdigest()
        with open(INTEGRITY_FILE, "w", encoding="utf-8") as f:
            f.write(sha)
    except Exception:
        pass


def get_secret(key: str, default: str = "") -> str:
    """Retrieve a decrypted secret from the vault."""
    with _lock:
        data = _load_vault()
        enc_val = data.get(key.upper())
        if enc_val:
            dec = _decrypt_val(enc_val)
            if dec:
                return dec
        return default


def set_secret(key: str, value: str) -> None:
    """Store a secret encrypted in the vault."""
    with _lock:
        data = _load_vault()
        data[key.upper()] = _encrypt_val(value)
        _save_vault(data)


def list_secrets() -> Dict[str, str]:
    """Return all keys and their decrypted values (useful for local config loader)."""
    with _lock:
        data = _load_vault()
        decrypted = {}
        for k, v in data.items():
            dec = _decrypt_val(v)
            if dec:
                decrypted[k] = dec
        return decrypted


def verify_integrity() -> bool:
    """Verify that the vault file matches its SHA-256 checksum."""
    if not os.path.exists(VAULT_FILE):
        return True
    if not os.path.exists(INTEGRITY_FILE):
        return False
    try:
        with open(VAULT_FILE, "rb") as rb:
            curr_sha = hashlib.sha256(rb.read()).hexdigest()
        with open(INTEGRITY_FILE, "r", encoding="utf-8") as f:
            saved_sha = f.read().strip()
        return curr_sha == saved_sha
    except Exception:
        return False


def export_vault(filepath: str, password: str) -> bool:
    """Export all secrets to a password-protected JSON backup file."""
    if not HAS_CRYPTO:
        return False
    try:
        secrets = list_secrets()
        plain_text = json.dumps(secrets)
        salt = os.urandom(16)
        key = _derive_fernet_key(salt, password)
        f = Fernet(key)
        ciphertext = f.encrypt(plain_text.encode("utf-8"))
        
        payload = {
            "salt": base64.b64encode(salt).decode(),
            "ciphertext": ciphertext.decode()
        }
        with open(filepath, "w", encoding="utf-8") as out:
            json.dump(payload, out, indent=4)
        return True
    except Exception:
        return False


def import_vault(filepath: str, password: str) -> bool:
    """Import secrets from an encrypted backup file, re-encrypting them natively."""
    if not HAS_CRYPTO:
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)
        salt = base64.b64decode(payload["salt"])
        key = _derive_fernet_key(salt, password)
        f_obj = Fernet(key)
        plain_bytes = f_obj.decrypt(payload["ciphertext"].encode())
        secrets = json.loads(plain_bytes.decode("utf-8"))
        
        with _lock:
            for k, v in secrets.items():
                set_secret(k, v)
        return True
    except Exception:
        return False


def migrate_settings_to_vault(user_config_path: str) -> None:
    """Migrate plaintext user configs to the secure vault if vault is empty."""
    if not os.path.exists(user_config_path):
        return
    try:
        with open(user_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in cfg.items():
            # Only migrate key values (usually uppercase names containing KEY, SECRET, TOKEN, or PASSWORD)
            k_upper = k.upper()
            if any(x in k_upper for x in ["KEY", "SECRET", "TOKEN", "PASSWORD", "CLIENT_ID"]):
                if v and not get_secret(k_upper):
                    set_secret(k_upper, v)
    except Exception:
        pass
