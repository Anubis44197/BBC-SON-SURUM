HEAL_BUDGET_DEFAULT = 5
SESSION_HEAL_BUDGET_DEFAULT = 5
import os

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