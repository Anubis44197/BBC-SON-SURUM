from datetime import datetime
from .bbc_logger import get_logger
from .telemetry import get_telemetry

logger = get_logger("BBC_StateManager")
_tele = get_telemetry()


class StateManager:
    _instance = None

    def __new__(cls, heal_budget: int = 100, session_heal_budget: int = 100, db_path: str = None, project_path: str = None):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance.heal_budget = heal_budget
            cls._instance.session_heal_budget = session_heal_budget
            cls._instance.degenerate_count = 0
            cls._instance.tokens_used = 0
            cls._instance.token_savings = 0
            cls._instance.files_processed = 0
            cls._instance.project_path = project_path
            cls._instance.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"--- NEW SESSION STARTED (ID: {cls._instance.session_id}) ---")
            logger.info(f"--- ENGINE: BBC Master v8.3 (7-State + Telemetry) ---")
            _tele.set_session(cls._instance.session_id)
            _tele.log_event("SESSION_START", {
                "session_id": cls._instance.session_id,
                "heal_budget": heal_budget,
                "session_heal_budget": session_heal_budget,
                "project_path": project_path or ""
            })
            if project_path:
                logger.info(f"--- PROJECT: {project_path} ---")
        return cls._instance

    def request_heal(self, origin_info="unknown"):
        """Request heal permission from budget."""
        if self.heal_budget > 0:
            self.heal_budget -= 1
            logger.info(f"[HEAL APPROVED] Source: {origin_info} | Remaining: {self.heal_budget}")
            _tele.log_event("HEAL_APPROVED", {"source": origin_info, "remaining": self.heal_budget})
            return True
        else:
            logger.warning(f"[HEAL DENIED] Budget exhausted! Source: {origin_info}")
            _tele.log_event("HEAL_DENIED", {"source": origin_info})
            return False

    def consume_heal_budget(self):
        """Consume one heal from session budget. Returns 1 if OK, -2 if exhausted."""
        if self.session_heal_budget > 0:
            self.session_heal_budget -= 1
            logger.info(f"[HEAL CONSUMED] Remaining session budget: {self.session_heal_budget}")
            _tele.log_event("HEAL_CONSUMED", {"remaining": self.session_heal_budget})
            return 1
        else:
            logger.warning("[HEAL DENIED] Session heal budget exhausted!")
            _tele.log_event("HEAL_DENIED", {"type": "session_budget"})
            return -2

    def record_degenerate(self, origin_info="unknown"):
        """Record a DEGENERATE (system crash) event."""
        self.degenerate_count += 1
        logger.critical(f"[DEGENERATE] CRITICAL! Source: {origin_info} | Total: {self.degenerate_count}")
        _tele.log_event("DEGENERATE", {"source": origin_info, "total": self.degenerate_count})

    def update_tokens(self, used: int = 0, saved: int = 0, files: int = 0):
        """Update token usage metrics."""
        self.tokens_used += used
        self.token_savings += saved
        self.files_processed += files

    def increment_files_analyzed(self):
        """Increment the count of files analyzed."""
        self.files_processed += 1

    def increment_recipes_created(self):
        """Increment the count of recipes created."""
        if not hasattr(self, 'recipes_created'):
            self.recipes_created = 0
        self.recipes_created += 1

    def add_data_processed(self, bytes_count: int):
        """Add to total data processed (in bytes)."""
        if not hasattr(self, 'data_processed'):
            self.data_processed = 0
        self.data_processed += bytes_count

    def add_token_savings(self, tokens: float):
        """Add to total token savings."""
        self.token_savings += int(tokens)

    @property
    def stats(self) -> dict:
        """Property alias for get_stats() — used by http_server and hmpu_engine."""
        return self.get_stats()

    def reset_session(self):
        """Reset session state for a fresh run (used by tests and ai_integration)."""
        self.degenerate_count = 0
        self.tokens_used = 0
        self.token_savings = 0
        self.files_processed = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"--- SESSION RESET (ID: {self.session_id}) ---")
        _tele.set_session(self.session_id)
        _tele.log_event("SESSION_RESET", {"session_id": self.session_id})

    @classmethod
    def _reset_for_testing(cls):
        """Destroy singleton so tests get a fresh instance."""
        cls._instance = None

    def get_stats(self) -> dict:
        """Return current session statistics."""
        return {
            "session_id": self.session_id,
            "tokens_used": self.tokens_used,
            "token_savings": self.token_savings,
            "files_processed": self.files_processed,
            "recipes_created": getattr(self, 'recipes_created', 0),
            "data_processed": getattr(self, 'data_processed', 0),
            "heal_budget": self.heal_budget,
            "session_heal_budget": self.session_heal_budget,
            "degenerate_count": self.degenerate_count,
            "degenerate_seen_total": self.degenerate_count
        }

    def close(self):
        """Cleanup on shutdown. Called by http_server lifespan."""
        logger.info(f"--- SESSION ENDED (ID: {self.session_id}) ---")
        _tele.log_event("SESSION_END", self.get_stats())
