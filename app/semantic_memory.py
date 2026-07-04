import os
import json
import math
import urllib.request
from collections import Counter
import re

import config

def get_embedding(text):
    text = text.strip()
    if not text:
        return None
    
    url = None
    headers = {"Content-Type": "application/json"}
    payload = {"input": text}
    
    if getattr(config, "OPENAI_API_KEY", ""):
        url = "https://api.openai.com/v1/embeddings"
        headers["Authorization"] = f"Bearer {config.OPENAI_API_KEY}"
        payload["model"] = "text-embedding-3-small"
    elif getattr(config, "GEMINI_API_KEY", ""):
        url = "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
        headers["Authorization"] = f"Bearer {config.GEMINI_API_KEY}"
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
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            if "data" in res and len(res["data"]) > 0:
                return res["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
    return None

def cosine_similarity(v1, v2):
    if not v1 or not v2: return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0: return 0.0
    return dot / (mag1 * mag2)

class SemanticMemory:
    def __init__(self, path="data/semantic_memory.json"):
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

    def add_memory(self, text, tags=None):
        vector = get_embedding(text)
        doc = {
            "id": len(self.documents),
            "text": text.strip(),
            "tags": tags or [],
            "vector": vector
        }
        self.documents.append(doc)
        self._save()
        return doc["id"]

    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def search(self, query, top_k=3):
        if not self.documents:
            return []
            
        q_vec = get_embedding(query)
        
        if q_vec:
            # Vector search
            scores = []
            for doc in self.documents:
                d_vec = doc.get("vector")
                if d_vec:
                    score = cosine_similarity(q_vec, d_vec)
                    scores.append((score, doc))
            if scores:
                scores.sort(key=lambda x: x[0], reverse=True)
                return [doc for score, doc in scores[:top_k] if score > 0.4]

        # Fallback BM25 search
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        N = len(self.documents)
        df = Counter()
        for doc in self.documents:
            tokens = set(self._tokenize(doc["text"]))
            for t in tokens:
                df[t] += 1
        
        idf = {}
        for t in query_tokens:
            idf[t] = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
        
        avgdl = sum(len(self._tokenize(d["text"])) for d in self.documents) / N if N else 1
        k1 = 1.5
        b = 0.75

        scores = []
        for doc in self.documents:
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
            scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scores[:top_k] if score > 0]

# Global instance
memory = SemanticMemory()
