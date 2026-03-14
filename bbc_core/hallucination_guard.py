"""
BBC Hallucination Guard (v1.0)
Post-generation doğrulama — AI'ın ürettiği koddaki sembollerin
BBC sealed context'te var olup olmadığını kontrol eder.

BBC Matematiği:
  - Shannon entropy (chaos density) ile kod karmaşıklığını ölçer
  - Aura Field Score: match_ratio → S, chaos → C, freshness → P
  - HMPU Governor ile confidence hesaplar
  - CVP (Constraint Violation Protocol) ile ihlal raporlar
"""

import json
import math
import os
import re
from collections import Counter
from typing import Dict, Any, List, Optional
from .bbc_scalar import BBCScalar, STABLE, WEAK, UNSTABLE, DEGENERATE, OmegaOperator


class HallucinationGuard:
    """
    AI çıktısındaki sembolleri BBC context'e karşı doğrular.
    Halüsinasyon tespit edilirse CVP violation döndürür.
    """

    # Spekülatif dil kalıpları (adaptive_mode.py ile uyumlu)
    SPECULATIVE_PATTERNS = [
        r"\bprobably\b", r"\bmight\b", r"\bcould be\b",
        r"\bperhaps\b", r"\bi think\b", r"\bmaybe\b",
        r"\bguess\b", r"\bassume\b", r"\blikely\b",
    ]

    def __init__(self, context_path: str):
        """
        Args:
            context_path: .bbc/bbc_context.json yolu
        """
        if not os.path.exists(context_path):
            raise FileNotFoundError(f"Context not found: {context_path}")

        with open(context_path, 'r', encoding='utf-8') as f:
            self.context = json.load(f)

        # Context'ten tüm sembolleri çıkar
        self.known_symbols = set()
        self.known_imports = set()
        self.file_paths = set()

        for file_obj in self.context.get("code_structure", []):
            if not isinstance(file_obj, dict):
                continue
            self.file_paths.add(file_obj.get("path", ""))
            struct = file_obj.get("structure", {})
            self.known_symbols.update(struct.get("classes", []))
            self.known_symbols.update(struct.get("functions", []))
            self.known_imports.update(struct.get("imports", []))

    def _calculate_chaos(self, text: str) -> float:
        """Shannon Chaos Density — HMPU Governor ile aynı formül."""
        if not text:
            return 0.0
        cnt = Counter(text)
        ln = len(text)
        entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
        return entropy if not math.isnan(entropy) else 0.0

    def _extract_referenced_symbols(self, code: str) -> set:
        """
        Verilen kod parçasından referans edilen sembolleri çıkarır.
        Tanımları (def/class) ve kullanımları (çağrıları) ayrı ayrı toplar.
        """
        symbols = set()

        # Fonksiyon/sınıf tanımları
        for m in re.finditer(r'^\s*(?:class|def|function|fn|func|struct)\s+([a-zA-Z_][a-zA-Z0-9_]*)', code, re.MULTILINE):
            symbols.add(m.group(1))

        # Fonksiyon çağrıları: name(...)
        for m in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code):
            name = m.group(1)
            # Dil keyword'lerini atla
            if name not in {'if', 'for', 'while', 'return', 'print', 'range', 'len',
                            'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
                            'isinstance', 'hasattr', 'getattr', 'setattr', 'super',
                            'open', 'type', 'map', 'filter', 'zip', 'enumerate',
                            'sorted', 'reversed', 'any', 'all', 'min', 'max', 'sum',
                            'abs', 'round', 'format', 'input', 'hash', 'id', 'repr',
                            'try', 'except', 'with', 'as', 'from', 'import', 'assert'}:
                symbols.add(name)

        # Sınıf instantiation: ClassName(...)
        for m in re.finditer(r'\b([A-Z][a-zA-Z0-9_]*)\s*\(', code):
            symbols.add(m.group(1))

        # import from ... import Name
        for m in re.finditer(r'from\s+\S+\s+import\s+(.+)', code):
            for name in m.group(1).split(','):
                name = name.strip().split(' as ')[0].strip()
                if name and name[0].isalpha():
                    symbols.add(name)

        return symbols

    def _detect_speculative_language(self, text: str) -> List[str]:
        """Spekülatif dil kalıplarını tespit eder."""
        violations = []
        text_lower = text.lower()
        for pattern in self.SPECULATIVE_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(f"Speculative language: {pattern}")
        return violations

    def check(self, generated_code: str, strict: bool = True) -> Dict[str, Any]:
        """
        AI'ın ürettiği kodu BBC context'e karşı doğrular.

        BBC Matematiği (tam native):
          S, C, P → BBCScalar (state + origin taşır)
          S = match_ratio → state: STABLE/WEAK/UNSTABLE/DEGENERATE
          C = Shannon chaos density (normalize) → state: chaos seviyesi
          P = 1.0 (üretim anında freshness varsayımı)

          Aura Score = HMPU aura_field_score(S, C, P) → iteratif alan dönüşümü
          Confidence = 1 / (1 + log10(κ)) → BBCScalar
          Verdict = state propagation'dan türetilir

        Args:
            generated_code: AI'ın ürettiği kod metni
            strict: True ise eşleşmeyen semboller CVP violation olur

        Returns:
            dict with match_ratio, hallucinated_symbols, aura_score, confidence, violations
        """
        referenced = self._extract_referenced_symbols(generated_code)

        if not referenced:
            return {
                "status": "ok",
                "match_ratio": 1.0,
                "total_referenced": 0,
                "matched": 0,
                "hallucinated_symbols": [],
                "speculative_violations": [],
                "aura_score": 1.0,
                "confidence": 1.0,
                "verdict": "NO_SYMBOLS"
            }

        # Eşleşen ve eşleşmeyen semboller
        matched = referenced & self.known_symbols
        hallucinated = referenced - self.known_symbols
        match_ratio = len(matched) / len(referenced) if referenced else 1.0

        # Spekülatif dil kontrolü
        speculative = self._detect_speculative_language(generated_code)

        # BBC Matematik: S, C, P → BBCScalar (origin="semantic")
        s_val = max(0.0, min(1.0, match_ratio))
        s_state = STABLE if s_val >= 0.9 else WEAK if s_val >= 0.7 else UNSTABLE if s_val >= 0.4 else DEGENERATE
        S = BBCScalar(s_val, state=s_state, metadata={"origin": "semantic"})

        chaos_raw = self._calculate_chaos(generated_code)
        c_val = max(0.0, min(1.0, chaos_raw / 8.0))
        c_state = STABLE if c_val <= 0.1 else WEAK if c_val <= 0.3 else UNSTABLE if c_val <= 0.6 else DEGENERATE
        C = BBCScalar(c_val, state=c_state, metadata={"origin": "semantic"})

        p_val = 1.0  # Üretim anında freshness varsayımı
        P = BBCScalar(p_val, state=STABLE, metadata={"origin": "semantic"})

        # Aura Field Score: HMPU Governor (tam BBC matematik)
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

            # State propagation: S, C, P state'lerinin birleşimi
            combined_state = S._determine_new_state(C.state)
            combined_state_2 = BBCScalar(0, state=combined_state)._determine_new_state(P.state)
            aura_score_scalar = BBCScalar(aura_raw, state=combined_state_2, metadata={"origin": "math"})

            if not math.isinf(field_stability) and field_stability > 0:
                conf_val = 1.0 / (1.0 + math.log10(field_stability))
                conf_val = min(max(conf_val, 0.0), 1.0)
                conf_state = STABLE if conf_val >= 0.7 else WEAK if conf_val >= 0.4 else UNSTABLE
                confidence_scalar = BBCScalar(conf_val, state=conf_state, metadata={"origin": "math"})
        except Exception:
            # Fallback: BBC state-aware weighted synthesis
            w_s = BBCScalar(0.6, state=STABLE, metadata={"origin": "math"})
            w_c = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            w_p = BBCScalar(0.2, state=STABLE, metadata={"origin": "math"})
            one = BBCScalar(1.0, state=STABLE, metadata={"origin": "math"})
            aura_score_scalar = (w_s * S) + (w_c * (one - C)) + (w_p * P)
            confidence_scalar = aura_score_scalar

        # Heal: UNSTABLE ise OmegaOperator ile iyileştirmeyi dene
        if aura_score_scalar.state in [UNSTABLE, DEGENERATE]:
            aura_score_scalar = OmegaOperator.trigger(
                BBCScalar(aura_score_scalar.value, state=aura_score_scalar.state,
                          heal_count=aura_score_scalar.heal_count,
                          metadata=aura_score_scalar.metadata)
            )

        # CVP Violations
        violations = list(speculative)
        if strict and hallucinated:
            for sym in sorted(hallucinated)[:20]:
                violations.append(f"HALLUCINATED_SYMBOL: {sym}")

        # Verdict — BBCScalar state'ten türetilir
        final_state = aura_score_scalar.state
        if final_state == STABLE and not violations:
            verdict = "SAFE"
        elif final_state == WEAK:
            verdict = "WARNING"
        else:
            verdict = "HALLUCINATION_DETECTED"

        return {
            "status": "ok" if verdict == "SAFE" else "warning" if verdict == "WARNING" else "violation",
            "match_ratio": round(match_ratio, 3),
            "total_referenced": len(referenced),
            "matched": len(matched),
            "hallucinated_symbols": sorted(hallucinated)[:20],
            "speculative_violations": speculative,
            "violations": violations,
            "aura_field": {
                "S_match": {"value": round(float(S), 3), "state": S.state, "origin": S.origin},
                "C_chaos": {"value": round(float(C), 3), "state": C.state, "origin": C.origin},
                "P_pulse": {"value": round(float(P), 3), "state": P.state, "origin": P.origin},
                "aura_score": {"value": round(float(aura_score_scalar), 4), "state": aura_score_scalar.state, "origin": aura_score_scalar.origin},
                "field_stability": round(field_stability, 4) if not math.isinf(field_stability) else "inf",
                "confidence": {"value": round(float(confidence_scalar), 3), "state": confidence_scalar.state},
                "governor_used": governor_used
            },
            "verdict": verdict
        }
