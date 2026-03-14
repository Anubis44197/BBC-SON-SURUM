"""
BBC Background Daemon
Arkaplanda sürekli BBC monitoring ve proje adaptasyonu
"""

import os
import sys
import time
import json
import signal
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class BBCDaemon:
    """BBC Background Daemon"""
    
    def __init__(self, project_root: str = None):
        self.running = False
        # Resolve .bbc/ relative to project root, not CWD
        if project_root:
            self.bbc_dir = Path(project_root).resolve() / ".bbc"
        else:
            # Default: script directory (repo root where bbc_daemon.py lives)
            self.bbc_dir = Path(__file__).resolve().parent / ".bbc"
        self.bbc_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.bbc_dir / "daemon.pid"
        self.log_file = self.bbc_dir / "daemon.log"
        self.config_file = self.bbc_dir / "config.json"
        
        # Signal handler'ları ayarla
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Daemon sinyal handler'ı"""
        self._log(f"Received signal {signum}. Shutting down...")
        self.stop()
    
    def _log(self, message: str):
        """Daemon log'u yaz"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Silent fail for daemon
    
    def _write_pid(self):
        """PID dosyasını yaz"""
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
    
    def _remove_pid(self):
        """PID dosyasını sil"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass
    
    def _is_running(self) -> bool:
        """Daemon'ın çalışıp çalışmadığını kontrol et"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            
            if os.name == 'nt':
                import ctypes
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except (OSError, ValueError):
            return False
    
    def start(self, project_path: str = ".", auto_detect: bool = True):
        """Daemon'ı başlat"""
        # Re-anchor .bbc/ to the target project if provided
        resolved_project = Path(project_path).resolve()
        self.bbc_dir = resolved_project / ".bbc"
        self.bbc_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.bbc_dir / "daemon.pid"
        self.log_file = self.bbc_dir / "daemon.log"
        self.config_file = self.bbc_dir / "config.json"

        if self._is_running():
            print("BBC Daemon is already running")
            return False
        
        # Fork işlemi (Unix/Linux için)
        if os.name != 'nt':
            try:
                pid = os.fork()
                if pid > 0:
                    # Parent process - exit
                    print(f"BBC Daemon started with PID: {pid}")
                    return True
            except OSError:
                pass  # Fork başarısız, foreground'da çalıştır
        
        # Daemon process
        self.running = True
        self._write_pid()
        
        # Working directory'i ayarla
        os.chdir(Path(project_path).resolve())
        
        # Standart I/O'yu yönlendir
        sys.stdout.flush()
        sys.stderr.flush()
        
        self._log("BBC Daemon started")
        self._log(f"Project path: {Path(project_path).resolve()}")
        self._log(f"Auto-detect: {auto_detect}")
        
        try:
            self._run_daemon_loop(project_path, auto_detect)
        except Exception as e:
            self._log(f"Daemon error: {e}")
        finally:
            self._remove_pid()
            self._log("BBC Daemon stopped")
    
    def stop(self):
        """Daemon'ı durdur"""
        if not self.pid_file.exists():
            print("BBC Daemon is not running")
            return False
        
        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            
            if os.name == 'nt':
                import subprocess
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
                
                for _ in range(10):
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.5)
                    except OSError:
                        break
                else:
                    os.kill(pid, signal.SIGKILL)
            
            self._remove_pid()
            print("BBC Daemon stopped")
            return True
            
        except Exception as e:
            print(f"Failed to stop BBC Daemon: {e}")
            return False
    
    def status(self):
        """Daemon durumunu göster"""
        if self._is_running():
            print("[OK] BBC Daemon is running")
            
            # Config dosyasından durum bilgilerini oku
            if self.config_file.exists():
                try:
                    with open(self.config_file, "r") as f:
                        config = json.load(f)
                    
                    print(f"Project: {config.get('project_path', 'Unknown')}")
                    print(f"Status: {config.get('status', 'Unknown')}")
                    print(f"Started: {config.get('start_time', 'Unknown')}")
                    
                except Exception:
                    pass
        else:
            print("[ERR] BBC Daemon is not running")
    
    def _scan_project_files(self, project_path: Path) -> set:
        """Projedeki kaynak dosyalarını tara, relative path set'i döndür"""
        exts = ('.py', '.md', '.json', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
                '.sql', '.rs', '.go', '.c', '.cpp', '.h', '.hpp', '.java', '.cs',
                '.php', '.rb', '.swift', '.kt')
        forbidden_dirs = {'node_modules', '.venv', 'dist', 'build', '.git', '__pycache__', 'target', '.bbc'}
        found = set()
        try:
            for root, dirs, files in os.walk(str(project_path)):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in forbidden_dirs]
                for f in files:
                    if f.lower().endswith(exts):
                        rel = os.path.relpath(os.path.join(root, f), str(project_path))
                        found.add(rel)
        except Exception:
            pass
        return found

    def _run_reanalysis(self, project_path: str):
        """Projeyi yeniden analiz et ve AI config'lerini inject et"""
        import subprocess as sp
        run_bbc = Path(__file__).resolve().parent / "run_bbc.py"
        if not run_bbc.exists():
            self._log(f"run_bbc.py not found at {run_bbc}")
            return False
        try:
            sp.run([sys.executable, str(run_bbc), "analyze", project_path, "--silent"],
                   capture_output=True, text=True, timeout=120)
            sp.run([sys.executable, str(run_bbc), "inject", project_path, "--auto-analyze", "--silent"],
                   capture_output=True, text=True, timeout=60)
            self._log("Re-analysis and re-injection completed")
            return True
        except Exception as e:
            self._log(f"Re-analysis error: {e}")
            return False

    def _run_daemon_loop(self, project_path: str, auto_detect: bool):
        """Ana daemon döngüsü — dosya değişikliği/eklenmesi/silinmesi algılar"""
        project_path = Path(project_path).resolve()
        project_str = str(project_path)
        last_project = None
        bbc_active = False
        
        # File watcher state
        FRESHNESS_INTERVAL = 30  # saniye — hash kontrolü aralığı
        last_freshness_check = 0.0
        known_files = set()  # bilinen dosya seti
        
        # BBC modüllerini import et
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        
        try:
            from bbc_core.auto_detector import get_auto_detector
            from bbc_core.ide_hooks import get_ide_hooks
            
            detector = get_auto_detector()
            ide_hooks = get_ide_hooks()
            
            # İlk dosya listesini al
            ctx_path = self.bbc_dir / "bbc_context.json"
            if ctx_path.exists():
                try:
                    with open(ctx_path, "r", encoding="utf-8") as f:
                        ctx_data = json.load(f)
                    known_files = {item.get("path", "") for item in ctx_data.get("code_structure", []) if isinstance(item, dict)}
                    self._log(f"Initial file set loaded: {len(known_files)} files")
                except Exception as e:
                    self._log(f"Failed to load initial context: {e}")
            
            if not known_files:
                known_files = self._scan_project_files(project_path)
                self._log(f"Initial scan: {len(known_files)} files")
            
            while self.running:
                try:
                    current_dir = Path.cwd()
                    
                    # Proje değişikliği kontrol et
                    if current_dir != last_project:
                        if last_project:
                            self._log(f"Project changed: {last_project.name} -> {current_dir.name}")
                            if bbc_active:
                                detector.stop_bbc_monitoring()
                                ide_hooks.stop_monitoring()
                                bbc_active = False
                        
                        if auto_detect:
                            self._log(f"Auto-detecting new project: {current_dir.name}")
                            if detector.auto_detect_and_start():
                                ide_hooks.auto_setup_ide_integration(current_dir)
                                bbc_active = True
                                self._update_config(current_dir, "ACTIVE")
                        
                        last_project = current_dir
                    
                    # === FILE WATCHER: periyodik freshness kontrolü ===
                    now = time.time()
                    if now - last_freshness_check >= FRESHNESS_INTERVAL:
                        last_freshness_check = now
                        needs_reanalysis = False
                        reason = ""
                        
                        # 1) Yeni/silinen dosya kontrolü
                        current_files = self._scan_project_files(project_path)
                        new_files = current_files - known_files
                        deleted_files = known_files - current_files
                        
                        if new_files:
                            reason = f"{len(new_files)} new file(s): {list(new_files)[:5]}"
                            self._log(f"[WATCH] New files detected: {reason}")
                            needs_reanalysis = True
                        
                        if deleted_files:
                            reason = f"{len(deleted_files)} deleted file(s): {list(deleted_files)[:5]}"
                            self._log(f"[WATCH] Deleted files detected: {reason}")
                            needs_reanalysis = True
                        
                        # 2) Hash değişikliği kontrolü (adaptive_mode kullanarak)
                        if not needs_reanalysis and ctx_path.exists():
                            try:
                                from bbc_core.adaptive_mode import BBCAdaptiveMode
                                mode = BBCAdaptiveMode(str(ctx_path))
                                freshness = mode.check_context_freshness()
                                
                                if not freshness["context_fresh"]:
                                    stale_count = freshness["stale_count"]
                                    rec = freshness["recommendation"]
                                    self._log(f"[WATCH] Stale files: {stale_count}, recommendation: {rec}")
                                    
                                    if rec in ("RESCAN", "PARTIAL_RESCAN"):
                                        needs_reanalysis = True
                                        reason = f"{stale_count} modified file(s)"
                            except Exception as e:
                                self._log(f"[WATCH] Freshness check error: {e}")
                        
                        # 3) Yeniden analiz gerekiyorsa çalıştır
                        if needs_reanalysis:
                            self._log(f"[WATCH] Triggering re-analysis: {reason}")
                            if self._run_reanalysis(project_str):
                                # Dosya setini güncelle
                                known_files = current_files
                                self._update_config(project_path, "RESEALED")
                                self._log("[WATCH] Context resealed successfully")
                            else:
                                self._log("[WATCH] Re-analysis failed")
                        else:
                            known_files = current_files
                    
                    # 5 saniyede bir döngü
                    time.sleep(5)
                    
                except Exception as e:
                    self._log(f"Loop error: {e}")
                    time.sleep(10)
        
        except ImportError as e:
            self._log(f"Failed to import BBC modules: {e}")
            self._log("Make sure BBC is properly installed")
    
    def _update_config(self, project_path: Path, status: str):
        """Config dosyasını güncelle"""
        config = {
            "project_path": str(project_path),
            "status": status,
            "start_time": datetime.now().isoformat(),
            "timestamp": time.time()
        }
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self._log(f"Failed to update config: {e}")

def main():
    """Daemon CLI fonksiyonu"""
    if len(sys.argv) < 2:
        print("Usage: python bbc_daemon.py [start|stop|status] [project_path]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    project_path = sys.argv[2] if len(sys.argv) > 2 else "."
    
    daemon = BBCDaemon(project_root=project_path)
    
    if command == "start":
        daemon.start(project_path)
    elif command == "stop":
        daemon.stop()
    elif command == "status":
        daemon.status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
