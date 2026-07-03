"""
KALKI Vault — DPAPI-encrypted local password store.
Per-Windows-user, machine-locked. No master password.
Falls back to base64 (clearly marked) if pywin32 is missing.
"""

import os
import json
import base64
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False

_lock = threading.RLock()

VAULT_PATH: Optional[str] = None  # set by server.py before first use


def _enc(plain: Union[str, bytes, None]) -> str:
    """Encrypt a plaintext string or bytes using Windows DPAPI."""
    if plain is None or plain == "":
        return ""
    data = plain.encode("utf-8") if isinstance(plain, str) else plain
    if HAS_DPAPI:
        blob = win32crypt.CryptProtectData(data, "kalki-vault", None, None, None, 0)
        return "DPAPI:" + base64.b64encode(blob).decode()
    return "B64:" + base64.b64encode(data).decode()


def _dec(blob: str) -> str:
    """Decrypt a DPAPI or Base64 encoded blob."""
    if not blob:
        return ""
    if blob.startswith("DPAPI:") and HAS_DPAPI:
        raw = base64.b64decode(blob[6:])
        try:
            return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1].decode("utf-8")
        except Exception:
            return ""
    if blob.startswith("B64:"):
        try:
            return base64.b64decode(blob[4:]).decode("utf-8")
        except Exception:
            return ""
    return blob


def _load() -> Dict[str, Any]:
    """Load the vault JSON file into a dictionary."""
    if VAULT_PATH is None:
        return {}
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: Dict[str, Any]) -> None:
    """Save the vault dictionary securely to disk."""
    if VAULT_PATH is None:
        return
    os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
    tmp = VAULT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, VAULT_PATH)


def save_entry(label: str, username: str = "", password: str = "", url: str = "", notes: str = "") -> Union[bool, Dict[str, str]]:
    """
    Save a new entry to the encrypted vault.
    
    Args:
        label (str): The unique label/name of the entry.
        username (str): The username for the entry.
        password (str): The password to encrypt.
        url (str): Associated URL.
        notes (str): Any extra encrypted notes.
        
    Returns:
        Union[bool, Dict[str, str]]: True if saved successfully, Dict containing error if pywin32 is missing, or False on bad input.
    """
    if not label:
        return False
    # Refuse to "encrypt" with reversible base64. Without DPAPI (pywin32),
    # storing a secret would be no better than plaintext — fail loudly instead.
    if (password or username) and not HAS_DPAPI:
        return {"error": "DPAPI unavailable (install pywin32) — refusing to "
                         "store credentials without real encryption."}
    with _lock:
        d = _load()
        key = label.lower().strip()
        d[key] = {
            "label": label,
            "username": _enc(username),
            "password": _enc(password),
            "url": url or "",
            "notes": notes or "",
            "saved": datetime.now().isoformat(timespec="seconds"),
        }
        _save(d)
    return True


def list_labels() -> List[Dict[str, str]]:
    """
    List all entry labels and unencrypted metadata in the vault.
    
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing label, url, and save date.
    """
    d = _load()
    return [
        {"label": v["label"], "url": v.get("url", ""), "saved": v.get("saved", "")}
        for v in d.values()
    ]


def get_entry(label: str) -> Optional[Dict[str, str]]:
    """
    Retrieve and decrypt a specific entry by exact label.
    
    Args:
        label (str): The exact label to fetch.
        
    Returns:
        Optional[Dict[str, str]]: The decrypted entry dictionary, or None if not found.
    """
    if not str(label).strip():
        return None
    d = _load()
    e = d.get(label.lower().strip())
    if not e:
        return None
    return {
        "label": e["label"],
        "username": _dec(e.get("username", "")),
        "password": _dec(e.get("password", "")),
        "url": e.get("url", ""),
        "notes": e.get("notes", ""),
        "saved": e.get("saved", ""),
    }


def find_entry(query: str) -> Optional[Dict[str, str]]:
    """
    Fuzzy match — returns the first decrypted entry containing the query.
    
    Args:
        query (str): The string to search for in the labels.
        
    Returns:
        Optional[Dict[str, str]]: The decrypted entry, or None if not found.
    """
    if not query:
        return None
    q = query.lower().strip()
    d = _load()
    if q in d:
        return get_entry(q)
    for k in d.keys():
        if q in k or k in q:
            return get_entry(k)
    return None


def delete_entry(label: str) -> bool:
    """
    Delete an entry from the vault.
    
    Args:
        label (str): The exact or partial label of the entry to delete.
        
    Returns:
        bool: True if an entry was deleted, False otherwise.
    """
    query = str(label).strip().lower()
    if not query:
        return False
    with _lock:
        data = _load()
        if query in data:
            del data[query]
            _save(data)
            return True
        for key in list(data):
            if query in key:
                del data[key]
                _save(data)
                return True
    return False
