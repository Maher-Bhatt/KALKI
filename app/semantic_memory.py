import os
import json
import math
import urllib.request
import urllib.parse
from collections import Counter
import re
import threading
from datetime import datetime

import db
import secure_store

_lock = threading.RLock()


def get_embedding(text):
    """Retrieve embedding vector from OpenAI or Gemini."""
    text = text.strip()
    if not text:
        return None
    
    # Lazy import config to avoid import loops
    import config
    
    url = None
    headers = {"Content-Type": "application/json"}
    payload = {"input": text}
    
    openai_key = getattr(config, "OPENAI_API_KEY", "")
    gemini_key = getattr(config, "GEMINI_API_KEY", "")
    
    if openai_key and not openai_key.startswith("PASTE_"):
        url = "https://api.openai.com/v1/embeddings"
        headers["Authorization"] = f"Bearer {openai_key}"
        payload["model"] = "text-embedding-3-small"
    elif gemini_key and not gemini_key.startswith("PASTE_"):
        url = "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
        headers["Authorization"] = f"Bearer {gemini_key}"
        payload["model"] = "text-embedding-004"
        
    if not url:
        return None
        
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode("utf-8"))
            if "data" in res and len(res["data"]) > 0:
                return res["data"][0]["embedding"]
    except Exception:
        pass
    return None


def embeddings_configured():
    """True when vector search can really run. Otherwise search is keyword-only."""
    import config
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        key = getattr(config, name, "")
        if key and not key.startswith("PASTE_"):
            return True
    return False


def cosine_similarity(v1, v2):
    if not v1 or not v2: 
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0: 
        return 0.0
    return dot / (mag1 * mag2)


class SemanticMemory:
    """Long-term facts. Each memory is its own encrypted row, so one that can't be
    decrypted (say, after moving to another PC) simply stays stored, untouched,
    while everything else keeps working. Nothing rewrites the whole collection."""

    def __init__(self, path=None):
        # Only the old JSON file to import from. The data itself lives in SQLite.
        if path is None:
            path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "semantic_memory.json")
        self.path = path
        self._documents = None
        self._unreadable = 0

    @property
    def documents(self):
        with _lock:
            if self._documents is None:
                self.reload()
            return self._documents

    @documents.setter
    def documents(self, value):
        self._documents = value

    def reload(self):
        """Read everything from the store again, for example after a restore."""
        documents, unreadable = [], 0
        with db.connect() as conn:
            rows = conn.execute("SELECT id, payload FROM memories ORDER BY id").fetchall()
        for row in rows:
            try:
                doc = json.loads(secure_store.unprotect(row["payload"]))
                doc["id"] = row["id"]
                documents.append(doc)
            except (secure_store.UnprotectError, ValueError):
                unreadable += 1
        with _lock:
            self._documents = documents
            self._unreadable = unreadable

    def unreadable_count(self):
        self.documents  # make sure the store has been read
        return self._unreadable

    @staticmethod
    def _payload(doc):
        return secure_store.protect(json.dumps({k: v for k, v in doc.items() if k != "id"}))

    def _insert(self, doc, doc_id=None):
        with db.connect() as conn:
            cursor = conn.execute("INSERT INTO memories (id, payload) VALUES (?, ?)", (doc_id, self._payload(doc)))
            return int(cursor.lastrowid)

    def _persist(self, doc):
        with db.connect() as conn:
            conn.execute("UPDATE memories SET payload = ? WHERE id = ?", (self._payload(doc), doc["id"]))

    def _read_legacy(self):
        with open(self.path, "r", encoding="utf-8") as handle:
            content = handle.read().strip()
        if secure_store.is_protected(content):
            content = secure_store.unprotect(content)
        docs = json.loads(content) if content else []
        if not isinstance(docs, list):
            raise ValueError("expected a list")
        return docs

    def reimport_legacy(self):
        """Replace memories from the old file, after an old-format backup restore.
        Reads the file first: if it can't be read, this raises and nothing changes."""
        self._read_legacy()
        with _lock:
            with db.connect() as conn:
                conn.execute("DELETE FROM memories")
                conn.execute("DELETE FROM legacy_imports WHERE name = 'semantic_memory'")
            self.reload()
            return self.import_legacy()

    def import_legacy(self):
        """Import the old JSON file once. Returns None if there's nothing to do.
        The file is left unchanged, and an unreadable one is retried next start."""
        marker = "semantic_memory"
        if db.was_imported(marker) or not os.path.exists(self.path):
            return None
        try:
            docs = self._read_legacy()
        except (OSError, ValueError, secure_store.UnprotectError) as exc:
            return {"failed": str(exc)}
        imported = skipped = 0
        with _lock:
            known = {d["id"] for d in self.documents}
            for doc in docs:
                if not isinstance(doc, dict) or not doc.get("text"):
                    skipped += 1
                    continue
                wanted = doc.get("id") if isinstance(doc.get("id"), int) and doc.get("id") not in known else None
                known.add(self._insert(doc, wanted))
                imported += 1
            db.mark_imported(marker, imported, skipped)
            self.reload()
        return {"imported": imported}

    def add_memory(self, text, tags=None, importance=5, memory_type="fact", topic=None, metadata=None, **kwargs):
        """
        Add a fact/memory.
        memory_type: 'fact' (long-term), 'pinned' (always in prompt), 'project' (current workspace docs)
        """
        vector = get_embedding(text)
        with _lock:
            resolved_topic = topic or (tags[0] if tags and len(tags) > 0 else "General")
            resolved_tags = list(tags) if tags else ([resolved_topic] if resolved_topic else [])
            meta = dict(metadata) if isinstance(metadata, dict) else {}
            if "topic" not in meta:
                meta["topic"] = resolved_topic
                
            doc = {
                "text": text.strip(),
                "tags": resolved_tags,
                "importance": importance,  # scale 1-10
                "type": memory_type,
                "topic": resolved_topic,
                "metadata": meta,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_accessed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "vector": vector,
                **kwargs
            }
            doc["id"] = self._insert(doc)
            self.documents.append(doc)
            return doc["id"]

    def update_memory(self, doc_id, text, tags=None, importance=None, memory_type=None, topic=None, metadata=None):
        """Update an existing memory node."""
        try:
            target_id = int(doc_id)
        except (ValueError, TypeError):
            target_id = doc_id
        vector = get_embedding(text)
        with _lock:
            for doc in self.documents:
                if doc.get("id") == target_id:
                    doc["text"] = text.strip()
                    if tags is not None:
                        doc["tags"] = tags
                    if importance is not None:
                        doc["importance"] = importance
                    if memory_type is not None:
                        doc["type"] = memory_type
                    if topic is not None:
                        doc["topic"] = topic
                    if metadata is not None:
                        doc["metadata"] = metadata
                    # Re-vectorize if content changed
                    doc["vector"] = vector
                    self._persist(doc)
                    return True
            return False

    def delete_memory(self, doc_id):
        """Delete memory from storage."""
        try:
            target_id = int(doc_id)
        except (ValueError, TypeError):
            target_id = doc_id
        with _lock:
            remaining = [d for d in self.documents if d.get("id") != target_id]
            if len(remaining) == len(self.documents):
                return False
            with db.connect() as conn:
                conn.execute("DELETE FROM memories WHERE id = ?", (target_id,))
            self.documents = remaining
            return True

    def list_all(self):
        """Return all memories without vectors (for web serialization)."""
        with _lock:
            return [
                {
                    "id": d["id"],
                    "text": d["text"],
                    "tags": d.get("tags", []),
                    "importance": d.get("importance", 5),
                    "type": d.get("type", "fact"),
                    "topic": d.get("topic", (d.get("tags", ["General"])[0] if d.get("tags") else "General")),
                    "metadata": d.get("metadata", {}),
                    "created_at": d.get("created_at", "")
                }
                for d in self.documents
            ]

    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def search(self, query, top_k=5, memory_type=None):
        """Semantic search with type filtering and importance weighting."""
        q_vec = get_embedding(query)  # a network call: don't hold the lock for it
        with _lock:
            docs = self.documents
            if memory_type:
                docs = [d for d in docs if d.get("type") == memory_type]
            
            # Pinned memories are always included first, bypassing score check
            pinned = [d for d in docs if d.get("type") == "pinned"]
            
            if not docs:
                return pinned

            # Update last accessed for matches
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            scores = []
            
            if q_vec:
                # Vector Search
                for doc in docs:
                    d_vec = doc.get("vector")
                    if d_vec:
                        sim = cosine_similarity(q_vec, d_vec)
                        # Scale score by importance: higher importance gives higher weight
                        importance_weight = 1.0 + (doc.get("importance", 5) - 5) * 0.05
                        score = sim * importance_weight
                        scores.append((score, doc))
                
                scores.sort(key=lambda x: x[0], reverse=True)
                results = []
                for score, doc in scores[:top_k]:
                    if score > 0.4:
                        doc["last_accessed"] = now_str
                        self._persist(doc)
                        results.append(doc)
                
                # Merge pinned & semantic results
                merged = {d["id"]: d for d in pinned + results}.values()
                return list(merged)

            # BM25 text fallback
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return pinned

            N = len(docs)
            df = Counter()
            for doc in docs:
                tokens = set(self._tokenize(doc["text"]))
                for t in tokens:
                    df[t] += 1
            
            idf = {}
            for t in query_tokens:
                idf[t] = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            
            avgdl = sum(len(self._tokenize(d["text"])) for d in docs) / N if N else 1
            k1 = 1.5
            b = 0.75

            for doc in docs:
                tokens = self._tokenize(doc["text"])
                dl = len(tokens)
                tf = Counter(tokens)
                score = 0
                for t in query_tokens:
                    if t in tf:
                        term_freq = tf[t]
                        numerator = term_freq * (k1 + 1)
                        denominator = term_freq + k1 * (1 - b + b * dl / avgdl)
                        score += idf[t] * (numerator / denominator)
                
                importance_weight = 1.0 + (doc.get("importance", 5) - 5) * 0.05
                score *= importance_weight
                scores.append((score, doc))

            scores.sort(key=lambda x: x[0], reverse=True)
            results = [doc for score, doc in scores[:top_k] if score > 0]
            
            for r in results:
                r["last_accessed"] = now_str
                self._persist(r)
            
            merged = {d["id"]: d for d in pinned + results}.values()
            return list(merged)


# Global instance
memory = SemanticMemory()
