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
    
    # BBC isolation directory - all output goes here
    BBC_DIR = ".bbc"
    
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
        """Merkezi BBC loglama altyapısını başlat."""
        from .bbc_logger import get_logger
        get_logger("BBC")  # İlk çağrıda _init_logging() çalışır

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