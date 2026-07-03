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
    Push local memory array to Firestore document asynchronously.
    """
    if not _db:
        return
        
    def _sync():
        try:
            with open(local_memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            doc_ref = _db.collection('users').document(user_id).collection('data').document('memory')
            doc_ref.set({"facts": data})
        except Exception as e:
            print(f"[CLOUD SYNC] Memory push failed: {e}")
            
    threading.Thread(target=_sync, daemon=True).start()

def sync_history_to_cloud(user_id, local_history_path):
    """
    Push local chat history array to Firestore asynchronously.
    """
    if not _db:
        return
        
    def _sync():
        try:
            with open(local_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Truncate to last 50 for cloud size limits
            doc_ref = _db.collection('users').document(user_id).collection('data').document('history')
            doc_ref.set({"messages": data[-50:]})
        except Exception as e:
            print(f"[CLOUD SYNC] History push failed: {e}")
            
    threading.Thread(target=_sync, daemon=True).start()
