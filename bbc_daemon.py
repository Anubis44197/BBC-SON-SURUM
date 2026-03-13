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
    
    def _run_daemon_loop(self, project_path: str, auto_detect: bool):
        """Ana daemon döngüsü"""
        project_path = Path(project_path).resolve()
        last_project = None
        bbc_active = False
        
        # BBC modüllerini import et
        sys.path.append(str(Path(__file__).parent.parent))
        
        try:
            from bbc_core.auto_detector import get_auto_detector
            from bbc_core.ide_hooks import get_ide_hooks
            
            detector = get_auto_detector()
            ide_hooks = get_ide_hooks()
            
            while self.running:
                try:
                    current_dir = Path.cwd()
                    
                    # Proje değişikliği kontrol et
                    if current_dir != last_project:
                        if last_project:
                            self._log(f"Project changed: {last_project.name} → {current_dir.name}")
                            # Önceki BBC'yi durdur
                            if bbc_active:
                                detector.stop_bbc_monitoring()
                                ide_hooks.stop_monitoring()
                                bbc_active = False
                        
                        # Yeni proje için adaptasyon yap
                        if auto_detect:
                            self._log(f"Auto-detecting new project: {current_dir.name}")
                            
                            # BBC'yi otomatik başlat
                            if detector.auto_detect_and_start():
                                # IDE entegrasyonunu kur
                                ide_hooks.auto_setup_ide_integration(current_dir)
                                bbc_active = True
                                
                                # Config'i güncelle
                                self._update_config(current_dir, "ACTIVE")
                        
                        last_project = current_dir
                    
                    # 5 saniyede bir kontrol
                    time.sleep(5)
                    
                except Exception as e:
                    self._log(f"Loop error: {e}")
                    time.sleep(10)  # Hata durumunda daha uzun bekle
        
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
