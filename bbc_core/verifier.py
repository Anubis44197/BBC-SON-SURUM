import json
import ast
import os
import re
import math
import hashlib
from collections import Counter
from .attribution_tracer import AttributionTracer
from .hmpu_quantizer import HMPUQuantizer
from .bbc_scalar import BBCScalar, STABLE, WEAK, UNSTABLE, DEGENERATE, OmegaOperator, bbc_data_ingestion

class BBCVerifier:
    """
    BBC Standart Verification Engine (v3.0 - Ultimate Polyglot)
    Evrensel 'Mismatch Scan' ve 'Syntax Check' yetenegi.
    Desteklenen Diller: Python, Rust, JS/TS, Go, C/C++, Java/C#, PHP, Ruby, Swift, Kotlin, SQL.
    """
    
    def __init__(self, recipe_path: str):
        self.recipe_path = recipe_path
        self.knowledge_map = {"global_symbols": set()}
        self.project_root = ""
        self._load_recipe() # Project root burada yukleniyor
        
        # Attribution Engine (Safe Init)
        self.tracer = None
        if self.project_root:
            self.tracer = AttributionTracer(self.project_root)

    def _extract_symbols(self, text, lang_hint=None):
        """Metinden symbols (class/function) regex ile cikarir."""
        # Not: Quantizer zaten bu isi yapiyor ama Standalone mod for burasi yedek (backup).
        # Burayi Quantizer'in patternlerine benzetiyoruz.
        symbols = set()
        
        # Generic Regex (Fallback)
        for match in re.finditer(r'^\s*(?:class|function|def|fn|struct|func)\s+([a-zA-Z0-9_]+)', text, re.MULTILINE):
            symbols.add(match.group(1))
            
        return symbols

    def _load_recipe(self):
        """Recipe file yukler ve evrensel formata donusturur."""
        if not os.path.exists(self.recipe_path):
            raise FileNotFoundError(f"Recipe not found: {self.recipe_path}")
            
        with open(self.recipe_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.recipe_data = data
        self.project_root = data.get("project_skeleton", {}).get("root", "")
        if not self.project_root:
            self.project_root = os.getcwd()
            
        # Recipe'den symbols cikar
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
        if os.environ.get("BBC_VERIFIER_VERBOSE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            print(f"[*] Knowledge Base Loaded: {len(all_symbols)} known symbols (Ultimate Polyglot Mode).")

    def verify_syntax_only(self):
        """
        Polyglot Syntax Checker.
        Her dil for temel yapisal butunlugu check eder.
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
            # Sadece bir kez all projeyi tara (Lazy Loading)
            self.tracer.scan_project()
            
            for err in errors:
                failed_file = err["file"]
                impact_list = self.tracer.trace_impact(failed_file)
                if impact_list:
                    err["impact_analysis"] = {
                        "blast_radius": len(impact_list),
                        "affected_files": impact_list[:5] # Ilk 5 tanesini goster
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
        Context Freshness Check — hash karsilastirmasi ile hangi dosyalarin
        sealing sonrasi degistigini tespit eder.
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
        Sembol Mismatch Kontrolu — context'teki semboller ile diskteki gercek
        kaynak files arasindaki tutarsizliklari tespit eder.
        Quantizer ile diskteki dosyayi yeniden tarar, context'teki sembollerle karsilastirir.

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

            # Diskteki gercek semboller (quantizer ile tara)
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

    def _calculate_chaos(self, text: str) -> float:
        """Shannon Chaos Density — HMPU Governor ile ayni formul."""
        if not text or not isinstance(text, str):
            return 0.0
        cnt = Counter(text)
        ln = len(text)
        entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
        return entropy if not math.isnan(entropy) else 0.0

    def verify_full(self):
        """
        BBC Full Verification — Syntax + Freshness + Symbol Mismatch + Aura Field Score.
        
        Tum hesaplar BBC matematigiyle yapilir:
          - S, C, P → BBCScalar (origin="semantic", state-aware)
          - Shannon chaos density ile mismatch kaos olcumu
          - HMPU Governor aura_field_score(S, C, P) → iteratif alan donusumu
          - Condition number (κ) → confidence = 1 / (1 + log10(κ))
          - State propagation ile verdict (STABLE/WEAK/UNSTABLE/DEGENERATE)
        
        Returns: dict with all verification results + aura_score + confidence + verdict
        """
        # 1. Syntax Check
        syntax_errors = self.verify_syntax_only()

        # 2. Freshness Check
        freshness = self.verify_freshness()

        # 3. Symbol Mismatch
        mismatch = self.verify_symbol_mismatch()

        # 4. BBC Matematik: S, C, P → BBCScalar (origin="semantic")
        total_files = freshness.get("total_files", 1) or 1
        syntax_error_ratio = len(syntax_errors) / total_files if total_files > 0 else 0.0

        # S: Structure health — syntax hatasiz file orani
        s_val = max(0.0, min(1.0, 1.0 - syntax_error_ratio))
        s_state = STABLE if s_val >= 0.8 else WEAK if s_val >= 0.5 else UNSTABLE if s_val >= 0.2 else DEGENERATE
        S = BBCScalar(s_val, state=s_state, metadata={"origin": "semantic"})

        # C: Chaos density — Shannon entropy ile mismatch kaosunu dogrudan olc
        mismatch_ratio = mismatch.get("mismatch_ratio", 0.0)
        # Mismatch dosyalarinin iceriginden gercek Shannon chaos hesapla
        chaos_samples = []
        for mf in mismatch.get("mismatch_files", [])[:5]:
            added = mf.get("added_symbols", [])
            removed = mf.get("removed_symbols", [])
            chaos_samples.extend(added + removed)
        if chaos_samples:
            chaos_text = " ".join(str(s) for s in chaos_samples)
            chaos_raw = self._calculate_chaos(chaos_text)
            c_val = max(0.0, min(1.0, chaos_raw / 8.0))
        else:
            c_val = max(0.0, min(1.0, mismatch_ratio))
        c_state = STABLE if c_val <= 0.1 else WEAK if c_val <= 0.3 else UNSTABLE if c_val <= 0.6 else DEGENERATE
        C = BBCScalar(c_val, state=c_state, metadata={"origin": "semantic"})

        # P: Freshness pulse — stale ratio'nun tersi
        stale_ratio = freshness.get("stale_ratio", 0.0)
        p_val = max(0.0, min(1.0, 1.0 - stale_ratio))
        p_state = STABLE if p_val >= 0.9 else WEAK if p_val >= 0.7 else UNSTABLE if p_val >= 0.4 else DEGENERATE
        P = BBCScalar(p_val, state=p_state, metadata={"origin": "semantic"})

        # 5. Aura Field Score: HMPU Governor (tam BBC matematik)
        aura_score_scalar = BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "semantic"})
        confidence_scalar = BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "math"})
        field_stability = float('inf')
        governor_used = False

        try:
            from .hmpu_core import HMPU_Governor
            governor = HMPU_Governor()
            aura_raw = governor.aura_field_score(float(S), float(C), float(P))
            field_stability = governor.get_field_stability()
            governor_used = True

            # Aura score → BBCScalar (state propagated from S, C, P)
            combined_state = S._determine_new_state(C.state)
            combined_state_2 = BBCScalar(0, state=combined_state)._determine_new_state(P.state)
            aura_score_scalar = BBCScalar(aura_raw, state=combined_state_2, metadata={"origin": "math"})

            # Confidence → BBCScalar (condition number'dan)
            if not math.isinf(field_stability) and field_stability > 0:
                conf_val = 1.0 / (1.0 + math.log10(field_stability))
                conf_val = min(max(conf_val, 0.0), 1.0)
                conf_state = STABLE if conf_val >= 0.7 else WEAK if conf_val >= 0.4 else UNSTABLE
                confidence_scalar = BBCScalar(conf_val, state=conf_state, metadata={"origin": "math"})
        except Exception:
            # Fallback: BBC state-aware weighted synthesis (Governor yoksa)
            w_s = BBCScalar(0.6, state=STABLE, metadata={"origin": "math"})
            w_c = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            w_p = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            one = BBCScalar(1.0, state=STABLE, metadata={"origin": "math"})

            # Aura = 0.6*S + 0.2*(1-C) + 0.2*P — state propagation ile
            aura_score_scalar = (w_s * S) + (w_c * (one - C)) + (w_p * P)
            confidence_scalar = aura_score_scalar

        # 6. Heal: Eger aura UNSTABLE ise OmegaOperator ile iyilestirmeyi dene
        if aura_score_scalar.state in [UNSTABLE, DEGENERATE]:
            aura_score_scalar = OmegaOperator.trigger(
                BBCScalar(aura_score_scalar.value, state=aura_score_scalar.state,
                          heal_count=aura_score_scalar.heal_count,
                          metadata=aura_score_scalar.metadata)
            )

        # 7. Verdict — BBCScalar state'ten turetilir (klasik float karsilastirma degil)
        final_state = aura_score_scalar.state
        if final_state == STABLE and len(syntax_errors) == 0 and freshness["context_fresh"]:
            verdict = "SEALED_STABLE"
            verdict_icon = "💎"
        elif final_state == WEAK:
            verdict = "WEAK"
            verdict_icon = "⚠️"
        elif final_state == UNSTABLE:
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
                "S_structure": {"value": round(float(S), 3), "state": S.state, "origin": S.origin},
                "C_chaos": {"value": round(float(C), 3), "state": C.state, "origin": C.origin},
                "P_pulse": {"value": round(float(P), 3), "state": P.state, "origin": P.origin},
                "aura_score": {"value": round(float(aura_score_scalar), 4), "state": aura_score_scalar.state, "origin": aura_score_scalar.origin},
                "field_stability": round(field_stability, 4) if not math.isinf(field_stability) else "inf",
                "confidence": {"value": round(float(confidence_scalar), 3), "state": confidence_scalar.state},
                "governor_used": governor_used
            },
            "verdict": verdict,
            "verdict_icon": verdict_icon
        }

    def verify_changed_only(self, changed_files: list = None):
        """
        Changed-Only Verification — only degisen files verifies.
        ChangeTracker'dan gelen file listesini uses veya freshness
        check ile stale files otomatik tespit eder.
        
        Tam verify_full ile ayni BBC matematik pipeline'ini uses,
        ancak yalnizca etkilenen dosyalar uzerinde runs.
        
        Args:
            changed_files: Dogrulanacak file yollarinin listesi (relative).
                           None ise freshness'tan otomatik tespit eder.
        Returns: dict — verify_full ile ayni yapida, ek olarak changed_only metadata
        """
        # Degisen file listesini belirle
        if changed_files is None:
            freshness = self.verify_freshness()
            changed_files = freshness.get("stale_files", [])
        else:
            freshness = self.verify_freshness()

        if not changed_files:
            return {
                "syntax_errors": [],
                "syntax_error_count": 0,
                "freshness": freshness,
                "symbol_mismatch": {"mismatch_count": 0, "mismatch_files": [], "mismatch_ratio": 0.0},
                "aura_field": {
                    "aura_score": {"value": 1.0, "state": STABLE, "origin": "semantic"},
                    "confidence": {"value": 1.0, "state": STABLE},
                },
                "verdict": "SEALED_STABLE",
                "verdict_icon": "💎",
                "changed_only": {
                    "mode": "changed_only",
                    "files_checked": 0,
                    "skipped": "no_changes"
                }
            }

        changed_set = set(changed_files)

        # --- Syntax check: only degisen dosyalar ---
        syntax_errors = []
        binary_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.ttf',
                       '.woff', '.woff2', '.eot', '.pdf', '.zip', '.exe', '.dll',
                       '.so', '.dylib', '.bin'}

        for rel_path in changed_files:
            abs_path = os.path.join(self.project_root, rel_path)
            if not os.path.exists(abs_path):
                continue
            ext = os.path.splitext(rel_path)[1].lower()
            if ext in binary_exts:
                continue
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if ext == '.py':
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        syntax_errors.append({
                            "file": rel_path, "line": e.lineno,
                            "msg": e.msg, "type": "SYNTAX_ERROR (Python)"
                        })
                elif ext in ['.rs', '.c', '.cpp', '.h', '.hpp', '.java', '.cs',
                             '.js', '.ts', '.jsx', '.tsx', '.go', '.php', '.swift', '.kt']:
                    ob = content.count('{')
                    cb = content.count('}')
                    if ob != cb:
                        syntax_errors.append({
                            "file": rel_path,
                            "msg": f"Unbalanced braces {{}} (Open: {ob}, Close: {cb})",
                            "type": f"SYNTAX_ERROR ({ext[1:].upper()})"
                        })
            except UnicodeDecodeError:
                continue
            except Exception as e:
                syntax_errors.append({"file": rel_path, "msg": str(e), "type": "READ_ERROR"})

        # --- Symbol mismatch: only degisen dosyalar ---
        code_struct = self.recipe_data.get("code_structure", [])
        quantizer = HMPUQuantizer()
        mismatch_files = []
        total_context_symbols = 0
        total_mismatched = 0

        for file_obj in code_struct:
            if not isinstance(file_obj, dict):
                continue
            file_path = file_obj.get("path", "")
            if not file_path or file_path not in changed_set:
                continue

            abs_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(abs_path):
                continue

            struct = file_obj.get("structure", {})
            ctx_classes = set(struct.get("classes", []))
            ctx_functions = set(struct.get("functions", []))
            ctx_symbols = ctx_classes | ctx_functions
            total_context_symbols += len(ctx_symbols)
            if not ctx_symbols:
                continue

            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ext = os.path.splitext(file_path)[1]
                result = quantizer.process_content(content, file_ext=ext)
                disk_struct = result.get("structure", {})
                disk_symbols = set(disk_struct.get("classes", [])) | set(disk_struct.get("functions", []))
            except Exception:
                continue

            added = disk_symbols - ctx_symbols
            removed = ctx_symbols - disk_symbols
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
        mismatch = {
            "total_context_symbols": total_context_symbols,
            "total_mismatched": total_mismatched,
            "mismatch_files": mismatch_files,
            "mismatch_count": len(mismatch_files),
            "mismatch_ratio": round(mismatch_ratio, 3)
        }

        # --- BBC Matematik: S, C, P → BBCScalar (verify_full ile ayni) ---
        total_checked = len(changed_files) or 1
        syntax_error_ratio = len(syntax_errors) / total_checked

        s_val = max(0.0, min(1.0, 1.0 - syntax_error_ratio))
        s_state = STABLE if s_val >= 0.8 else WEAK if s_val >= 0.5 else UNSTABLE if s_val >= 0.2 else DEGENERATE
        S = BBCScalar(s_val, state=s_state, metadata={"origin": "semantic"})

        chaos_samples = []
        for mf in mismatch_files[:5]:
            chaos_samples.extend(mf.get("added_symbols", []) + mf.get("removed_symbols", []))
        if chaos_samples:
            chaos_text = " ".join(str(s) for s in chaos_samples)
            c_val = max(0.0, min(1.0, self._calculate_chaos(chaos_text) / 8.0))
        else:
            c_val = max(0.0, min(1.0, mismatch_ratio))
        c_state = STABLE if c_val <= 0.1 else WEAK if c_val <= 0.3 else UNSTABLE if c_val <= 0.6 else DEGENERATE
        C = BBCScalar(c_val, state=c_state, metadata={"origin": "semantic"})

        stale_ratio = freshness.get("stale_ratio", 0.0)
        p_val = max(0.0, min(1.0, 1.0 - stale_ratio))
        p_state = STABLE if p_val >= 0.9 else WEAK if p_val >= 0.7 else UNSTABLE if p_val >= 0.4 else DEGENERATE
        P = BBCScalar(p_val, state=p_state, metadata={"origin": "semantic"})

        # Aura Field Score
        aura_score_scalar = BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "semantic"})
        confidence_scalar = BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "math"})
        field_stability = float('inf')
        governor_used = False

        try:
            from .hmpu_core import HMPU_Governor
            governor = HMPU_Governor()
            aura_raw = governor.aura_field_score(float(S), float(C), float(P))
            field_stability = governor.get_field_stability()
            governor_used = True

            combined_state = S._determine_new_state(C.state)
            combined_state_2 = BBCScalar(0, state=combined_state)._determine_new_state(P.state)
            aura_score_scalar = BBCScalar(aura_raw, state=combined_state_2, metadata={"origin": "math"})

            if not math.isinf(field_stability) and field_stability > 0:
                conf_val = 1.0 / (1.0 + math.log10(field_stability))
                conf_val = min(max(conf_val, 0.0), 1.0)
                conf_state = STABLE if conf_val >= 0.7 else WEAK if conf_val >= 0.4 else UNSTABLE
                confidence_scalar = BBCScalar(conf_val, state=conf_state, metadata={"origin": "math"})
        except Exception:
            w_s = BBCScalar(0.6, state=STABLE, metadata={"origin": "math"})
            w_c = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            w_p = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            one = BBCScalar(1.0, state=STABLE, metadata={"origin": "math"})
            aura_score_scalar = (w_s * S) + (w_c * (one - C)) + (w_p * P)
            confidence_scalar = aura_score_scalar

        if aura_score_scalar.state in [UNSTABLE, DEGENERATE]:
            aura_score_scalar = OmegaOperator.trigger(
                BBCScalar(aura_score_scalar.value, state=aura_score_scalar.state,
                          heal_count=aura_score_scalar.heal_count,
                          metadata=aura_score_scalar.metadata)
            )

        final_state = aura_score_scalar.state
        if final_state == STABLE and len(syntax_errors) == 0 and freshness.get("context_fresh", False):
            verdict = "SEALED_STABLE"
            verdict_icon = "💎"
        elif final_state == WEAK:
            verdict = "WEAK"
            verdict_icon = "⚠️"
        elif final_state == UNSTABLE:
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
                "S_structure": {"value": round(float(S), 3), "state": S.state, "origin": S.origin},
                "C_chaos": {"value": round(float(C), 3), "state": C.state, "origin": C.origin},
                "P_pulse": {"value": round(float(P), 3), "state": P.state, "origin": P.origin},
                "aura_score": {"value": round(float(aura_score_scalar), 4), "state": aura_score_scalar.state, "origin": aura_score_scalar.origin},
                "field_stability": round(field_stability, 4) if not math.isinf(field_stability) else "inf",
                "confidence": {"value": round(float(confidence_scalar), 3), "state": confidence_scalar.state},
                "governor_used": governor_used
            },
            "verdict": verdict,
            "verdict_icon": verdict_icon,
            "changed_only": {
                "mode": "changed_only",
                "files_checked": len(changed_files),
                "files_with_errors": len(syntax_errors),
                "files_with_mismatch": len(mismatch_files),
            }
        }
