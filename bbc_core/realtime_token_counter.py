"""
BBC Real-Time Token Counter
Track token usage in real-time during development
With timestamp logging
"""

import threading
import json
import os
from datetime import datetime
from typing import Dict, Optional, Callable
from dataclasses import dataclass, asdict

# BBC isolation: all logs go to .bbc/logs/
_BBC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BBC_LOG_DIR = os.path.join(_BBC_ROOT, '.bbc', 'logs')

@dataclass
class TokenMetrics:
    """Data structure for token metrics"""
    session_id: str
    start_time: str
    tokens_used: int = 0
    tokens_saved: int = 0
    files_processed: int = 0
    current_file: str = ""
    last_update: str = ""
    status: str = "ACTIVE"
    
    def to_dict(self) -> Dict:
        return asdict(self)

class RealTimeTokenCounter:
    """Real-time token tracking system"""
    
    def __init__(self, log_path: str = None):
        if log_path is None:
            log_path = os.path.join(_BBC_LOG_DIR, "realtime_tokens.log")
        self.log_path = log_path
        self.metrics = None
        self.is_running = False
        self.update_callbacks = []
        self._lock = threading.Lock()
        
        # Create log directory
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start new monitoring session"""
        session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with self._lock:
            self.metrics = TokenMetrics(
                session_id=session_id,
                start_time=datetime.now().isoformat(),
                last_update=datetime.now().isoformat()
            )
            self.is_running = True
            
        self._log_event("SESSION_START", f"Monitoring session started: {session_id}")
        return session_id
    
    def update_tokens(self, tokens_used: int, tokens_saved: int = 0, 
                    file_path: str = "", status: str = "ACTIVE"):
        """Update token usage"""
        if not self.is_running or not self.metrics:
            return
            
        with self._lock:
            self.metrics.tokens_used += tokens_used
            self.metrics.tokens_saved += tokens_saved
            self.metrics.last_update = datetime.now().isoformat()
            
            if file_path:
                self.metrics.current_file = file_path
                self.metrics.files_processed += 1
            
            self.metrics.status = status
            
        # Trigger callbacks
        for callback in self.update_callbacks:
            try:
                callback(self.metrics)
            except Exception as e:
                self._log_event("CALLBACK_ERROR", str(e))
                
        # Log
        self._log_event("TOKEN_UPDATE", 
                       f"Used: +{tokens_used}, Saved: +{tokens_saved}, File: {file_path}")
    
    def get_metrics(self) -> Optional[TokenMetrics]:
        """Return current metrics"""
        return self.metrics
    
    def end_session(self, final_status: str = "COMPLETED"):
        """End monitoring session"""
        if not self.is_running:
            return
            
        with self._lock:
            if self.metrics:
                self.metrics.status = final_status
                self.metrics.last_update = datetime.now().isoformat()
            
            self.is_running = False
            
        self._log_event("SESSION_END", f"Session ended with status: {final_status}")
        self._save_session_summary()
    
    def add_callback(self, callback: Callable[[TokenMetrics], None]):
        """Add real-time update callback"""
        self.update_callbacks.append(callback)
    
    def _log_event(self, event_type: str, message: str):
        """Log event"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {event_type}: {message}"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Log error: {e}")
    
    def _save_session_summary(self):
        """Save session summary"""
        if not self.metrics:
            return
            
        summary_path = os.path.join(_BBC_LOG_DIR, f"session_{self.metrics.session_id}_summary.json")
        
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(self.metrics.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_event("SAVE_ERROR", f"Failed to save summary: {e}")

# Global instance
_global_counter = None

def get_token_counter() -> RealTimeTokenCounter:
    """Get global token counter instance"""
    global _global_counter
    if _global_counter is None:
        _global_counter = RealTimeTokenCounter()
    return _global_counter

def start_monitoring(session_id: Optional[str] = None) -> str:
    """Start new monitoring session (global)"""
    return get_token_counter().start_session(session_id)

def update_token_usage(tokens_used: int, tokens_saved: int = 0, 
                     file_path: str = "", status: str = "ACTIVE"):
    """Update token usage (global)"""
    get_token_counter().update_tokens(tokens_used, tokens_saved, file_path, status)

def end_monitoring(final_status: str = "COMPLETED"):
    """End monitoring session (global)"""
    get_token_counter().end_session(final_status)

def get_current_metrics() -> Optional[TokenMetrics]:
    """Get current metrics (global)"""
    return get_token_counter().get_metrics()
