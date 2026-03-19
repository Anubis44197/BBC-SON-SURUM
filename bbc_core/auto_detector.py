"""
BBC Auto-Detection System
Auto-detect project and start BBC when terminal opens
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class BBCAutoDetector:
    """BBC Automatic Project Detection and Adaptation System"""
    
    def __init__(self):
        self.current_project = None
        self.bbc_active = False
        self.monitor_thread = None
        self.config_file = None
        self.session_log = None
        
    def detect_project_type(self, project_path: Path) -> Dict[str, any]:
        """Auto-detect project type"""
        indicators = {
            "python": [".py", "requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "javascript": [".js", "package.json", "node_modules", "yarn.lock"],
            "typescript": [".ts", "tsconfig.json", "package.json"],
            "java": [".java", "pom.xml", "build.gradle", "src/main"],
            "cpp": [".cpp", ".c", ".h", "CMakeLists.txt", "Makefile"],
            "go": [".go", "go.mod", "go.sum"],
            "rust": [".rs", "Cargo.toml", "src/main.rs"],
            "web": [".html", ".css", ".scss", "index.html"],
            "generic": []  # Her project
        }
        
        import itertools
        from .config import BBCConfig
        project_files = list(itertools.islice(project_path.rglob("*"), BBCConfig.MAX_FILES))
        detected_types = []
        
        for proj_type, files in indicators.items():
            if proj_type == "generic":
                continue
            score = 0
            for indicator in files:
                if any(f.name == indicator for f in project_files):
                    score += 2
                elif any(f.suffix == indicator for f in project_files):
                    score += 1
            if score > 0:
                detected_types.append((proj_type, score))
        
        detected_types.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "type": detected_types[0][0] if detected_types else "generic",
            "confidence": detected_types[0][1] if detected_types else 0,
            "all_scores": detected_types
        }
    
    def check_bbc_installed(self, project_path: Path) -> bool:
        """Check if BBC is installed in the project"""
        # bbc_context.json lives inside .bbc/ isolation directory
        required_files = [
            os.path.join(".bbc", "bbc_context.json"),
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (project_path / file_path).exists():
                missing_files.append(file_path)
        
        return len(missing_files) == 0, missing_files
    
    def auto_install_bbc(self, project_path: Path) -> bool:
        """Auto-install BBC to project - analyzes and injects directly"""
        try:
            print(f"[BBC AUTO] Installing BBC to {project_path.name}...")
            auto_inject_enabled = os.environ.get("BBC_AUTO_INJECT_CONFIGS", "0") == "1"
            
            # BBC core directory
            bbc_home = Path(__file__).parent.parent
            
            # Step 1: Analyze project and create bbc_context.json
            print(f"[BBC AUTO] Step 1/3: Analyzing project...")
            print("[BBC AUTO] Analysis output will stream below. Duration depends on file count and complexity.")
            run_bbc = bbc_home / "run_bbc.py"
            if not run_bbc.exists():
                print(f"[BBC AUTO] run_bbc.py not found at {run_bbc}")
                return False
            
            analyze_timeout = self._get_analyze_timeout_seconds()
            result = subprocess.run(
                [sys.executable, str(run_bbc), "analyze", str(project_path)],
                timeout=analyze_timeout
            )
            if result.returncode != 0:
                print("[BBC AUTO] Analysis failed.")
                return False
            print(f"[BBC AUTO] Step 1/3: Analysis complete")
            
            # Step 2: Inject AI assistant configs (optional, disabled by default)
            context_file = project_path / ".bbc" / "bbc_context.json"
            if auto_inject_enabled:
                print(f"[BBC AUTO] Step 2/3: Injecting AI configurations...")
                if context_file.exists():
                    try:
                        from bbc_core.agent_adapter import inject_to_project
                        results = inject_to_project(str(context_file), str(project_path))
                        injected = [k for k, v in results.items() if v != "skipped"] if results else []
                        print(f"[BBC AUTO] Step 2/3: Injected to {len(injected)} AI assistants")
                    except Exception as e:
                        print(f"[BBC AUTO] Injection warning: {e}")
                else:
                    print(f"[BBC AUTO] Warning: bbc_context.json not created")
            else:
                print("[BBC AUTO] Step 2/3: Skipped AI config injection (BBC_AUTO_INJECT_CONFIGS=0)")
            
            # Step 3: Verify installation
            print(f"[BBC AUTO] Step 3/3: Verifying installation...")
            installed, missing = self.check_bbc_installed(project_path)
            if installed:
                print(f"[BBC AUTO] Successfully installed BBC")
                return True
            else:
                print(f"[BBC AUTO] Installation incomplete, missing: {missing}")
                return False
                
        except subprocess.TimeoutExpired:
            print(
                "[BBC AUTO] Analysis reached timeout. "
                "Increase BBC_ANALYZE_TIMEOUT_SECONDS (e.g. 3600 for 60 minutes)."
            )
            return False
        except Exception as e:
            print(f"[BBC AUTO] Auto-installation error: {e}")
            return False

    def _get_analyze_timeout_seconds(self) -> int:
        """Read analyze timeout from env with a safe, large default for big repositories."""
        raw_value = os.environ.get("BBC_ANALYZE_TIMEOUT_SECONDS", "3600").strip()
        try:
            timeout = int(raw_value)
        except ValueError:
            timeout = 3600
        return max(60, timeout)
    
    def start_bbc_monitoring(self, project_path: Path):
        """Start BBC monitoring automatically"""
        try:
            # Start AI integration
            from bbc_core.ai_integration import start_ai_session
            
            session_info = {
                "project_type": self.detect_project_type(project_path),
                "project_path": str(project_path),
                "auto_detected": True,
                "timestamp": datetime.now().isoformat()
            }
            
            session_id = start_ai_session(str(project_path), session_info)
            
            self.bbc_active = True
            self.current_project = project_path
            
            print(f"[BBC AUTO] Started monitoring: {project_path.name}")
            print(f"[BBC AUTO] Session: {session_id}")
            print(f"[BBC AUTO] Project type: {session_info['project_type']['type']}")
            
            # Session log'u kaydet
            self._log_session("AUTO_START", session_id, project_path, session_info)
            
            return session_id
            
        except Exception as e:
            print(f"[BBC AUTO] Failed to start monitoring: {e}")
            return None
    
    def stop_bbc_monitoring(self):
        """BBC monitoring'i stop"""
        if self.bbc_active:
            try:
                from bbc_core.ai_integration import end_ai_session
                from bbc_core.terminal_monitor import stop_live_monitoring
                
                end_ai_session("AUTO_STOP")
                stop_live_monitoring()
                
                self.bbc_active = False
                print(f"[BBC AUTO] Stopped monitoring: {self.current_project.name if self.current_project else 'Unknown'}")
                
                # Session log'u kaydet
                self._log_session("AUTO_STOP", None, self.current_project, {"auto_stopped": True})
                
            except Exception as e:
                print(f"[BBC AUTO] Failed to stop monitoring: {e}")
    
    def auto_detect_and_start(self, force_restart: bool = False, project_path: str = None, start_monitoring: bool = True):
        """Detect project and prepare/start BBC."""
        current_dir = Path(project_path).resolve() if project_path else Path.cwd()
        
        # Project mi diye check et
        if not self._is_project_directory(current_dir):
            return False
        
        # Zaten BBC aktif mi ve restart gerekmiyor mu?
        if self.bbc_active and not force_restart:
            if self.current_project == current_dir:
                print(f"[BBC AUTO] Already monitoring: {current_dir.name}")
                return True
        
        # BBC kurulu mu check et
        installed, missing_files = self.check_bbc_installed(current_dir)
        
        if not installed:
            print(f"[BBC AUTO] BBC not installed in {current_dir.name}")
            print(f"[BBC AUTO] Missing files: {missing_files}")
            
            # Otomatik installation yap
            if self.auto_install_bbc(current_dir):
                installed = True
            else:
                print(f"[BBC AUTO] Failed to install BBC")
                return False
        
        # BBC'yi start veya only hazirla
        if installed:
            if not start_monitoring:
                return True
            return self.start_bbc_monitoring(current_dir)
        
        return False
    
    def _is_project_directory(self, path: Path) -> bool:
        """Check if this directory is a project directory"""
        # Git reposu mu?
        if (path / ".git").exists():
            return True
        
        # Project files var mi?
        project_indicators = [
            "package.json", "requirements.txt", "setup.py", "pyproject.toml",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
            "CMakeLists.txt", "Makefile", "index.html"
        ]
        
        return any((path / indicator).exists() for indicator in project_indicators)
    
    def _log_session(self, action: str, session_id: Optional[str], project_path: Optional[Path], data: Dict):
        """Session log'u kaydet"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "session_id": session_id,
            "project_path": str(project_path) if project_path else None,
            "data": data
        }
        
        try:
            if project_path:
                log_dir = project_path / ".bbc" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / "auto_sessions.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[BBC AUTO] Failed to log session: {e}")
    
    def start_background_monitoring(self):
        """Start background project change monitoring"""
        def monitor_loop():
            last_project = None
            
            while True:
                try:
                    current_dir = Path.cwd()
                    
                    if current_dir != last_project:
                        if last_project:
                            print(f"[BBC AUTO] Project changed: {last_project.name} -> {current_dir.name}")
                            self.stop_bbc_monitoring()
                        
                        self.auto_detect_and_start()
                        last_project = current_dir
                    
                    time.sleep(2)  # 2 saniyede bir check
                    
                except KeyboardInterrupt:
                    print(f"\n[BBC AUTO] Background monitoring stopped")
                    self.stop_bbc_monitoring()
                    break
                except Exception as e:
                    print(f"[BBC AUTO] Background monitoring error: {e}")
                    time.sleep(5)
        
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
            self.monitor_thread.start()
            print(f"[BBC AUTO] Background monitoring started")

# Global instance
_global_detector = None

def get_auto_detector() -> BBCAutoDetector:
    """Get global auto detector instance"""
    global _global_detector
    if _global_detector is None:
        _global_detector = BBCAutoDetector()
    return _global_detector

def auto_start_bbc(force_restart: bool = False, project_path: str = None, start_monitoring: bool = True) -> bool:
    """Auto-start BBC (global)"""
    return get_auto_detector().auto_detect_and_start(force_restart, project_path, start_monitoring)

def start_background_monitoring():
    """Start background monitoring (global)"""
    get_auto_detector().start_background_monitoring()

def stop_bbc_auto():
    """BBC otomatik sistemini stop (global)"""
    get_auto_detector().stop_bbc_monitoring()
