"""
BBC AI Request Integration
Auto-start BBC monitoring on each AI request
"""

import os
import sys
import json
import atexit
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from .realtime_token_counter import start_monitoring, update_token_usage, end_monitoring, get_current_metrics
from .terminal_monitor import start_live_monitoring, stop_live_monitoring, print_final_summary

class BBCAIIntegration:
    """BBC integration for AI requests"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.session_id = None
        self.is_active = False
        self.request_count = 0
        self.live_monitor_enabled = os.environ.get("BBC_ENABLE_LIVE_MONITOR", "0") == "1"
        
        # Check project adaptation
        self._ensure_project_adapted()
        
    def _ensure_project_adapted(self):
        """Ensure project is adapted for BBC"""
        required_files = [
            os.path.join(".bbc", "bbc_context.json"),
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_path / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"[BBC] Missing adaptation files: {missing_files}")
            print("[BBC] Running automatic adaptation...")
            self._auto_adapt_project()
    
    def _auto_adapt_project(self):
        """Auto-adapt project for BBC"""
        try:
            # Run BBC analyze command
            import subprocess
            result = subprocess.run([
                sys.executable, "run_bbc.py", "analyze", str(self.project_path)
            ], capture_output=True, text=True, cwd=self.project_path)
            
            if result.returncode == 0:
                print("[BBC] Project adapted successfully")
                # Context enjeksiyonu yap
                subprocess.run([
                    sys.executable, "run_bbc.py", "inject", str(self.project_path)
                ], capture_output=True, text=True, cwd=self.project_path)
            else:
                print(f"[BBC] Adaptation failed: {result.stderr}")
        except Exception as e:
            print(f"[BBC] Adaptation error: {e}")

    def _sync_unified_metrics(self, status: str, source: str = "live", current_file: str = ""):
        """Write unified metrics to .bbc/bbc_context.json without creating new files."""
        ctx_path = self.project_path / ".bbc" / "bbc_context.json"
        if not ctx_path.exists():
            return

        try:
            with open(ctx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        metrics = data.setdefault("metrics", {})
        live = get_current_metrics()

        if live:
            used = int(getattr(live, "tokens_used", 0) or 0)
            saved = int(getattr(live, "tokens_saved", 0) or 0)
            normal = int(metrics.get("unified_tokens_normal", used + saved) or (used + saved))
            if normal < used + saved:
                normal = used + saved
            pct = (saved / normal * 100) if normal > 0 else 0.0

            metrics["unified_tokens_used"] = used
            metrics["unified_tokens_saved"] = saved
            metrics["unified_tokens_normal"] = normal
            metrics["unified_savings_pct"] = round(pct, 1)

        metrics["unified_status"] = status
        metrics["unified_source"] = source
        metrics["unified_updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if current_file:
            metrics["unified_current_file"] = current_file

        try:
            with open(ctx_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def start_ai_request(self, request_info: Dict[str, Any] = None) -> str:
        """Start new AI request"""
        if self.is_active:
            print("[BBC] Warning: Session already active, ending previous session")
            self.end_ai_request("INTERRUPTED")
        
        self.request_count += 1
        request_info = request_info or {}
        
        # Create session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"AI_REQ_{self.request_count}_{timestamp}"
        
        # Start monitoring
        start_monitoring(self.session_id)
        if self.live_monitor_enabled:
            start_live_monitoring()
        
        self.is_active = True
        self._sync_unified_metrics("ACTIVE", source="live")
        
        # Start log
        print(f"\n[BBC] AI Request #{self.request_count} Started")
        print(f"[BBC] Session: {self.session_id}")
        print(f"[BBC] Project: {self.project_path.name}")
        print(f"[BBC] Time: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
        
        return self.session_id
    
    def update_progress(self, tokens_used: int = 0, tokens_saved: int = 0, 
                       current_file: str = "", operation: str = "PROCESSING"):
        """Update AI request progress"""
        if not self.is_active:
            return
        
        update_token_usage(tokens_used, tokens_saved, current_file, operation)
        self._sync_unified_metrics(operation, source="live", current_file=current_file)
        if not self.live_monitor_enabled:
            metrics = get_current_metrics()
            if metrics:
                print(
                    f"[BBC TOKENS] used={int(metrics.tokens_used)} "
                    f"saved={int(metrics.tokens_saved)} file={current_file or '-'}"
                )
    
    def end_ai_request(self, status: str = "COMPLETED"):
        """End AI request"""
        if not self.is_active:
            return
        
        # Monitoring'i bitir
        end_monitoring(status)
        self._sync_unified_metrics(status, source="live")
        if self.live_monitor_enabled:
            stop_live_monitoring()
        
        # Show final summary
        if self.live_monitor_enabled:
            print_final_summary()
        
        # Session log
        print(f"\n[BBC] AI Request #{self.request_count} Ended")
        print(f"[BBC] Status: {status}")
        print(f"[BBC] Time: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)
        
        self.is_active = False
        
        # Save session summary
        self._save_session_summary(status)
    
    def _save_session_summary(self, status: str):
        """Save session summary"""
        metrics = get_current_metrics()
        if not metrics:
            return
        
        summary = {
            "session_id": self.session_id,
            "request_number": self.request_count,
            "project_path": str(self.project_path),
            "start_time": metrics.start_time,
            "end_time": datetime.now().isoformat(),
            "status": status,
            "tokens_used": metrics.tokens_used,
            "tokens_saved": metrics.tokens_saved,
            "files_processed": metrics.files_processed,
            "efficiency_rate": (metrics.tokens_saved / metrics.tokens_used * 100) if metrics.tokens_used > 0 else 0
        }
        
        # Append to summary file
        bbc_log_dir = self.project_path / ".bbc" / "logs"
        bbc_log_dir.mkdir(parents=True, exist_ok=True)
        summary_file = bbc_log_dir / "ai_requests_summary.json"
        
        try:
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
            else:
                summaries = []
            
            summaries.append(summary)
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[BBC] Failed to save session summary: {e}")

# Global instance
_global_integration = None

def get_bbc_integration(project_path: str = ".") -> BBCAIIntegration:
    """Get global BBC integration instance"""
    global _global_integration
    if _global_integration is None:
        _global_integration = BBCAIIntegration(project_path)
    return _global_integration

def start_ai_session(project_path: str = ".", request_info: Dict[str, Any] = None) -> str:
    """Start AI session (global)"""
    return get_bbc_integration(project_path).start_ai_request(request_info)

def update_ai_progress(tokens_used: int = 0, tokens_saved: int = 0, 
                      current_file: str = "", operation: str = "PROCESSING"):
    """Update AI progress (global)"""
    get_bbc_integration().update_progress(tokens_used, tokens_saved, current_file, operation)

def end_ai_session(status: str = "COMPLETED"):
    """End AI session (global)"""
    get_bbc_integration().end_ai_request(status)

# Auto cleanup
atexit.register(lambda: end_ai_session("INTERRUPTED") if _global_integration and _global_integration.is_active else None)
