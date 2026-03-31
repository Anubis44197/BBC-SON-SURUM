import re
import time
import os

class HMPUQuantizer:
    """
    BBC HMPU Polyglot Quantizer (v8.0 Enhanced)
    
    Bu motor, metin verisini (kod) analysis ederek yapisal bilesenlerini (Siniflar, Fonksiyonlar)
    deterministik olarak cikarir. 
    
    DESTEKLENEN DILLER:
    - Python (Tree-sitter AST), Rust, JS/TS, Go
    - C/C++, Java, C#, Swift, Kotlin
    - PHP, Ruby, SQL
    
    v8.0: Tree-sitter integration for Python with simple cache
    """
    
    def __init__(self, project_root=None, use_enhanced=True):
        # Quantizer initialized silently (v8.0)
        self.project_root = project_root
        self.enhanced_extractor = None
        
        # Try to load full symbol extractor with tree-sitter
        if use_enhanced and project_root:
            try:
                from bbc_core.full_symbol_extractor import FullSymbolExtractor
                self.enhanced_extractor = FullSymbolExtractor(
                    project_root,
                    use_cache=True,
                    use_indices=True
                )
            except Exception:
                pass
        
        # Regex Patterns for ALL Major Languages
        self.PATTERNS = {
            "python": {
                "class": r'''^\s*class\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*def\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)'''
            },
            "rust": {
                "class": r'''^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*(?:pub\s+)?fn\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*use\s+([a-zA-Z0-9_:]+)'''
            },
            "javascript": {
                "class": r'''^\s*(?:export\s+)?class\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)''',
                "variable_func": r'''^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?(?:function|\(.*\)\s*=>)''',
                "object_method": r'''^\s{2,}([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{''',
                "import": r'''^\s*import\s+.*\s+from\s+['"](.*?)['"]'''
            },
            "go": {
                "class": r'''^\s*type\s+([a-zA-Z0-9_]+)\s+struct''',
                "function": r'''^\s*func\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*import\s+['"](.*?)['"]'''
            },
            "c_cpp": {
                "class": r'''^\s*(?:class|struct)\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*(?:[a-zA-Z0-9_]+[\s\*]+)+([a-zA-Z0-9_]+)\s*\(''', # ReturnType funcName(
                "import": r'''^\s*#include\s+[<"](.*?)['">]'''
            },
            "java_csharp": {
                "class": r'''^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:class|interface|enum)\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:[a-zA-Z0-9_<>\[\]]+\s+)+([a-zA-Z0-9_]+)\s*\(''',
                "import": r'''^\s*(?:import|using)\s+([a-zA-Z0-9_\.]+)'''
            },
            "php": {
                "class": r'''^\s*(?:abstract\s+)?class\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*function\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*(?:use|require|include)\s+['"](.*?)['"]'''
            },
            "ruby": {
                "class": r'''^\s*class\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*def\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*require\s+['"](.*?)['"]'''
            },
            "swift": {
                "class": r'''^\s*(?:public|private)?\s*(?:class|struct|enum|protocol)\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*(?:public|private)?\s*func\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*import\s+([a-zA-Z0-9_]+)'''
            },
            "kotlin": {
                "class": r'''^\s*(?:open|data)?\s*class\s+([a-zA-Z0-9_]+)''',
                "function": r'''^\s*fun\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*import\s+([a-zA-Z0-9_\.]+)'''
            },
            "sql": {
                "class": r'''^\s*CREATE\s+TABLE\s+([a-zA-Z0-9_]+)''', # Table as Class
                "function": r'''^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\s+([a-zA-Z0-9_]+)''',
                "import": r'''^\s*--\s*IMPORT\s+(.*)''' # Dummy for SQL
            }
        }
        
        # Aliases
        self.PATTERNS["typescript"] = self.PATTERNS["javascript"]
        self.PATTERNS["c"] = self.PATTERNS["c_cpp"]
        self.PATTERNS["cpp"] = self.PATTERNS["c_cpp"]
        self.PATTERNS["java"] = self.PATTERNS["java_csharp"]
        self.PATTERNS["csharp"] = self.PATTERNS["java_csharp"]

    def detect_language(self, content):
        """Icerik analysis ile dil tahmini."""
        if "#include" in content: return "c_cpp"
        if "public class" in content: return "java"
        if "func " in content and "var " in content: return "go"
        if "fn " in content: return "rust"
        if "def " in content and ":" in content: return "python"
        return "python" # Default

    def process_content(self, content, file_ext=None, file_path=None):
        start_time = time.time()
        
        # Try enhanced extractor first (tree-sitter)
        if self.enhanced_extractor and file_ext:
            try:
                symbols = self.enhanced_extractor.extract_symbols(
                    file_path or "unknown",
                    content,
                    file_ext
                )
                
                # Convert to legacy format
                structure = self._convert_to_legacy_format(symbols)
                
                duration = time.time() - start_time
                return {
                    "structure": structure,
                    "stats": {
                        "size": len(content),
                        "time": duration,
                        "method": symbols.get('_meta', {}).get('method', 'tree-sitter')
                    }
                }
            except Exception:
                pass
        
        # Fallback to regex (original implementation)
        lang = "python"
        if file_ext:
            ext = file_ext.lower()
            if ext in ['.rs']: lang = "rust"
            elif ext in ['.js', '.jsx', '.ts', '.tsx']: lang = "javascript"
            elif ext in ['.go']: lang = "go"
            elif ext in ['.c', '.h', '.cpp', '.hpp']: lang = "c_cpp"
            elif ext in ['.java', '.cs']: lang = "java_csharp"
            elif ext in ['.php']: lang = "php"
            elif ext in ['.rb']: lang = "ruby"
            elif ext in ['.swift']: lang = "swift"
            elif ext in ['.kt', '.kts']: lang = "kotlin"
            elif ext in ['.sql']: lang = "sql"
        else:
            lang = self.detect_language(content)
            
        patterns = self.PATTERNS.get(lang, self.PATTERNS["python"])
        
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "language": lang
        }
        
        try:
            if "class" in patterns:
                for match in re.finditer(patterns["class"], content, re.MULTILINE):
                    structure["classes"].append(match.group(1))
            
            if "function" in patterns:
                for match in re.finditer(patterns["function"], content, re.MULTILINE):
                    structure["functions"].append(match.group(1))
                
            if "variable_func" in patterns:
                for match in re.finditer(patterns["variable_func"], content, re.MULTILINE):
                    structure["functions"].append(match.group(1))
            
            if "object_method" in patterns:
                for match in re.finditer(patterns["object_method"], content, re.MULTILINE):
                    method_name = match.group(1)
                    if method_name not in ['if', 'for', 'while', 'switch', 'catch', 'with']:
                        structure["functions"].append(method_name)
            
            if "import" in patterns:
                for match in re.finditer(patterns["import"], content, re.MULTILINE):
                    structure["imports"].append(match.group(1))
                
        except Exception as e:
            print(f"[!] Quantizer Error: {e}")
            
        duration = time.time() - start_time
        return {
            "structure": structure,
            "stats": {"size": len(content), "time": duration, "method": "regex"}
        }
    
    def _convert_to_legacy_format(self, symbols: dict) -> dict:
        """Convert new symbol format to legacy format for compatibility"""
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "language": symbols.get('_meta', {}).get('language', 'unknown')
        }
        
        # Extract class names
        for cls in symbols.get('classes', []):
            if isinstance(cls, dict):
                structure["classes"].append(cls.get('name', 'Unknown'))
            else:
                structure["classes"].append(str(cls))
        
        # Extract function names
        for func in symbols.get('functions', []):
            if isinstance(func, dict):
                structure["functions"].append(func.get('name', 'unknown'))
            else:
                structure["functions"].append(str(func))
        
        # Extract import names
        for imp in symbols.get('imports', []):
            if isinstance(imp, dict):
                structure["imports"].append(imp.get('name') or imp.get('path') or imp.get('source', 'unknown'))
            else:
                structure["imports"].append(str(imp))
        
        return structure
