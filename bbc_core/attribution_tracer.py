import re
import os
from collections import defaultdict
from .config import BBCConfig

class AttributionTracer:
    """
    BBC Attribution Engine v1.0
    Builds a project-wide call graph using static analysis.
    
    Method: Regex-based (lightweight and fast)
    Goal: Determine which files are impacted by an error in a target file.
    """
    def __init__(self, project_root):
        self.project_root = project_root
        self.symbol_map = {} # {symbol_name: defined_in_file}
        self.reference_map = defaultdict(list) # {symbol_name: [used_in_file1, used_in_file2]}
        self.ignore_dirs = BBCConfig.get_forbidden_scan_dirs({
            '.svn', '.hg', 'vendor', 'packages', 'out', '.temp', '.clinerules'
        })

    def _iter_source_files(self, target_extensions):
        """Yield source files while skipping heavyweight/non-source directories."""
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in files:
                if file.lower().endswith(target_extensions):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, self.project_root)
                    yield path, rel_path
        
    def scan_project(self, target_extensions=None):
        """Projedeki all tanimlari ve kullanimlari tarar."""
        if not target_extensions:
            target_extensions = ('.py', '.js', '.ts', '.c', '.cpp', '.h', '.java', '.go', '.rs')
            
        print(f"[*] Attribution Tracer: Scanning dependency network in {self.project_root}...")
        
        # 1. PASS: Tanimlari Bul (Definition Scan)
        for path, rel_path in self._iter_source_files(target_extensions):
            self._extract_definitions(path, rel_path)
                    
        print(f"[*] Knowledge Base: Found {len(self.symbol_map)} global symbols.")

        # 2. PASS: Kullanimlari Bul (Reference Scan)
        # (Optimizasyon: Sadece iliskili olabilecek files tara)
        # Simdilik basitlik adina ayni file setini tariyoruz.
        count = 0
        for path, rel_path in self._iter_source_files(target_extensions):
            self._find_references(path, rel_path)
            count += 1
        
        print(f"[*] Trace Complete: Mapped {len(self.reference_map)} cross-file references across {count} files.")

    def _extract_definitions(self, file_path, rel_path):
        """Dosyadaki fonksiyon/sinif tanimlarini bulur."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Basit Regex Patternleri (Polyglot)
            # Python: def foo, class Bar
            # C/JS/Java: function foo, class Bar, void foo(
            
            patterns = [
                r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', # Python func
                r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', # Class def
                r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)', # JS func
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', # Generic C-style func call/def (agresif)
            ]
            
            for pat in patterns:
                matches = re.finditer(pat, content)
                for m in matches:
                    symbol = m.group(1)
                    if len(symbol) > 3: # Gurultu onleme (if, for gibi kisa kelimeleri atla)
                        # Cakisma varsa listeye ekle (Overloading destegi)
                        if symbol not in self.symbol_map:
                            self.symbol_map[symbol] = []
                        if rel_path not in self.symbol_map[symbol]:
                            self.symbol_map[symbol].append(rel_path)
        except Exception:
            pass

    def _find_references(self, file_path, rel_path):
        """Dosyadaki symbol kullanimlarini bulur."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Tum bilinen symbols bu dosyada ara
            # (Bu kisim buyuk projelerde yavas olabilir, v7.3'te optimize edilecek)
            # Hiz for only import edilenleri veya basit text search'u kullanacagiz.
            
            # Basit Text Search (Hizli ama kaba)
            for symbol in self.symbol_map:
                if symbol in content:
                    # Kendi dosyasindaki kullanimi referans sayma (Self-reference exclusion)
                    if rel_path not in self.symbol_map[symbol]:
                        self.reference_map[symbol].append(rel_path)
        except Exception:
            pass

    def trace_impact(self, faulty_file):
        """
        Hatali dosyanin kimleri etkileyecegini raporlar.
        Input: faulty_file (Hatali file yolu)
        Output: Etkilenen dosyalar listesi (Blast Radius)
        """
        impacted_files = set()
        
        # 1. Hatali dosyadaki symbols bul
        defined_symbols = [sym for sym, files in self.symbol_map.items() if faulty_file in files]
        
        # 2. Bu symbols kullananlari bul
        for sym in defined_symbols:
            users = self.reference_map.get(sym, [])
            impacted_files.update(users)
            
        return list(impacted_files)
