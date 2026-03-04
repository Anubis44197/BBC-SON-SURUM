import os
import json
import time
import hashlib
from pathlib import Path

# Pure Python SimHash Implementation (Zero-Dependency)
# No external libraries like FAISS required


def compute_simhash(text: str) -> int:
    """
    Saf Matematiksel Vektorleme (SimHash 128-bit)
    Metni 128 boyutlu bir parmak izine donusturur.
    Dependencies: None (Standard Python only)
    """
    features = {}
    # 1. Basit Tokenizasyon (Kelime bazli)
    words = text.lower().split()
    for w in words:
        features[w] = features.get(w, 0) + 1
        
    v = [0] * 128
    
    for word, weight in features.items():
        # Kelimenin 128-bit hash'ini al (SHA-256'dan 128-bit al)
        h = int(hashlib.sha256(word.encode('utf-8')).hexdigest()[:32], 16)
        for i in range(128):
            bit_mask = 1 << i
            if h & bit_mask:
                v[i] += weight
            else:
                v[i] -= weight
                
    # Fingerprint olustur
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
    Iki metin arasindaki benzerlik yuzdesini dondurur (0-100)
    """
    dist = hamming_distance(hash1, hash2)
    # 128 bit uzerinden normalize et
    return max(0, 100 - (dist / 128.0 * 100))


class HMPUIndexer:
    """
    BBC Pure Math Indexer (v3.0 - Zero Dependency)
    Uses 128-bit SimHash + Hamming Distance
    No external dependencies like FAISS required
    """
    def __init__(self, index_dir="02_Indices"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db = []  # List of (hash_int, metadata_dict)
        self.is_trained = True  # Pure Math no need training
        self.index_type = "PURE_BINARY_128"
        self.cache = {}  # Performance cache for frequent searches
        
    def add_document(self, doc_id: str, content: str, metadata: dict = None):
        """Add a document to the index with SimHash fingerprint"""
        hash_val = compute_simhash(content)
        entry = {
            "id": doc_id,
            "hash": hash_val,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.vector_db.append(entry)
        # Invalidate cache when new data added
        self.cache.clear()
        
    def search_similar(self, query_content: str, top_k: int = 5, threshold: float = 70.0):
        """
        Find similar documents using HYBRID Vector Memory.
        Combines SimHash (Structural) with Keyword Density (Semantic Hint).
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
            simhash_score = similarity_score(query_hash, entry["hash"])
            
            # 2. Semantic Hint (Keyword Overlap)
            doc_words = set(entry.get("metadata", {}).get("content_summary", "").lower().split())
            if not doc_words and "id" in entry: # Fallback if summary missing
                doc_words = set(entry["id"].lower().replace("_", " ").split())
                
            overlap = query_words.intersection(doc_words)
            keyword_score = (len(overlap) / len(query_words) * 100) if query_words else 0
            
            # 3. Hybrid Calculation (60% SimHash, 40% Keywords)
            hybrid_score = (simhash_score * 0.6) + (keyword_score * 0.4)
            
            if hybrid_score >= threshold:
                results.append({
                    "id": entry["id"],
                    "similarity": hybrid_score,
                    "simhash_score": simhash_score,
                    "keyword_score": keyword_score,
                    "metadata": entry["metadata"]
                })
        
        # Sort by hybrid similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]
        
        self.cache[cache_key] = results
        return results
        
    def search(self, query_hash: int, top_k: int = 5):
        """Legacy search method for hash-based lookup"""
        return self.search_similar_by_hash(query_hash, top_k)
        
    def search_similar_by_hash(self, query_hash: int, top_k: int = 5):
        """Search by pre-computed hash"""
        results = []
        for entry in self.vector_db:
            similarity = similarity_score(query_hash, entry["hash"])
            results.append({
                "id": entry["id"],
                "similarity": similarity,
                "metadata": entry["metadata"]
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
        
    def finalize_and_save(self, prefix: str, total_count: int = None):
        """Save index to disk"""
        base_path = self.index_dir / f"{prefix}_index"
        
        data = {
            "index_type": self.index_type,
            "count": len(self.vector_db),
            "timestamp": time.time(),
            "vectors": self.vector_db
        }
        
        with open(f"{base_path}.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"[FINALIZE] Index saved to {base_path}.json")
        return str(base_path)
        
    def load_index(self, filepath: str):
        """Load index from disk"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.vector_db = data.get("vectors", [])
            self.index_type = data.get("index_type", "PURE_BINARY_128")
            print(f"[LOAD] Loaded {len(self.vector_db)} vectors from {filepath}")
            
    def get_stats(self):
        """Return index statistics"""
        return {
            "total_documents": len(self.vector_db),
            "index_type": self.index_type,
            "cache_size": len(self.cache),
            "index_dir": str(self.index_dir)
        }


# Performance test
if __name__ == "__main__":
    import time
    
    indexer = HMPUIndexer()
    
    # Add test documents
    test_docs = [
        ("doc1", "print hello world python code"),
        ("doc2", "print hello python programming"),
        ("doc3", "def function calculate sum math"),
        ("doc4", "class MyClass object oriented"),
        ("doc5", "print hello world java code"),
    ]
    
    for doc_id, content in test_docs:
        indexer.add_document(doc_id, content)
    
    # Search test
    query = "print hello python"
    start = time.time()
    results = indexer.search_similar(query, top_k=3)
    elapsed = (time.time() - start) * 1000  # Convert to ms
    
    print(f"\n[TEST] Query: '{query}'")
    print(f"[TEST] Search time: {elapsed:.2f} ms")
    print("[TEST] Top results:")
    for r in results:
        print(f"  - {r['id']}: {r['similarity']:.1f}%")
        
    # Stats
    print(f"\n[Index Stats]")
    print(json.dumps(indexer.get_stats(), indent=2))
