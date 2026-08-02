"""
KALKI WhatsApp messaging via pywhatkit (uses WhatsApp Web).
First-time use: WhatsApp Web must be logged in in your browser.
"""

import os
import json
import urllib.parse
import webbrowser
import threading

CONTACTS_PATH = None  # set by server
_lock = threading.RLock()


def _load_contacts():
    try:
        with open(CONTACTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_contacts(d):
    os.makedirs(os.path.dirname(CONTACTS_PATH), exist_ok=True)
    tmp = CONTACTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CONTACTS_PATH)


def add_contact(name, phone):
    """phone must include country code, e.g. +91xxxxxxxxxx"""
    name = str(name).strip()
    phone = str(phone).strip()
    if not name or not phone.startswith("+") or not phone[1:].isdigit():
        return False
    with _lock:
        contacts = _load_contacts()
        contacts[name.lower()] = phone
        _save_contacts(contacts)
        return True


def get_contact(name):
    if not str(name).strip():
        return None
    contacts = _load_contacts()
    key = name.lower().strip()
    if key in contacts:
        return contacts[key]
    # fuzzy: find any contact whose name contains the query
    for k, v in contacts.items():
        if key in k or k in key:
            return v
    return None


def list_contacts():
    return _load_contacts()


def send_message(name_or_phone, message):
    """Send via pywhatkit — opens WhatsApp Web, sends instantly."""
    name_or_phone = str(name_or_phone).strip()
    message = str(message).strip()
    if not name_or_phone or not message:
        return {"ok": False, "error": "recipient and message are required"}
    phone = name_or_phone
    if not name_or_phone.startswith("+"):
        # Treat as contact name
        phone = get_contact(name_or_phone)
        if not phone:
            return {"ok": False, "error": f"No contact named {name_or_phone}"}

    try:
        import pywhatkit
    except ImportError:
        return {"ok": False, "error": "pywhatkit not installed"}

    try:
        # wait_time = seconds to wait before sending (browser load buffer)
        pywhatkit.sendwhatmsg_instantly(
            phone, message,
            wait_time=15,    # WhatsApp Web load buffer
            tab_close=True,
            close_time=4,
        )
        return {"ok": True, "phone": phone}
    except Exception as e:
        # Fallback: just open the chat
        try:
            url = f"https://web.whatsapp.com/send?phone={urllib.parse.quote(phone)}&text={urllib.parse.quote(message)}"
            webbrowser.open(url)
            return {"ok": True, "phone": phone, "note": "opened web — please press send"}
        except Exception as e2:
            return {"ok": False, "error": f"{e} / {e2}"}
