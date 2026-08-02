import os
import json
import base64
import threading

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

_db = None


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypt(plaintext: str, passphrase: str) -> dict:
    """Returns {"salt": b64_salt, "ciphertext": token} - both go to Firestore.
    The salt is not secret; portability requires it travel with the data."""
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(plaintext.encode("utf-8"))
    return {"salt": base64.b64encode(salt).decode(), "ciphertext": token.decode()}


def _decrypt(payload: dict, passphrase: str) -> str:
    salt = base64.b64decode(payload["salt"])
    key = _derive_key(passphrase, salt)
    return Fernet(key).decrypt(payload["ciphertext"].encode("utf-8")).decode("utf-8")


def init_cloud_sync(config):
    global _db
    if not FIREBASE_AVAILABLE:
        return
    cred_path = getattr(config, "FIREBASE_CREDENTIALS_PATH", "data/firebase_credentials.json")
    if os.path.exists(cred_path):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            _db = firestore.client()
            print("[CLOUD SYNC] Firebase initialized successfully.")
        except Exception as e:
            print(f"[CLOUD SYNC] Failed to init Firebase: {e}")


def sync_memory_to_cloud(user_id, local_memory_path, passphrase):
    if not _db or not passphrase:
        return

    def _sync():
        try:
            with open(local_memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            payload = _encrypt(json.dumps(data), passphrase)
            doc_ref = _db.collection("users").document(user_id).collection("data").document("memory")
            doc_ref.set({"facts": payload})
        except Exception as e:
            print(f"[CLOUD SYNC] Memory push failed: {e}")

    threading.Thread(target=_sync, daemon=True).start()


def sync_history_to_cloud(user_id, local_history_path, passphrase):
    if not _db or not passphrase:
        return

    def _sync():
        try:
            with open(local_history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            payload = _encrypt(json.dumps(data[-50:]), passphrase)
            doc_ref = _db.collection("users").document(user_id).collection("data").document("history")
            doc_ref.set({"messages": payload})
        except Exception as e:
            print(f"[CLOUD SYNC] History push failed: {e}")

    threading.Thread(target=_sync, daemon=True).start()


def restore_memory_from_cloud(user_id, local_memory_path, passphrase):
    if not _db:
        return False
    try:
        doc = _db.collection("users").document(user_id).collection("data").document("memory").get()
        if doc.exists:
            payload = doc.to_dict().get("facts")
            if payload:
                data = json.loads(_decrypt(payload, passphrase))
                with open(local_memory_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                return True
    except Exception as e:
        print(f"[CLOUD SYNC] Memory restore failed: {e}")
    return False


def restore_history_from_cloud(user_id, local_history_path, passphrase):
    if not _db:
        return False
    try:
        doc = _db.collection("users").document(user_id).collection("data").document("history").get()
        if doc.exists:
            payload = doc.to_dict().get("messages")
            if payload:
                data = json.loads(_decrypt(payload, passphrase))
                with open(local_history_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                return True
    except Exception as e:
        print(f"[CLOUD SYNC] History restore failed: {e}")
    return False
