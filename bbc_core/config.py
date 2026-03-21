HEAL_BUDGET_DEFAULT = 5
SESSION_HEAL_BUDGET_DEFAULT = 5
import os
import json
import tempfile
import hashlib
from typing import Any, Dict, Iterable, Optional

class BBCConfig:
    LOG_LEVEL = os.getenv("BBC_LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # State Drift Gate
    STATE_DRIFT_TOLERANCE = 0.05 # 5% drift allowed before warning
    STATE_DRIFT_FAIL_THRESHOLD = 0.20 # 20% drift -> Release Gate Fail
    
    # Healing Limits
    HEAL_HARD_LIMIT = 3 # Maximum times a scalar can be healed before DEGENERATE
    
    # Analysis Limits
    MAX_FILES = 2000 # Maximum files to scan in a project
    
    # Incremental Analysis
    CHANGE_INDEX_FILE = "change_index.json"
    CONTEXT_SEGMENTS_FILE = "context_segments.json"
    INCREMENTAL_HASH_ALGO = "sha256"
    
    # BBC isolation directory - all output goes here
    BBC_DIR = ".bbc"
    
    # BBC Policy Defaults
    BBC_INSTRUCTIONS_VERSION = "1.0"
    CONTEXT_SCHEMA_VERSION = "8.5"
    DEFAULT_FAIL_POLICY = "fail_closed"       # fail_closed | fail_open
    DEFAULT_ENFORCEMENT = "strict"            # strict | balanced | relaxed

    # Secret Signal Detection (varsayılan KAPALI)
    BBC_ENABLE_SECRET_DETECT = os.getenv("BBC_ENABLE_SECRET_DETECT", "0").strip().lower() in ("1", "true", "yes", "on")
    SECRET_MIN_CONFIDENCE = float(os.getenv("BBC_SECRET_MIN_CONFIDENCE", "0.5"))
    SECRET_ENTROPY_THRESHOLD = float(os.getenv("BBC_SECRET_ENTROPY_THRESHOLD", "3.0"))
    SECRET_AURA_MAX_INFLUENCE = float(os.getenv("BBC_SECRET_AURA_MAX_INFLUENCE", "0.10"))  # ±10% üst sınır

    # Shared scan defaults
    SOURCE_EXTENSIONS = (
        '.py', '.md', '.json', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
        '.sql', '.rs', '.go', '.c', '.cpp', '.h', '.hpp', '.java', '.cs',
        '.php', '.rb', '.swift', '.kt'
    )
    FORBIDDEN_SCAN_DIRS = {
        "node_modules", ".venv", "venv", "dist", "build", ".git",
        "__pycache__", "target", ".bbc", "coverage", ".gradle",
        ".idea", ".vscode", ".cursor", ".gemini", ".claude", ".next",
        ".turbo", ".cache", "tmp", "logs", "BBC", "BBC-SON-SURUM",
    }
    
    # Enforcement Profile Definitions
    ENFORCEMENT_PROFILES = {
        "strict": {
            "allow_unknown_symbols": False,
            "require_context_first": True,
            "require_impact_before_change": True,
            "require_verify_after_change": True,
            "auto_patch_check": True,
            "stale_context_action": "block",
        },
        "balanced": {
            "allow_unknown_symbols": False,
            "require_context_first": True,
            "require_impact_before_change": False,
            "require_verify_after_change": True,
            "auto_patch_check": False,
            "stale_context_action": "warn",
        },
        "relaxed": {
            "allow_unknown_symbols": True,
            "require_context_first": True,
            "require_impact_before_change": False,
            "require_verify_after_change": False,
            "auto_patch_check": False,
            "stale_context_action": "warn",
        },
    }
    
    @staticmethod
    def get_bbc_dir(project_root: str = ".") -> str:
        """Get or create the .bbc isolation directory."""
        bbc_dir = os.path.join(project_root, BBCConfig.BBC_DIR)
        os.makedirs(bbc_dir, exist_ok=True)
        return bbc_dir

    @staticmethod
    def get_context_path(project_root: str = ".") -> str:
        """Get the path to bbc_context.json inside .bbc/ isolation directory."""
        bbc_dir = BBCConfig.get_bbc_dir(project_root)
        return os.path.join(bbc_dir, "bbc_context.json")

    @staticmethod
    def get_install_root() -> str:
        """Return BBC installation root directory."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def get_install_bbc_dir() -> str:
        """Return central .bbc directory under BBC installation root."""
        bbc_dir = os.path.join(BBCConfig.get_install_root(), BBCConfig.BBC_DIR)
        os.makedirs(bbc_dir, exist_ok=True)
        return bbc_dir

    @staticmethod
    def get_project_storage_key(project_root: str) -> str:
        """Build a stable project key for centralized artifact storage."""
        project_abs = os.path.abspath(project_root)
        project_name = os.path.basename(project_abs) or "project"
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in project_name)
        digest = hashlib.sha1(project_abs.encode("utf-8", errors="ignore")).hexdigest()[:12]
        return f"{safe_name}_{digest}"

    @staticmethod
    def get_central_project_dir(project_root: str) -> str:
        """Return per-project central storage directory under BBC installation .bbc."""
        root_dir = os.path.join(BBCConfig.get_install_bbc_dir(), "projects")
        project_dir = os.path.join(root_dir, BBCConfig.get_project_storage_key(project_root))
        os.makedirs(project_dir, exist_ok=True)
        return project_dir

    @staticmethod
    def get_central_project_snapshot_path(project_root: str) -> str:
        """Return centralized path for project_snapshot.json."""
        project_dir = BBCConfig.get_central_project_dir(project_root)
        cache_dir = os.path.join(project_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "project_snapshot.json")

    @staticmethod
    def get_central_agent_context_path(project_root: str, task: str) -> str:
        """Return centralized path for agent_context_<task>.json."""
        project_dir = BBCConfig.get_central_project_dir(project_root)
        agent_dir = os.path.join(project_dir, "agent_context")
        os.makedirs(agent_dir, exist_ok=True)
        return os.path.join(agent_dir, f"agent_context_{task}.json")

    @staticmethod
    def get_scan_extensions() -> tuple:
        """Return source extensions used by project scans."""
        raw = os.environ.get("BBC_SCAN_EXTENSIONS", "").strip()
        if not raw:
            return BBCConfig.SOURCE_EXTENSIONS
        cleaned = []
        for item in raw.split(","):
            ext = item.strip().lower()
            if not ext:
                continue
            if not ext.startswith('.'):
                ext = f".{ext}"
            cleaned.append(ext)
        return tuple(cleaned) if cleaned else BBCConfig.SOURCE_EXTENSIONS

    @staticmethod
    def get_forbidden_scan_dirs(extra: Optional[Iterable[str]] = None) -> set:
        """Return directories excluded from scans, with optional env/custom additions."""
        out = set(BBCConfig.FORBIDDEN_SCAN_DIRS)
        raw = os.environ.get("BBC_EXCLUDE_DIRS", "").strip()
        if raw:
            out.update({p.strip() for p in raw.split(",") if p.strip()})
        if extra:
            out.update({str(p).strip() for p in extra if str(p).strip()})
        return out

    @staticmethod
    def atomic_write_json(path: str, payload: Dict[str, Any], encoder_cls=None) -> None:
        """Atomically write JSON to disk to avoid partial-read JSON parse failures."""
        target = os.path.abspath(path)
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(prefix=".bbc_tmp_", suffix=".json", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                if encoder_cls is None:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(payload, f, indent=2, ensure_ascii=False, cls=encoder_cls)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target)
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
    
    @staticmethod
    def setup_logging(project_root: str = "."):
        """Merkezi BBC loglama altyapisini start."""
        from .bbc_logger import get_logger
        get_logger("BBC")  # Ilk cagrida _init_logging() runs

    @staticmethod
    def check_state_drift(drift_value):
        """
        Release gate check.
        Returns (passed: bool, message: str)
        """
        if drift_value > BBCConfig.STATE_DRIFT_FAIL_THRESHOLD:
            return False, f"CRITICAL: State drift {drift_value:.2f} exceeds threshold {BBCConfig.STATE_DRIFT_FAIL_THRESHOLD}"
        if drift_value > BBCConfig.STATE_DRIFT_TOLERANCE:
            return True, f"WARNING: State drift {drift_value:.2f} is high"
        return True, "OK"