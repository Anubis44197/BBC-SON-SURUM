"""
BBC IDE Hook System
Automatic BBC integration for VS Code, Cursor and other IDEs
"""

import os
import json
import time
import threading
from pathlib import Path

class BBCIDEHooks:
    """BBC IDE Integration and Hook System"""
    
    def __init__(self):
        self.active_hooks = []
        self.monitoring_active = False
        self.project_root = None
        self.last_file_change = None
        
    def detect_ide(self) -> str:
        """Detect running IDE"""
        # Environment variables
        env_ide = os.environ.get('TERM_PROGRAM', '')
        if 'vscode' in env_ide.lower():
            return 'vscode'
        elif 'cursor' in env_ide.lower():
            return 'cursor'
        
        # Process list
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info and proc.info['name']:
                    name = proc.info['name'].lower()
                    if 'code' in name and 'visual' in name:
                        return 'vscode'
                    elif 'cursor' in name:
                        return 'cursor'
                    elif 'vim' in name:
                        return 'vim'
                    elif 'emacs' in name:
                        return 'emacs'
        except ImportError:
            pass
        
        return 'unknown'
    
    def setup_vscode_hooks(self, project_path: Path):
        """Install VS Code hooks"""
        vscode_dir = project_path / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        # VS Code tasks.json
        tasks_file = vscode_dir / "tasks.json"
        tasks = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "BBC Start",
                    "type": "shell",
                    "command": "python",
                    "args": ["run_bbc.py", "start"],
                    "group": "build",
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "new"
                    },
                    "problemMatcher": []
                },
                {
                    "label": "BBC Stop",
                    "type": "shell", 
                    "command": "python",
                    "args": ["run_bbc.py", "stop"],
                    "group": "build",
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "new"
                    }
                },
                {
                    "label": "BBC Status",
                    "type": "shell",
                    "command": "python",
                    "args": ["run_bbc.py", "status"],
                    "group": "build"
                }
            ]
        }
        
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2)
        
        # VS Code extensions.json
        extensions_file = vscode_dir / "extensions.json"
        extensions = {
            "recommendations": [
                "ms-python.python",
                "ms-vscode.vscode-json",
                "github.copilot",
                "ms-vscode.vscode-tailwindcss"
            ]
        }
        
        with open(extensions_file, 'w', encoding='utf-8') as f:
            json.dump(extensions, f, indent=2)
        
        print(f"[BBC IDE] VS Code hooks installed")
    
    def setup_cursor_hooks(self, project_path: Path):
        """Install Cursor hooks"""
        # Cursor already uses .cursorrules
        # Update BBC context automatically
        
        cursor_rules = project_path / ".cursorrules"
        if cursor_rules.exists():
            # Update BBC context in Cursor format
            from bbc_core.agent_adapter import BBCAgentAdapter
            
            try:
                adapter = BBCAgentAdapter(str(project_path / ".bbc" / "bbc_context.json"))
                cursor_content = adapter.to_cursor_context()
                
                with open(cursor_rules, 'w', encoding='utf-8') as f:
                    f.write(cursor_content)
                
                print(f"[BBC IDE] Cursor hooks updated")
            except Exception as e:
                print(f"[BBC IDE] Failed to update Cursor rules: {e}")
    
    def setup_file_watcher(self, project_path: Path):
        """Watch file changes"""
        try:
            import watchdog.observers
            import watchdog.events
            
            class BBCFileHandler(watchdog.events.FileSystemEventHandler):
                def __init__(self, ide_hooks):
                    self.ide_hooks = ide_hooks
                
                def on_modified(self, event):
                    if not event.is_directory:
                        file_path = Path(event.src_path)
                        
                        # Only watch code files
                        if file_path.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']:
                            self.ide_hooks._handle_file_change(file_path)
            
            handler = BBCFileHandler(self)
            observer = watchdog.observers.Observer()
            observer.schedule(handler, str(project_path), recursive=True)
            observer.start()
            
            self.active_hooks.append(observer)
            print(f"[BBC IDE] File watcher started for {project_path}")
            
        except ImportError:
            print(f"[BBC IDE] Watchdog not installed. Using polling watcher.")
            self._start_polling_watcher(project_path)

    def _start_polling_watcher(self, project_path: Path):
        """Fallback file watcher using mtime polling."""
        tracked_ext = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'}
        file_state = {}

        def scan_once():
            current = {}
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if d not in ['.git', '.venv', '__pycache__', '.bbc']]
                for name in files:
                    p = Path(root) / name
                    if p.suffix.lower() not in tracked_ext:
                        continue
                    try:
                        current[str(p)] = p.stat().st_mtime
                    except Exception:
                        continue
            return current

        def poll_loop():
            try:
                file_state.update(scan_once())
                while self.monitoring_active:
                    latest = scan_once()
                    for p_str, mtime in latest.items():
                        old = file_state.get(p_str)
                        if old is None or mtime > old:
                            self._handle_file_change(Path(p_str))
                    file_state.clear()
                    file_state.update(latest)
                    time.sleep(1.0)
            except Exception as e:
                print(f"[BBC IDE] Polling watcher stopped: {e}")

        poll_thread = threading.Thread(target=poll_loop, daemon=True)
        poll_thread.start()
        self.active_hooks.append(poll_thread)
        print(f"[BBC IDE] Polling watcher started for {project_path}")
    
    def _handle_file_change(self, file_path: Path):
        """Handle file change event"""
        # Debounce: prevent rapid updates for same file
        now = time.time()
        if self.last_file_change and (now - self.last_file_change['time']) < 1.0:
            if self.last_file_change['file'] == str(file_path):
                return
        
        self.last_file_change = {
            'file': str(file_path),
            'time': now
        }
        
        # Update AI progress
        try:
            # Estimate tokens from file size
            file_size = file_path.stat().st_size
            estimated_tokens = file_size // 4  # Approximate 1 token = 4 characters
            
            from bbc_core.ai_integration import update_ai_progress
            update_ai_progress(
                tokens_used=estimated_tokens,
                current_file=str(file_path.relative_to(self.project_root)),
                operation="FILE_CHANGE"
            )
            
            # Real-time Re-sealing (Force Protocol)
            from bbc_core.auto_detector import auto_start_bbc
            auto_start_bbc(force_restart=True, project_path=str(self.project_root), start_monitoring=False)
            
        except Exception as e:
            print(f"[BBC IDE] Failed to update progress: {e}")
    
    def setup_ai_prompt_hook(self):
        """Capture AI prompts"""
        # This part requires IDE-specific implementation
        # For VS Code, we can listen to Copilot API
        # For Cursor, we can use Cursor API
        
        try:
            # VS Code Copilot integration
            if self.detect_ide() == 'vscode':
                self._setup_vscode_copilot_hook()
            
            # Cursor integration  
            elif self.detect_ide() == 'cursor':
                self._setup_cursor_hook()
                
        except Exception as e:
            print(f"[BBC IDE] AI prompt hook setup failed: {e}")
    
    def _setup_vscode_copilot_hook(self):
        """VS Code Copilot hook"""
        # Use VS Code extension API to capture Copilot requests
        # This is an advanced feature and requires a custom extension
        
        # Placeholder for VS Code Copilot integration
        pass
    
    def _setup_cursor_hook(self):
        """Cursor hook"""
        # Listen to Cursor AI API
        # This also requires custom implementation
        
        # Placeholder for Cursor integration
        pass
    
    def auto_setup_ide_integration(self, project_path: Path):
        """Auto-setup IDE integration"""
        ide = self.detect_ide()
        self.project_root = project_path
        
        print(f"[BBC IDE] Detected IDE: {ide}")
        
        if ide == 'vscode':
            self.setup_vscode_hooks(project_path)
        elif ide == 'cursor':
            self.setup_cursor_hooks(project_path)
        
        # General hooks
        self.setup_file_watcher(project_path)
        self.setup_ai_prompt_hook()
        
        self.monitoring_active = True
        print(f"[BBC IDE] IDE integration completed")
    
    def stop_monitoring(self):
        """Stop all hooks"""
        for hook in self.active_hooks:
            try:
                if hasattr(hook, 'stop'):
                    hook.stop()
                elif hasattr(hook, 'join'):
                    hook.join(timeout=1)
            except Exception as e:
                print(f"[BBC IDE] Failed to stop hook: {e}")
        
        self.active_hooks.clear()
        self.monitoring_active = False
        print(f"[BBC IDE] All hooks stopped")

# Global instance
_global_ide_hooks = None

def get_ide_hooks() -> BBCIDEHooks:
    """Get global IDE hooks instance"""
    global _global_ide_hooks
    if _global_ide_hooks is None:
        _global_ide_hooks = BBCIDEHooks()
    return _global_ide_hooks

def setup_ide_integration(project_path: str = "."):
    """Setup IDE integration (global)"""
    return get_ide_hooks().auto_setup_ide_integration(Path(project_path).resolve())

def stop_ide_integration():
    """Stop IDE integration (global)"""
    get_ide_hooks().stop_monitoring()
