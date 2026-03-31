"""
BBC Symbol Similarity Engine
Adapts Harrier's contrastive learning to BBC Mathematics

Uses Focus Projection (sqrt-free cosine similarity) with BBCScalar arithmetic
NO neural networks - pure BBC mathematical similarity computation
"""

from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from collections import defaultdict
import math

from .bbc_scalar import BBCScalar, bbc_data_ingestion, STABLE, WEAK, DEGENERATE
from .hmpu_core import HMPU_Governor
from .symbol_state_encoder import SymbolStateEncoder, SymbolSignature


@dataclass
class SimilarityResult:
    """Result of a similarity comparison between two symbols"""
    source_name: str
    target_name: str
    similarity_score: float  # 0.0 - 1.0
    confidence: BBCScalar     # State-aware confidence
    match_details: Dict[str, Any]


class BBCSymbolSimilarity:
    """
    Computes symbol similarity using BBC's Focus Projection algorithm.
    
    This is BBC's adaptation of Harrier's contrastive learning:
    - NO neural network embeddings
    - BBCScalar [S, C, P] vectors instead of float embeddings
    - sqrt-free cosine similarity (cos²(θ) > threshold² comparison)
    - State-aware matching with confidence propagation
    
    Key features:
    - Symbol indexing with BBC mathematical signatures
    - Similarity search via Focus Projection
    - Duplicate code detection
    - Token-aware reranking for context optimization
    """
    
    def __init__(self, governor: Optional[HMPU_Governor] = None):
        self.governor = governor or HMPU_Governor()
        self.encoder = SymbolStateEncoder(self.governor)
        self.symbol_vectors: Dict[str, List[BBCScalar]] = {}  # name -> [S, C, P]
        self.symbol_metadata: Dict[str, Dict[str, Any]] = {}
        self.indexed_count = 0
    
    def index_symbol(self, symbol: Dict[str, Any]) -> SymbolSignature:
        """
        Index a symbol as BBCScalar [S, C, P] vector.
        
        Args:
            symbol: Symbol dictionary with name, type, code, etc.
            
        Returns:
            SymbolSignature with S, C, P BBCScalar components
        """
        # Encode symbol to BBCScalar vector
        signature = self.encoder.encode_symbol(symbol)
        
        # Store vector
        self.symbol_vectors[signature.name] = signature.to_vector()
        self.symbol_metadata[signature.name] = signature.metadata
        self.indexed_count += 1
        
        return signature
    
    def index_symbols_batch(self, symbols: List[Dict[str, Any]]) -> List[SymbolSignature]:
        """Index multiple symbols efficiently"""
        signatures = []
        for symbol in symbols:
            try:
                sig = self.index_symbol(symbol)
                signatures.append(sig)
            except Exception as e:
                # Skip problematic symbols
                if hasattr(self.governor, '_log'):
                    self.governor._log(f"Failed to index symbol {symbol.get('name', 'unknown')}: {e}")
        return signatures
    
    def find_similar(self, query_symbol: Dict[str, Any], 
                     threshold: float = 0.80,
                     top_k: int = 10) -> List[SimilarityResult]:
        """
        Find symbols similar to query using Focus Projection.
        
        Uses sqrt-free cosine similarity:
        - cos²(θ) = (q·t)² / (|q|²|t|²)
        - Compare: cos²(θ) > threshold² (no sqrt needed!)
        
        Args:
            query_symbol: Query symbol dictionary
            threshold: Minimum similarity threshold (0.0-1.0)
            top_k: Maximum number of results
            
        Returns:
            List of SimilarityResult sorted by score
        """
        # Encode query symbol
        query_sig = self.encoder.encode_symbol(query_symbol)
        q_vector = query_sig.to_vector()
        
        # Compute similarities with all indexed symbols
        results = []
        
        for target_name, t_vector in self.symbol_vectors.items():
            # Skip self-match
            if target_name == query_sig.name:
                continue
            
            # Compute sqrt-free cosine similarity
            similarity, confidence = self._compute_similarity(q_vector, t_vector, threshold)
            
            if similarity >= threshold:
                result = SimilarityResult(
                    source_name=query_sig.name,
                    target_name=target_name,
                    similarity_score=similarity,
                    confidence=confidence,
                    match_details={
                        'source_type': query_sig.metadata.get('type'),
                        'target_type': self.symbol_metadata.get(target_name, {}).get('type'),
                        's_component_match': self._component_similarity(
                            q_vector[0], t_vector[0]
                        ),
                        'c_component_match': self._component_similarity(
                            q_vector[1], t_vector[1]
                        ),
                        'p_component_match': self._component_similarity(
                            q_vector[2], t_vector[2]
                        )
                    }
                )
                results.append(result)
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results[:top_k]
    
    def find_duplicates(self, threshold: float = 0.90) -> List[Tuple[str, str, float]]:
        """
        Find potentially duplicate/similar code symbols.
        
        Args:
            threshold: Similarity threshold for duplicate detection
            
        Returns:
            List of (symbol1, symbol2, similarity) tuples
        """
        duplicates = []
        symbol_names = list(self.symbol_vectors.keys())
        
        # Compare all pairs (O(n²) - acceptable for project-scale)
        for i, name1 in enumerate(symbol_names):
            for name2 in symbol_names[i+1:]:
                v1 = self.symbol_vectors[name1]
                v2 = self.symbol_vectors[name2]
                
                similarity, _ = self._compute_similarity(v1, v2, threshold)
                
                if similarity >= threshold:
                    duplicates.append((name1, name2, similarity))
        
        # Sort by similarity
        duplicates.sort(key=lambda x: x[2], reverse=True)
        return duplicates
    
    def rerank_for_query(self, query: str, 
                         symbols: List[Dict[str, Any]],
                         max_tokens: int = 100000) -> List[Dict[str, Any]]:
        """
        Rerank symbols for a natural language query.
        
        This adapts Harrier's retrieval to BBC by:
        1. Converting query to pseudo-symbol [S, C, P] vector
        2. Using Focus Projection for similarity
        3. Selecting best symbols within token budget
        
        Args:
            query: Natural language query (e.g., "user authentication")
            symbols: List of symbol dictionaries
            max_tokens: Maximum tokens for context
            
        Returns:
            Reranked list of symbols within token budget
        """
        # Create pseudo-symbol from query for encoding
        query_symbol = {
            'name': f'__query__{hash(query) & 0xFFFFFFFF}',
            'type': 'query',
            'code': query,
            'docstring': query,
            'references': []
        }
        
        # Index query symbol temporarily
        query_sig = self.encoder.encode_symbol(query_symbol)
        q_vector = query_sig.to_vector()
        
        # Score all symbols
        scored_symbols = []
        total_tokens = 0
        
        for symbol in symbols:
            symbol_name = symbol.get('name', '')
            
            # Get or compute symbol vector
            if symbol_name in self.symbol_vectors:
                s_vector = self.symbol_vectors[symbol_name]
            else:
                # Index on-the-fly
                sig = self.encoder.encode_symbol(symbol)
                s_vector = sig.to_vector()
                self.symbol_vectors[symbol_name] = s_vector
            
            # Compute similarity
            similarity, confidence = self._compute_similarity(q_vector, s_vector, 0.0)
            
            # Boost score based on metadata
            boosted_score = self._boost_score(symbol, similarity)
            
            # Estimate token count
            code = symbol.get('code', '')
            estimated_tokens = len(code.split()) * 1.3  # Rough estimate
            
            scored_symbols.append({
                'symbol': symbol,
                'score': boosted_score,
                'confidence': confidence,
                'tokens': estimated_tokens
            })
        
        # Sort by score
        scored_symbols.sort(key=lambda x: x['score'], reverse=True)
        
        # Select within token budget (greedy selection)
        selected = []
        for item in scored_symbols:
            if total_tokens + item['tokens'] <= max_tokens:
                selected.append(item['symbol'])
                total_tokens += item['tokens']
            else:
                break
        
        return selected
    
    def _compute_similarity(self, 
                           q_vector: List[BBCScalar], 
                           t_vector: List[BBCScalar],
                           threshold: float) -> Tuple[float, BBCScalar]:
        """
        Compute sqrt-free cosine similarity between two BBCScalar vectors.
        
        Algorithm (Focus Projection adaptation):
        1. dot = Σ(q[i] * t[i]) for i in [S, C, P]
        2. q_norm_sq = Σ(q[i]²)
        3. t_norm_sq = Σ(t[i]²)
        4. cos²(θ) = dot² / (q_norm_sq * t_norm_sq)
        5. Compare: cos²(θ) > threshold² (sqrt-free!)
        
        Args:
            q_vector: Query vector [S, C, P] as BBCScalars
            t_vector: Target vector [S, C, P] as BBCScalars
            threshold: Minimum similarity threshold
            
        Returns:
            (similarity_score, confidence_scalar)
        """
        # Compute dot product: dot = Σ(q[i] * t[i])
        dot = BBCScalar(0.0, state=STABLE, origin="math")
        q_norm_sq = BBCScalar(0.0, state=STABLE, origin="math")
        t_norm_sq = BBCScalar(0.0, state=STABLE, origin="math")
        
        for i in range(3):  # S, C, P dimensions
            dot = dot + (q_vector[i] * t_vector[i])
            q_norm_sq = q_norm_sq + (q_vector[i] * q_vector[i])
            t_norm_sq = t_norm_sq + (t_vector[i] * t_vector[i])
        
        # Check for DEGENERATE states
        if dot.state == DEGENERATE or q_norm_sq.state == DEGENERATE or t_norm_sq.state == DEGENERATE:
            confidence = BBCScalar(0.0, state=DEGENERATE, origin="math")
            return 0.0, confidence
        
        # Compute denominator: denom_sq = q_norm_sq * t_norm_sq
        denom_sq = q_norm_sq * t_norm_sq
        
        if float(denom_sq) <= 0:
            confidence = BBCScalar(0.0, state=WEAK, origin="math")
            return 0.0, confidence
        
        # sqrt-free comparison: cos²(θ) > threshold²
        # We can compare without computing actual cos(θ)!
        threshold_scalar = BBCScalar(threshold, state=STABLE, origin="math")
        threshold_sq = threshold_scalar * threshold_scalar
        
        # cos²(θ) * denom_sq > threshold² * denom_sq
        # → dot² > threshold² * denom_sq
        lhs = dot * dot  # cos²(θ) * |q|² * |t|²
        rhs = threshold_sq * denom_sq  # threshold² * |q|² * |t|²
        
        # Calculate actual similarity score
        similarity = float(lhs) / float(denom_sq) if float(denom_sq) > 0 else 0.0
        similarity = min(max(similarity, 0.0), 1.0)  # Clamp to [0, 1]
        
        # Confidence based on state
        combined_state = dot._determine_new_state(q_norm_sq.state)
        combined_state = BBCScalar(0, state=combined_state)._determine_new_state(t_norm_sq.state)
        
        confidence_val = 1.0 / (1.0 + abs(1.0 - similarity))  # Higher confidence for clear matches
        confidence = BBCScalar(confidence_val, state=combined_state, origin="math")
        
        return similarity, confidence
    
    def _component_similarity(self, q_comp: BBCScalar, t_comp: BBCScalar) -> float:
        """Compute similarity for a single S/C/P component"""
        q_val = float(q_comp)
        t_val = float(t_comp)
        
        # Simple relative similarity
        if q_val == 0 and t_val == 0:
            return 1.0
        if q_val == 0 or t_val == 0:
            return 0.0
        
        # Geometric mean of relative closeness
        ratio = min(q_val, t_val) / max(q_val, t_val)
        return ratio
    
    def _boost_score(self, symbol: Dict[str, Any], base_score: float) -> float:
        """Boost similarity score based on symbol metadata"""
        score = base_score
        
        # Importance boost
        refs = symbol.get('references', [])
        ref_count = len(refs) if isinstance(refs, list) else refs
        score += min(ref_count * 0.02, 0.1)
        
        # Documentation boost
        if symbol.get('docstring'):
            score += 0.05
        
        # Recency boost
        if symbol.get('recently_modified', False):
            score += 0.1
        
        return min(score, 1.0)
    
    def bbc_normalize(self, vector: List[BBCScalar]) -> List[BBCScalar]:
        """
        L2 Normalize BBCScalar vector (state-aware normalization).
        
        Harrier uses L2 normalization: v / ||v||_2
        BBC adaptation: sqrt-free L2 normalization using BBCScalar arithmetic
        
        Algorithm (sqrt-free):
        1. Compute |v|² = Σ(v[i]²) 
        2. Compare |v|² > 0 (avoid division by zero)
        3. Normalize: v[i] / sqrt(|v|²) ≈ v[i] * (1 / sqrt(|v|²))
        
        For BBC math, we use: v[i] * |v| / |v|²  (avoids explicit sqrt)
        Which simplifies to: v[i] / |v|
        
        Args:
            vector: List of BBCScalars [S, C, P]
            
        Returns:
            L2-normalized vector as BBCScalars (unit vector)
        """
        # Compute |v|² = Σ(v[i]²)
        norm_sq = BBCScalar(0.0, state=STABLE, origin="math")
        for v in vector:
            norm_sq = norm_sq + (v * v)
        
        # Check DEGENERATE or zero norm
        if norm_sq.state == DEGENERATE or float(norm_sq) <= 0:
            return [BBCScalar(0.0, state=DEGENERATE, origin="math") for _ in vector]
        
        # For true L2 normalization: v / ||v||
        # ||v|| = sqrt(|v|²)
        # We compute this once as regular float (BBC doesn't have native sqrt)
        norm_val = float(norm_sq) ** 0.5
        norm_scalar = BBCScalar(norm_val, state=norm_sq.state, origin="math")
        
        # Normalize each component: v[i] / ||v||
        normalized = []
        for v in vector:
            norm_v = v / norm_scalar
            normalized.append(norm_v)
        
        return normalized
    
    def bbc_normalize_batch(self, vectors: List[List[BBCScalar]]) -> List[List[BBCScalar]]:
        """L2 normalize multiple BBCScalar vectors"""
        return [self.bbc_normalize(v) for v in vectors]
    
    def l2_normalize(self, vector: List[BBCScalar]) -> List[BBCScalar]:
        """Alias for bbc_normalize - matches Harrier L2 normalization"""
        return self.bbc_normalize(vector)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            'indexed_symbols': self.indexed_count,
            'vector_dimension': 3,  # [S, C, P]
            'governor_present': self.governor is not None,
            'encoder_present': self.encoder is not None
        }
    
    def clear(self):
        """Clear all indexed symbols"""
        self.symbol_vectors.clear()
        self.symbol_metadata.clear()
        self.indexed_count = 0


# Convenience functions for direct usage

def compute_symbol_similarity(sym1: Dict[str, Any], 
                                sym2: Dict[str, Any],
                                governor: Optional[HMPU_Governor] = None) -> float:
    """
    Compute similarity between two symbols using BBC mathematics.
    
    Args:
        sym1: First symbol dictionary
        sym2: Second symbol dictionary
        governor: Optional HMPU Governor
        
    Returns:
        Similarity score (0.0-1.0)
    """
    engine = BBCSymbolSimilarity(governor)
    
    # Index both symbols
    engine.index_symbol(sym1)
    engine.index_symbol(sym2)
    
    # Find similarity
    results = engine.find_similar(sym1, threshold=0.0, top_k=1)
    
    if results:
        return results[0].similarity_score
    return 0.0


def find_similar_symbols(query: Dict[str, Any],
                         candidates: List[Dict[str, Any]],
                         top_k: int = 5,
                         threshold: float = 0.70) -> List[Tuple[str, float]]:
    """
    Find symbols similar to query from candidates.
    
    Args:
        query: Query symbol
        candidates: List of candidate symbols
        top_k: Number of top results
        threshold: Minimum similarity
        
    Returns:
        List of (symbol_name, similarity) tuples
    """
    engine = BBCSymbolSimilarity()
    
    # Index candidates
    engine.index_symbols_batch(candidates)
    
    # Find similar
    results = engine.find_similar(query, threshold=threshold, top_k=top_k)
    
    return [(r.target_name, r.similarity_score) for r in results]
