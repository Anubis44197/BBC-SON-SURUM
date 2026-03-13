import re
import os
from collections import defaultdict

class AttributionTracer:
    """
    BBC Attribution Engine (Suçlu Bulma Motoru) v1.0
    Statik analiz ile proje genelindeki 'Call Graph' (Çağrı Ağı) haritasını çıkarır.
    
    Yöntem: Regex (Hafif ve Hızlı)
    Amaç: Bir dosyadaki hatanın, hangi diğer dosyaları etkilediğini bulmak.
    """
    def __init__(self, project_root):
        self.project_root = project_root
        self.symbol_map = {} # {symbol_name: defined_in_file}
        self.reference_map = defaultdict(list) # {symbol_name: [used_in_file1, used_in_file2]}
        
    def scan_project(self, target_extensions=None):
        """Projedeki tüm tanımları ve kullanımları tarar."""
        if not target_extensions:
            target_extensions = ('.py', '.js', '.ts', '.c', '.cpp', '.h', '.java', '.go', '.rs')
            
        print(f"[*] Attribution Tracer: Scanning dependency network in {self.project_root}...")
        
        # 1. PASS: Tanımları Bul (Definition Scan)
        for root, _, files in os.walk(self.project_root):
            for file in files:
                if file.lower().endswith(target_extensions):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, self.project_root)
                    self._extract_definitions(path, rel_path)
                    
        print(f"[*] Knowledge Base: Found {len(self.symbol_map)} global symbols.")

        # 2. PASS: Kullanımları Bul (Reference Scan)
        # (Optimizasyon: Sadece ilişkili olabilecek dosyaları tara)
        # Şimdilik basitlik adına aynı dosya setini tarıyoruz.
        count = 0
        for root, _, files in os.walk(self.project_root):
            for file in files:
                if file.lower().endswith(target_extensions):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, self.project_root)
                    self._find_references(path, rel_path)
                    count += 1
        
        print(f"[*] Trace Complete: Mapped {len(self.reference_map)} cross-file references across {count} files.")

    def _extract_definitions(self, file_path, rel_path):
        """Dosyadaki fonksiyon/sınıf tanımlarını bulur."""
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
                    if len(symbol) > 3: # Gürültü önleme (if, for gibi kısa kelimeleri atla)
                        # Çakışma varsa listeye ekle (Overloading desteği)
                        if symbol not in self.symbol_map:
                            self.symbol_map[symbol] = []
                        if rel_path not in self.symbol_map[symbol]:
                            self.symbol_map[symbol].append(rel_path)
        except Exception:
            pass

    def _find_references(self, file_path, rel_path):
        """Dosyadaki sembol kullanımlarını bulur."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Tüm bilinen sembolleri bu dosyada ara
            # (Bu kısım büyük projelerde yavaş olabilir, v7.3'te optimize edilecek)
            # Hız için sadece import edilenleri veya basit text search'ü kullanacağız.
            
            # Basit Text Search (Hızlı ama kaba)
            for symbol in self.symbol_map:
                if symbol in content:
                    # Kendi dosyasındaki kullanımı referans sayma (Self-reference exclusion)
                    if rel_path not in self.symbol_map[symbol]:
                        self.reference_map[symbol].append(rel_path)
        except Exception:
            pass

    def trace_impact(self, faulty_file):
        """
        Hatalı dosyanın kimleri etkileyeceğini raporlar.
        Input: faulty_file (Hatalı dosya yolu)
        Output: Etkilenen dosyalar listesi (Blast Radius)
        """
        impacted_files = set()
        
        # 1. Hatalı dosyadaki sembolleri bul
        defined_symbols = [sym for sym, files in self.symbol_map.items() if faulty_file in files]
        
        # 2. Bu sembolleri kullananları bul
        for sym in defined_symbols:
            users = self.reference_map.get(sym, [])
            impacted_files.update(users)
            
        return list(impacted_files)
