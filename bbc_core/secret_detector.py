"""
BBC Secret Signal Detector (v1.0)
Proje dosyalarındaki hassas bilgi sinyallerini tespit eder.

BBC Mimarisi ile Entegrasyon:
  - Pattern tabanlı algılama (regex, context filtering)
  - False-positive azaltma (hint listesi, bağlam analizi)
  - BBC matematiğine sinyal besleme (S/C/P katkısı)
  - Incremental cache desteği (hash tabanlı drift kontrolü)
  - Güvenlik: Raw secret maskeleme, fingerprint saklama

Varsayılan: KAPALI. Sadece --detect-secrets flag veya BBC_ENABLE_SECRET_DETECT=1 ile aktif.
"""

import hashlib
import json
import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Pattern Yükleme ─────────────────────────────────────────────────────
_PATTERNS_FILE = os.path.join(os.path.dirname(__file__), "secret_patterns.json")


def _load_patterns(path: str = _PATTERNS_FILE) -> List[Dict[str, Any]]:
    """Pattern JSON dosyasını yükler ve regex'leri derler."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("patterns", [])
    compiled: List[Dict[str, Any]] = []
    for p in raw:
        try:
            p["_compiled"] = re.compile(p["regex"])
            compiled.append(p)
        except re.error:
            continue
    return compiled


_COMPILED_PATTERNS: Optional[List[Dict[str, Any]]] = None


def _get_patterns() -> List[Dict[str, Any]]:
    """Lazy-load ve cache."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS is None:
        _COMPILED_PATTERNS = _load_patterns()
    return _COMPILED_PATTERNS


# ── Yardımcı Fonksiyonlar ───────────────────────────────────────────────

def _mask_value(raw: str, visible_chars: int = 4) -> str:
    """Hassas değerleri maskeler — sadece ilk N karakter görünür."""
    if len(raw) <= visible_chars:
        return "***"
    return raw[:visible_chars] + "*" * min(8, len(raw) - visible_chars)


def _fingerprint(raw: str) -> str:
    """Hassas değerin kısa SHA-256 parmak izi."""
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _is_false_positive(match_text: str, hints: List[str], line: str) -> bool:
    """Hint listesi ve bağlam bazlı false-positive kontrolü."""
    lower_line = line.lower()
    lower_match = match_text.lower()
    for hint in hints:
        h = hint.lower()
        if h in lower_match or h in lower_line:
            return True
    # Yorum satırı kontrolü
    stripped = line.lstrip()
    if stripped.startswith(("#", "//", "/*", "*", "<!--")):
        return True
    # Test / mock / fixture dosya yolu ipuçları (caller tarafından line'a eklenir)
    return False


def _shannon_entropy(text: str) -> float:
    """Shannon entropi hesabı (BBC chaos density formülüyle uyumlu)."""
    if not text:
        return 0.0
    cnt = Counter(text)
    ln = len(text)
    entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
    return entropy if not math.isnan(entropy) else 0.0


# ── Dosya Seviyesi Tarama ────────────────────────────────────────────────

class SecretFinding:
    """Tek bir secret bulgusu."""
    __slots__ = ("pattern_id", "category", "label", "severity",
                 "confidence", "line_number", "masked_value",
                 "fingerprint", "file_path", "entropy")

    def __init__(self, pattern_id: str, category: str, label: str,
                 severity: str, confidence: float, line_number: int,
                 masked_value: str, fingerprint: str, file_path: str,
                 entropy: float = 0.0):
        self.pattern_id = pattern_id
        self.category = category
        self.label = label
        self.severity = severity
        self.confidence = confidence
        self.line_number = line_number
        self.masked_value = masked_value
        self.fingerprint = fingerprint
        self.file_path = file_path
        self.entropy = entropy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "category": self.category,
            "label": self.label,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "line": self.line_number,
            "masked_value": self.masked_value,
            "fingerprint": self.fingerprint,
            "file": self.file_path,
            "entropy": round(self.entropy, 4),
        }


def scan_content(content: str, file_path: str = "<unknown>",
                 categories: Optional[Set[str]] = None,
                 min_confidence: float = 0.0,
                 entropy_threshold: float = 3.0) -> List[SecretFinding]:
    """
    Tek bir dosyanın içeriğini tarar.

    Args:
        content: Dosya metni
        file_path: Göreceli dosya yolu (raporlama için)
        categories: Filtre — sadece bu kategorilerdeki patternler çalışır (None = hepsi)
        min_confidence: Alt güven eşiği (0.0 – 1.0)
        entropy_threshold: Eşik altı entropili eşleşmeleri atla (düşük entropi = muhtemelen sabit/test)

    Returns:
        SecretFinding listesi
    """
    patterns = _get_patterns()
    findings: List[SecretFinding] = []

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        for pat in patterns:
            # Kategori filtresi
            if categories and pat["category"] not in categories:
                continue
            # Güven eşiği
            if pat["confidence"] < min_confidence:
                continue

            compiled: re.Pattern = pat["_compiled"]
            for m in compiled.finditer(line):
                match_text = m.group(0)

                # False positive kontrolü
                if _is_false_positive(match_text, pat.get("false_positive_hints", []), line):
                    continue

                # Entropi kontrolü — çok düşük entropili eşleşmeler muhtemelen sabit
                ent = _shannon_entropy(match_text)
                if ent < entropy_threshold and pat["severity"] not in ("critical",):
                    continue

                # Eşleşen değerin maskeli + fingerprint hali
                val = m.group(1) if m.lastindex and m.lastindex >= 1 else match_text
                findings.append(SecretFinding(
                    pattern_id=pat["id"],
                    category=pat["category"],
                    label=pat["label"],
                    severity=pat["severity"],
                    confidence=pat["confidence"],
                    line_number=line_idx,
                    masked_value=_mask_value(val),
                    fingerprint=_fingerprint(val),
                    file_path=file_path,
                    entropy=ent,
                ))

    return findings


# ── Proje Seviyesi Tarama ────────────────────────────────────────────────

class SecretScanResult:
    """Proje genelinde secret tarama özeti."""

    def __init__(self):
        self.findings: List[SecretFinding] = []
        self.files_scanned: int = 0
        self.files_with_findings: int = 0

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def severity_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for f in self.findings:
            dist[f.severity] = dist.get(f.severity, 0) + 1
        return dist

    def category_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for f in self.findings:
            dist[f.category] = dist.get(f.category, 0) + 1
        return dist

    def high_risk_files(self, min_severity: str = "high") -> List[str]:
        """En az belirtilen severity'de bulgu içeren dosyalar."""
        sev_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold = sev_order.get(min_severity, 2)
        files: Set[str] = set()
        for f in self.findings:
            if sev_order.get(f.severity, 0) >= threshold:
                files.add(f.file_path)
        return sorted(files)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "files_scanned": self.files_scanned,
            "files_with_findings": self.files_with_findings,
            "severity_distribution": self.severity_distribution(),
            "category_distribution": self.category_distribution(),
            "high_risk_files": self.high_risk_files(),
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Hafif özet — findings listesi olmadan."""
        return {
            "total_findings": self.total_findings,
            "files_scanned": self.files_scanned,
            "files_with_findings": self.files_with_findings,
            "severity_distribution": self.severity_distribution(),
            "category_distribution": self.category_distribution(),
            "high_risk_files": self.high_risk_files(),
        }


def scan_project(project_root: str,
                 categories: Optional[Set[str]] = None,
                 min_confidence: float = 0.0,
                 entropy_threshold: float = 3.0,
                 file_list: Optional[List[str]] = None,
                 silent: bool = False) -> SecretScanResult:
    """
    Proje genelinde secret taraması yapar.

    Args:
        project_root: Proje kök dizini
        categories: Sadece bu kategorileri tara (None = hepsi)
        min_confidence: Alt güven eşiği
        file_list: Taranacak dosya listesi (None ise tüm kaynak dosyalar otomatik taranır)
        silent: Çıktı bastırmak için

    Returns:
        SecretScanResult
    """
    from .config import BBCConfig

    result = SecretScanResult()
    root = os.path.abspath(project_root)
    exts = BBCConfig.get_scan_extensions()
    forbidden = BBCConfig.get_forbidden_scan_dirs()

    files_to_scan: List[Tuple[str, str]] = []

    if file_list is not None:
        for rel in file_list:
            abs_path = os.path.join(root, rel) if not os.path.isabs(rel) else rel
            if os.path.isfile(abs_path):
                files_to_scan.append((rel, abs_path))
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in forbidden]
            for fname in filenames:
                if fname.lower().endswith(exts):
                    abs_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(abs_path, root)
                    files_to_scan.append((rel_path, abs_path))

    for rel_path, abs_path in files_to_scan:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        file_findings = scan_content(
            content, file_path=rel_path,
            categories=categories, min_confidence=min_confidence,
            entropy_threshold=entropy_threshold,
        )
        result.files_scanned += 1
        if file_findings:
            result.files_with_findings += 1
            result.findings.extend(file_findings)

    if not silent and result.total_findings > 0:
        print(f"[SECRET] {result.total_findings} signal(s) in {result.files_with_findings} file(s)")

    return result


# ── BBC Matematik Entegrasyon Yardımcıları ───────────────────────────────

def compute_secret_risk_score(scan_result: SecretScanResult) -> float:
    """
    Tarama sonuçlarından 0.0–1.0 aralığında normalize risk skoru üretir.
    Bu skor S/C/P katkısı olarak HMPU'ya beslenebilir.

    Formül:
      base = sum(severity_weight * confidence) / max_possible
      clamped ∈ [0.0, 1.0]
    """
    if not scan_result.findings:
        return 0.0

    severity_weights = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 1.0}
    total_weight = 0.0
    for f in scan_result.findings:
        w = severity_weights.get(f.severity, 0.3)
        total_weight += w * f.confidence

    # Normalize: en fazla 20 critical bulgu full risk sayılsın
    max_possible = 20.0 * 1.0 * 1.0
    score = min(1.0, total_weight / max_possible)
    return round(score, 4)


def compute_aura_secret_adjustment(risk_score: float,
                                   max_influence: float = 0.10) -> float:
    """
    Secret risk skorunun Aura Field Score'a maksimum etkisini sınırlar.
    Regresyon koruması: risk skoru ne olursa olsun aura'yı ±max_influence'den
    fazla değiştirmez.

    Returns:
        Negatif bir katkı (aura'yı düşürür): [-max_influence, 0.0]
    """
    if risk_score <= 0.0:
        return 0.0
    adjustment = -(risk_score * max_influence)
    return max(-max_influence, adjustment)
