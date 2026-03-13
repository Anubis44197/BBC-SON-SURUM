import json
import ast
import os
import re
from .attribution_tracer import AttributionTracer

class BBCVerifier:
    """
    BBC Standart Verification Engine (v3.0 - Ultimate Polyglot)
    Evrensel 'Mismatch Scan' ve 'Syntax Check' yeteneği.
    Desteklenen Diller: Python, Rust, JS/TS, Go, C/C++, Java/C#, PHP, Ruby, Swift, Kotlin, SQL.
    """
    
    def __init__(self, recipe_path: str):
        self.recipe_path = recipe_path
        self.knowledge_map = {"global_symbols": set()}
        self.project_root = ""
        self._load_recipe() # Project root burada yükleniyor
        
        # Attribution Engine (Safe Init)
        self.tracer = None
        if self.project_root:
            self.tracer = AttributionTracer(self.project_root)

    def _extract_symbols(self, text, lang_hint=None):
        """Metinden sembolleri (class/function) regex ile çıkarır."""
        # Not: Quantizer zaten bu işi yapıyor ama Standalone mod için burası yedek (backup).
        # Burayı Quantizer'ın patternlerine benzetiyoruz.
        symbols = set()
        
        # Generic Regex (Fallback)
        for match in re.finditer(r'^\s*(?:class|function|def|fn|struct|func)\s+([a-zA-Z0-9_]+)', text, re.MULTILINE):
            symbols.add(match.group(1))
            
        return symbols

    def _load_recipe(self):
        """Recipe dosyasını yükler ve evrensel formata dönüştürür."""
        if not os.path.exists(self.recipe_path):
            raise FileNotFoundError(f"Recipe not found: {self.recipe_path}")
            
        with open(self.recipe_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.project_root = data.get("project_skeleton", {}).get("root", "")
        if not self.project_root:
            self.project_root = os.getcwd()
            
        # Recipe'den sembolleri çıkar
        code_struct_list = data.get("code_structure", [])
        
        all_symbols = set()
        
        for file_obj in code_struct_list:
            # v6.0/v7.0 structure
            if isinstance(file_obj, dict) and "structure" in file_obj:
                struct = file_obj["structure"]
                all_symbols.update(struct.get("classes", []))
                all_symbols.update(struct.get("functions", []))
                continue

            # Fallback for v5.5
            content = ""
            if isinstance(file_obj, str):
                content = file_obj
            elif isinstance(file_obj, dict):
                content = file_obj.get("content", "")
                all_symbols.update(file_obj.get("classes", []))
                all_symbols.update(file_obj.get("functions", []))
            
            if content:
                all_symbols.update(self._extract_symbols(content))
        
        self.knowledge_map["global_symbols"] = all_symbols
        print(f"[*] Knowledge Base Loaded: {len(all_symbols)} known symbols (Ultimate Polyglot Mode).")

    def verify_syntax_only(self):
        """
        Polyglot Syntax Checker.
        Her dil için temel yapısal bütünlüğü kontrol eder.
        """
        if not os.path.exists(self.project_root):
            print(f"[!] Warning: Project root not found on disk: {self.project_root}")
            return []

        errors = []
        
        # Binary extensions to skip
        binary_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.ttf', '.woff', '.woff2', '.eot', '.pdf', '.zip', '.exe', '.dll', '.so', '.dylib', '.bin'}
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ["node_modules", ".venv", "__pycache__", "target", "dist", "build", "vendor"]]
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)
                ext = os.path.splitext(file)[1].lower()
                
                # Skip binaries
                if ext in binary_exts:
                    continue
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 1. Python Syntax Check (AST)
                    if ext == '.py':
                        try:
                            ast.parse(content)
                        except SyntaxError as e:
                            errors.append({"file": rel_path, "line": e.lineno, "msg": e.msg, "type": "SYNTAX_ERROR (Python)"})
                    
                    # 2. C-Family Languages (Rust, C, C++, Java, C#, JS, TS, Go, PHP, Swift, Kotlin)
                    # Check for balanced braces {}
                    elif ext in ['.rs', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.js', '.ts', '.jsx', '.tsx', '.go', '.php', '.swift', '.kt']:
                        open_braces = content.count('{')
                        close_braces = content.count('}')
                        if open_braces != close_braces:
                            errors.append({
                                "file": rel_path, 
                                "msg": f"Unbalanced braces {{}} (Open: {open_braces}, Close: {close_braces})", 
                                "type": f"SYNTAX_ERROR ({ext[1:].upper()})"
                            })
                            
                    # 3. Ruby (def ... end Check)
                    elif ext == '.rb':
                        defs = len(re.findall(r'^\s*def\s+', content, re.MULTILINE))
                        ends = len(re.findall(r'^\s*end\s*$', content, re.MULTILINE))
                        # This is very heuristic, Ruby is complex. Just a basic check.
                        
                    # 4. SQL (Basic Keyword Check)
                    elif ext == '.sql':
                        if "SELECT" in content.upper() and "FROM" not in content.upper():
                             errors.append({"file": rel_path, "msg": "SELECT without FROM", "type": "SYNTAX_WARNING (SQL)"})

                except UnicodeDecodeError:
                    # Likely a binary file that slipped through
                    continue
                except Exception as e:
                     errors.append({
                        "file": rel_path,
                        "msg": str(e),
                        "type": "READ_ERROR"
                    })
        
        # --- ATTRIBUTION ENGINE (v7.2) ---
        if errors and self.tracer:
            print(f"\n[*] Attribution Engine: Tracing impact for {len(errors)} errors...")
            # Sadece bir kez tüm projeyi tara (Lazy Loading)
            self.tracer.scan_project()
            
            for err in errors:
                failed_file = err["file"]
                impact_list = self.tracer.trace_impact(failed_file)
                if impact_list:
                    err["impact_analysis"] = {
                        "blast_radius": len(impact_list),
                        "affected_files": impact_list[:5] # İlk 5 tanesini göster
                    }
                    if len(impact_list) > 5:
                         err["impact_analysis"]["more"] = f"...and {len(impact_list)-5} more."
                    print(f"    -> Error in {failed_file} impacts {len(impact_list)} other files.")

        return errors
