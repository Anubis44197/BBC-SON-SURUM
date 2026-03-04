"""
BBC Symbol Extractor - Aşama 1: Symbol Bazlı Blast Radius Sistemi

Bu modül dosyalardan sembolleri (class, function, method, variable) çıkarır.
- Python için AST modülü kullanır (deterministik)
- Diğer diller için regex patterns kullanır (polyglot)
- LLM/AI kullanmaz - tamamen deterministiktir

Çıktı Formatı:
{
  "file": "path/to/file.py",
  "symbols": [
    {"name": "ClassName", "type": "class", "line": 10},
    {"name": "method_name", "type": "method", "line": 15, "class": "ClassName"},
    {"name": "function_name", "type": "function", "line": 20}
  ]
}
"""

import ast
import os
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class SymbolType(Enum):
    """Sembol tipleri."""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    PROPERTY = "property"


@dataclass
class Symbol:
    """Bir sembolü temsil eden veri sınıfı."""
    name: str
    type: str
    line: int
    column: int = 0
    class_name: Optional[str] = None
    parent: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    docstring: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        result = {
            "name": self.name,
            "type": self.type,
            "line": self.line,
        }
        if self.class_name:
            result["class"] = self.class_name
        if self.parent and not self.class_name:
            result["parent"] = self.parent
        if self.decorators:
            result["decorators"] = self.decorators
        if self.signature:
            result["signature"] = self.signature
        return result


@dataclass
class FileSymbols:
    """Bir dosyadaki tüm sembolleri temsil eder."""
    file: str
    language: str
    symbols: List[Symbol] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        return {
            "file": self.file,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols]
        }
    
    def to_json(self, indent: int = 2) -> str:
        """JSON formatına dönüştür."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class PythonSymbolExtractor(ast.NodeVisitor):
    """Python dosyalarından sembol çıkaran AST tabanlı extractor."""
    
    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.symbols: List[Symbol] = []
        self.current_class: Optional[str] = None
        self.lines = source_code.split('\n')
    
    def extract(self) -> List[Symbol]:
        """Sembolleri çıkar ve döndür."""
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError as e:
            # Sözdizimi hatası durumunda boş liste döndür
            pass
        return self.symbols
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Sınıf tanımlarını ziyaret et."""
        symbol = Symbol(
            name=node.name,
            type=SymbolType.CLASS.value,
            line=node.lineno,
            column=node.col_offset,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list]
        )
        self.symbols.append(symbol)
        
        # Sınıf içindeki metodları çıkar
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Fonksiyon tanımlarını ziyaret et."""
        self._process_function(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Async fonksiyon tanımlarını ziyaret et."""
        self._process_function(node)
    
    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Fonksiyon/metod işleme."""
        is_method = self.current_class is not None
        symbol_type = SymbolType.METHOD.value if is_method else SymbolType.FUNCTION.value
        
        # Signature oluştur
        signature = self._get_function_signature(node)
        
        symbol = Symbol(
            name=node.name,
            type=symbol_type,
            line=node.lineno,
            column=node.col_offset,
            class_name=self.current_class if is_method else None,
            parent=self.current_class,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            signature=signature,
            docstring=ast.get_docstring(node)
        )
        self.symbols.append(symbol)
        
        # İç içe fonksiyonları ziyaret etme (sadece üst seviye)
        # Metodun içindeki değişkenleri çıkar
        self._extract_variables(node)
    
    def _get_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Fonksiyon imzasını oluştur."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        # *args ve **kwargs
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        sig = f"({', '.join(args)})"
        if node.returns:
            sig += f" -> {ast.unparse(node.returns)}"
        
        return sig
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Dekoratör adını al."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{ast.unparse(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return f"{decorator.func.id}()"
            elif isinstance(decorator.func, ast.Attribute):
                return f"{ast.unparse(decorator.func.value)}.{decorator.func.attr}()"
        return "<unknown>"
    
    def _extract_variables(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Fonksiyon içindeki yerel değişkenleri çıkar."""
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        # Büyük harfli değişkenleri constant olarak işaretle
                        is_constant = target.id.isupper() and '_' in target.id
                        symbol = Symbol(
                            name=target.id,
                            type=SymbolType.CONSTANT.value if is_constant else SymbolType.VARIABLE.value,
                            line=child.lineno,
                            column=child.col_offset,
                            class_name=self.current_class,
                            parent=node.name
                        )
                        self.symbols.append(symbol)


class RegexSymbolExtractor:
    """Regex tabanlı sembol çıkarıcı (diğer diller için)."""
    
    # Dil başına regex pattern'leri
    PATTERNS = {
        'javascript': {
            'class': r'class\s+(\w+)',
            'function': r'function\s+(\w+)',
            'arrow_function_const': r'const\s+(\w+)\s*=\s*(?:async\s*)?\(',
            'method': r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{',
            'interface': r'interface\s+(\w+)',
            'enum': r'enum\s+(\w+)',
        },
        'typescript': {
            'class': r'class\s+(\w+)',
            'function': r'function\s+(\w+)',
            'interface': r'interface\s+(\w+)',
            'enum': r'enum\s+(\w+)',
            'type': r'type\s+(\w+)',
            'method': r'(?:public|private|protected|readonly)?\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*:',
        },
        'java': {
            'class': r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)',
            'interface': r'interface\s+(\w+)',
            'enum': r'enum\s+(\w+)',
            'method': r'(?:public|private|protected)?\s*(?:static|final|abstract)?\s*(?:\w+)\s+(\w+)\s*\([^)]*\)\s*(?:\{|;|\w+)',
        },
        'csharp': {
            'class': r'(?:public|private|protected|internal)?\s*(?:abstract|sealed|static)?\s*class\s+(\w+)',
            'interface': r'interface\s+(\w+)',
            'enum': r'enum\s+(\w+)',
            'method': r'(?:public|private|protected|internal)?\s*(?:static|virtual|abstract|override)?\s*(?:\w+)\s+(\w+)\s*\([^)]*\)',
        },
        'go': {
            'function': r'func\s+(\w+)',
            'method': r'func\s+\([^)]*\)\s*(\w+)',
            'struct': r'type\s+(\w+)\s+struct',
            'interface': r'type\s+(\w+)\s+interface',
        },
        'rust': {
            'function': r'fn\s+(\w+)',
            'struct': r'struct\s+(\w+)',
            'enum': r'enum\s+(\w+)',
            'trait': r'trait\s+(\w+)',
            'impl': r'impl\s+(?:\w+\s+for\s+)?(\w+)',
        },
        'cpp': {
            'class': r'class\s+(\w+)',
            'struct': r'struct\s+(\w+)',
            'function': r'(?:\w+[\s*&]+)+(\w+)\s*\([^)]*\)\s*(?:\{|const)',
            'namespace': r'namespace\s+(\w+)',
        },
        'php': {
            'class': r'class\s+(\w+)',
            'function': r'function\s+(\w+)',
            'interface': r'interface\s+(\w+)',
            'trait': r'trait\s+(\w+)',
        },
        'ruby': {
            'class': r'class\s+(\w+)',
            'module': r'module\s+(\w+)',
            'method': r'def\s+(\w+)',
        },
    }
    
    def __init__(self, source_code: str, language: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.language = language.lower()
        self.filename = filename
        self.lines = source_code.split('\n')
    
    def extract(self) -> List[Symbol]:
        """Regex pattern'leri kullanarak sembolleri çıkar."""
        symbols = []
        
        if self.language not in self.PATTERNS:
            return symbols
        
        patterns = self.PATTERNS[self.language]
        current_class = None
        
        for line_num, line in enumerate(self.lines, 1):
            line_stripped = line.strip()
            
            # Yorum satırlarını atla
            if line_stripped.startswith('//') or line_stripped.startswith('#'):
                continue
            
            # Class/Struct detection
            for pattern_type in ['class', 'struct', 'interface', 'enum', 'trait']:
                if pattern_type in patterns:
                    match = re.search(patterns[pattern_type], line)
                    if match:
                        name = match.group(1)
                        current_class = name
                        symbols.append(Symbol(
                            name=name,
                            type=pattern_type,
                            line=line_num,
                            column=line.index(name) if name in line else 0
                        ))
            
            # Function/Method detection
            for pattern_type in ['function', 'method', 'arrow_function_const']:
                if pattern_type in patterns:
                    match = re.search(patterns[pattern_type], line)
                    if match:
                        name = match.group(1)
                        # Anahtar kelimeleri filtrele
                        if name in ['if', 'while', 'for', 'switch', 'catch']:
                            continue
                        
                        symbol_type = 'method' if current_class and pattern_type != 'function' else 'function'
                        symbols.append(Symbol(
                            name=name,
                            type=symbol_type,
                            line=line_num,
                            column=line.index(name) if name in line else 0,
                            class_name=current_class if symbol_type == 'method' else None
                        ))
        
        return symbols


class SymbolExtractor:
    """Ana sembol çıkarıcı sınıfı - dil tespiti ve uygun extractor seçimi."""
    
    # Dosya uzantısı -> dil eşleştirmesi
    EXTENSION_MAP = {
        '.py': 'python',
        '.pyw': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.h': 'cpp',
        '.php': 'php',
        '.rb': 'ruby',
    }
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'symbols_found': 0,
            'errors': 0
        }
    
    def detect_language(self, filepath: str) -> Optional[str]:
        """Dosya yolundan dili tespit et."""
        path = Path(filepath)
        ext = path.suffix.lower()
        return self.EXTENSION_MAP.get(ext)
    
    def extract_from_file(self, filepath: str) -> Optional[FileSymbols]:
        """Bir dosyadan sembolleri çıkar."""
        path = Path(filepath)
        
        if not path.exists():
            return None
        
        language = self.detect_language(filepath)
        if not language:
            return None
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            return self.extract_from_source(source_code, filepath, language)
            
        except Exception as e:
            self.stats['errors'] += 1
            return None
    
    def extract_from_source(self, source_code: str, filepath: str, language: str) -> FileSymbols:
        """Kaynak kodundan sembolleri çıkar."""
        symbols = []
        
        if language == 'python':
            # Python için AST kullan
            extractor = PythonSymbolExtractor(source_code, filepath)
            symbols = extractor.extract()
        else:
            # Diğer diller için regex kullan
            extractor = RegexSymbolExtractor(source_code, language, filepath)
            symbols = extractor.extract()
        
        self.stats['files_processed'] += 1
        self.stats['symbols_found'] += len(symbols)
        
        return FileSymbols(
            file=filepath,
            language=language,
            symbols=symbols
        )
    
    # native_adapter ile uyumlu yasaklı dizinler
    FORBIDDEN_DIRS = {
        "node_modules", ".venv", "dist", "build", ".git",
        "__pycache__", "target", ".bbc", ".old", "venv",
        ".tox", ".mypy_cache", ".pytest_cache", "env",
    }

    def extract_from_directory(self, directory: str,
                               extensions: Optional[List[str]] = None,
                               max_files: Optional[int] = None) -> List[FileSymbols]:
        """
        Bir dizinden tüm dosyalardan sembolleri çıkar.

        Args:
            directory: Taranacak dizin
            extensions: Dosya uzantıları (None ise EXTENSION_MAP kullanılır)
            max_files: Performans limiti — en fazla bu kadar dosya işlenir (None ise BBCConfig.MAX_FILES)
        """
        from .config import BBCConfig
        if max_files is None:
            max_files = BBCConfig.MAX_FILES

        if extensions is None:
            extensions = list(self.EXTENSION_MAP.keys())

        results = []
        path = Path(directory)
        files_processed = 0

        for root, dirs, files in os.walk(str(path)):
            # Yasaklı dizinleri atla (native_adapter ile uyumlu)
            dirs[:] = [d for d in dirs if d not in self.FORBIDDEN_DIRS and not d.startswith('.')]

            for fname in sorted(files):
                if files_processed >= max_files:
                    break

                fpath = Path(root) / fname
                if fpath.suffix.lower() in set(extensions):
                    result = self.extract_from_file(str(fpath))
                    if result and result.symbols:
                        results.append(result)
                    files_processed += 1

            if files_processed >= max_files:
                break

        return results
    
    def get_stats(self) -> Dict[str, int]:
        """İstatistikleri döndür."""
        return self.stats.copy()
    
    def export_to_json(self, results: List[FileSymbols], output_path: str):
        """Sonuçları JSON dosyasına kaydet."""
        data = {
            'stats': self.stats,
            'files': [r.to_dict() for r in results]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def get_supported_languages() -> List[str]:
        """Desteklenen dilleri döndür."""
        return list(set(SymbolExtractor.EXTENSION_MAP.values()))


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BBC Symbol Extractor - Stage 1 for symbol-based analysis'
    )
    parser.add_argument('path', help='File or directory path')
    parser.add_argument('--out', '-o', help='Output JSON file', default='symbols.json')
    parser.add_argument('--lang', '-l', help='Language hint (python, javascript, etc.)')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics')
    
    args = parser.parse_args()
    
    extractor = SymbolExtractor()
    path = Path(args.path)
    
    if path.is_file():
        result = extractor.extract_from_file(str(path))
        if result:
            print(result.to_json())
            if args.out:
                with open(args.out, 'w', encoding='utf-8') as f:
                    f.write(result.to_json())
        else:
            print(f"Error: failed to process file: {path}")
    
    elif path.is_dir():
        results = extractor.extract_from_directory(str(path))
        extractor.export_to_json(results, args.out)
        print(f"Processed {len(results)} files, found {extractor.stats['symbols_found']} symbols")
        print(f"Output: {args.out}")
    
    if args.stats:
        print(f"\nStatistics:")
        for key, value in extractor.get_stats().items():
            print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
