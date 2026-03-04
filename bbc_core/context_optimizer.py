"""
BBC Context Optimizer - Aşama 3.7: Context Optimizer Guardrails

Bu modül sembol graph'ını analiz ederek AI için optimize edilmiş context üretir.
- SymbolGraph çıktısını input olarak alır
- Blast radius hesaplar (kim kimi çağırır)
- BBC kararı üretir: "Bu semboller önemli, diğerleri gürültü"
- LLM/AI kullanmaz - tamamen deterministiktir

IMPORTANT GUARANTEES:
- Runtime guarantee YOK - Sadece AST-based static analysis
- Dynamic call'ları (eval, getattr, import_string vb.) çözmez
- Sadece kodda explicit görülen çağrıları analiz eder

Çıktı Formatı (BBC Kararı):
{
  "target": "compute_hash",
  "primary": ["compute_hash"],        # %40 önem - değişen sembol (TEKİL)
  "direct": ["analyze_project"],      # %30 önem - doğrudan çağıranlar
  "indirect": ["run_analysis"],       # %20 önem - dolaylı çağıranlar  
  "ignored": ["external_calls"],      # IGNORED - external ve unknown çağrılar
  "safety": ["signature değişmesin"]  # güvenlik kuralları ve uyarılar
}
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum
from pathlib import Path


class ImpactLevel(Enum):
    """Etki seviyeleri - önem sırasına göre."""
    PRIMARY = "primary"      # %40 - Hedef sembol kendisi
    DIRECT = "direct"        # %30 - Doğrudan bağımlılar (1. seviye)
    INDIRECT = "indirect"    # %20 - Dolaylı bağımlılar (2+ seviye)
    DISTANT = "distant"      # %10 - Uzak bağımlılar (gerekiyorsa)
    IGNORE = "ignore"        # %0 - Gürültü, dahil etme


class ContextOptimizerError(Exception):
    """Context Optimizer hata sınıfı."""
    pass


class ContextReductionError(ContextOptimizerError):
    """Context reduction çok düşükse fırlatılır."""
    pass


@dataclass
class SymbolResolutionResult:
    """SymbolResolver'ın ürettiği çözümleme sonucu."""
    primary: Optional[str]          # Çözümlenen tam sembol adı (veya None)
    candidates: List[str]           # Tüm eşleşen adaylar
    resolution_type: str            # "exact", "unique_short", "graph_scored", "ambiguous", "not_found"
    warnings: List[str]             # Güvenlik uyarıları
    scores: Dict[str, float]        # Adayların skorları (graph_scored için)
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        return {
            "primary": self.primary,
            "candidates": self.candidates,
            "resolution_type": self.resolution_type,
            "warnings": self.warnings,
            "scores": {k: round(v, 3) for k, v in self.scores.items()}
        }


class SymbolResolver:
    """
    Kısa sembol isimlerini graph'taki tam isimlerle eşleştirir.
    
    Problem: Kullanıcı "extract" der ama graph'ta "PythonSymbolExtractor.extract" var
    Çözüm: Deterministik çözümleme algoritması (LLM kullanmaz)
    
    Çözüm sırası (DETERMINISTIK):
    1. Exact full_name match
    2. Unique short-name match  
    3. Graph-score ile çözümleme
    4. Ambiguous durumda: primary=None, resolution_status="ambiguous"
    
    Fallback YOK - Belirsiz durumda None döner.
    """
    
    def __init__(self, symbol_graph: Dict[str, Any]):
        """
        Args:
            symbol_graph: SymbolGraph çıktısı
        """
        # DETERMINISM: sorted ile deterministik sıralama
        symbols_list = symbol_graph.get("symbols", [])
        self.symbols = {s["symbol"]: s for s in sorted(symbols_list, key=lambda x: x["symbol"])}
        
        # Hızlı lookup için indeksler
        self._build_short_name_index()
        self._build_graph_metrics()
    
    def _build_short_name_index(self):
        """Kısa isimlerden tam isimlere indeks oluştur."""
        self.short_name_map: Dict[str, List[str]] = {}
        
        # DETERMINISM: sorted keys ile iterasyon
        for full_name in sorted(self.symbols.keys()):
            # Kısa ismi çıkar (son parça)
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
            
            # Indegree: Bu sembolü çağıranların sayısı
            called_by = sym_data.get("called_by", [])
            indegree = len(called_by)
            
            # Outdegree: Bu sembolün çağırdıklarının sayısı
            calls = sym_data.get("calls", [])
            outdegree = len(calls)
            
            # Toplam çağrı sayısı (graph'taki önemi)
            total_calls = indegree + outdegree
            
            # Dosya bilgisi
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
        Hedef sembolü çözümle.
        
        Çözüm sırası:
        1. Exact match (deterministik)
        2. Unique short-name match (deterministik)
        3. Graph-score ile çözümle (deterministik - sorted candidates)
        4. Ambiguous durumda primary=None
        
        Args:
            target: Kullanıcı tarafından verilen sembol adı
            context_file: İsteğe bağlı - hedef sembolün bulunması muhtemel dosya
            
        Returns:
            SymbolResolutionResult - çözümleme sonucu
        """
        warnings = []
        
        # Adım 1: Exact match
        if target in self.symbols:
            return SymbolResolutionResult(
                primary=target,
                candidates=[target],
                resolution_type="exact",
                warnings=[],
                scores={target: 1.0}
            )
        
        # Adım 2: Unique short-name match
        if target in self.short_name_map:
            candidates = self.short_name_map[target]
            
            if len(candidates) == 1:
                # Tek eşleşme - unique match
                full_name = candidates[0]
                return SymbolResolutionResult(
                    primary=full_name,
                    candidates=candidates,
                    resolution_type="unique_short",
                    warnings=[],
                    scores={full_name: 1.0}
                )
            else:
                # Birden fazla eşleşme - graph-score ile çözümle
                return self._resolve_by_graph_score(target, candidates, context_file)
        
        # Hiç eşleşme bulunamadı
        return SymbolResolutionResult(
            primary=None,
            candidates=[],
            resolution_type="not_found",
            warnings=[f"'{target}' sembolü graph'ta bulunamadı"],
            scores={}
        )
    
    def _resolve_by_graph_score(self, short_name: str, candidates: List[str], 
                                 context_file: Optional[str]) -> SymbolResolutionResult:
        """
        Birden fazla aday arasından graph metriklerine göre seçim yap.
        
        Skorlama (DETERMINISTIK):
        - indegree * 2.0: Çok çağrılan semboller daha merkezi/önemli
        - total_calls * 0.5: Aktif semboller (çağıran + çağrılan)
        - same_file * 3.0: Aynı dosyadaki sembol bonus (eğer context_file verilmişse)
        
        Ambiguous durum: En iyi ve ikinci en iyi skor çok yakınsa (< 1.0 fark)
        """
        scores: Dict[str, float] = {}
        
        # DETERMINISM: sorted candidates ile deterministik hesaplama
        for full_name in sorted(candidates):
            metrics = self.symbol_metrics[full_name]
            
            # Base score: indegree önemli (başkaları tarafından çağrılma)
            score = metrics["indegree"] * 2.0
            
            # Aktivite bonusu
            score += metrics["total_calls"] * 0.5
            
            # Same-file bonus (eğer context biliniyorsa)
            if context_file and metrics["file"]:
                if context_file in metrics["file"] or metrics["file"] in context_file:
                    score += 3.0
            
            scores[full_name] = score
        
        # DETERMINISM: Skora göre sırala (skor DESC, isim ASC tie-breaker)
        sorted_candidates = sorted(scores.keys(), key=lambda x: (-scores[x], x))
        
        # En yüksek skorlu aday
        best_candidate = sorted_candidates[0]
        best_score = scores[best_candidate]
        
        # İkinci en yüksek skorlu aday (ambiguity kontrolü için)
        second_best_score = scores[sorted_candidates[1]] if len(sorted_candidates) > 1 else 0
        
        # Ambiguity check: En iyi ve ikinci en iyi skor çok yakınsa
        if second_best_score > 0 and (best_score - second_best_score) < 1.0:
            # Ambiguous durum - primary boş bırak (GUARDRAIL)
            warnings = [
                f"'{short_name}' için birden fazla eşleşme bulundu: {candidates}",
                f"En iyi aday: {best_candidate} (score: {best_score:.1f})",
                f"İkinci aday: {sorted_candidates[1]} (score: {second_best_score:.1f})",
                "Lütfen tam sembol adını (full_name) kullanın"
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
        """Tüm kısa isimlerin eşleştiği tam isimleri döndür."""
        return self.short_name_map.copy()


@dataclass
class SymbolImpact:
    """Bir sembolün etki analizini temsil eder."""
    symbol: str
    level: ImpactLevel
    score: float                    # 0.0 - 1.0 arası etki skoru
    depth: int                      # Hedeften uzaklık (0=kendisi, 1=direct, 2+=indirect)
    call_paths: List[List[str]] = field(default_factory=list)  # Çağrı zincirleri
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür."""
        return {
            "symbol": self.symbol,
            "level": self.level.value,
            "score": round(self.score, 3),
            "depth": self.depth,
            "call_paths": self.call_paths[:3]  # Max 3 path göster
        }


@dataclass  
class ContextDecision:
    """BBC Context Optimizer'ın ürettiği karar."""
    target: str
    primary: List[str]              # %40 önem - TEKİL (max 1 sembol)
    direct: List[str]               # %30 önem
    indirect: List[str]             # %20 önem
    ignored: List[str]              # IGNORED - external ve unknown çağrılar
    safety: List[str]               # Güvenlik kuralları ve uyarılar
    impact_scores: Dict[str, float] # Tüm sembollerin skorları
    stats: Dict[str, Any]           # İstatistikler
    
    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştür - DETERMINISTIK sıralama."""
        # DETERMINISM: Tüm listeler sorted, dictler sorted keys
        return {
            "target": self.target,
            "primary": sorted(self.primary),
            "direct": sorted(self.direct),
            "indirect": sorted(self.indirect),
            "ignored": sorted(self.ignored),
            "safety": self.safety,  # Safety sıralı değil (insertion order önemli)
            "impact_scores": {k: round(v, 3) for k, v in sorted(self.impact_scores.items())},
            "stats": self.stats
        }


class BlastRadiusAnalyzer:
    """
    Blast radius analizcisi - hedef sembol değişirse etki alanını hesaplar.
    
    Algoritma:
    1. Hedef sembolden başla (depth=0)
    2. called_by ilişkilerini takip et (depth=1,2,3...)
    3. Her seviyedeki sembollere skor ata
    4. Çevrimsel bağımlılıkları tespit et
    
    GUARDRAILS:
    - EXTERNAL çağrılar: traversal'a girmez, ignore listesine alınır
    - UNKNOWN çağrılar: traversal'a girmez, safety uyarısı üretilir
    """
    
    def __init__(self, symbol_graph: Dict[str, Any]):
        """
        Args:
            symbol_graph: SymbolGraph.to_dict() çıktısı
        """
        # DETERMINISM: sorted ile deterministik yükleme
        symbols_list = symbol_graph.get("symbols", [])
        self.symbols = {s["symbol"]: s for s in sorted(symbols_list, key=lambda x: x["symbol"])}
        self.graph_stats = symbol_graph.get("graph_stats", {})
        
        # Hızlı lookup için called_by index
        self.called_by_index: Dict[str, List[str]] = {}
        self._build_called_by_index()
    
    def _build_called_by_index(self):
        """Called_by ilişkilerini indexle - sadece INTERNAL çağrılar."""
        for sym_name in sorted(self.symbols.keys()):
            sym_data = self.symbols[sym_name]
            self.called_by_index[sym_name] = []
            called_by = sym_data.get("called_by", [])
            
            for call in called_by:
                caller = call.get("symbol") if isinstance(call, dict) else call
                call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
                
                # GUARDRAIL: Sadece INTERNAL çağrıları ekle
                if caller and caller != sym_name and call_type == "internal":
                    self.called_by_index[sym_name].append(caller)
            
            # DETERMINISM: Listeyi sırala
            self.called_by_index[sym_name] = sorted(self.called_by_index[sym_name])
    
    def analyze(self, target: str, max_depth: int = 5) -> Tuple[List[SymbolImpact], List[str], List[str]]:
        """
        Bir sembolün blast radius'ını analiz et.
        
        Args:
            target: Hedef sembol adı
            max_depth: Maksimum arama derinliği (Sonsuz döngüyü önlemek için)
            
        Returns:
            Tuple: (SymbolImpact listesi, ignored_external_calls, safety_warnings)
            - impacts: Etki analizi sonuçları (sıralanmış)
            - ignored_external_calls: External çağrılar listesi
            - safety_warnings: Unknown çağrılar ve diğer uyarılar
        """
        if target not in self.symbols:
            return [], [], [f"Target '{target}' not found in graph"]
        
        impacts: Dict[str, SymbolImpact] = {}
        visited: Set[str] = set()
        ignored_external_calls: List[str] = []
        safety_warnings: List[str] = []
        
        # GUARDRAIL: Hedef sembolün kendi external call'larını topla
        target_sym = self.symbols[target]
        target_calls = target_sym.get("calls", [])
        for call in target_calls:
            call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
            call_symbol = call.get("symbol") if isinstance(call, dict) else call
            
            if call_type == "external" and call_symbol:
                ignored_external_calls.append(call_symbol)
            elif call_type == "unknown" and call_symbol:
                safety_warnings.append(f"Unknown call '{call_symbol}' detected in target")
        
        # DETERMINISM: BFS kuyruğu sorted liste olarak başlat
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
            
            # Sonraki seviyeyi kuyruğa ekle - sadece INTERNAL çağıranlar
            if depth < max_depth:
                current_sym = self.symbols.get(current, {})
                callers_data = current_sym.get("called_by", [])
                
                for call in callers_data:
                    caller = call.get("symbol") if isinstance(call, dict) else call
                    call_type = call.get("type", "internal") if isinstance(call, dict) else "internal"
                    
                    # GUARDRAIL: EXTERNAL çağrılar traversal'a girmez
                    if call_type == "external":
                        if caller and caller not in ignored_external_calls:
                            ignored_external_calls.append(caller)
                        continue
                    
                    # GUARDRAIL: UNKNOWN çağrılar traversal'a girmez, safety'e ekle
                    if call_type == "unknown":
                        if caller and caller not in safety_warnings:
                            safety_warnings.append(f"Unknown call '{caller}' detected in graph traversal")
                        continue
                    
                    # Sadece internal ve çevrimsel olmayan çağrılar
                    if caller and caller not in path:
                        new_path = path + [caller]
                        queue.append((caller, depth + 1, new_path))
                
                # DETERMINISM: Kuyruğu sırala (symbol name ASC)
                queue = sorted(queue, key=lambda x: x[0])
        
        # DETERMINISM: Skora göre sırala (skor DESC, sembol ASC tie-breaker)
        sorted_impacts = sorted(impacts.values(), key=lambda x: (-x.score, x.depth, x.symbol))
        
        return sorted_impacts, sorted(ignored_external_calls), safety_warnings
    
    def _calculate_impact_score(self, depth: int, symbol: str) -> float:
        """
        Derinliğe göre etki skoru hesapla.
        
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
        
        # Sembolün graph'taki önemine göre ayarlama
        # Çok çağrılan semboller daha önemli
        caller_count = len(self.called_by_index.get(symbol, []))
        if caller_count > 5:
            base *= 1.1  # Çok kullanılan sembol - sınırı aşma
        elif caller_count == 0 and depth > 0:
            base *= 0.9  # Leaf node - daha az kritik
        
        return min(base, 1.0)  # Max 1.0
    
    def _depth_to_level(self, depth: int) -> ImpactLevel:
        """Derinliği etki seviyesine dönüştür."""
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
    BBC Context Optimizer - AI için optimize edilmiş context üretir.
    
    Bu sınıf:
    1. Blast radius analizi yapar
    2. Sembolleri önem sırasına göre kategorize eder
    3. "Gürültü" sembolleri filtreler
    4. Güvenlik kuralları üretir
    5. Deterministik BBC kararı oluşturur
    
    GUARDRAILS (Aşama 3.7):
    - External Call Guard: EXTERNAL çağrılar PRIMARY/DIRECT/INDIRECT olamaz
    - Unknown Call Guard: UNKNOWN çağrılar dependency olarak sayılmaz
    - Deterministic SymbolResolver: Sıralı çözümleme, ambiguous durumda None
    - PRIMARY Seçim Kuralı: Sadece Internal + Resolved + Score>0, TEKİL
    - Context Reduction Kilidi: ratio < 0.6 ise exception
    - Determinizm Kilidi: sorted node list, stable edge ordering
    - Çıktı Kontratı: {"primary", "direct", "indirect", "ignored", "safety"}
    """
    
    # Varsayılan parametreler
    DEFAULT_PRIMARY_THRESHOLD = 0.85   # %40
    DEFAULT_DIRECT_THRESHOLD = 0.60    # %30  
    DEFAULT_INDIRECT_THRESHOLD = 0.35  # %20
    DEFAULT_MAX_CONTEXT_SYMBOLS = 50   # Maksimum sembol sayısı
    DEFAULT_MIN_REDUCTION_RATIO = 0.6  # GUARDRAIL: Minimum context reduction ratio
    
    def __init__(self, symbol_graph: Dict[str, Any],
                 primary_threshold: float = DEFAULT_PRIMARY_THRESHOLD,
                 direct_threshold: float = DEFAULT_DIRECT_THRESHOLD,
                 indirect_threshold: float = DEFAULT_INDIRECT_THRESHOLD,
                 max_symbols: int = DEFAULT_MAX_CONTEXT_SYMBOLS,
                 min_reduction_ratio: float = DEFAULT_MIN_REDUCTION_RATIO):
        """
        Args:
            symbol_graph: SymbolGraph çıktısı
            primary_threshold: Primary sınırı (varsayılan: 0.85)
            direct_threshold: Direct sınırı (varsayılan: 0.60)
            indirect_threshold: Indirect sınırı (varsayılan: 0.35)
            max_symbols: Maksimum context sembolü
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
        Bir hedef sembol için optimize edilmiş context üret.
        
        GUARDRAILS:
        - Ambiguous resolution: primary=None
        - External çağrılar: ignored listesine
        - Unknown çağrılar: safety uyarısına
        - Reduction < 0.6: exception
        - PRIMARY tekil olmak zorunda
        
        Args:
            target: Hedef sembol adı (kısa veya tam ad)
            context_file: İsteğe bağlı - hedef sembolün bulunması muhtemel dosya
            
        Returns:
            ContextDecision - BBC kararı
            
        Raises:
            ContextReductionError: Eğer context reduction ratio < min_reduction_ratio
        """
        # 1. Sembol çözümleme (SymbolResolver)
        resolution = self.resolver.resolve(target, context_file)
        
        # Çözümleme başarısızsa veya ambiguous ise
        if resolution.resolution_type == "not_found":
            return self._unresolved_decision(target, resolution)
        
        if resolution.resolution_type == "ambiguous":
            return self._ambiguous_decision(target, resolution)
        
        # Çözümlenen tam sembol adını kullan
        resolved_target = resolution.primary
        
        # GUARDRAIL: PRIMARY seçim kuralı kontrolü
        # Sadece Internal + Resolved + Score>0 olabilir
        if not resolved_target or resolved_target not in self.analyzer.symbols:
            return self._unresolved_decision(target, resolution)
        
        # 2. Blast radius analizi
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
            # En yüksek skorlu olanı primary yap, diğerlerini direct'e taşı
            sorted_primary = sorted(primary, key=lambda x: -impact_scores[x])
            primary = [sorted_primary[0]]
            direct = sorted_primary[1:] + direct
        
        # External çağrıları ignored listesine ekle
        ignored.extend(ignored_external)
        
        # 4. Context limiti kontrolü
        total_selected = len(primary) + len(direct) + len(indirect)
        if total_selected > self.max_symbols:
            # Öncelik sırasına göre kes
            indirect = self._limit_category(indirect, 
                max(0, self.max_symbols - len(primary) - len(direct)))
            if len(primary) + len(direct) > self.max_symbols:
                direct = self._limit_category(direct,
                    max(0, self.max_symbols - len(primary)))
        
        # 5. Güvenlik kuralları üret
        safety_rules = self._generate_safety_rules(resolved_target, impacts)
        
        # Resolution bilgisi için ek uyarılar
        if resolution.resolution_type in ("unique_short", "graph_scored"):
            safety_rules.insert(0, f"'{target}' -> '{resolved_target}' olarak çözümlendi")
        
        # Unknown çağrı uyarılarını ekle
        safety_rules.extend(safety_warnings)
        
        # 6. Context reduction hesapla ve kontrol et (GUARDRAIL)
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
        
        # 7. İstatistikler
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
        """Bir kategorideki sembolleri limite göre sınırla - DETERMINISTIK."""
        if len(symbols) <= limit:
            return sorted(symbols)
        # DETERMINISM: Sıralı kesme
        return sorted(symbols)[:limit]
    
    def _generate_safety_rules(self, target: str, 
                               impacts: List[SymbolImpact]) -> List[str]:
        """
        Güvenlik kuralları üret.
        
        Bu kurallar AI'ın dikkat etmesi gereken şeyleri belirtir.
        """
        rules = []
        
        # Hedef sembol bilgisi
        target_sym = self.analyzer.symbols.get(target, {})
        sym_type = target_sym.get("type", "unknown")
        
        # Temel güvenlik kuralı
        rules.append(f"'{target}' sembolünün imzası korunmalı")
        
        # Tip özel kurallar
        if sym_type == "function":
            rules.append("Fonksiyon dönüş tipi değişirse çağıranlar etkilenir")
        elif sym_type == "method":
            rules.append("self/cls parametre imzası korunmalı")
        elif sym_type == "class":
            rules.append("Sınıf constructor'ı değişirse instantiation noktaları etkilenir")
        
        # Yüksek etkili sembol kontrolü
        high_impact = [i for i in impacts if i.score > 0.5 and i.symbol != target]
        if high_impact:
            rules.append(f"{len(high_impact)} yüksek etkili sembol var - dikkatli refactor")
        
        # Çevrimsel bağımlılık kontrolü
        cycles = self._detect_cycles(target, impacts)
        if cycles:
            rules.append(f"Çevrimsel bağımlılık tespit edildi: kontrollü değişim yap")
        
        return rules
    
    def _detect_cycles(self, target: str, 
                       impacts: List[SymbolImpact]) -> List[List[str]]:
        """Çevrimsel bağımlılıkları tespit et."""
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
        """Hedef bulunamazsa boş karar döndür."""
        return ContextDecision(
            target=target,
            primary=[],
            direct=[],
            indirect=[],
            ignored=[],
            safety=[f"Hedef sembol '{target}' graph'ta bulunamadı"],
            impact_scores={},
            stats={"error": "Target not found"}
        )
    
    def _unresolved_decision(self, target: str, resolution: SymbolResolutionResult) -> ContextDecision:
        """Sembol çözümlenemezse karar döndür."""
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
        """Ambiguous durumda karar döndür - primary boş kalır."""
        # Adayları ignore listesine koy (kullanıcı bilgilensin)
        return ContextDecision(
            target=target,
            primary=[],  # BOŞ - güvenlik için
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
        Birden fazla hedef için kararları karşılaştır.
        
        Bu, çakışan değişikliklerin analizinde kullanılır.
        """
        decisions = {}
        # DETERMINISM: sorted targets
        for target in sorted(targets):
            decisions[target] = self.optimize(target)
        return decisions
    
    def export_decision(self, decision: ContextDecision, 
                        output_path: str, format: str = "json"):
        """
        Kararı dosyaya kaydet.
        
        Args:
            decision: ContextDecision nesnesi
            output_path: Çıktı dosya yolu
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
        """Kararı insan-okunabilir metin formatına dönüştür."""
        lines = [
            "=" * 60,
            "BBC CONTEXT OPTIMIZER - KARAR RAPORU",
            "=" * 60,
            "",
            f"Hedef Sembol: {decision.target}",
            "",
            "[PRIMARY - %40 Önem]",
        ]
        
        for sym in sorted(decision.primary):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[DIRECT - %30 Önem]"])
        for sym in sorted(decision.direct):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[INDIRECT - %20 Önem]"])
        for sym in sorted(decision.indirect):
            score = decision.impact_scores.get(sym, 0)
            lines.append(f"  • {sym} (score: {score:.2f})")
        
        lines.extend(["", "[IGNORED - External/Unknown]"])
        for sym in sorted(decision.ignored):
            lines.append(f"  • {sym}")
        
        lines.extend(["", "[SAFETY - Güvenlik Kuralları]"])
        for rule in decision.safety:
            lines.append(f"  ⚠ {rule}")
        
        lines.extend(["", "[İSTATİSTİKLER]"])
        for key, value in decision.stats.items():
            lines.append(f"  {key}: {value}")
        
        lines.extend(["", "=" * 60])
        
        return "\n".join(lines)


def main():
    """Komut satırı arayüzü."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BBC Context Optimizer - Symbol bazlı context optimizasyonu'
    )
    parser.add_argument('graph_json', help='SymbolGraph JSON çıktısı')
    parser.add_argument('target', help='Hedef sembol adı')
    parser.add_argument('--out', '-o', help='Çıktı dosyası', default=None)
    parser.add_argument('--format', '-f', choices=['json', 'txt'], 
                       default='json', help='Çıktı formatı')
    parser.add_argument('--max-symbols', '-m', type=int, default=50,
                       help='Maksimum context sembolü')
    
    args = parser.parse_args()
    
    # Graph'ı oku
    with open(args.graph_json, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # Optimizer oluştur
    optimizer = ContextOptimizer(
        symbol_graph=graph_data,
        max_symbols=args.max_symbols
    )
    
    # Optimize et
    decision = optimizer.optimize(args.target)
    
    # Çıktı
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
