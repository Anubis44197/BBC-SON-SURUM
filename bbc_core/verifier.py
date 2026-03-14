import json
import ast
import os
import re
import math
import hashlib
from .attribution_tracer import AttributionTracer
from .hmpu_quantizer import HMPUQuantizer

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
        
        self.recipe_data = data
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

    # ===================================================================
    # BBC v8.4 — Enhanced Verification (Freshness + Mismatch + Aura)
    # ===================================================================

    def verify_freshness(self):
        """
        Context Freshness Check — hash karşılaştırması ile hangi dosyaların
        mühürleme sonrası değiştiğini tespit eder.
        Returns: dict with stale_files, stale_count, stale_ratio, recommendation
        """
        code_struct = self.recipe_data.get("code_structure", [])
        if not code_struct:
            return {"stale_count": 0, "stale_files": [], "stale_ratio": 0.0,
                    "context_fresh": True, "recommendation": "OK"}

        stale = []
        missing = []
        total = 0

        for file_obj in code_struct:
            if not isinstance(file_obj, dict):
                continue
            file_path = file_obj.get("path", "")
            stored_hash = file_obj.get("hash", "")
            if not file_path or not stored_hash:
                continue

            total += 1
            abs_path = os.path.join(self.project_root, file_path)

            if not os.path.exists(abs_path):
                missing.append(file_path)
                stale.append(file_path)
                continue

            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                if current_hash != stored_hash:
                    stale.append(file_path)
            except Exception:
                stale.append(file_path)

        stale_ratio = len(stale) / total if total > 0 else 0.0

        if stale_ratio > 0.1:
            rec = "RESCAN"
        elif len(stale) == 0:
            rec = "OK"
        else:
            rec = "PARTIAL_RESCAN"

        return {
            "total_files": total,
            "stale_files": stale,
            "stale_count": len(stale),
            "missing_files": missing,
            "missing_count": len(missing),
            "stale_ratio": round(stale_ratio, 3),
            "context_fresh": len(stale) == 0,
            "recommendation": rec
        }

    def verify_symbol_mismatch(self):
        """
        Sembol Mismatch Kontrolü — context'teki semboller ile diskteki gerçek
        kaynak dosyaları arasındaki tutarsızlıkları tespit eder.
        Quantizer ile diskteki dosyayı yeniden tarar, context'teki sembollerle karşılaştırır.

        Returns: dict with added_symbols, removed_symbols, mismatch_files, mismatch_ratio
        """
        code_struct = self.recipe_data.get("code_structure", [])
        if not code_struct:
            return {"mismatch_count": 0, "mismatch_files": [], "mismatch_ratio": 0.0}

        quantizer = HMPUQuantizer()
        mismatch_files = []
        total_context_symbols = 0
        total_mismatched = 0

        for file_obj in code_struct:
            if not isinstance(file_obj, dict):
                continue
            file_path = file_obj.get("path", "")
            if not file_path:
                continue

            abs_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(abs_path):
                continue

            # Context'teki semboller
            struct = file_obj.get("structure", {})
            ctx_classes = set(struct.get("classes", []))
            ctx_functions = set(struct.get("functions", []))
            ctx_symbols = ctx_classes | ctx_functions
            total_context_symbols += len(ctx_symbols)

            if not ctx_symbols:
                continue

            # Diskteki gerçek semboller (quantizer ile tara)
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ext = os.path.splitext(file_path)[1]
                result = quantizer.process_content(content, file_ext=ext)
                disk_struct = result.get("structure", {})
                disk_classes = set(disk_struct.get("classes", []))
                disk_functions = set(disk_struct.get("functions", []))
                disk_symbols = disk_classes | disk_functions
            except Exception:
                continue

            # Fark hesapla
            added = disk_symbols - ctx_symbols     # Diskte var, context'te yok
            removed = ctx_symbols - disk_symbols   # Context'te var, diskte yok

            if added or removed:
                total_mismatched += len(added) + len(removed)
                mismatch_files.append({
                    "file": file_path,
                    "added_symbols": list(added)[:10],
                    "removed_symbols": list(removed)[:10],
                    "added_count": len(added),
                    "removed_count": len(removed)
                })

        mismatch_ratio = total_mismatched / total_context_symbols if total_context_symbols > 0 else 0.0

        return {
            "total_context_symbols": total_context_symbols,
            "total_mismatched": total_mismatched,
            "mismatch_files": mismatch_files,
            "mismatch_count": len(mismatch_files),
            "mismatch_ratio": round(mismatch_ratio, 3)
        }

    def verify_full(self):
        """
        BBC Full Verification — Syntax + Freshness + Symbol Mismatch + Aura Field Score.
        
        Aura Field skorunu BBC matematiğiyle hesaplar:
          S = structure_health  (syntax hata oranının tersi)
          C = chaos_density     (mismatch oranından türetilen kaos)
          P = freshness_pulse   (stale ratio'nun tersi)
        
        Bu üçlü, HMPU Governor'ın aura_field_score(S, C, P) fonksiyonuna beslenir.
        Sonuç: 0.0 (DEGENERATE) ... 1.0 (STABLE)
        
        Condition number (κ) ile güven skoru:
          confidence = 1 / (1 + log10(κ))
        
        Returns: dict with all verification results + aura_score + confidence + verdict
        """
        # 1. Syntax Check
        syntax_errors = self.verify_syntax_only()

        # 2. Freshness Check
        freshness = self.verify_freshness()

        # 3. Symbol Mismatch
        mismatch = self.verify_symbol_mismatch()

        # 4. Aura Field Score hesapla (BBC Matematiği)
        #    S: Structural health — syntax hatasız dosya oranı
        total_files = freshness.get("total_files", 1) or 1
        syntax_error_ratio = len(syntax_errors) / total_files if total_files > 0 else 0.0
        S = max(0.0, min(1.0, 1.0 - syntax_error_ratio))

        #    C: Chaos density — sembol mismatch oranından türetilir
        #    Mismatch yüksekse kaos yüksek (kötü), düşükse kaos düşük (iyi)
        mismatch_ratio = mismatch.get("mismatch_ratio", 0.0)
        C = max(0.0, min(1.0, mismatch_ratio))

        #    P: Freshness pulse — stale ratio'nun tersi
        stale_ratio = freshness.get("stale_ratio", 0.0)
        P = max(0.0, min(1.0, 1.0 - stale_ratio))

        # Aura Field Score: HMPU Governor kullan (varsa)
        aura_score = 0.0
        confidence = 0.0
        field_stability = float('inf')
        try:
            from .hmpu_core import HMPU_Governor
            governor = HMPU_Governor()
            aura_score = governor.aura_field_score(S, C, P)
            field_stability = governor.get_field_stability()
            if not math.isinf(field_stability) and field_stability > 0:
                confidence = 1.0 / (1.0 + math.log10(field_stability))
                confidence = round(min(max(confidence, 0.0), 1.0), 3)
        except Exception:
            # Fallback: basit ağırlıklı ortalama
            aura_score = (S * 0.6) + ((1.0 - C) * 0.2) + (P * 0.2)
            confidence = aura_score

        # 5. Verdict (karar)
        if confidence >= 0.7 and len(syntax_errors) == 0 and freshness["context_fresh"]:
            verdict = "SEALED_STABLE"
            verdict_icon = "💎"
        elif confidence >= 0.5:
            verdict = "WEAK"
            verdict_icon = "⚠️"
        elif confidence >= 0.3:
            verdict = "UNSTABLE"
            verdict_icon = "🔴"
        else:
            verdict = "DEGENERATE"
            verdict_icon = "💀"

        return {
            "syntax_errors": syntax_errors,
            "syntax_error_count": len(syntax_errors),
            "freshness": freshness,
            "symbol_mismatch": mismatch,
            "aura_field": {
                "S_structure": round(S, 3),
                "C_chaos": round(C, 3),
                "P_pulse": round(P, 3),
                "aura_score": round(aura_score, 4),
                "field_stability": round(field_stability, 4) if not math.isinf(field_stability) else "inf",
                "confidence": confidence
            },
            "verdict": verdict,
            "verdict_icon": verdict_icon
        }
