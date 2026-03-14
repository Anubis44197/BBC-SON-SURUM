"""
BBC Token Optimizer (v1.0)
Genel amaçlı token sıkıştırma aracı — Shannon entropy tabanlı
adaptif örnekleme ve compact JSON optimizasyonu.

BBC Matematiği:
  - Shannon Chaos Density (dC/dt) ile veri karmaşıklığını ölçer
  - Yüksek entropy → detaylı tut (önemli veri noktaları)
  - Düşük entropy → agresif sıkıştır (tekrarlayan veriler)
  - HMPU chaos_derivative_filter ile gürültü eliminasyonu
"""

import json
import math
import re
from collections import Counter
from typing import List, Dict, Any, Optional, Union
from .bbc_scalar import BBCScalar, STABLE, WEAK, UNSTABLE, DEGENERATE


class TokenOptimizer:
    """
    BBC Token Optimizer — Shannon entropy tabanlı adaptif sıkıştırma.
    
    Kullanım:
        optimizer = TokenOptimizer()
        result = optimizer.optimize(data, target_ratio=0.1)
    """

    def __init__(self, max_field_length: int = 3, decimal_places: int = 2):
        """
        Args:
            max_field_length: Compact JSON'da alan adı kısaltma uzunluğu
            decimal_places: Sayılar için yuvarlama hassasiyeti
        """
        self.max_field_length = max_field_length
        self.decimal_places = decimal_places

    # ─── Shannon Entropy (BBC HMPU formülü — BBCScalar native) ─────

    def _shannon_entropy(self, text: str) -> BBCScalar:
        """
        Shannon Chaos Density — HMPU Governor ile aynı formül.
        Sonuç BBCScalar olarak döner: değer + state + origin.
        """
        if not text:
            return BBCScalar(0.0, state=STABLE, metadata={"origin": "math"})
        cnt = Counter(text)
        ln = len(text)
        entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
        if math.isnan(entropy):
            entropy = 0.0
        # State: entropy seviyesine göre
        state = STABLE if entropy <= 3.0 else WEAK if entropy <= 5.0 else UNSTABLE if entropy <= 7.0 else DEGENERATE
        return BBCScalar(entropy, state=state, metadata={"origin": "math"})

    def _chunk_entropy(self, data: List[Any], chunk_size: int = 10) -> List[BBCScalar]:
        """Veri listesini parçalara ayırıp her parçanın entropy'sini BBCScalar olarak hesaplar."""
        entropies = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_str = json.dumps(chunk, ensure_ascii=False)
            entropies.append(self._shannon_entropy(chunk_str))
        return entropies

    def _chaos_derivative_filter(self, entropies: List[BBCScalar], threshold: float = 0.4) -> List[int]:
        """
        Chaos Derivative Filter (dC/dt) — HMPU Governor Operator 1.
        Ardışık chunk'lar arasındaki entropy farkı eşiği geçerse
        o chunk'u 'sinyal' (faz değişimi) olarak işaretler.
        Returns: sinyal içeren chunk indeksleri
        """
        signal_indices = []
        prev_entropy = 0.0
        for i, e_scalar in enumerate(entropies):
            curr = float(e_scalar)
            dc_dt = abs(curr - prev_entropy)
            if dc_dt > threshold:
                signal_indices.append(i)
            prev_entropy = curr
        return signal_indices

    # ─── Adaptif Örnekleme ────────────────────────────────────────

    def adaptive_sample(self, data: List[Any], target_ratio: float = 0.1,
                        key_field: Optional[str] = None) -> List[Any]:
        """
        Shannon entropy tabanlı adaptif örnekleme.
        
        Yüksek entropy bölgelerden daha fazla, düşük entropy bölgelerden
        daha az örnek alır. Bu sayede önemli veri noktaları korunurken
        tekrarlayan veriler atılır.
        
        BBC Matematiği:
          chunk_entropy = H(chunk)
          sample_weight = H(chunk) / max(H(all_chunks))
          sample_count = max(1, round(chunk_size * sample_weight * target_ratio))
        
        Args:
            data: Örneklenecek veri listesi
            target_ratio: Hedef sıkıştırma oranı (0.0-1.0, düşük = daha agresif)
            key_field: Sıralama anahtarı (dict listesi için)
            
        Returns:
            Adaptif olarak örneklenmiş veri listesi
        """
        if not data:
            return []
        
        n = len(data)
        target_count = max(1, int(n * target_ratio))
        
        if n <= target_count:
            return data
        
        # Chunk boyutunu hesapla
        chunk_size = max(1, n // 10)
        
        # Her chunk'ın entropy'sini hesapla (BBCScalar olarak döner)
        entropies = self._chunk_entropy(data, chunk_size)
        max_entropy = max(float(e) for e in entropies) if entropies else 1.0
        if max_entropy == 0:
            max_entropy = 1.0
        
        # Chaos derivative filter: sinyal içeren chunk'ları işaretle
        signal_indices = set(self._chaos_derivative_filter(entropies, threshold=0.4))

        # Her chunk'tan BBCScalar entropy ağırlıklı örnekleme
        sampled = []
        remaining_budget = target_count
        
        for i, e_scalar in enumerate(entropies):
            start = i * chunk_size
            end = min(start + chunk_size, n)
            chunk = data[start:end]
            
            if not chunk:
                continue
            
            # BBCScalar entropy ağırlığı
            entropy_val = float(e_scalar)
            weight = entropy_val / max_entropy

            # Sinyal chunk'larına bonus (dC/dt > 0.4 olan faz değişimleri)
            if i in signal_indices:
                weight = min(weight * 1.5, 1.0)

            # State-aware: UNSTABLE/DEGENERATE chunk'lardan daha az örnek
            if e_scalar.state == DEGENERATE:
                weight *= 0.3
            elif e_scalar.state == UNSTABLE:
                weight *= 0.6

            sample_count = max(1, round(len(chunk) * weight * target_ratio * 2))
            sample_count = min(sample_count, remaining_budget, len(chunk))
            
            if sample_count <= 0:
                continue
            
            # Eşit aralıklı örnekleme
            step = max(1, len(chunk) // sample_count)
            for j in range(0, len(chunk), step):
                if remaining_budget <= 0:
                    break
                sampled.append(chunk[j])
                remaining_budget -= 1
        
        # İlk ve son elemanı garanti et (sınır noktaları)
        if data[0] not in sampled:
            sampled.insert(0, data[0])
        if data[-1] not in sampled:
            sampled.append(data[-1])
        
        return sampled

    # ─── Compact JSON ─────────────────────────────────────────────

    def compact_json(self, data: Any, field_map: Optional[Dict[str, str]] = None) -> Any:
        """
        JSON verisini sıkıştırır:
          1. Alan adlarını kısaltır (field_map veya otomatik)
          2. Null/None değerleri temizler
          3. Sayıları yuvarlar
          4. Boş string/list/dict temizler
        
        Args:
            data: Sıkıştırılacak JSON verisi
            field_map: Özel alan adı kısaltma haritası (örn: {"timestamp": "ts"})
            
        Returns:
            Sıkıştırılmış veri
        """
        if field_map is None:
            field_map = {}
        
        return self._compact_recursive(data, field_map)

    def _compact_recursive(self, obj: Any, field_map: Dict[str, str]) -> Any:
        """Recursive compact JSON işlemi."""
        if obj is None:
            return None  # Üst seviyede temizlenecek
        
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Null/None temizle
                if value is None:
                    continue
                # Boş string/list/dict temizle
                if value == "" or value == [] or value == {}:
                    continue
                
                # Alan adı kısalt
                short_key = field_map.get(key, self._shorten_field(key))
                
                # Recursive
                compact_val = self._compact_recursive(value, field_map)
                if compact_val is not None:
                    result[short_key] = compact_val
            return result if result else None
        
        elif isinstance(obj, list):
            result = []
            for item in obj:
                compact_item = self._compact_recursive(item, field_map)
                if compact_item is not None:
                    result.append(compact_item)
            return result if result else None
        
        elif isinstance(obj, float):
            return round(obj, self.decimal_places)
        
        elif isinstance(obj, str):
            return obj.strip() if obj.strip() else None
        
        return obj

    def _shorten_field(self, field_name: str) -> str:
        """Alan adını kısaltır — snake_case ve camelCase desteği."""
        if len(field_name) <= self.max_field_length:
            return field_name
        
        # snake_case: her kelimenin ilk harfi
        if '_' in field_name:
            parts = field_name.split('_')
            short = ''.join(p[0] for p in parts if p)
            if len(short) >= 2:
                return short
        
        # camelCase: büyük harfler
        uppers = [c for c in field_name if c.isupper()]
        if len(uppers) >= 2:
            return ''.join(uppers).lower()
        
        # Fallback: ilk N karakter
        return field_name[:self.max_field_length]

    # ─── Tam Optimizasyon Pipeline ────────────────────────────────

    def optimize(self, data: Any, target_ratio: float = 0.1,
                 field_map: Optional[Dict[str, str]] = None,
                 key_field: Optional[str] = None) -> Dict[str, Any]:
        """
        Tam token optimizasyon pipeline'ı:
          1. Veri listesi ise → adaptif örnekleme
          2. JSON sıkıştırma (alan kısaltma + null temizleme + yuvarlama)
          3. Token tasarruf raporu
        
        Args:
            data: Optimize edilecek veri
            target_ratio: Hedef sıkıştırma oranı
            field_map: Özel alan adı kısaltma haritası
            key_field: Sıralama anahtarı (list of dict için)
            
        Returns:
            {
                "data": optimized_data,
                "metrics": {
                    "original_chars": int,
                    "optimized_chars": int,
                    "savings_ratio": float,
                    "entropy_original": float,
                    "entropy_optimized": float
                }
            }
        """
        original_str = json.dumps(data, ensure_ascii=False)
        original_chars = len(original_str)
        entropy_original = self._shannon_entropy(original_str)
        
        # 1. Adaptif örnekleme (sadece list ise)
        if isinstance(data, list) and len(data) > 10:
            data = self.adaptive_sample(data, target_ratio=target_ratio, key_field=key_field)
        
        # 2. Compact JSON
        optimized = self.compact_json(data, field_map=field_map)
        if optimized is None:
            optimized = {}
        
        optimized_str = json.dumps(optimized, ensure_ascii=False)
        optimized_chars = len(optimized_str)
        entropy_optimized = self._shannon_entropy(optimized_str)
        
        savings_ratio = 1.0 - (optimized_chars / original_chars) if original_chars > 0 else 0.0

        # Savings → BBCScalar (yüksek tasarruf = STABLE, düşük = WEAK)
        sr_state = STABLE if savings_ratio >= 0.5 else WEAK if savings_ratio >= 0.2 else UNSTABLE
        savings_scalar = BBCScalar(savings_ratio, state=sr_state, metadata={"origin": "math"})
        
        return {
            "data": optimized,
            "metrics": {
                "original_chars": original_chars,
                "optimized_chars": optimized_chars,
                "savings_ratio": {"value": round(float(savings_scalar), 4), "state": savings_scalar.state},
                "savings_percent": f"{savings_ratio * 100:.1f}%",
                "entropy_original": {"value": round(float(entropy_original), 3), "state": entropy_original.state},
                "entropy_optimized": {"value": round(float(entropy_optimized), 3), "state": entropy_optimized.state},
                "compression_factor": f"{original_chars / optimized_chars:.1f}x" if optimized_chars > 0 else "inf"
            }
        }
