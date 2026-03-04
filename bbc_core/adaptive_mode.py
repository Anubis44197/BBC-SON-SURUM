"""
BBC Adaptive Mode Engine v1.0
Deterministic Context-Aware Response Generator

GOAL:
Prevent hallucinations while remaining usable in production.

MODE SELECTION:
- If context_match_ratio >= 0.90 → STRICT MODE
- If context_match_ratio < 0.90 → RELAXED MODE

STRICT MODE RULES:
- Use ONLY provided BBC context
- No guessing, no general knowledge
- If information is missing, respond EXACTLY: "Information not found in sealed context."

RELAXED MODE RULES:
- Use BBC context as PRIMARY source
- You MAY ask user confirmation to expand context
- Do NOT invent symbols or logic
"""

import json
import re
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Mode(Enum):
    """BBC Adaptive Mode Types"""
    STRICT = "strict"
    RELAXED = "relaxed"


class BBCViolation(Exception):
    """Hallucination / Context Boundary Violation Error"""
    def __init__(self, message: str = "Context boundary violation"):
        self.message = message
        super().__init__(self.message)


@dataclass
class SymbolReference:
    """Symbol reference with source attribution"""
    statement: str
    source_symbol: str
    file_path: str = ""
    confidence: float = 1.0


@dataclass
class AdaptiveResponse:
    """Standard BBC Adaptive Response"""
    mode: str
    confidence: float
    answers: List[Dict[str, str]]
    safety: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "answers": self.answers,
            "safety": self.safety,
            "violations": self.violations
        }
    
    def to_json(self) -> str:
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback to plain text
            return f"[BBC-FALLBACK] Mode: {self.mode}, Confidence: {self.confidence}, Answers: {len(self.answers)}"


class BBCAdaptiveMode:
    """
    BBC Adaptive Mode Engine
    
    Provides hallucination-resistant responses based on sealed BBC context.
    """
    
    # Forbidden speculative language patterns (English + Turkish)
    SPECULATIVE_PATTERNS = [
        # English patterns
        r'\bprobably\b',
        r'\bmaybe\b',
        r'\bperhaps\b',
        r'\bmight be\b',
        r'\bcould be\b',
        r'\bi think\b',
        r'\bi guess\b',
        r'\bi assume\b',
        r'\bi believe\b',
        r'\bgenerally\b',
        r'\busually\b',
        r'\btypically\b',
        r'\bit seems\b',
        r'\blikely\b',
        r'\bunlikely\b',
        r'\bpossibly\b',
        # Turkish patterns
        r'\bmuhtemelen\b',
        r'\bolabilir\b',
        r'\bgenelde\b',
        r'\btahminen\b',
        r'\bgaliba\b',
    ]
    
    def __init__(self, context_path: Optional[str] = None):
        """
        Initialize BBC Adaptive Mode Engine
        
        Args:
            context_path: Path to bbc_context.json
        """
        self.context_path = context_path
        self.context_data: Dict[str, Any] = {}
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.file_hashes: Dict[str, str] = {}
        self.dependency_graph: Dict[str, Dict[str, List[str]]] = {}
        self.files: List[str] = []
        self.project_root: str = ""
        self.match_ratio_threshold = 0.90
        self.stale_files: List[str] = []
        
        if context_path:
            self._load_context(context_path)
    
    def _load_context(self, context_path: str) -> None:
        """Load BBC context from file"""
        path = Path(context_path)
        if not path.exists():
            raise FileNotFoundError(f"Context file not found: {context_path}")
        
        with open(context_path, 'r', encoding='utf-8') as f:
            self.context_data = json.load(f)
        
        # Extract project skeleton
        skeleton = self.context_data.get("project_skeleton", {})
        self.files = skeleton.get("hierarchy", [])
        self.project_root = skeleton.get("root", "")
        
        # Extract dependency graph
        self.dependency_graph = self.context_data.get("dependency_graph", {})
        
        # Extract symbols and hashes from code structure
        code_structure = self.context_data.get("code_structure", [])
        for item in code_structure:
            if isinstance(item, dict):
                file_path = item.get("path", "")
                structure = item.get("structure", {})
                stats = item.get("stats", {})
                
                self.symbols[file_path] = {
                    "classes": structure.get("classes", []),
                    "functions": structure.get("functions", []),
                    "imports": structure.get("imports", []),
                    "line_count": stats.get("lines", 0)
                }
                
                # Store file hash for staleness detection
                if stats.get("hash"):
                    self.file_hashes[file_path] = stats["hash"]
    
    def detect_mode(self, context_match_ratio: float) -> Mode:
        """
        Detect operation mode based on context match ratio
        
        Args:
            context_match_ratio: Float between 0.0 and 1.0
            
        Returns:
            Mode.STRICT if >= 0.90, else Mode.RELAXED
        """
        if context_match_ratio >= self.match_ratio_threshold:
            return Mode.STRICT
        return Mode.RELAXED
    
    def verify_file_hash(self, file_path: str) -> bool:
        """
        Verify if a file's current hash matches the sealed context hash.
        Returns True if file is unchanged, False if stale/modified.
        """
        import hashlib
        stored_hash = self.file_hashes.get(file_path)
        if not stored_hash:
            return False

        # Resolve absolute path
        if self.project_root:
            abs_path = os.path.join(self.project_root, file_path)
        else:
            abs_path = file_path

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            return current_hash == stored_hash
        except (FileNotFoundError, OSError):
            return False

    def check_context_freshness(self) -> Dict[str, Any]:
        """
        Check which files have changed since context was sealed.
        Returns a report of stale files and their impact radius.
        """
        stale = []
        impact = []

        for file_path in self.file_hashes:
            if not self.verify_file_hash(file_path):
                stale.append(file_path)
                # Find all files affected by this change via dependency graph
                dep_info = self.dependency_graph.get(file_path, {})
                affected = dep_info.get("depended_by", [])
                for af in affected:
                    if af not in impact:
                        impact.append(af)

        self.stale_files = stale
        total_files = len(self.file_hashes)
        stale_ratio = len(stale) / total_files if total_files > 0 else 0.0

        return {
            "total_files": total_files,
            "stale_files": stale,
            "stale_count": len(stale),
            "stale_ratio": round(stale_ratio, 3),
            "impact_radius": impact,
            "impact_count": len(impact),
            "context_fresh": len(stale) == 0,
            "recommendation": "RESCAN" if stale_ratio > 0.1 else "OK" if len(stale) == 0 else "PARTIAL_RESCAN"
        }

    def get_impact_radius(self, file_path: str) -> List[str]:
        """
        Get all files that would be affected if the given file changes.
        Uses dependency graph for accurate impact analysis.
        """
        affected = set()
        visited = set()

        def _walk(fp):
            if fp in visited:
                return
            visited.add(fp)
            dep_info = self.dependency_graph.get(fp, {})
            for dep in dep_info.get("depended_by", []):
                affected.add(dep)
                _walk(dep)

        _walk(file_path)
        return list(affected)

    def find_symbol(self, symbol_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Find a symbol in the loaded context
        
        Args:
            symbol_name: Name of class/function to find
            
        Returns:
            Tuple of (file_path, symbol_info) or None
        """
        symbol_lower = symbol_name.lower()
        
        for file_path, info in self.symbols.items():
            # Check classes
            for cls in info.get("classes", []):
                if cls.lower() == symbol_lower or symbol_lower in cls.lower():
                    return (file_path, info)
            
            # Check functions
            for func in info.get("functions", []):
                if func.lower() == symbol_lower or symbol_lower in func.lower():
                    return (file_path, info)
        
        return None
    
    def validate_statement(self, statement: str) -> Tuple[bool, List[str]]:
        """
        Validate statement for speculative language
        
        Args:
            statement: The statement to validate
            
        Returns:
            Tuple of (is_valid, violations)
        """
        violations = []
        statement_lower = statement.lower()
        
        for pattern in self.SPECULATIVE_PATTERNS:
            if re.search(pattern, statement_lower):
                violations.append(f"Speculative language detected: {pattern}")
        
        return len(violations) == 0, violations
    
    def answer(
        self,
        question: str,
        context_match_ratio: float = 0.95,
        primary_symbol: Optional[str] = None,
        require_confirmation: bool = False
    ) -> AdaptiveResponse:
        """
        Generate an adaptive, hallucination-resistant answer
        
        Args:
            question: The user's question
            context_match_ratio: Confidence ratio (0.0 - 1.0)
            primary_symbol: Optional specific symbol to reference
            require_confirmation: Whether to ask for context expansion
            
        Returns:
            AdaptiveResponse with mode, confidence, and answers
        """
        mode = self.detect_mode(context_match_ratio)
        violations = []
        answers = []
        safety = []
        
        # STRICT MODE
        if mode == Mode.STRICT:
            if primary_symbol:
                symbol_info = self.find_symbol(primary_symbol)
                if symbol_info:
                    file_path, info = symbol_info
                    
                    # Hash verification: check if source file is stale
                    if self.file_hashes and not self.verify_file_hash(file_path):
                        safety.append(f"STALE_WARNING: {file_path} has changed since context was sealed.")
                        # Get impact radius
                        impacted = self.get_impact_radius(file_path)
                        if impacted:
                            safety.append(f"IMPACT: {len(impacted)} dependent files may be affected: {', '.join(impacted[:5])}")
                    
                    # Build factual statement
                    classes = info.get("classes", [])
                    functions = info.get("functions", [])
                    
                    statement = f"[{primary_symbol}] found in: {file_path}"
                    if classes:
                        statement += f" - Classes: {', '.join(classes[:3])}"
                    if functions:
                        statement += f" - Functions: {', '.join(functions[:5])}"
                    
                    # Validate no speculative language
                    is_valid, val_violations = self.validate_statement(statement)
                    if not is_valid:
                        violations.extend(val_violations)
                        return AdaptiveResponse(
                            mode=Mode.STRICT.value,
                            confidence=0.0,
                            answers=[],
                            violations=["HALLUCINATION"] + val_violations
                        )
                    
                    answers.append({
                        "statement": statement,
                        "source_symbol": primary_symbol
                    })
                    
                    return AdaptiveResponse(
                        mode=Mode.STRICT.value,
                        confidence=context_match_ratio,
                        answers=answers,
                        safety=safety,
                        violations=violations
                    )
                else:
                    # Symbol not found in context
                    return AdaptiveResponse(
                        mode=Mode.STRICT.value,
                        confidence=0.0,
                        answers=[{
                            "statement": "Information not found in sealed context.",
                            "source_symbol": "NONE"
                        }],
                        violations=[]
                    )
            else:
                # No primary symbol provided
                return AdaptiveResponse(
                    mode=Mode.STRICT.value,
                    confidence=0.0,
                    answers=[{
                        "statement": "Information not found in sealed context.",
                        "source_symbol": "NONE"
                    }],
                    violations=[]
                )
        
        # RELAXED MODE
        else:
            if primary_symbol:
                symbol_info = self.find_symbol(primary_symbol)
                if symbol_info:
                    file_path, info = symbol_info
                    
                    statement = f"[{primary_symbol}] found in: {file_path}"
                    classes = info.get("classes", [])
                    functions = info.get("functions", [])
                    
                    if classes:
                        statement += f" - Classes: {', '.join(classes[:3])}"
                    if functions:
                        statement += f" - Functions: {', '.join(functions[:5])}"
                    
                    answers.append({
                        "statement": statement,
                        "source_symbol": primary_symbol
                    })
                    
                    if require_confirmation:
                        answers.append({
                            "statement": "Expand context scope?",
                            "source_symbol": "SYSTEM"
                        })
                    
                    return AdaptiveResponse(
                        mode=Mode.RELAXED.value,
                        confidence=context_match_ratio,
                        answers=answers,
                        violations=violations
                    )
                else:
                    # In relaxed mode, we can ask for expansion
                    if require_confirmation:
                        return AdaptiveResponse(
                            mode=Mode.RELAXED.value,
                            confidence=context_match_ratio,
                            answers=[{
                                "statement": "Information not found in sealed context.",
                                "source_symbol": "NONE"
                            }, {
                                "statement": "Expand context scope?",
                                "source_symbol": "SYSTEM"
                            }],
                            violations=[]
                        )
                    else:
                        return AdaptiveResponse(
                            mode=Mode.RELAXED.value,
                            confidence=0.0,
                            answers=[{
                                "statement": "Information not found in sealed context.",
                                "source_symbol": "NONE"
                            }],
                            violations=[]
                        )
            else:
                return AdaptiveResponse(
                    mode=Mode.RELAXED.value,
                    confidence=0.0,
                    answers=[{
                        "statement": "Information not found in sealed context.",
                        "source_symbol": "NONE"
                    }],
                    violations=[]
                )
    
    def process_query(
        self,
        inputs: Dict[str, Any]
    ) -> Union[str, Dict[str, Any]]:
        """
        Process a BBC Adaptive Mode query
        
        Args:
            inputs: Dictionary with keys:
                - primary: Primary symbol name
                - direct: Direct context
                - indirect: Indirect context
                - safety: Safety constraints
                - context_match_ratio: Float (0.0 - 1.0)
                
        Returns:
            JSON string or fallback plain text
        """
        primary = inputs.get("primary", "")
        direct = inputs.get("direct", "")
        indirect = inputs.get("indirect", "")
        safety = inputs.get("safety", [])
        context_match_ratio = inputs.get("context_match_ratio", 0.0)
        
        # Detect mode
        mode = self.detect_mode(context_match_ratio)
        
        # Generate response
        response = self.answer(
            question=direct,
            context_match_ratio=context_match_ratio,
            primary_symbol=primary,
            require_confirmation=(mode == Mode.RELAXED)
        )
        
        # Merge safety constraints (keep engine-generated + user-provided)
        if isinstance(safety, list) and safety:
            response.safety = response.safety + safety
        
        try:
            return response.to_json()
        except Exception:
            # Fallback to plain text
            return response.to_dict()


# Convenience function for quick usage
def adaptive_mode_query(
    context_path: str,
    primary: str,
    direct: str,
    indirect: str = "",
    safety: List[str] = None,
    context_match_ratio: float = 0.95
) -> str:
    """
    Quick query function for BBC Adaptive Mode
    
    Example:
        >>> result = adaptive_mode_query(
        ...     context_path="bbc_context.json",
        ...     primary="HMPUMathChat",
        ...     direct="What does this class do?",
        ...     context_match_ratio=0.95
        ... )
    """
    engine = BBCAdaptiveMode(context_path)
    
    inputs = {
        "primary": primary,
        "direct": direct,
        "indirect": indirect,
        "safety": safety or [],
        "context_match_ratio": context_match_ratio
    }
    
    result = engine.process_query(inputs)
    
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    # Example usage
    print("BBC Adaptive Mode Engine v1.0")
    print("=" * 40)
    
    # Example with no context
    engine = BBCAdaptiveMode()
    
    # Test STRICT mode (>= 0.90)
    print("\n--- STRICT MODE TEST (ratio=0.95) ---")
    response = engine.answer(
        question="What is HMPUMathChat?",
        context_match_ratio=0.95,
        primary_symbol="HMPUMathChat"
    )
    print(response.to_json())
    
    # Test RELAXED mode (< 0.90)
    print("\n--- RELAXED MODE TEST (ratio=0.85) ---")
    response = engine.answer(
        question="What is HMPUMathChat?",
        context_match_ratio=0.85,
        primary_symbol="HMPUMathChat",
        require_confirmation=True
    )
    print(response.to_json())
    
    # Test missing symbol
    print("\n--- MISSING SYMBOL TEST ---")
    response = engine.answer(
        question="What is UnknownSymbol?",
        context_match_ratio=0.95,
        primary_symbol="UnknownSymbol"
    )
    print(response.to_json())
