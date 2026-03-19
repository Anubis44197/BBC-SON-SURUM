from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bbc_cli_help_runs():
    """The primary CLI should render help without crashing."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bbc.py"), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "bbc" in result.stdout.lower()


def test_runtime_requirements_exclude_dev_tools():
    """Runtime requirements should not contain test/lint-only tools."""
    req_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "pytest" not in req_text
    assert "ruff" not in req_text


def test_readme_version_matches_package_major_minor():
    """README headline version should stay aligned with package version series."""
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'version = "8.3.0"' in pyproject_text
    assert "v8.3" in readme_text
