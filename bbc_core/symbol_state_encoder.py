"""
BBC Symbol State Encoder
Adapts Harrier's last-token pooling to BBC Mathematics

Converts code symbols to BBCScalar [S, C, P] representation
NO neural networks - pure BBC mathematics
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

from .bbc_scalar import BBCScalar, bbc_data_ingestion, STABLE, WEAK, DEGENERATE
from .hmpu_core import HMPU_Governor


@dataclass
class SymbolSignature:
    """Represents a code symbol's BBC mathematical signature"""
    name: str
    s_component: BBCScalar  # Structural
    c_component: BBCScalar  # Chaos  
    p_component: BBCScalar  # Pulse
    metadata: Dict[str, Any]
    
    def to_vector(self) -> List[BBCScalar]:
        """Return [S, C, P] BBCScalar vector"""
        return [self.s_component, self.c_component, self.p_component]
    
    def aura_score(self, governor: HMPU_Governor) -> float:
        """Calculate Aura Field score using HMPU Governor"""
        return governor.aura_field_score(
            float(self.s_component),
            float(self.c_component),
            float(self.p_component)
        )


class SymbolStateEncoder:
    """
    Encodes code symbols as BBCScalar [S, C, P] vectors.
    
    S (Structural): Symbol's importance in codebase hierarchy
    C (Chaos): Code complexity via Shannon entropy  
    P (Pulse): Recency/freshness of the symbol
    
    NO neural networks - uses BBC's native mathematical operators.
    """
    
    def __init__(self, governor: Optional[HMPU_Governor] = None):
        self.governor = governor or HMPU_Governor()
        
        # Structural scoring weights
        self.structural_weights = {
            'class': 1.0,
            'function': 0.8,
            'method': 0.75,
            'variable': 0.3,
            'import': 0.2,
            'decorator': 0.5
        }
    
    def encode_symbol(self, symbol: Dict[str, Any]) -> SymbolSignature:
        """
        Encode a symbol dictionary to BBCScalar [S, C, P] representation.
        
        Args:
            symbol: Dictionary with 'name', 'type', 'code', 'file', etc.
            
        Returns:
            SymbolSignature with S, C, P BBCScalar components
        """
        # S: Structural score
        s_val = self._calculate_structural_score(symbol)
        s_state = self._determine_structural_state(symbol)
        S = BBCScalar(s_val, state=s_state, metadata={
            "origin": "semantic",
            "component": "structural",
            "symbol_name": symbol.get('name', 'unknown')
        })
        
        # C: Chaos score (Shannon entropy of code)
        code = symbol.get('code', '')
        c_val = self.governor._calculate_chaos(code) if code else 0.0
        # Normalize chaos to [0, 1] range (typical code chaos is 2-6)
        c_val = min(c_val / 6.0, 1.0)
        c_state = STABLE if c_val < 0.7 else WEAK if c_val < 0.9 else DEGENERATE
        C = BBCScalar(c_val, state=c_state, metadata={
            "origin": "math",
            "component": "chaos",
            "symbol_name": symbol.get('name', 'unknown')
        })
        
        # P: Pulse score (recency/freshness)
        p_val = self._calculate_pulse_score(symbol)
        p_state = self._determine_pulse_state(symbol)
        P = BBCScalar(p_val, state=p_state, metadata={
            "origin": "semantic",
            "component": "pulse",
            "symbol_name": symbol.get('name', 'unknown')
        })
        
        return SymbolSignature(
            name=symbol.get('name', 'unknown'),
            s_component=S,
            c_component=C,
            p_component=P,
            metadata={
                'file': symbol.get('file', ''),
                'type': symbol.get('type', 'unknown'),
                'line': symbol.get('line', 0),
                'hash': self._compute_symbol_hash(symbol)
            }
        )
    
    def encode_symbols_batch(self, symbols: List[Dict[str, Any]]) -> List[SymbolSignature]:
        """Encode multiple symbols efficiently"""
        return [self.encode_symbol(sym) for sym in symbols]
    
    def _calculate_structural_score(self, symbol: Dict[str, Any]) -> float:
        """
        Calculate structural importance score (S component).
        
        Factors:
        - Symbol type (class > function > method > variable)
        - Reference count (how many times referenced)
        - Centrality (in import graph)
        - Documentation quality
        """
        score = 0.0
        
        # Base weight by type
        sym_type = symbol.get('type', 'unknown').lower()
        score += self.structural_weights.get(sym_type, 0.3)
        
        # References boost score
        refs = symbol.get('references', [])
        ref_count = len(refs) if isinstance(refs, list) else refs
        score += min(ref_count * 0.05, 0.3)  # Cap at 0.3
        
        # Documentation presence
        if symbol.get('docstring') or symbol.get('documentation'):
            score += 0.1
        
        # Complexity factor (simple symbols less important)
        code = symbol.get('code', '')
        lines = len(code.split('\n')) if code else 0
        if lines > 20:  # Complex symbol
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_structural_state(self, symbol: Dict[str, Any]) -> str:
        """Determine BBC state based on structural reliability"""
        # Check for red flags
        if not symbol.get('name'):
            return DEGENERATE
        
        code = symbol.get('code', '')
        if not code or len(code) < 3:
            return WEAK  # Minimal code
        
        # Check for syntax-like errors in stored code
        if self._has_syntax_red_flags(code):
            return WEAK
        
        return STABLE
    
    def _calculate_pulse_score(self, symbol: Dict[str, Any]) -> float:
        """
        Calculate pulse/recency score (P component).
        
        Freshly modified symbols have higher pulse.
        Uses file modification time and symbol hash.
        """
        # Default moderate pulse
        base_pulse = 0.5
        
        # Check for modification metadata
        mtime = symbol.get('mtime', 0)
        if mtime:
            import time
            age_days = (time.time() - mtime) / (24 * 3600)
            # Exponential decay: fresh = 1.0, 30 days = 0.5, 90 days = 0.2
            base_pulse = max(0.1, 1.0 - (age_days / 60))
        
        # Symbol activity indicator
        if symbol.get('recently_modified', False):
            base_pulse = 1.0
        
        # Test coverage presence boosts pulse (recently tested)
        if symbol.get('has_tests', False):
            base_pulse += 0.1
        
        return min(base_pulse, 1.0)
    
    def _determine_pulse_state(self, symbol: Dict[str, Any]) -> str:
        """Determine BBC state based on pulse reliability"""
        # Very old symbols might be stale
        mtime = symbol.get('mtime', 0)
        if mtime:
            import time
            age_days = (time.time() - mtime) / (24 * 3600)
            if age_days > 365:  # Very old
                return WEAK
        
        return STABLE
    
    def _has_syntax_red_flags(self, code: str) -> bool:
        """Quick heuristic for code quality red flags"""
        if not code:
            return True
        
        # Check for unbalanced braces (simple heuristic)
        open_braces = code.count('{') + code.count('(') + code.count('[')
        close_braces = code.count('}') + code.count(')') + code.count(']')
        if abs(open_braces - close_braces) > 3:
            return True
        
        # Check for excessive line length (style issue)
        long_lines = sum(1 for line in code.split('\n') if len(line) > 200)
        if long_lines > 5:
            return True
        
        return False
    
    def _compute_symbol_hash(self, symbol: Dict[str, Any]) -> str:
        """Compute unique hash for symbol versioning"""
        content = f"{symbol.get('name', '')}:{symbol.get('code', '')[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


class SymbolVectorCache:
    """Caches symbol [S, C, P] vectors for fast retrieval"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path('.bbc') / 'cache' / 'symbol_vectors'
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, SymbolSignature] = {}
    
    def get(self, symbol_hash: str) -> Optional[SymbolSignature]:
        """Retrieve cached symbol signature"""
        return self._memory_cache.get(symbol_hash)
    
    def put(self, symbol_hash: str, signature: SymbolSignature):
        """Cache symbol signature"""
        self._memory_cache[symbol_hash] = signature
    
    def invalidate(self, file_path: str):
        """Invalidate cache for symbols from a file"""
        keys_to_remove = [
            k for k, v in self._memory_cache.items()
            if v.metadata.get('file') == file_path
        ]
        for k in keys_to_remove:
            del self._memory_cache[k]
    
    def clear(self):
        """Clear all cached vectors"""
        self._memory_cache.clear()
