"""
Full Symbol Extractor with Tree-sitter support for all major languages
Includes robust caching, symbol indices, and multi-pass analysis
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class FullSymbolExtractor:
    """
    Production-grade symbol extraction system
    - Tree-sitter AST parsing for 7+ languages
    - Robust file-based cache with invalidation
    - Symbol indices for fast lookup
    - Fallback to regex when tree-sitter unavailable
    """
    
    # Language to parser mapping
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.rs': 'rust',
        '.go': 'go',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.hpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.java': 'java',
        '.cs': 'csharp'
    }
    
    def __init__(self, project_root: str, use_cache: bool = True, use_indices: bool = True):
        """
        Initialize full symbol extractor
        
        Args:
            project_root: Project root path
            use_cache: Enable file-based cache
            use_indices: Enable symbol indices
        """
        self.project_root = Path(project_root)
        self.use_cache = use_cache
        self.use_indices = use_indices
        
        # Ensure BBC structure exists
        from bbc_core.config import BBCConfig
        BBCConfig.ensure_bbc_structure(str(self.project_root))
        
        self.cache_dir = self.project_root / ".bbc" / "cache"
        self.indices_dir = self.project_root / ".bbc" / "indices"
        
        # Initialize tree-sitter parsers
        self.parsers = {}
        self.extractors = {}
        self._init_tree_sitter()
        
        # Symbol index (in-memory, persisted to disk)
        self.symbol_index = {}
        if self.use_indices:
            self._load_symbol_index()
    
    def _init_tree_sitter(self):
        """Initialize tree-sitter parsers and extractors"""
        try:
            from tree_sitter import Language, Parser
            
            # Language modules
            language_modules = {
                'python': 'tree_sitter_python',
                'javascript': 'tree_sitter_javascript',
                'typescript': 'tree_sitter_typescript.typescript',
                'rust': 'tree_sitter_rust',
                'go': 'tree_sitter_go',
                'c': 'tree_sitter_c',
                'cpp': 'tree_sitter_cpp',
                'java': 'tree_sitter_java',
                'csharp': 'tree_sitter_c_sharp'
            }
            
            # Extractor classes
            from bbc_core.symbol_extractors import (
                PythonExtractor,
                JavaScriptExtractor,
                TypeScriptExtractor,
                RustExtractor,
                GoExtractor,
                CCppExtractor,
                JavaExtractor
            )
            
            extractor_classes = {
                'python': PythonExtractor,
                'javascript': JavaScriptExtractor,
                'typescript': TypeScriptExtractor,
                'rust': RustExtractor,
                'go': GoExtractor,
                'c': CCppExtractor,
                'cpp': CCppExtractor,
                'java': JavaExtractor
            }
            
            # Initialize each language
            for lang, module_path in language_modules.items():
                try:
                    # Import language module
                    parts = module_path.split('.')
                    module = __import__(parts[0])
                    for part in parts[1:]:
                        module = getattr(module, part)
                    
                    # Create parser (tree-sitter v0.25 API - wrap in Language)
                    language = Language(module.language())
                    parser = Parser(language)
                    self.parsers[lang] = parser
                    
                    # Create extractor
                    if lang in extractor_classes:
                        self.extractors[lang] = extractor_classes[lang]()
                    
                except Exception as e:
                    # Language not available, skip
                    logger.debug(f"Tree-sitter language {lang} not available: {e}")
                    pass
        
        except Exception as e:
            # Tree-sitter not available at all
            logger.debug(f"Tree-sitter initialization failed: {e}")
            pass
    
    def extract_symbols(self, file_path: str, content: str, ext: str) -> Dict[str, Any]:
        """
        Extract symbols from file with full pipeline
        
        Args:
            file_path: Relative file path
            content: File content
            ext: File extension
            
        Returns:
            Dict with extracted symbols
        """
        # Check cache first
        if self.use_cache:
            cached = self._get_from_cache(file_path, content)
            if cached is not None:
                return cached
        
        # Determine language
        language = self.LANGUAGE_MAP.get(ext.lower())
        
        # Extract symbols
        if language and language in self.parsers:
            symbols = self._extract_with_tree_sitter(content, language)
        else:
            symbols = self._extract_with_regex(content, ext)
        
        # Add metadata
        symbols['_meta'] = {
            'file': file_path,
            'language': language or 'unknown',
            'method': 'tree-sitter' if language in self.parsers else 'regex',
            'extracted_at': datetime.now().isoformat()
        }
        
        # Update indices
        if self.use_indices:
            self._update_symbol_index(file_path, symbols)
        
        # Cache result
        if self.use_cache:
            self._save_to_cache(file_path, content, symbols)
        
        return symbols
    
    def _extract_with_tree_sitter(self, content: str, language: str) -> Dict[str, Any]:
        """Extract symbols using tree-sitter"""
        try:
            parser = self.parsers[language]
            extractor = self.extractors.get(language)
            
            if not extractor:
                return self._extract_with_regex(content, f'.{language}')
            
            # Parse with tree-sitter
            tree = parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Extract symbols
            symbols = extractor.extract(root_node, content)
            
            return symbols
        
        except Exception:
            return self._extract_with_regex(content, f'.{language}')
    
    def _extract_with_regex(self, content: str, ext: str) -> Dict[str, Any]:
        """Fallback to regex-based extraction"""
        import re
        
        symbols = {
            "classes": [],
            "functions": [],
            "imports": []
        }
        
        # Simple regex patterns (existing logic from hmpu_quantizer)
        if ext in ['.py']:
            class_pattern = r'^\s*class\s+(\w+)'
            func_pattern = r'^\s*def\s+(\w+)'
            import_pattern = r'^\s*(?:from\s+[\w.]+\s+)?import\s+([\w\s,]+)'
            
            for line_num, line in enumerate(content.split('\n'), 1):
                if match := re.match(class_pattern, line):
                    symbols['classes'].append({
                        "name": match.group(1),
                        "line": line_num
                    })
                elif match := re.match(func_pattern, line):
                    symbols['functions'].append({
                        "name": match.group(1),
                        "line": line_num
                    })
                elif match := re.match(import_pattern, line):
                    imports = [i.strip() for i in match.group(1).split(',')]
                    symbols['imports'].extend([{"name": i, "line": line_num} for i in imports])
        
        return symbols
    
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate cache key from file path and content hash"""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        safe_path = file_path.replace('/', '_').replace('\\', '_').replace(':', '').replace('.', '_')
        return f"{safe_path}_{content_hash}.json"
    
    def _get_from_cache(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Try to load symbols from cache"""
        try:
            cache_key = self._get_cache_key(file_path, content)
            cache_file = self.cache_dir / cache_key
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load cached symbols: {e}")
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
    
    def _load_symbol_index(self) -> None:
        """Load symbol index from disk"""
        try:
            index_file = self.indices_dir / "symbol_index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.symbol_index = json.load(f)
        except Exception:
            self.symbol_index = {}
    
    def _save_symbol_index(self) -> None:
        """Save symbol index to disk"""
        try:
            index_file = self.indices_dir / "symbol_index.json"
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.symbol_index, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _update_symbol_index(self, file_path: str, symbols: Dict[str, Any]) -> None:
        """Update symbol index with extracted symbols"""
        # Index classes
        for cls in symbols.get('classes', []):
            if isinstance(cls, dict) and 'name' in cls:
                name = cls['name']
                if name not in self.symbol_index:
                    self.symbol_index[name] = []
                self.symbol_index[name].append({
                    "type": "class",
                    "file": file_path,
                    "line": cls.get('line', 0)
                })
        
        # Index functions
        for func in symbols.get('functions', []):
            if isinstance(func, dict) and 'name' in func:
                name = func['name']
                if name not in self.symbol_index:
                    self.symbol_index[name] = []
                self.symbol_index[name].append({
                    "type": "function",
                    "file": file_path,
                    "line": func.get('line', 0)
                })
        
        # Save index
        self._save_symbol_index()
    
    def find_symbol(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Find symbol in index"""
        return self.symbol_index.get(symbol_name, [])
    
    def clear_cache(self) -> int:
        """Clear all cached symbol files"""
        count = 0
        try:
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob('*.json'):
                    try:
                        cache_file.unlink()
                        count += 1
                    except Exception as e:
                        logger.debug(f"Failed to delete cache file {cache_file}: {e}")
        except Exception as e:
            logger.debug(f"Failed to clear cache: {e}")
            pass
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extractor statistics"""
        stats = {
            "tree_sitter_available": len(self.parsers) > 0,
            "supported_languages": list(self.parsers.keys()),
            "cache_enabled": self.use_cache,
            "indices_enabled": self.use_indices,
            "cache_files": 0,
            "cache_size_bytes": 0,
            "indexed_symbols": len(self.symbol_index)
        }
        
        if self.use_cache and self.cache_dir.exists():
            try:
                cache_files = list(self.cache_dir.glob('*.json'))
                stats["cache_files"] = len(cache_files)
                stats["cache_size_bytes"] = sum(f.stat().st_size for f in cache_files)
            except Exception as e:
                logger.debug(f"Failed to get cache stats: {e}")
                pass
        
        return stats
    
    def cleanup_old_cache(self, max_age_days: int = 30, max_cache_size_mb: int = 100):
        """
        Eski cache dosyalarını temizle ve toplam cache boyutunu kontrol et.
        
        Args:
            max_age_days: Bu günden eski cache'ler silinir (default: 30)
            max_cache_size_mb: Maksimum toplam cache boyutu MB (default: 100)
        
        Returns:
            int: Silinen dosya sayısı
        """
        if not self.cache_dir.exists():
            return 0
        
        import time
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        # Eski cache dosyalarını sil
        cleaned_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    cleaned_count += 1
            except (OSError, PermissionError):
                continue
        
        # Toplam cache boyutunu kontrol et
        total_size = 0
        cache_files = []
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                size = cache_file.stat().st_size
                mtime = cache_file.stat().st_mtime
                total_size += size
                cache_files.append((cache_file, size, mtime))
            except (OSError, PermissionError):
                continue
        
        # Boyut limiti aşıldıysa en eski dosyaları sil
        max_size_bytes = max_cache_size_mb * 1024 * 1024
        if total_size > max_size_bytes:
            # En eski dosyalardan başla
            cache_files.sort(key=lambda x: x[2])  # mtime'a göre sırala
            
            while total_size > max_size_bytes and cache_files:
                oldest_file, size, _ = cache_files.pop(0)
                try:
                    oldest_file.unlink()
                    total_size -= size
                    cleaned_count += 1
                except (OSError, PermissionError):
                    continue
        
        return cleaned_count
