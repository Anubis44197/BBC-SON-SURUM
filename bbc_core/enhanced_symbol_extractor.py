"""
Enhanced Symbol Extractor with Tree-sitter support and simple cache
Falls back to regex if tree-sitter unavailable
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path


class EnhancedSymbolExtractor:
    """
    Symbol extraction with tree-sitter (when available) and simple file cache
    """
    
    def __init__(self, project_root: str, use_cache: bool = True):
        """
        Initialize enhanced symbol extractor
        
        Args:
            project_root: Project root path
            use_cache: Enable file-based cache
        """
        self.project_root = Path(project_root)
        self.use_cache = use_cache
        self.cache_dir = self.project_root / ".bbc" / "cache"
        
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load tree-sitter
        self.ts_available = False
        self.ts_parser = None
        self.ts_language = None
        self.python_extractor = None
        
        try:
            from tree_sitter import Language, Parser
            import tree_sitter_python
            
            self.ts_language = Language(tree_sitter_python.language())
            self.ts_parser = Parser()
            self.ts_parser.set_language(self.ts_language)
            
            from bbc_core.symbol_extractors import PythonExtractor
            self.python_extractor = PythonExtractor()
            
            self.ts_available = True
        except Exception:
            self.ts_available = False
    
    def extract_symbols(self, file_path: str, content: str, ext: str) -> Dict[str, Any]:
        """
        Extract symbols from file with caching
        
        Args:
            file_path: Relative file path
            content: File content
            ext: File extension (.py, .js, etc.)
            
        Returns:
            Dict with extracted symbols
        """
        # Check cache first
        if self.use_cache:
            cached = self._get_from_cache(file_path, content)
            if cached is not None:
                return cached
        
        # Extract symbols
        if ext == '.py' and self.ts_available:
            symbols = self._extract_python_ts(content)
        else:
            symbols = self._extract_regex_fallback(content, ext)
        
        # Cache result
        if self.use_cache:
            self._save_to_cache(file_path, content, symbols)
        
        return symbols
    
    def _extract_python_ts(self, content: str) -> Dict[str, Any]:
        """Extract Python symbols using tree-sitter"""
        try:
            tree = self.ts_parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            return self.python_extractor.extract(root_node, content)
        except Exception:
            return self._extract_regex_fallback(content, '.py')
    
    def _extract_regex_fallback(self, content: str, ext: str) -> Dict[str, Any]:
        """Fallback to regex-based extraction"""
        import re
        
        symbols = {
            "classes": [],
            "functions": [],
            "imports": []
        }
        
        if ext == '.py':
            # Simple regex patterns (existing logic)
            class_pattern = r'^\s*class\s+(\w+)'
            func_pattern = r'^\s*def\s+(\w+)'
            import_pattern = r'^\s*(?:from\s+[\w.]+\s+)?import\s+([\w\s,]+)'
            
            for line_num, line in enumerate(content.split('\n'), 1):
                if match := re.match(class_pattern, line):
                    symbols['classes'].append({
                        "name": match.group(1),
                        "line": line_num,
                        "bases": [],
                        "methods": []
                    })
                elif match := re.match(func_pattern, line):
                    symbols['functions'].append({
                        "name": match.group(1),
                        "line": line_num,
                        "params": [],
                        "is_method": False
                    })
                elif match := re.match(import_pattern, line):
                    imports = [i.strip() for i in match.group(1).split(',')]
                    symbols['imports'].extend(imports)
        
        return symbols
    
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate cache key from file path and content hash"""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        safe_path = file_path.replace('/', '_').replace('\\', '_').replace(':', '')
        return f"{safe_path}_{content_hash}.json"
    
    def _get_from_cache(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Try to load symbols from cache"""
        try:
            cache_key = self._get_cache_key(file_path, content)
            cache_file = self.cache_dir / cache_key
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return None
    
    def _save_to_cache(self, file_path: str, content: str, symbols: Dict[str, Any]) -> None:
        """Save symbols to cache"""
        try:
            cache_key = self._get_cache_key(file_path, content)
            cache_file = self.cache_dir / cache_key
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(symbols, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def clear_cache(self) -> int:
        """Clear all cached symbol files"""
        count = 0
        try:
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob('*.json'):
                    cache_file.unlink()
                    count += 1
        except Exception:
            pass
        
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "enabled": self.use_cache,
            "file_count": 0,
            "total_size_bytes": 0,
            "tree_sitter_available": self.ts_available
        }
        
        if self.use_cache and self.cache_dir.exists():
            try:
                cache_files = list(self.cache_dir.glob('*.json'))
                stats["file_count"] = len(cache_files)
                stats["total_size_bytes"] = sum(f.stat().st_size for f in cache_files)
            except Exception:
                pass
        
        return stats
