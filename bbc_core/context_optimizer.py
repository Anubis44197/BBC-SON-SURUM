"""
BBC Context Optimizer - Asama 3.7: Context Optimizer Guardrails

Bu modul symbol graph'ini analysis ederek AI for optimize edilmis context uretir.
- SymbolGraph ciktisini input olarak alir
- Blast radius hesaplar (kim kimi cagirir)
- BBC karari uretir: "Bu semboller onemli, digerleri gurultu"
- LLM/AI kullanmaz - tamamen deterministiktir

IMPORTANT GUARANTEES:
- Runtime guarantee YOK - Sadece AST-based static analysis
- Dynamic call'lari (eval, getattr, import_string vb.) cozmez
- Sadece kodda explicit gorulen calls analysis eder

Cikti Formati (BBC Karari):
{
  "target": "compute_hash",
  "primary": ["compute_hash"],        # %40 onem - degisen symbol (TEKIL)
  "direct": ["analyze_project"],      # %30 onem - dogrudan cagiranlar
  "indirect": ["run_analysis"],       # %20 onem - dolayli cagiranlar  
  "ignored": ["external_calls"],      # IGNORED - external ve unknown cagrilar
  "safety": ["signature degismesin"]  # guvenlik kurallari ve uyarilar
}
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum
from pathlib import Path


class ImpactLevel(Enum):
    """Etki seviyeleri - onem sirasina gore."""
    PRIMARY = "primary"      # %40 - Hedef symbol kendisi
    DIRECT = "direct"        # %30 - Dogrudan bagimlilar (1. seviye)
    INDIRECT = "indirect"    # %20 - Dolayli bagimlilar (2+ seviye)
    DISTANT = "distant"      # %10 - Uzak bagimlilar (gerekiyorsa)
    IGNORE = "ignore"        # %0 - Gurultu, dahil etme


class ContextOptimizerError(Exception):
    """Context Optimizer error sinifi."""
    pass


class ContextReductionError(ContextOptimizerError):
    """Context reduction cok dusukse firlatilir."""
    pass


@dataclass
class SymbolResolutionResult:
    """SymbolResolver'in urettigi cozumleme sonucu."""
    primary: Optional[str]          # Cozumlenen tam symbol adi (veya None)
    candidates: List[str]           # Tum eslesen adaylar
    resolution_type: str            # "exact", "unique_short", "graph_scored", "ambiguous", "not_found"
    warnings: List[str]             # Guvenlik warnings
    scores: Dict[str, float]        # Adaylarin skorlari (graph_scored for)
    
    def to_dict(self) -> Dict[str, Any]:
        """Sozluk formatina donustur."""
        return {
            "primary": self.primary,
            "candidates": self.candidates,
            "resolution_type": self.resolution_type,
            "warnings": self.warnings,
            "scores": {k: round(v, 3) for k, v in self.scores.items()}
        }


class SymbolResolver:
    """
    Kisa symbol isimlerini graph'taki tam isimlerle eslestirir.
    
    Problem: Kullanici "extract" der ama graph'ta "PythonSymbolExtractor.extract" var
    Cozum: Deterministik cozumleme algoritmasi (LLM kullanmaz)
    
    Cozum sirasi (DETERMINISTIK):
    1. Exact full_name match
    2. Unique short-name match  
    3. Graph-score ile cozumleme
    4. Ambiguous durumda: primary=None, resolution_status="ambiguous"
    
    Fallback YOK - Belirsiz durumda None returns.
    """
    
    def __init__(self, symbol_graph: Dict[str, Any]):
        """
        Args:
            symbol_graph: SymbolGraph ciktisi
        """
        # DETERMINISM: sorted ile deterministik siralama
        symbols_list = symbol_graph.get("symbols", [])
        self.symbols = {s["symbol"]: s for s in sorted(symbols_list, key=lambda x: x["symbol"])}
        
        # Hizli lookup for indeksler
        self._build_short_name_index()
        self._build_graph_metrics()
    
    def _build_short_name_index(self):
        """Kisa isimlerden tam isimlere indeks create."""
        self.short_name_map: Dict[str, List[str]] = {}
        
        # DETERMINISM: sorted keys ile iterasyon
        for full_name in sorted(self.symbols.keys()):
            # Kisa ismi cikar (son parca)
            short_name = full_name.split('.')[-1]
            
            if short_name not in self.short_name_map:
                self.short_name_map[short_name] = []
            self.short_name_map[short_name].append(full_name)
        
        # DETERMINISM: Her liste de sorted olsun
        for short_name in self.short_name_map:
            self.short_name_map[short_name] = sorted(self.short_name_map[short_name])
    
    def _build_graph_metrics(self):
        """Graph metriklerini hesapla."""
        self.symbol_metrics: Dict[str, Dict[str, Any]] = {}
        
        # DETERMINISM: sorted ile iterasyon
        for full_name in sorted(self.symbols.keys()):
            sym_data = self.symbols[full_name]
            
            # Indegree: Bu sembolu cagiranlarin sayisi
            called_by = sym_data.get("called_by", [])
            indegree = len(called_by)
            
            # Outdegree: Bu sembolun cagirdiklarinin sayisi
            calls = sym_data.get("calls", [])
            outdegree = len(calls)
            
            # Toplam call sayisi (graph'taki onemi)
            total_calls = indegree + outdegree
            
            # File bilgisi
            file_path = sym_data.get("file", "")
            
            self.symbol_metrics[full_name] = {
                "indegree": indegree,
                "outdegree": outdegree,
                "total_calls": total_calls,
                "file": file_path,
                "short_name": full_name.split('.')[-1]
            }
    
    def resolve(self, target: str, context_file: Optional[str] = None) -> SymbolResolutionResult:
        """
        Hedef sembolu cozumle.
        
        Cozum sirasi:
        1. Exact match (deterministik)
        2. Unique short-name match (deterministik)
        3. Graph-score ile cozumle (deterministik - sorted candidates)
        4. Ambiguous durumda primary=None
        
        Args:
            target: Kullanici tarafindan verilen symbol adi
            context_file: Istege bagli - hedef sembolun bulunmasi muhtemel file
            
        Returns:
            SymbolResolutionResult - cozumleme sonucu
        """
        warnings = []
        
        # Adim 1: Exact match
        if target in self.symbols:
            return SymbolResolutionResult(
                primary=target,
                candidates=[target],
                resolution_type="exact",
                warnings=[],
                scores={target: 1.0}
            )
        
        # Adim 2: Unique short-name match
        if target in self.short_name_map:
            candidates = self.short_name_map[target]
            
            if len(candidates) == 1:
                # Tek eslesme - unique match
                full_name = candidates[0]
                return SymbolResolutionResult(
                    primary=full_name,
                    candidates=candidates,
                    resolution_type="unique_short",
                    warnings=[],
                    scores={full_name: 1.0}
                )
            else:
                # Birden fazla eslesme - graph-score ile cozumle
                return self._resolve_by_graph_score(target, candidates, context_file)
        
        # Hic eslesme bulunamadi
        return SymbolResolutionResult(
            primary=None,
            candidates=[],
            resolution_type="not_found",
            warnings=[f"'{target}' sembolu graph'ta bulunamadi"],
            scores={}
        )
    
    def _resolve_by_graph_score(self, short_name: str, candidates: List[str], 
                                 context_file: Optional[str]) -> SymbolResolutionResult:
        """
        Birden fazla aday arasindan graph metriklerine gore secim yap.
        
        Skorlama (DETERMINISTIK):
        - indegree * 2.0: Cok called semboller daha merkezi/onemli
        - total_calls * 0.5: Aktif semboller (cagiran + called)
        - same_file * 3.0: Ayni dosyadaki symbol bonus (eger context_file verilmisse)
        
        Ambiguous durum: En iyi ve ikinci en iyi skor cok yakinsa (< 1.0 fark)
        """
        scores: Dict[str, float] = {}
        
        # DETERMINISM: sorted candidates ile deterministik hesaplama
        for full_name in sorted(candidates):
            metrics = self.symbol_metrics[full_name]
            
            # Base score: indegree onemli (baskalari tarafindan cagrilma)
            score = metrics["indegree"] * 2.0
            
            # Aktivite bonusu
            score += metrics["total_calls"] * 0.5
            
            # Same-file bonus (eger context biliniyorsa)
            if context_file and metrics["file"]:
                if context_file in metrics["file"] or metrics["file"] in context_file:
                    score += 3.0
            
            scores[full_name] = score
        
        # DETERMINISM: Skora gore sirala (skor DESC, isim ASC tie-breaker)
        sorted_candidates = sorted(scores.keys(), key=lambda x: (-scores[x], x))
        
        # En yuksek skorlu aday
        best_candidate = sorted_candidates[0]
        best_score = scores[best_candidate]
        
        # Ikinci en yuksek skorlu aday (ambiguity check for)
        second_best_score = scores[sorted_candidates[1]] if len(sorted_candidates) > 1 else 0
        
        # Ambiguity check: En iyi ve ikinci en iyi skor cok yakinsa
        if second_best_score > 0 and (best_score - second_best_score) < 1.0:
            # Ambiguous durum - primary bos birak (GUARDRAIL)
            warnings = [
                f"'{short_name}' for birden fazla eslesme bulundu: {candidates}",
                f"En iyi aday: {best_candidate} (score: {best_score:.1f})",
                f"Ikinci aday: {sorted_candidates[1]} (score: {second_best_score:.1f})",
                "Lutfen tam symbol adini (full_name) kullanin"
            ]
            return SymbolResolutionResult(
                primary=None,  # GUARDRAIL: Ambiguous durumda None
                candidates=sorted_candidates,
                resolution_type="ambiguous",
                warnings=warnings,
                scores=scores
            )
        
        # Net bir kazanan var
        return SymbolResolutionResult(
            primary=best_candidate,
            candidates=sorted_candidates,
            resolution_type="graph_scored",
            warnings=[],
            scores=scores
        )
    
    def get_all_short_names(self) -> Dict[str, List[str]]:
        """Tum kisa isimlerin eslestigi tam isimleri return."""
        return self.short_name_map.copy()


@dataclass
class SymbolImpact:
    """Bir sembolun etki analizini temsil eder."""
    symbol: str
    level: ImpactLevel
    score: float                    # 0.0 - 1.0 arasi etki skoru
    depth: int                      # Hedeften uzaklik (0=kendisi, 1=direct, 2+=indirect)
    call_paths: List[List[str]] = field(default_factory=list)  # Cagri zincirleri
    
    def to_dict(self) -> Dict[str, Any]:
        """Sozluk formatina donustur."""
        return {
            "symbol": self.symbol,
            "level": self.level.value,
            "score": round(self.score, 3),
            "depth": self.depth,
            "call_paths": self.call_paths[:3]  # Max 3 path goster
        }


@dataclass  
class ContextDecision:
    """BBC Context Optimizer'in urettigi karar."""
    target: str
    primary: List[str]              # %40 onem - TEKIL (max 1 symbol)
    direct: List[str]               # %30 onem
    indirect: List[str]             # %20 onem
    ignored: List[str]              # IGNORED - external ve unknown cagrilar
    safety: List[str]               # Guvenlik kurallari ve uyarilar
    impact_scores: Dict[str, float] # Tum sembollerin skorlari
    stats: Dict[str, Any]           # Istatistikler
    
    def to_dict(self) -> Dict[str, Any]:
        """Sozluk formatina donustur - DETERMINISTIK siralama."""
        # DETERMINISM: Tum listeler sorted, dictler sorted keys
        return {
            "target": self.target,
            "primary": sorted(self.primary),
            "direct": sorted(self.direct),
            "indirect": sorted(self.indirect),
            "ignored": sorted(self.ignored),
            "safety": self.safety,  # Safety sirali degil (insertion order onemli)
            "impact_scores": {k: round(v, 3) for k, v in sorted(self.impact_scores.items())},
            "stats": self.stats
        }


class BlastRadiusAnalyzer:
    """
    Blast radius analizcisi - hedef symbol degisirse etki alanini hesaplar.
    
    Algoritma:
    1. Hedef sembolden basla (depth=0)
    2. called_by iliskilerini takip et (depth=1,2,3...)
    3. Her seviyedeki sembollere skor ata
    4. Cevrimsel bagimliliklari tespit et
    
    GUARDRAILS:
    - EXTERNAL cagrilar: traversal'a girmez, ignore listesine alinir
    - UNKNOWN cagrilar: traversal'a girmez, safety uyarisi uretilir
    """
    
    def __init__(self, symbol_graph: Dict[str, Any]):
        """
        Args:
            symbol_graph: SymbolGraph.to_dict() ciktisi
        """
        # DETERMINISM: sorted ile deterministik yukleme
        symbols_list = symbol_graph.get("symbols", [])
        self.symbols = {s["symbol"]: s for s in sorted(symbols_list, key=lambda x: x["symbol"])}
        self.graph_stats = symbol_graph.get("graph_stats", {})
        
        # Hizli lookup for called_by index
        self.called_by_index: Dict[str, List[str]] = {}
        self._build_called_by_index()
    
    def _build_called_by_index(self):
        """Called_by iliskilerini indexle - only INTERNAL cagrilar."""
        for sym_name in sorted(self.symbols.keys()):
            sym_data = self.symbols[sym_name]
            self.called_by_index[sym_name] = []
            called_by = sym_data.get("called_by", [])
            
            for call in called_by:
                caller = call.get("symbol") if isinstance(call, dict) else call
                call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
                
                # GUARDRAIL: Sadece INTERNAL calls ekle
                if caller and caller != sym_name and call_type == "internal":
                    self.called_by_index[sym_name].append(caller)
            
            # DETERMINISM: Listeyi sirala
            self.called_by_index[sym_name] = sorted(self.called_by_index[sym_name])
    
    def analyze(self, target: str, max_depth: int = 5) -> Tuple[List[SymbolImpact], List[str], List[str]]:
        """
        Bir sembolun blast radius'ini analysis et.
        
        Args:
            target: Hedef symbol adi
            max_depth: Maksimum arama derinligi (Sonsuz donguyu onlemek for)
            
        Returns:
            Tuple: (SymbolImpact listesi, ignored_external_calls, safety_warnings)
            - impacts: Etki analysis sonuclari (siralanmis)
            - ignored_external_calls: External cagrilar listesi
            - safety_warnings: Unknown cagrilar ve diger uyarilar
        """
        if target not in self.symbols:
            return [], [], [f"Target '{target}' not found in graph"]
        
        impacts: Dict[str, SymbolImpact] = {}
        visited: Set[str] = set()
        ignored_external_calls: List[str] = []
        safety_warnings: List[str] = []
        
        # GUARDRAIL: Hedef sembolun kendi external call'larini topla
        target_sym = self.symbols[target]
        target_calls = target_sym.get("calls", [])
        for call in target_calls:
            call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
            call_symbol = call.get("symbol") if isinstance(call, dict) else call
            
            if call_type == "external" and call_symbol:
                ignored_external_calls.append(call_symbol)
            elif call_type == "unknown" and call_symbol:
                safety_warnings.append(f"Unknown call '{call_symbol}' detected in target")
        
        # DETERMINISM: BFS kuyrugu sorted liste olarak start
        queue: List[Tuple[str, int, List[str]]] = [(target, 0, [target])]
        
        while queue:
            current, depth, path = queue.pop(0)
            
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            
            # Etki skorunu hesapla
            score = self._calculate_impact_score(depth, current)
            level = self._depth_to_level(depth)
            
            # Sembol etkisini kaydet
            if current not in impacts:
                impacts[current] = SymbolImpact(
                    symbol=current,
                    level=level,
                    score=score,
                    depth=depth,
                    call_paths=[]
                )
            
            # Path ekle (maksimum 3)
            if len(impacts[current].call_paths) < 3:
                impacts[current].call_paths.append(path.copy())
            
            # Sonraki seviyeyi kuyruga ekle - only INTERNAL cagiranlar
            if depth < max_depth:
                current_sym = self.symbols.get(current, {})
                callers_data = current_sym.get("called_by", [])
                
                for call in callers_data:
                    caller = call.get("symbol") if isinstance(call, dict) else call
                    call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
                    
                    # GUARDRAIL: EXTERNAL cagrilar traversal'a girmez
                    if call_type == "external":
                        if caller and caller not in ignored_external_calls:
                            ignored_external_calls.append(caller)
                        continue
                    
                    # GUARDRAIL: UNKNOWN cagrilar traversal'a girmez, safety'e ekle
                    if call_type == "unknown":
                        if caller and caller not in safety_warnings:
                            safety_warnings.append(f"Unknown call '{caller}' detected in graph traversal")
                        continue
                    
                    # Sadece internal ve cevrimsel olmayan cagrilar
                    if caller and caller not in path:
                        new_path = path + [caller]
                        queue.append((caller, depth + 1, new_path))
                
                # DETERMINISM: Kuyrugu sirala (symbol name ASC)
                queue = sorted(queue, key=lambda x: x[0])
        
        # DETERMINISM: Skora gore sirala (skor DESC, symbol ASC tie-breaker)
        sorted_impacts = sorted(impacts.values(), key=lambda x: (-x.score, x.depth, x.symbol))
        
        return sorted_impacts, sorted(ignored_external_calls), safety_warnings
    
    def _calculate_impact_score(self, depth: int, symbol: str) -> float:
        """
        Derinlige gore etki skoru hesapla.
        
        Skorlama (DETERMINISTIK):
        - Depth 0 (target): 1.0 (%40)
        - Depth 1 (direct): 0.75 (%30)
        - Depth 2 (indirect): 0.50 (%20)
        - Depth 3+ (distant): 0.25 (%10)
        """
        base_scores = {
            0: 1.0,   # PRIMARY
            1: 0.75,  # DIRECT
            2: 0.50,  # INDIRECT
            3: 0.25,  # DISTANT
        }
        
        base = base_scores.get(min(depth, 3), 0.1)
        
        # Sembolun graph'taki onemine gore ayarlama
        # Cok called semboller daha onemli
        caller_count = len(self.called_by_index.get(symbol, []))
        if caller_count > 5:
            base *= 1.1  # Cok kullanilan symbol - siniri asma
        elif caller_count == 0 and depth > 0:
            base *= 0.9  # Leaf node - daha az kritik
        
        return min(base, 1.0)  # Max 1.0
    
    def _depth_to_level(self, depth: int) -> ImpactLevel:
        """Derinligi etki seviyesine donustur."""
        if depth == 0:
            return ImpactLevel.PRIMARY
        elif depth == 1:
            return ImpactLevel.DIRECT
        elif depth == 2:
            return ImpactLevel.INDIRECT
        else:
            return ImpactLevel.DISTANT


class ContextOptimizer:
    """
    BBC Context Optimizer - AI for optimize edilmis context uretir.
    
    Bu sinif:
    1. Blast radius analysis yapar
    2. Sembolleri onem sirasina gore kategorize eder
    3. "Gurultu" symbols filtreler
    4. Guvenlik kurallari uretir
    5. Deterministik BBC karari creates
    
    GUARDRAILS (Asama 3.7):
    - External Call Guard: EXTERNAL cagrilar PRIMARY/DIRECT/INDIRECT olamaz
    - Unknown Call Guard: UNKNOWN cagrilar dependency olarak sayilmaz
    - Deterministic SymbolResolver: Sirali cozumleme, ambiguous durumda None
    - PRIMARY Secim Kurali: Sadece Internal + Resolved + Score>0, TEKIL
    - Context Reduction Kilidi: ratio < 0.6 ise exception
    - Determinizm Kilidi: sorted node list, stable edge ordering
    - Cikti Kontrati: {"primary", "direct", "indirect", "ignored", "safety"}
    """
    
    # Varsayilan parametreler
    DEFAULT_PRIMARY_THRESHOLD = 0.85   # %40
    DEFAULT_DIRECT_THRESHOLD = 0.60    # %30  
    DEFAULT_INDIRECT_THRESHOLD = 0.35  # %20
    DEFAULT_MAX_CONTEXT_SYMBOLS = 50   # Maksimum symbol sayisi
    DEFAULT_MIN_REDUCTION_RATIO = 0.6  # GUARDRAIL: Minimum context reduction ratio
    
    def __init__(self, symbol_graph: Dict[str, Any],
                 primary_threshold: float = DEFAULT_PRIMARY_THRESHOLD,
                 direct_threshold: float = DEFAULT_DIRECT_THRESHOLD,
                 indirect_threshold: float = DEFAULT_INDIRECT_THRESHOLD,
                 max_symbols: int = DEFAULT_MAX_CONTEXT_SYMBOLS,
                 min_reduction_ratio: float = DEFAULT_MIN_REDUCTION_RATIO):
        """
        Args:
            symbol_graph: SymbolGraph ciktisi
            primary_threshold: Primary siniri (varsayilan: 0.85)
            direct_threshold: Direct siniri (varsayilan: 0.60)
            indirect_threshold: Indirect siniri (varsayilan: 0.35)
            max_symbols: Maksimum context sembolu
            min_reduction_ratio: Minimum context reduction ratio (GUARDRAIL)
        """
        self.symbol_graph = symbol_graph
        self.analyzer = BlastRadiusAnalyzer(symbol_graph)
        self.resolver = SymbolResolver(symbol_graph)
        
        self.primary_threshold = primary_threshold
        self.direct_threshold = direct_threshold
        self.indirect_threshold = indirect_threshold
        self.max_symbols = max_symbols
        self.min_reduction_ratio = min_reduction_ratio  # GUARDRAIL
    
    def optimize(self, target: str, context_file: Optional[str] = None) -> ContextDecision:
        """
        Bir hedef symbol for optimize edilmis context uret.
        
        GUARDRAILS:
        - Ambiguous resolution: primary=None
        - External cagrilar: ignored listesine
        - Unknown cagrilar: safety uyarisina
        - Reduction < 0.6: exception
        - PRIMARY tekil olmak zorunda
        
        Args:
            target: Hedef symbol adi (kisa veya tam ad)
            context_file: Istege bagli - hedef sembolun bulunmasi muhtemel file
            
        Returns:
            ContextDecision - BBC karari
            
        Raises:
            ContextReductionError: Eger context reduction ratio < min_reduction_ratio
        """
        # 1. Sembol cozumleme (SymbolResolver)
        resolution = self.resolver.resolve(target, context_file)
        
        # Cozumleme basarisizsa veya ambiguous ise
        if resolution.resolution_type == "not_found":
            return self._unresolved_decision(target, resolution)
        
        if resolution.resolution_type == "ambiguous":
            return self._ambiguous_decision(target, resolution)
        
        # Cozumlenen tam symbol adini kullan
        resolved_target = resolution.primary
        
        # GUARDRAIL: PRIMARY secim kurali check
        # Sadece Internal + Resolved + Score>0 olabilir
        if not resolved_target or resolved_target not in self.analyzer.symbols:
            return self._unresolved_decision(target, resolution)
        
        # 2. Blast radius analysis
        impacts, ignored_external, safety_warnings = self.analyzer.analyze(resolved_target)
        
        if not impacts:
            return self._empty_decision(resolved_target)
        
        # 3. Sembolleri kategorize et
        primary = []
        direct = []
        indirect = []
        ignored = []
        
        impact_scores = {}
        
        for imp in impacts:
            impact_scores[imp.symbol] = imp.score
            
            # GUARDRAIL: Sadece internal semboller kategorize edilir
            if imp.score >= self.primary_threshold:
                primary.append(imp.symbol)
            elif imp.score >= self.direct_threshold:
                direct.append(imp.symbol)
            elif imp.score >= self.indirect_threshold:
                indirect.append(imp.symbol)
            else:
                ignored.append(imp.symbol)
        
        # GUARDRAIL: PRIMARY tekil olmak zorunda
        if len(primary) > 1:
            # En yuksek skorlu olani primary yap, digerlerini direct'e tasi
            sorted_primary = sorted(primary, key=lambda x: -impact_scores[x])
            primary = [sorted_primary[0]]
            direct = sorted_primary[1:] + direct
        
        # External calls ignored listesine ekle
        ignored.extend(ignored_external)
        
        # 4. Context limiti check
        total_selected = len(primary) + len(direct) + len(indirect)
        if total_selected > self.max_symbols:
            # Oncelik sirasina gore kes
            indirect = self._limit_category(indirect, 
                max(0, self.max_symbols - len(primary) - len(direct)))
            if len(primary) + len(direct) > self.max_symbols:
                direct = self._limit_category(direct,
                    max(0, self.max_symbols - len(primary)))
        
        # 5. Guvenlik kurallari uret
        safety_rules = self._generate_safety_rules(resolved_target, impacts)
        
        # Resolution bilgisi for ek uyarilar
        if resolution.resolution_type in ("unique_short", "graph_scored"):
            safety_rules.insert(0, f"'{target}' -> '{resolved_target}' olarak cozumlendi")
        
        # Unknown call uyarilarini ekle
        safety_rules.extend(safety_warnings)
        
        # 6. Context reduction hesapla ve check et (GUARDRAIL)
        total_analyzed = len(impacts)
        selected_count = len(primary) + len(direct) + len(indirect)
        reduction_ratio = self._calculate_reduction_ratio(total_analyzed, selected_count)
        
        # GUARDRAIL: Context Reduction Kilidi
        if reduction_ratio < self.min_reduction_ratio:
            raise ContextReductionError(
                f"Context reduction ratio ({reduction_ratio:.2f}) is below minimum threshold "
                f"({self.min_reduction_ratio}). This indicates potential context explosion. "
                f"Analyzed: {total_analyzed}, Selected: {selected_count}"
            )
        
        # 7. Istatistikler
        stats = {
            "total_symbols": len(self.analyzer.symbols),
            "analyzed_symbols": len(impacts),
            "primary_count": len(primary),
            "direct_count": len(direct),
            "indirect_count": len(indirect),
            "ignored_count": len(ignored),
            "context_reduction": f"{reduction_ratio * 100:.1f}%",
            "resolution": {
                "original_target": target,
                "resolved_target": resolved_target,
                "resolution_type": resolution.resolution_type
            }
        }
        
        return ContextDecision(
            target=target,
            primary=primary,
            direct=direct,
            indirect=indirect,
            ignored=ignored,
            safety=safety_rules,
            impact_scores=impact_scores,
            stats=stats
        )
    
    def _limit_category(self, symbols: List[str], limit: int) -> List[str]:
        """Bir kategorideki symbols limite gore sinirla - DETERMINISTIK."""
        if len(symbols) <= limit:
            return sorted(symbols)
        # DETERMINISM: Sirali kesme
        return sorted(symbols)[:limit]
    
    def _generate_safety_rules(self, target: str, 
                               impacts: List[SymbolImpact]) -> List[str]:
        """
        Guvenlik kurallari uret.
        
        Bu kurallar AI'in dikkat etmesi gereken seyleri belirtir.
        """
        rules = []
        
        # Hedef symbol bilgisi
        target_sym = self.analyzer.symbols.get(target, {})
        sym_type = target_sym.get("type", "unknown")
        
        # Temel guvenlik kurali
        rules.append(f"'{target}' sembolunun imzasi korunmali")
        
        # Tip ozel kurallar
        if sym_type == "function":
            rules.append("Fonksiyon donus tipi degisirse cagiranlar etkilenir")
        elif sym_type == "method":
            rules.append("self/cls parametre imzasi korunmali")
        elif sym_type == "class":
            rules.append("Sinif constructor'i degisirse instantiation noktalari etkilenir")
        
        # Yuksek etkili symbol check
        high_impact = [i for i in impacts if i.score > 0.5 and i.symbol != target]
        if high_impact:
            rules.append(f"{len(high_impact)} yuksek etkili symbol var - dikkatli refactor")
        
        # Cevrimsel bagimlilik check
        cycles = self._detect_cycles(target, impacts)
        if cycles:
            rules.append(f"Cevrimsel bagimlilik tespit edildi: kontrollu degisim yap")
        
        return rules
    
    def _detect_cycles(self, target: str, 
                       impacts: List[SymbolImpact]) -> List[List[str]]:
        """Cevrimsel bagimliliklari tespit et."""
        cycles = []
        for imp in impacts:
            for path in imp.call_paths:
                if len(path) > 2 and path[0] == path[-1]:
                    cycles.append(path)
        return cycles
    
    def _calculate_reduction_ratio(self, total: int, selected: int) -> float:
        """Context reduction ratio hesapla."""
        if total == 0:
            return 1.0
        reduction = (total - selected) / total
        return reduction
    
    def _empty_decision(self, target: str) -> ContextDecision:
        """Hedef bulunamazsa bos karar return."""
        return ContextDecision(
            target=target,
            primary=[],
            direct=[],
            indirect=[],
            ignored=[],
            safety=[f"Hedef symbol '{target}' graph'ta bulunamadi"],
            impact_scores={},
            stats={"error": "Target not found"}
        )
    
    def _unresolved_decision(self, target: str, resolution: SymbolResolutionResult) -> ContextDecision:
        """Sembol cozumlenemezse karar return."""
        return ContextDecision(
            target=target,
            primary=[],
            direct=[],
            indirect=[],
            ignored=[],
            safety=resolution.warnings,
            impact_scores={},
            stats={
                "error": "Symbol not found",
                "resolution_type": resolution.resolution_type,
                "candidates": resolution.candidates
            }
        )
    
    def _ambiguous_decision(self, target: str, resolution: SymbolResolutionResult) -> ContextDecision:
        """Ambiguous durumda karar return - primary bos kalir."""
        # Adaylari ignore listesine koy (kullanici bilgilensin)
        return ContextDecision(
            target=target,
            primary=[],  # BOS - guvenlik for
            direct=[],
            indirect=[],
            ignored=sorted(resolution.candidates),  # Adaylar bilgi olarak
            safety=resolution.warnings,
            impact_scores=resolution.scores,
            stats={
                "error": "Ambiguous symbol resolution",
                "resolution_type": resolution.resolution_type,
                "candidates_count": len(resolution.candidates),
                "candidates": sorted(resolution.candidates)
            }
        )
    
    def compare_targets(self, targets: List[str]) -> Dict[str, ContextDecision]:
        """
        Birden fazla hedef for kararlari karsilastir.
        
        Bu, cakisan degisikliklerin analizinde is used.
        """
        decisions = {}
        # DETERMINISM: sorted targets
        for target in sorted(targets):
            decisions[target] = self.optimize(target)
        return decisions
    
    def export_decision(self, decision: ContextDecision, 
                        output_path: str, format: str = "json"):
        """
        Karari dosyaya kaydet.
        
        Args:
            decision: ContextDecision nesnesi
            output_path: Cikti file yolu
            format: "json" veya "txt"
        """
        path = Path(output_path)
        
        if format == "json":
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(decision.to_dict(), f, indent=2, ensure_ascii=False)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._format_decision_text(decision))
    
    def _format_decision_text(self, decision: ContextDecision) -> str:
        """Karari insan-okunabilir metin formatina donustur."""
        lines = [
            "=" * 60,
            "BBC CONTEXT OPTIMIZER - KARAR RAPORU",
            "=" * 60,
            "",
            f"Hedef Sembol: {decision.target}",
            "",
            "[PRIMARY - %40 Onem]",
        ]
        
        for sym in sorted(decision.primary):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[DIRECT - %30 Onem]"])
        for sym in sorted(decision.direct):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[INDIRECT - %20 Onem]"])
        for sym in sorted(decision.indirect):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[IGNORED - External/Unknown]"])
        for sym in sorted(decision.ignored):
            lines.append(f"  • {sym}")
        
        lines.extend(["", "[SAFETY - Guvenlik Kurallari]"])
        for rule in decision.safety:
            lines.append(f"  ⚠ {rule}")
        
        lines.extend(["", "[ISTATISTIKLER]"])
        for key, value in decision.stats.items():
            lines.append(f"  {key}: {value}")
        
        lines.extend(["", "=" * 60])
        
        return "\n".join(lines)


def main():
    """Komut satiri arayuzu."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BBC Context Optimizer - Symbol bazli context optimizasyonu'
    )
    parser.add_argument('graph_json', help='SymbolGraph JSON ciktisi')
    parser.add_argument('target', help='Hedef symbol adi')
    parser.add_argument('--out', '-o', help='Cikti dosyasi', default=None)
    parser.add_argument('--format', '-f', choices=['json', 'txt'], 
                       default='json', help='Cikti formati')
    parser.add_argument('--max-symbols', '-m', type=int, default=50,
                       help='Maksimum context sembolu')
    
    args = parser.parse_args()
    
    # Graph'i oku
    with open(args.graph_json, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # Optimizer create
    optimizer = ContextOptimizer(
        symbol_graph=graph_data,
        max_symbols=args.max_symbols
    )
    
    # Optimize et
    decision = optimizer.optimize(args.target)
    
    # Cikti
    if args.out:
        optimizer.export_decision(decision, args.out, args.format)
        print(f"Karar kaydedildi: {args.out}")
    else:
        if args.format == 'json':
            print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(optimizer._format_decision_text(decision))


if __name__ == "__main__":
    main()
