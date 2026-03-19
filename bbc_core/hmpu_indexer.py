import json
import time
import hashlib
import os
from pathlib import Path
from .bbc_scalar import BBCScalar, STABLE, WEAK, SLEEPING, DEGENERATE, BBCEncoder


# ================================
# Top-level helper functions
# ================================

def compute_simhash(text: str) -> int:
    """
    Pure Math SimHash (128-bit) — SHA-256 tabanli.
    Metni 128 boyutlu bir parmak izine donusturur.
    Dependencies: None (Standard Python only)
    """
    features = {}
    words = text.lower().split()
    for w in words:
        features[w] = features.get(w, 0) + 1

    v = [0] * 128

    for word, weight in features.items():
        h = int(hashlib.sha256(word.encode('utf-8')).hexdigest()[:32], 16)
        for i in range(128):
            bit_mask = 1 << i
            if h & bit_mask:
                v[i] += weight
            else:
                v[i] -= weight

    fingerprint = 0
    for i in range(128):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """
    Iki SimHash arasindaki Hamming mesafesini hesaplar.
    Dusuk deger = Yuksek benzerlik
    """
    xor = hash1 ^ hash2
    distance = 0
    while xor:
        distance += xor & 1
        xor >>= 1
    return distance


def similarity_score(hash1: int, hash2: int) -> float:
    """
    Iki metin arasindaki benzerlik yuzdesini returns (0-100)
    """
    dist = hamming_distance(hash1, hash2)
    return max(0, 100 - (dist / 128.0 * 100))


# ================================
# Main Indexer Class
# ================================

class HMPUIndexer:
    """
    BBC PURE MATH INDEXER (v3.1 — Unified)
    Dependencies: None (Standard Python only)
    Logic: 128-bit SimHash (SHA-256) + Hamming Distance + Hybrid Search + BBCScalar Weighted
    
    Birlestirilmis ozellikler:
    - BBCScalar-weighted indexleme (Aura vektoru entegrasyonu)
    - Hybrid Search (SimHash %60 + Keyword %40)
    - Cache destegi
    - load/save index
    """
    def __init__(self, index_dir="02_Indices"):
        if isinstance(index_dir, str):
            index_dir = Path(index_dir)
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db = []  # List of dict entries
        self.is_trained = True  # Pure Math — no training needed
        self.index_type = "PURE_BINARY_128"
        self.cache = {}  # Performance cache for frequent searches

    # ================================
    # BBC-Weighted SimHash (Aura Entegrasyonu)
    # ================================

    def compute_bbc_simhash(self, text: str, aura_vector: list = None) -> BBCScalar:
        """
        BBC-Weighted SimHash.
        Returns a BBCScalar representing the confidence/quality score.
        The actual SimHash integer is stored in metadata["simhash"].
        State, aura vector'un durumuna bagli.
        """
        score = 1.0
        state = STABLE
        features = {}
        words = text.lower().split()
        for w in words:
            features[w] = features.get(w, 0) + 1

        v = [0.0] * 128
        S, C, P = 1.0, 0.0, 0.0
        S_state = STABLE

        if aura_vector:
            try:
                S = float(aura_vector[0]) if len(aura_vector) > 0 else 1.0
                C = float(aura_vector[1]) if len(aura_vector) > 1 else 0.0
                P = float(aura_vector[2]) if len(aura_vector) > 2 else 0.0
                if hasattr(aura_vector[0], 'state'):
                    S_state = aura_vector[0].state
            except Exception:
                pass

        total_weight = 0.0
        for word, freq in features.items():
            h = int(hashlib.sha256(word.encode('utf-8')).hexdigest()[:32], 16)
            weight = freq * 1.0
            if len(word) > 5:
                weight *= (1.0 + (S * 0.2))
            if len(word) < 4:
                weight *= (1.0 - (C * 0.3))
            total_weight += weight
            for i in range(128):
                bit_mask = 1 << i
                if h & bit_mask:
                    v[i] += weight
                else:
                    v[i] -= weight

        fingerprint = 0
        for i in range(128):
            if v[i] > 0:
                fingerprint |= (1 << i)

        # Heuristic score calculation
        if S_state == DEGENERATE:
            score = 0.0
            state = DEGENERATE
        elif len(words) > 0:
            avg_weight = total_weight / len(words)
            score = min(avg_weight, 2.0) / 2.0
            if avg_weight < 0.5:
                state = WEAK
        else:
            score = 0.0
            state = SLEEPING

        return BBCScalar(score, state, metadata={"simhash": str(fingerprint), "reason": "calculated", "decay": 0.0})

    # ================================
    # Document Adding (iki API — backward compat)
    # ================================

    def add_to_index(self, content: str, meta: dict, aura_vector: list = None):
        """
        Legacy API: Vectorize text and store with metadata.
        BBCScalar-weighted indexleme destekli.
        """
        try:
            if aura_vector:
                bbc_scalar = self.compute_bbc_simhash(content, aura_vector)
                vector_int = int(bbc_scalar.metadata.get("simhash", "0"))
                meta["method"] = "bbc_weighted"
                meta["confidence"] = bbc_scalar.value
                meta["state"] = bbc_scalar.state
                meta["simhash"] = bbc_scalar.metadata.get("simhash", "0")
            else:
                vector_int = compute_simhash(content)
                meta["method"] = "classic"

            self.vector_db.append({
                "id": meta.get("path", meta.get("id", f"doc_{len(self.vector_db)}")),
                "hash": vector_int,
                "v": str(vector_int),
                "metadata": meta,
                "timestamp": time.time()
            })
            # Invalidate cache when new data added
            self.cache.clear()
            return True
        except Exception as e:
            print(f"[INDEXER ERROR] {e}")
            return False

    def add_document(self, doc_id: str, content: str, metadata: dict = None):
        """
        New API: Add a document to the index with SimHash fingerprint.
        """
        hash_val = compute_simhash(content)
        entry = {
            "id": doc_id,
            "hash": hash_val,
            "v": str(hash_val),
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.vector_db.append(entry)
        self.cache.clear()

    # ================================
    # Search (Hybrid + Legacy)
    # ================================

    def search_similar(self, query_content: str, top_k: int = 5, threshold: float = 70.0):
        """
        Hybrid Vector Memory Search.
        SimHash (Structural %60) + Keyword Density (Semantic Hint %40)
        """
        query_hash = compute_simhash(query_content)
        query_words = set(query_content.lower().split())

        # Check cache first
        cache_key = (query_hash, hash(tuple(sorted(list(query_words)))), top_k, threshold)
        if cache_key in self.cache:
            return self.cache[cache_key]

        results = []
        for entry in self.vector_db:
            # 1. Structural Similarity (SimHash)
            doc_hash = entry.get("hash", int(entry.get("v", "0")))
            simhash_score = similarity_score(query_hash, doc_hash)

            # 2. Semantic Hint (Keyword Overlap)
            doc_words = set(entry.get("metadata", {}).get("content_summary", "").lower().split())
            if not doc_words and "id" in entry:
                doc_words = set(entry["id"].lower().replace("_", " ").split())

            overlap = query_words.intersection(doc_words)
            keyword_score = (len(overlap) / len(query_words) * 100) if query_words else 0

            # 3. Hybrid Calculation (60% SimHash, 40% Keywords)
            hybrid_score = (simhash_score * 0.6) + (keyword_score * 0.4)

            if hybrid_score >= threshold:
                results.append({
                    "id": entry.get("id", "unknown"),
                    "similarity": hybrid_score,
                    "simhash_score": simhash_score,
                    "keyword_score": keyword_score,
                    "metadata": entry.get("metadata", {})
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]

        self.cache[cache_key] = results
        return results

    def search(self, query, k=3):
        """
        Legacy search: accepts either a query string or pre-computed hash integer.
        """
        if isinstance(query, str):
            return self.search_similar(query, top_k=k)

        # Hash-based search (backward compat)
        q_vec = query
        results = []
        for item in self.vector_db:
            doc_vec = item.get("hash", int(item.get("v", "0")))
            dist = bin(q_vec ^ doc_vec).count('1')
            results.append((dist, item.get("metadata", item.get("m", {}))))

        results.sort(key=lambda x: x[0])
        return results[:k]

    # ================================
    # Persistence
    # ================================

    def finalize_and_save(self, prefix, total_count=0):
        """Save index database to disk as single JSON file."""
        base_path = self.index_dir / f"{prefix}_bbc_brain.json"

        # Serialize: hash alanini string'e cevir (buyuk int JSON uyumu)
        serializable_db = []
        for entry in self.vector_db:
            entry_copy = dict(entry)
            entry_copy["v"] = str(entry_copy.get("hash", entry_copy.get("v", "0")))
            if "hash" in entry_copy:
                del entry_copy["hash"]
            serializable_db.append(entry_copy)

        data = {
            "type": self.index_type,
            "created": time.time(),
            "count": len(self.vector_db),
            "db": serializable_db
        }

        with open(str(base_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, cls=BBCEncoder)

        if os.environ.get("BBC_VERBOSE_INDEX", "0").strip().lower() in {"1", "true", "yes", "on"}:
            print(f"[FINALIZE] Pure Math Index saved to {base_path} ({len(self.vector_db)} vectors)")
        return str(base_path)

    def load_index(self, filepath: str):
        """Load index from disk."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_db = data.get("db", data.get("vectors", []))
            self.vector_db = []
            for entry in raw_db:
                # Normalize: ensure hash field exists as int
                if "hash" not in entry and "v" in entry:
                    entry["hash"] = int(entry["v"])
                self.vector_db.append(entry)
            self.index_type = data.get("type", data.get("index_type", "PURE_BINARY_128"))
            if os.environ.get("BBC_VERBOSE_INDEX", "0").strip().lower() in {"1", "true", "yes", "on"}:
                print(f"[LOAD] Loaded {len(self.vector_db)} vectors from {filepath}")

    def get_stats(self):
        """Return index statistics."""
        return {
            "total_documents": len(self.vector_db),
            "index_type": self.index_type,
            "cache_size": len(self.cache),
            "index_dir": str(self.index_dir)
        }