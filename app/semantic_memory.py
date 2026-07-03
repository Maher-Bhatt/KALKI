import os
import json
import math
from collections import Counter
import re

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
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception:
            pass

    def add_memory(self, text, tags=None):
        doc = {
            "id": len(self.documents),
            "text": text.strip(),
            "tags": tags or []
        }
        self.documents.append(doc)
        self._save()
        return doc["id"]

    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def search(self, query, top_k=3):
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # BM25-like scoring
        N = len(self.documents)
        df = Counter()
        for doc in self.documents:
            tokens = set(self._tokenize(doc["text"]))
            for t in tokens:
                df[t] += 1
        
        idf = {}
        for t in query_tokens:
            idf[t] = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
        
        avgdl = sum(len(self._tokenize(d["text"])) for d in self.documents) / N
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
