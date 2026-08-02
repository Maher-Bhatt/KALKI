import os
import json
import math
import urllib.request
import urllib.parse
from collections import Counter
import re
import threading
from datetime import datetime

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
    def __init__(self, path=None):
        if path is None:
            # Place memory in APPDATA path
            path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "semantic_memory.json")
        self.path = path
        self.documents = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception:
            pass

    def add_memory(self, text, tags=None, importance=5, memory_type="fact"):
        """
        Add a fact/memory.
        memory_type: 'fact' (long-term), 'pinned' (always in prompt), 'project' (current workspace docs)
        """
        vector = get_embedding(text)
        with _lock:
            doc_id = len(self.documents)
            # Find a unique ID
            ids = [d.get("id", 0) for d in self.documents]
            if ids:
                doc_id = max(ids) + 1
                
            doc = {
                "id": doc_id,
                "text": text.strip(),
                "tags": tags or [],
                "importance": importance,  # scale 1-10
                "type": memory_type,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_accessed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "vector": vector
            }
            self.documents.append(doc)
            self._save()
            return doc["id"]

    def update_memory(self, doc_id, text, tags=None, importance=None, memory_type=None):
        """Update an existing memory node."""
        try:
            target_id = int(doc_id)
        except (ValueError, TypeError):
            target_id = doc_id
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
                    # Re-vectorize if content changed
                    doc["vector"] = get_embedding(text)
                    self._save()
                    return True
            return False

    def delete_memory(self, doc_id):
        """Delete memory from storage."""
        try:
            target_id = int(doc_id)
        except (ValueError, TypeError):
            target_id = doc_id
        with _lock:
            initial_len = len(self.documents)
            self.documents = [d for d in self.documents if d.get("id") != target_id]
            if len(self.documents) < initial_len:
                self._save()
                return True
            return False

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
                    "created_at": d.get("created_at", "")
                }
                for d in self.documents
            ]

    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def search(self, query, top_k=5, memory_type=None):
        """Semantic search with type filtering and importance weighting."""
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

            q_vec = get_embedding(query)
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
                        results.append(doc)
                
                # Merge pinned & semantic results
                merged = {d["id"]: d for d in pinned + results}.values()
                self._save()
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
            self._save()
            
            merged = {d["id"]: d for d in pinned + results}.values()
            return list(merged)


# Global instance
memory = SemanticMemory()
