"""
BBC Secret Signal Detector (v1.0)
Detects sensitive-information signals in project files.

BBC Architecture Integration:
    - Pattern-based detection (regex, context filtering)
    - False-positive reduction (hint list, context analysis)
    - Signal feed into BBC math (S/C/P contribution)
    - Incremental cache support (hash-based drift checks)
    - Security: raw secret masking and fingerprint storage

Default: OFF. Enabled only with the --detect-secrets flag or BBC_ENABLE_SECRET_DETECT=1.
"""

import hashlib
import json
import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Pattern Loading ─────────────────────────────────────────────────────
_PATTERNS_FILE = os.path.join(os.path.dirname(__file__), "secret_patterns.json")


def _load_patterns(path: str = _PATTERNS_FILE) -> List[Dict[str, Any]]:
    """Loads pattern JSON and compiles regex rules."""
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
    """Lazy-load and cache pattern definitions."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS is None:
        _COMPILED_PATTERNS = _load_patterns()
    return _COMPILED_PATTERNS


# ── Helper Functions ────────────────────────────────────────────────────

def _mask_value(raw: str, visible_chars: int = 4) -> str:
    """Masks sensitive values; only the first N characters are visible."""
    if len(raw) <= visible_chars:
        return "***"
    return raw[:visible_chars] + "*" * min(8, len(raw) - visible_chars)


def _fingerprint(raw: str) -> str:
    """Short SHA-256 fingerprint for a sensitive value."""
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _is_false_positive(match_text: str, hints: List[str], line: str) -> bool:
    """Hint-list and context-based false-positive filtering."""
    lower_line = line.lower()
    lower_match = match_text.lower()
    for hint in hints:
        h = hint.lower()
        if h in lower_match or h in lower_line:
            return True
    # Comment-line check
    stripped = line.lstrip()
    if stripped.startswith(("#", "//", "/*", "*", "<!--")):
        return True
    # Test/mock/fixture path hints can be appended by the caller.
    return False


def _shannon_entropy(text: str) -> float:
    """Shannon entropy calculation (aligned with BBC chaos-density formula)."""
    if not text:
        return 0.0
    cnt = Counter(text)
    ln = len(text)
    entropy = sum(-(v / ln) * math.log2(v / ln) for v in cnt.values())
    return entropy if not math.isnan(entropy) else 0.0


# ── File-Level Scan ─────────────────────────────────────────────────────

class SecretFinding:
    """Single secret finding."""
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
    Scans one file's content.

    Args:
        content: File content
        file_path: Relative file path (for reporting)
        categories: Filter; only patterns in these categories are used (None = all)
        min_confidence: Minimum confidence threshold (0.0 - 1.0)
        entropy_threshold: Skip matches below threshold (low entropy is likely constants/tests)

    Returns:
        List of SecretFinding
    """
    patterns = _get_patterns()
    findings: List[SecretFinding] = []

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        for pat in patterns:
            # Category filter
            if categories and pat["category"] not in categories:
                continue
            # Confidence threshold
            if pat["confidence"] < min_confidence:
                continue

            compiled: re.Pattern = pat["_compiled"]
            for m in compiled.finditer(line):
                match_text = m.group(0)

                # False-positive check
                if _is_false_positive(match_text, pat.get("false_positive_hints", []), line):
                    continue

                # Entropy check; very low-entropy matches are likely constants.
                ent = _shannon_entropy(match_text)
                if ent < entropy_threshold and pat["severity"] not in ("critical",):
                    continue

                # Store masked value and fingerprint of matched content.
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


# ── Project-Level Scan ──────────────────────────────────────────────────

class SecretScanResult:
    """Project-wide secret-scan summary."""

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
        """Files containing findings at or above the specified severity."""
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
        """Lightweight summary without full findings list."""
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
    Runs a project-wide secret scan.

    Args:
        project_root: Project root directory
        categories: Scan only these categories (None = all)
        min_confidence: Minimum confidence threshold
        file_list: Files to scan (None = auto-scan all source files)
        silent: Suppress output

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


# ── BBC Math Integration Helpers ────────────────────────────────────────

def compute_secret_risk_score(scan_result: SecretScanResult) -> float:
    """
    Produces a normalized risk score in the 0.0-1.0 range from scan results.
    This score can be fed into HMPU as an S/C/P contribution.

    Formula:
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

    # Normalize: treat up to 20 critical findings as full risk.
    max_possible = 20.0 * 1.0 * 1.0
    score = min(1.0, total_weight / max_possible)
    return round(score, 4)


def compute_aura_secret_adjustment(risk_score: float,
                                   max_influence: float = 0.10) -> float:
    """
    Bounds the maximum effect of secret risk on Aura Field Score.
    Regression guard: no matter the risk score, aura is not changed beyond
    +/-max_influence.

    Returns:
        Negative contribution (reduces aura): [-max_influence, 0.0]
    """
    if risk_score <= 0.0:
        return 0.0
    adjustment = -(risk_score * max_influence)
    return max(-max_influence, adjustment)
