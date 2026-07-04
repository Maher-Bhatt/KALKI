import os
import json
import threading

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

_db = None

def init_cloud_sync(config):
    """
    Initialize Firebase connection if credentials exist.
    Looks for data/google_credentials.json (or similar path in config).
    """
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

def sync_memory_to_cloud(user_id, local_memory_path):
    """
    Push local memory array to Firestore document asynchronously with encryption.
    """
    if not _db:
        return
        
    def _sync():
        try:
            with open(local_memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            import vault
            encrypted_data = vault._enc(json.dumps(data))
                
            doc_ref = _db.collection('users').document(user_id).collection('data').document('memory')
            doc_ref.set({"facts": encrypted_data})
        except Exception as e:
            print(f"[CLOUD SYNC] Memory push failed: {e}")
            
    threading.Thread(target=_sync, daemon=True).start()

def sync_history_to_cloud(user_id, local_history_path):
    """
    Push local chat history array to Firestore asynchronously with encryption.
    """
    if not _db:
        return
        
    def _sync():
        try:
            with open(local_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            import vault
            encrypted_data = vault._enc(json.dumps(data[-50:]))
                
            doc_ref = _db.collection('users').document(user_id).collection('data').document('history')
            doc_ref.set({"messages": encrypted_data})
        except Exception as e:
            print(f"[CLOUD SYNC] History push failed: {e}")
            
    threading.Thread(target=_sync, daemon=True).start()

def restore_memory_from_cloud(user_id, local_memory_path):
    if not _db:
        return False
    try:
        doc = _db.collection('users').document(user_id).collection('data').document('memory').get()
        if doc.exists:
            import vault
            enc = doc.to_dict().get("facts", "")
            if enc:
                dec = vault._dec(enc)
                if dec:
                    data = json.loads(dec)
                    with open(local_memory_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    return True
    except Exception as e:
        print(f"[CLOUD SYNC] Memory restore failed: {e}")
    return False

def restore_history_from_cloud(user_id, local_history_path):
    if not _db:
        return False
    try:
        doc = _db.collection('users').document(user_id).collection('data').document('history').get()
        if doc.exists:
            import vault
            enc = doc.to_dict().get("messages", "")
            if enc:
                dec = vault._dec(enc)
                if dec:
                    data = json.loads(dec)
                    with open(local_history_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    return True
    except Exception as e:
        print(f"[CLOUD SYNC] History restore failed: {e}")
    return False
