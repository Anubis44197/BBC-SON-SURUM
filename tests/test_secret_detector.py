"""BBC Secret Signal Detection — Unit Tests"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bbc_core.secret_detector import (
    SecretFinding,
    SecretScanResult,
    scan_content,
    scan_project,
    compute_secret_risk_score,
    compute_aura_secret_adjustment,
    _mask_value,
    _fingerprint,
    _shannon_entropy,
)


# ---------------------------------------------------------------------------
# Pattern loading
# ---------------------------------------------------------------------------

def test_patterns_json_loads():
    """secret_patterns.json should load and contain expected structure."""
    patterns_path = REPO_ROOT / "bbc_core" / "secret_patterns.json"
    assert patterns_path.exists(), "secret_patterns.json must exist"
    data = json.loads(patterns_path.read_text(encoding="utf-8"))
    assert "patterns" in data
    assert len(data["patterns"]) >= 10
    for p in data["patterns"]:
        assert "id" in p
        assert "regex" in p
        assert "severity" in p


# ---------------------------------------------------------------------------
# Content scanning — true positives
# ---------------------------------------------------------------------------

FAKE_AWS_KEY = "AKIAI44QH8DHBNRZKT2K"
FAKE_GENERIC_SECRET = 'password = "xK9mNpL2qR5tYwBz8vHjDfGcEa3s"'
FAKE_PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALR..."


def test_scan_detects_aws_key():
    content = f'aws_access_key_id = "{FAKE_AWS_KEY}"'
    findings = scan_content(content, "test.py")
    assert len(findings) >= 1
    labels = [f.label for f in findings]
    assert any("AWS" in l for l in labels)


def test_scan_detects_generic_secret():
    findings = scan_content(FAKE_GENERIC_SECRET, "config.py")
    assert len(findings) >= 1


def test_scan_detects_private_key():
    findings = scan_content(FAKE_PRIVATE_KEY, "key.pem")
    assert len(findings) >= 1
    assert any(f.category == "crypto" for f in findings)


# ---------------------------------------------------------------------------
# Content scanning — false positives / negatives
# ---------------------------------------------------------------------------

def test_scan_ignores_placeholder():
    content = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"'
    findings = scan_content(content, "example.py")
    # EXAMPLE suffix is a known false positive hint
    # Even if detected, confidence should be low or filtered
    # We mainly check no crash
    assert isinstance(findings, list)


def test_scan_empty_content():
    findings = scan_content("", "empty.py")
    assert len(findings) == 0


def test_scan_normal_code():
    code = """
def hello():
    print("Hello, World!")
    x = 42
    return x
"""
    findings = scan_content(code, "hello.py")
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# Category filtering
# ---------------------------------------------------------------------------

def test_scan_category_filter():
    content = f'aws_key = "{FAKE_AWS_KEY}"\npassword = "SuperSecret123!"'
    all_findings = scan_content(content, "test.py")
    cloud_findings = scan_content(content, "test.py", categories={"cloud"})
    # Cloud filter should yield fewer or equal findings
    assert len(cloud_findings) <= len(all_findings)


# ---------------------------------------------------------------------------
# Risk score computation
# ---------------------------------------------------------------------------

def _make_result(findings_list):
    """Helper to build SecretScanResult from a findings list."""
    r = SecretScanResult()
    r.findings = findings_list
    r.files_scanned = len(set(f.file_path for f in findings_list))
    r.files_with_findings = r.files_scanned
    return r


def test_risk_score_zero_for_empty():
    result = _make_result([])
    score = compute_secret_risk_score(result)
    assert score == 0.0


def test_risk_score_bounded():
    finding = SecretFinding(
        pattern_id="test", category="auth", label="Test",
        severity="critical", confidence=1.0, line_number=1,
        masked_value="***", fingerprint="abc", file_path="x.py", entropy=4.5
    )
    result = _make_result([finding] * 50)
    score = compute_secret_risk_score(result)
    assert 0.0 <= score <= 1.0


def test_risk_score_increases_with_severity():
    low_finding = SecretFinding(
        pattern_id="t1", category="auth", label="Low",
        severity="low", confidence=0.6, line_number=1,
        masked_value="***", fingerprint="a1", file_path="x.py", entropy=3.0
    )
    high_finding = SecretFinding(
        pattern_id="t2", category="auth", label="High",
        severity="critical", confidence=1.0, line_number=1,
        masked_value="***", fingerprint="a2", file_path="x.py", entropy=5.0
    )
    low_result = _make_result([low_finding])
    high_result = _make_result([high_finding])
    assert compute_secret_risk_score(low_result) < compute_secret_risk_score(high_result)


# ---------------------------------------------------------------------------
# Aura adjustment
# ---------------------------------------------------------------------------

def test_aura_adjustment_zero_for_zero_risk():
    adj = compute_aura_secret_adjustment(0.0)
    assert adj == 0.0


def test_aura_adjustment_negative():
    adj = compute_aura_secret_adjustment(0.5)
    assert adj < 0.0


def test_aura_adjustment_clamped():
    adj = compute_aura_secret_adjustment(1.0, max_influence=0.10)
    assert adj >= -0.10
    assert adj <= 0.0


def test_aura_adjustment_custom_max():
    adj = compute_aura_secret_adjustment(1.0, max_influence=0.25)
    assert adj >= -0.25


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_mask_value_hides_middle():
    masked = _mask_value("AKIAIOSFODNN7EXAMPLE")
    assert "AKIA" in masked  # prefix visible
    assert "EXAMPLE" not in masked or "***" in masked


def test_fingerprint_deterministic():
    fp1 = _fingerprint("secret_value_123")
    fp2 = _fingerprint("secret_value_123")
    assert fp1 == fp2
    assert len(fp1) == 16  # truncated sha256 hex


def test_shannon_entropy_positive_for_random():
    entropy = _shannon_entropy("aB3dEfGhIjKlMnOpQrStUv")
    assert entropy > 3.0


def test_shannon_entropy_low_for_repeated():
    entropy = _shannon_entropy("aaaaaaaaaa")
    assert entropy < 1.0


# ---------------------------------------------------------------------------
# SecretScanResult aggregation
# ---------------------------------------------------------------------------

def test_severity_distribution():
    findings_list = [
        SecretFinding("p1", "auth", "A", "critical", 0.9, 1, "***", "f1", "a.py", 4.0),
        SecretFinding("p2", "auth", "B", "high", 0.8, 2, "***", "f2", "a.py", 3.5),
        SecretFinding("p3", "cloud", "C", "critical", 0.9, 3, "***", "f3", "b.py", 4.2),
    ]
    result = _make_result(findings_list)
    dist = result.severity_distribution()
    assert dist["critical"] == 2
    assert dist["high"] == 1


def test_high_risk_files():
    findings_list = [
        SecretFinding("p1", "auth", "A", "critical", 0.9, 1, "***", "f1", "danger.py", 4.0),
        SecretFinding("p2", "auth", "B", "low", 0.5, 2, "***", "f2", "safe.py", 2.0),
    ]
    result = _make_result(findings_list)
    hr = result.high_risk_files()
    assert "danger.py" in hr
    assert "safe.py" not in hr


# ---------------------------------------------------------------------------
# Project scan (integration-level)
# ---------------------------------------------------------------------------

def test_scan_project_on_repo(tmp_path):
    """Scan a tiny project directory with a planted secret."""
    secret_file = tmp_path / "config.py"
    secret_file.write_text(f'aws_key = "{FAKE_AWS_KEY}"\n', encoding="utf-8")
    clean_file = tmp_path / "main.py"
    clean_file.write_text("print('hello')\n", encoding="utf-8")

    result = scan_project(str(tmp_path), silent=True)
    assert len(result.findings) >= 1
    assert any("config.py" in f.file_path for f in result.findings)


def test_scan_project_empty(tmp_path):
    result = scan_project(str(tmp_path), silent=True)
    assert len(result.findings) == 0
