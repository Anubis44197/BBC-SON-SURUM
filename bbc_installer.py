#!/usr/bin/env python3
"""
BBC Universal Installer
Tek komutla BBC kurulumu ve proje adaptasyonu
Kullanım: python bbc_installer.py install [proje_yolu]
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class BBCInstaller:
    """BBC Universal Installer"""
    
    def __init__(self):
        self.bbc_source = Path(__file__).parent
        self.python_exec = sys.executable
        self.embed_core = os.environ.get("BBC_INSTALL_EMBED_CORE", "0") == "1"
        
    def install_bbc(self, target_path: str = ".") -> bool:
        """BBC'yi hedef projeye kur"""
        target_path = Path(target_path).resolve()
        
        print("[INFO] [BBC Installer] Starting installation...")
        print(f"Target: {target_path}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        try:
            # 1. Proje kontrolü
            if not self._validate_project(target_path):
                return False
            
            # 2. BBC dosyalarını kopyala
            if not self._copy_bbc_files(target_path):
                return False
            
            # 3. Bağımlılıkları kur
            if not self._install_dependencies(target_path):
                return False
            
            # 4. Proje adaptasyonu (Analyze + Inject)
            if not self._adapt_project(target_path):
                return False
            
            # 5. Kurulum tamamla
            self._finalize_installation(target_path)
            
            print("[OK] [BBC Installer] Installation completed successfully!")
            print(f"Project: {target_path}")
            print("Next steps:")
            print(f"   cd {target_path}")
            print(f"   python run_bbc.py bootstrap . --yes")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"[ERR] [BBC Installer] Installation failed: {e}")
            return False
    
    def _validate_project(self, project_path: Path) -> bool:
        """Proje geçerliliğini kontrol et"""
        print("[INFO] [Step 1/5] Validating project...")
        
        # Proje dizini kontrolü
        if not project_path.exists():
            print(f"[ERR] Project path does not exist: {project_path}")
            return False
        
        # Proje tipi tespiti
        project_types = {
            "Python": [".py", "requirements.txt", "setup.py", "pyproject.toml"],
            "JavaScript": [".js", "package.json", "node_modules"],
            "TypeScript": [".ts", "tsconfig.json"],
            "Java": [".java", "pom.xml", "build.gradle"],
            "C/C++": [".c", ".cpp", ".h", "CMakeLists.txt", "Makefile"],
            "Go": [".go", "go.mod"],
            "Rust": [".rs", "Cargo.toml"],
            "Generic": []  # Her proje
        }
        
        detected_type = "Generic"
        files_in_project = list(project_path.rglob("*"))
        
        for proj_type, indicators in project_types.items():
            if proj_type == "Generic":
                continue
            for indicator in indicators:
                if any(f.name == indicator for f in files_in_project):
                    detected_type = proj_type
                    break
            if detected_type != "Generic":
                break
        
        print(f"[OK] Project type detected: {detected_type}")
        print(f"[OK] Project contains {len(files_in_project)} files")
        return True
    
    def _copy_bbc_files(self, project_path: Path) -> bool:
        """BBC dosyalarını hedef projeye kopyala"""
        print("[INFO] [Step 2/5] Copying BBC files...")

        if not self.embed_core:
            print("  [INFO] Isolated mode active: skipping BBC core copy into project")
            print("  [INFO] Set BBC_INSTALL_EMBED_CORE=1 to enable legacy embedded copy mode")
            return True
        
        try:
            # Gerekli BBC dosyaları
            bbc_files = [
                "bbc.py",
                "run_bbc.py",
                "bbc_daemon.py",
                "bbc.bat",
                "bbc.sh",
                "requirements.txt",
            ]
            
            # BBC dizinlerini kopyala
            bbc_dirs = [
                "bbc_core",
                "01_Engine",
            ]
            
            # Dosyaları kopyala
            for file_name in bbc_files:
                src = self.bbc_source / file_name
                if src.exists():
                    dst = project_path / file_name
                    shutil.copy2(src, dst)
                    print(f"  [OK] Copied: {file_name}")
            
            # Dizinleri kopyala
            for dir_name in bbc_dirs:
                src = self.bbc_source / dir_name
                if src.exists() and src.is_dir():
                    dst = project_path / dir_name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print(f"  [OK] Copied: {dir_name}/")
            
            return True
            
        except Exception as e:
            print(f"[ERR] Failed to copy BBC files: {e}")
            return False
    
    def _install_dependencies(self, project_path: Path) -> bool:
        """Bağımlılıkları kur"""
        print("[INFO] [Step 3/5] Installing dependencies...")
        
        try:
            # Virtual environment oluştur
            venv_path = project_path / ".venv"
            if not venv_path.exists():
                print("  [INFO] Creating virtual environment...")
                subprocess.run([
                    self.python_exec, "-m", "venv", str(venv_path)
                ], check=True, capture_output=True)
            
            # Python path'i belirle
            if os.name == 'nt':  # Windows
                python_path = venv_path / "Scripts" / "python.exe"
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:  # Linux/Mac
                python_path = venv_path / "bin" / "python"
                pip_path = venv_path / "bin" / "pip"
            
            # Requirements kur
            requirements_file = project_path / "requirements.txt"
            if requirements_file.exists():
                print("  [INFO] Installing requirements...")
                subprocess.run([
                    str(pip_path), "install", "-r", str(requirements_file)
                ], check=True, capture_output=True)
            
            return True
            
        except Exception as e:
            print(f"[ERR] Failed to install dependencies: {e}")
            return False
    
    def _adapt_project(self, project_path: Path) -> bool:
        """Projeyi BBC'ye adapte et"""
        print("[INFO] [Step 4/5] Adapting project...")
        
        try:
            # Virtual environment'daki python'ı kullan
            venv_path = project_path / ".venv"
            if os.name == 'nt':  # Windows
                python_path = venv_path / "Scripts" / "python.exe"
            else:  # Linux/Mac
                python_path = venv_path / "bin" / "python"

            # Interactive confirmation (TTY-only) to avoid surprising repo writes
            auto_confirm = True
            try:
                is_tty = sys.stdin.isatty()
            except Exception:
                is_tty = False

            if is_tty:
                print("  [INFO] BBC can now analyze the project and inject IDE/agent instructions.")
                confirm = input("  [?] Run BBC bootstrap now (analyze+inject)? (Y/n): ").strip().lower()
                auto_confirm = confirm in ("", "y", "yes")

            if not auto_confirm:
                print("  [INFO] Skipping bootstrap. You can run later:")
                print("         python run_bbc.py bootstrap . --yes")
                return True

            print("  [INFO] Running BBC bootstrap...")

            runner_script = project_path / "run_bbc.py"
            if not self.embed_core or not runner_script.exists():
                runner_script = self.bbc_source / "run_bbc.py"

            if not runner_script.exists():
                print(f"  [ERR] BBC runner not found: {runner_script}")
                return False

            result = subprocess.run(
                [str(python_path), str(runner_script), "bootstrap", str(project_path), "--yes", "--silent"],
                capture_output=True,
                text=True,
                cwd=str(project_path),
            )

            if result.returncode != 0:
                # Bootstrap failures should not be silent; show stderr to user
                err = (result.stderr or "").strip()
                print(f"  [WARN] Bootstrap warning: {err if err else 'Unknown error'}")
                return False

            return True
            
        except Exception as e:
            print(f"[ERR] Failed to adapt project: {e}")
            return False
    
    def _finalize_installation(self, project_path: Path):
        """Kurulumu tamamla"""
        print("[INFO] [Step 5/5] Finalizing installation...")
        
        # Kurulum kaydı oluştur
        install_record = {
            "installation_time": datetime.now().isoformat(),
            "bbc_version": "v8.3",
            "installer_version": "1.0",
            "project_path": str(project_path),
            "python_version": sys.version,
            "platform": sys.platform
        }
        
        from bbc_core.config import BBCConfig
        bbc_dir = Path(BBCConfig.get_bbc_dir(str(project_path)))
        record_file = bbc_dir / "logs" / "installation_record.json"
        record_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(install_record, f, indent=2, ensure_ascii=False)
        
        # README oluştur
        readme_content = f"""# BBC Installation Completed

This project is now protected with BBC (Bitter Brain Context).

## Quick Start

```bash
cd {project_path.name}

python "{(self.bbc_source / 'run_bbc.py')}" analyze "{project_path}"

# Start working with your AI assistant!
```

## Commands

- `python "{(self.bbc_source / 'run_bbc.py')}" analyze "{project_path}"` - Project analysis
- `python "{(self.bbc_source / 'run_bbc.py')}" inject "{project_path}"` - Context injection
- `python "{(self.bbc_source / 'run_bbc.py')}" bootstrap "{project_path}" --yes` - Analyze + Inject in one step
- `python "{(self.bbc_source / 'run_bbc.py')}" cleanup "{project_path}" --force` - Remove injected files
- `python "{(self.bbc_source / 'run_bbc.py')}" purge "{project_path}" --force` - Complete BBC removal

Installation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        readme_file = project_path / "BBC_README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("  [OK] Installation record created")
        print("  [OK] README file created")

def main():
    """Ana fonksiyon"""
    if len(sys.argv) < 2:
        print("Usage: python bbc_installer.py install [project_path]")
        print("Example: python bbc_installer.py install /path/to/project")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "install":
        target_path = sys.argv[2] if len(sys.argv) > 2 else "."
        installer = BBCInstaller()
        success = installer.install_bbc(target_path)
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: install")
        sys.exit(1)

if __name__ == "__main__":
    main()
