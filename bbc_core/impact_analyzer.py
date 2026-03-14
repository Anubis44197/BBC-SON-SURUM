"""
BBC Semantic Impact Analyzer (v1.0)
Bir dosya/sembol değiştiğinde projedeki tüm etkileri BBC matematiğiyle hesaplar.

BBC Matematiği:
  - Call Graph: import ve sembol bağımlılıklarından dependency haritası
  - Focus Projection: cos²(θ) ile ilgili sembolleri filtrele
  - Shannon Chaos Density: değişikliğin kaos etkisi
  - Aura Impact Score: BBCScalar state-aware etki yarıçapı
  - Pulse Perturbation: değişikliğin stabiliteyi bozma riski
"""

import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple

from .bbc_scalar import BBCScalar, STABLE, WEAK, UNSTABLE, DEGENERATE, OmegaOperator, bbc_data_ingestion


class ImpactAnalyzer:
    """
    BBC Semantic Impact Analyzer — bir değişikliğin proje genelindeki
    etkisini BBC matematiğiyle hesaplar.

    Kullanım:
        analyzer = ImpactAnalyzer(recipe_path)
        report = analyzer.analyze_impact("bbc_core/verifier.py")
    """

    def __init__(self, recipe_path: str):
        self.recipe_path = recipe_path
        self.context = {}
        self.call_graph = {}        # file → {imports_from: [], imported_by: []}
        self.symbol_map = {}        # symbol_name → [file1, file2, ...]
        self.file_symbols = {}      # file → {classes: [], functions: [], imports: []}
        self._load_context()
        self._build_call_graph()

    def _load_context(self):
        """BBC context'i yükle."""
        if not os.path.exists(self.recipe_path):
            return
        with open(self.recipe_path, "r", encoding="utf-8") as f:
            self.context = json.load(f)

        # code_structure'dan file_symbols map oluştur
        for entry in self.context.get("code_structure", []):
            path = entry.get("path", "")
            structure = entry.get("structure", {})
            self.file_symbols[path] = {
                "classes": structure.get("classes", []),
                "functions": structure.get("functions", []),
                "imports": structure.get("imports", []),
                "language": structure.get("language", "python")
            }

            # symbol_map: her sembolü hangi dosya tanımlıyor
            for cls in structure.get("classes", []):
                self.symbol_map.setdefault(cls, []).append(path)
            for func in structure.get("functions", []):
                self.symbol_map.setdefault(func, []).append(path)

    def _build_call_graph(self):
        """Import bağımlılıklarından call graph oluştur."""
        # Proje dosya adlarını topla (uzantısız)
        file_modules = {}
        for path in self.file_symbols:
            basename = os.path.splitext(os.path.basename(path))[0]
            # bbc_core\verifier.py → verifier, bbc_core.verifier
            parts = path.replace("\\", "/").replace("/", ".").replace(".py", "")
            file_modules[basename] = path
            file_modules[parts] = path

        for path, symbols in self.file_symbols.items():
            self.call_graph[path] = {
                "imports_from": [],   # bu dosya kimlerden import ediyor
                "imported_by": [],    # bu dosyayı kimler import ediyor
                "shared_symbols": []  # ortak kullanılan semboller
            }

        # Her dosyanın import'larını analiz et
        for path, symbols in self.file_symbols.items():
            for imp in symbols.get("imports", []):
                # Import string'inden dosya eşleşmesi bul
                imp_parts = imp.split(".")
                for part in imp_parts:
                    if part in file_modules:
                        target = file_modules[part]
                        if target != path:
                            if target not in self.call_graph[path]["imports_from"]:
                                self.call_graph[path]["imports_from"].append(target)
                            if path not in self.call_graph.get(target, {}).get("imported_by", []):
                                self.call_graph.setdefault(target, {
                                    "imports_from": [], "imported_by": [], "shared_symbols": []
                                })["imported_by"].append(path)

        # Shared symbols: aynı sembolü kullanan dosyaları bul
        for symbol, files in self.symbol_map.items():
            if len(files) > 1:
                for f in files:
                    if f in self.call_graph:
                        others = [x for x in files if x != f]
                        for o in others:
                            if o not in self.call_graph[f]["shared_symbols"]:
                                self.call_graph[f]["shared_symbols"].append(o)

    # ─── BBC Matematik: Shannon Chaos ──────────────────────────────

    def _calculate_chaos(self, text: str) -> BBCScalar:
        """Shannon Chaos Density — BBCScalar native."""
        if not text or not isinstance(text, str):
            return BBCScalar(0.0, state=STABLE, metadata={"origin": "math"})
        cnt = Counter(text)
        ln = len(text)
        entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
        if math.isnan(entropy):
            entropy = 0.0
        state = STABLE if entropy <= 3.0 else WEAK if entropy <= 5.0 else UNSTABLE if entropy <= 7.0 else DEGENERATE
        return BBCScalar(entropy, state=state, metadata={"origin": "math"})

    # ─── BBC Matematik: Focus Projection ───────────────────────────

    def _symbol_vector(self, file_path: str) -> List[BBCScalar]:
        """Dosyanın sembol vektörünü oluştur (tüm proje sembolleri üzerinden)."""
        all_symbols = sorted(self.symbol_map.keys())
        if not all_symbols:
            return []
        file_syms = self.file_symbols.get(file_path, {})
        file_all = set(file_syms.get("classes", []) + file_syms.get("functions", []))
        vec = []
        for sym in all_symbols:
            val = 1.0 if sym in file_all else 0.0
            vec.append(BBCScalar(val, state=STABLE, metadata={"origin": "semantic"}))
        return vec

    def _cosine_similarity(self, vec_a: List[BBCScalar], vec_b: List[BBCScalar]) -> BBCScalar:
        """
        BBC Focus Projection: cos²(θ) karşılaştırması (sqrt-free).
        Sonuç BBCScalar olarak döner.
        """
        if len(vec_a) != len(vec_b) or not vec_a:
            return BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "math"})

        dot = BBCScalar(0.0, metadata={"origin": "math"})
        norm_a_sq = BBCScalar(0.0, metadata={"origin": "math"})
        norm_b_sq = BBCScalar(0.0, metadata={"origin": "math"})

        for a, b in zip(vec_a, vec_b):
            dot = dot + (a * b)
            norm_a_sq = norm_a_sq + (a * a)
            norm_b_sq = norm_b_sq + (b * b)

        denom_sq = norm_a_sq * norm_b_sq
        if float(denom_sq) <= 0:
            return BBCScalar(0.0, state=DEGENERATE, metadata={"origin": "math"})

        # cos²(θ) = dot² / (|a|²·|b|²)
        cos_sq = (dot * dot)
        cos_sq_val = float(cos_sq) / float(denom_sq)
        # cos(θ) = sqrt(cos²(θ))
        cos_val = math.sqrt(max(0.0, min(1.0, cos_sq_val)))

        state = STABLE if cos_val >= 0.8 else WEAK if cos_val >= 0.5 else UNSTABLE if cos_val >= 0.2 else DEGENERATE
        return BBCScalar(cos_val, state=state, metadata={"origin": "math"})

    # ─── Etki Analizi ──────────────────────────────────────────────

    def _get_direct_dependents(self, file_path: str) -> List[str]:
        """Doğrudan etkilenen dosyalar (bu dosyayı import edenler)."""
        graph = self.call_graph.get(file_path, {})
        return graph.get("imported_by", [])

    def _get_indirect_dependents(self, file_path: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Dolaylı etkilenen dosyalar (BFS ile tüm bağımlılık zinciri)."""
        if visited is None:
            visited = set()
        visited.add(file_path)
        indirect = []
        for dep in self._get_direct_dependents(file_path):
            if dep not in visited:
                visited.add(dep)
                indirect.append(dep)
                indirect.extend(self._get_indirect_dependents(dep, visited))
        return indirect

    def _get_symbol_dependents(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Belirli bir sembolü kullanan tüm dosyalar."""
        results = []
        defining_files = self.symbol_map.get(symbol_name, [])
        for path, symbols in self.file_symbols.items():
            if path in defining_files:
                continue
            # Bu dosya bu sembolü import veya kullanıyor mu?
            all_syms = symbols.get("classes", []) + symbols.get("functions", []) + symbols.get("imports", [])
            if symbol_name in all_syms:
                results.append({"file": path, "type": "direct_usage"})
        return results

    # ─── Ana Analiz ────────────────────────────────────────────────

    def analyze_impact(self, changed_file: str, changed_symbols: Optional[List[str]] = None,
                       op_type: str = "Patch") -> Dict[str, Any]:
        """
        Bir dosya/sembol değişikliğinin proje genelindeki etkisini analiz eder.

        BBC Matematiği:
          1. Call graph ile doğrudan/dolaylı etkilenen dosyalar
          2. Focus Projection (cos²θ) ile semantik benzerlik
          3. Shannon Chaos: değişikliğin kaos etkisi
          4. Pulse Perturbation: stabilite riski
          5. Aura Impact Score: BBCScalar state-aware sonuç

        Args:
            changed_file: Değişen dosya yolu
            changed_symbols: Değişen semboller (opsiyonel)
            op_type: İşlem tipi (Refactor/Patch/Feature)

        Returns:
            Impact raporu
        """
        # Normalize path
        changed_file = changed_file.replace("/", "\\").replace("\\", os.sep)
        # Eğer tam yol verilmişse, context'teki relatif yola dönüştür
        for path in self.file_symbols:
            if changed_file.endswith(path) or path.endswith(changed_file):
                changed_file = path
                break

        # 1. Doğrudan ve dolaylı bağımlılar
        direct = self._get_direct_dependents(changed_file)
        indirect = self._get_indirect_dependents(changed_file)
        # indirect'ten direct'leri çıkar
        indirect_only = [f for f in indirect if f not in direct]

        # 2. Sembol bazlı etki
        symbol_impacts = []
        if changed_symbols:
            for sym in changed_symbols:
                deps = self._get_symbol_dependents(sym)
                if deps:
                    symbol_impacts.append({
                        "symbol": sym,
                        "affected_files": deps,
                        "affected_count": len(deps)
                    })

        # 3. Focus Projection: değişen dosyayla en çok örtüşen dosyalar
        changed_vec = self._symbol_vector(changed_file)
        semantic_similar = []
        for path in self.file_symbols:
            if path == changed_file:
                continue
            target_vec = self._symbol_vector(path)
            similarity = self._cosine_similarity(changed_vec, target_vec)
            if float(similarity) > 0.1:
                semantic_similar.append({
                    "file": path,
                    "similarity": {"value": round(float(similarity), 3), "state": similarity.state},
                    "risk": "HIGH" if similarity.state in [WEAK, UNSTABLE, DEGENERATE] and float(similarity) > 0.5 else "LOW"
                })
        semantic_similar.sort(key=lambda x: x["similarity"]["value"], reverse=True)

        # 4. Shannon Chaos: etkilenen dosyaların toplam kaos yoğunluğu
        all_affected = list(set(direct + indirect_only))
        affected_symbols_text = ""
        for af in all_affected:
            syms = self.file_symbols.get(af, {})
            affected_symbols_text += " ".join(syms.get("classes", []) + syms.get("functions", []))
        chaos = self._calculate_chaos(affected_symbols_text)

        # 5. Aura Impact Score: BBCScalar state-aware
        total_files = len(self.file_symbols)
        impact_ratio = len(all_affected) / total_files if total_files > 0 else 0.0

        # Impact → BBCScalar: düşük etki = STABLE, yüksek etki = DEGENERATE
        ir_val = max(0.0, min(1.0, impact_ratio))
        ir_state = STABLE if ir_val <= 0.1 else WEAK if ir_val <= 0.3 else UNSTABLE if ir_val <= 0.5 else DEGENERATE
        impact_scalar = BBCScalar(ir_val, state=ir_state, metadata={"origin": "semantic"})

        # 6. Pulse Perturbation: değişikliğin stabiliteyi bozma riski
        pulse_risk = BBCScalar(0.0, state=STABLE, metadata={"origin": "math"})
        try:
            from .hmpu_core import HMPU_Governor
            governor = HMPU_Governor()
            pulse = governor.pulse_perturbation_sim(
                current_aura=1.0 - ir_val,
                intent_magnitude=float(chaos) / 8.0,
                op_type=op_type
            )
            pr_val = 1.0 - pulse["predicted_pulse"] if pulse["predicted_pulse"] < 1.0 else 0.0
            pr_state = STABLE if pulse["is_stable"] else UNSTABLE
            pulse_risk = BBCScalar(pr_val, state=pr_state, metadata={"origin": "math"})
        except Exception:
            # Fallback: basit risk hesabı
            pr_val = ir_val * (float(chaos) / 8.0)
            pr_state = STABLE if pr_val < 0.2 else WEAK if pr_val < 0.4 else UNSTABLE
            pulse_risk = BBCScalar(pr_val, state=pr_state, metadata={"origin": "math"})

        # 7. Composite Risk: impact + chaos + pulse state propagation
        composite = impact_scalar + chaos + pulse_risk
        composite_val = min(1.0, float(composite) / 3.0)  # Normalize
        composite_scalar = BBCScalar(composite_val, state=composite.state, metadata={"origin": "math"})

        # Heal denemesi
        if composite_scalar.state in [UNSTABLE, DEGENERATE]:
            composite_scalar = OmegaOperator.trigger(
                BBCScalar(composite_scalar.value, state=composite_scalar.state,
                          heal_count=composite_scalar.heal_count,
                          metadata=composite_scalar.metadata)
            )

        # Verdict
        final_state = composite_scalar.state
        if final_state == STABLE:
            verdict = "SAFE_TO_CHANGE"
            verdict_icon = "✅"
        elif final_state == WEAK:
            verdict = "CAUTION"
            verdict_icon = "⚠️"
        else:
            verdict = "HIGH_RISK"
            verdict_icon = "🔴"

        return {
            "changed_file": changed_file,
            "changed_symbols": changed_symbols or [],
            "op_type": op_type,
            "direct_dependents": direct,
            "direct_count": len(direct),
            "indirect_dependents": indirect_only,
            "indirect_count": len(indirect_only),
            "total_affected": len(all_affected),
            "symbol_impacts": symbol_impacts,
            "semantic_similar": semantic_similar[:10],
            "aura_impact": {
                "impact_ratio": {"value": round(float(impact_scalar), 3), "state": impact_scalar.state},
                "chaos_density": {"value": round(float(chaos), 3), "state": chaos.state},
                "pulse_risk": {"value": round(float(pulse_risk), 3), "state": pulse_risk.state},
                "composite_risk": {"value": round(float(composite_scalar), 4), "state": composite_scalar.state}
            },
            "verdict": verdict,
            "verdict_icon": verdict_icon
        }
