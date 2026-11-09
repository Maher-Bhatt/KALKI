"""
KALKI Vault: an encrypted local store for labelled logins.
Encryption comes from secure_store, which fails loudly and never falls back to
reversible encoding.
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import secure_store

_lock = threading.RLock()

VAULT_PATH: Optional[str] = None  # set by server.py before first use


def _enc(plain: Union[str, bytes, None]) -> str:
    if plain is None or plain == "":
        return ""
    return secure_store.protect(plain.decode("utf-8") if isinstance(plain, bytes) else plain)


def _dec(blob: str) -> str:
    """Decrypt a stored field. Raises UnprotectError if it can't be read."""
    if not blob:
        return ""
    if not secure_store.is_protected(blob):
        return blob
    return secure_store.unprotect(blob)


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


def _single_match(data: Dict[str, Any], query: str) -> Optional[str]:
    """An exact label, or a partial match only if exactly one entry fits. A
    credential store must never guess which login was meant."""
    needle = str(query or "").lower().strip()
    if not needle:
        return None
    if needle in data:
        return needle
    matches = [key for key in data if needle in key]
    return matches[0] if len(matches) == 1 else None


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
    try:
        username_blob, password_blob = _enc(username), _enc(password)
    except Exception as exc:
        return {"error": f"Secure storage isn't available, so nothing was saved: {exc}"}
    with _lock:
        d = _load()
        key = label.lower().strip()
        d[key] = {
            "label": label,
            "username": username_blob,
            "password": password_blob,
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
    fields, unreadable = {}, False
    for field in ("username", "password"):
        try:
            fields[field] = _dec(e.get(field, ""))
        except secure_store.UnprotectError:
            fields[field] = ""
            unreadable = True
    return {
        "label": e["label"],
        "username": fields["username"],
        "password": fields["password"],
        "unreadable": unreadable,
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
    key = _single_match(_load(), query)
    return get_entry(key) if key else None


def delete_entry(label: str) -> bool:
    """
    Delete an entry from the vault.
    
    Args:
        label (str): The exact or partial label of the entry to delete.
        
    Returns:
        bool: True if an entry was deleted, False otherwise.
    """
    with _lock:
        data = _load()
        key = _single_match(data, label)
        if not key:
            return False
        del data[key]
        _save(data)
        return True
