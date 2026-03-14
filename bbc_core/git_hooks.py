"""
BBC Git Hooks Generator (v1.0)
Git hook'ları oluşturarak BBC'nin ekip genelinde otomatik başlatılmasını sağlar.

Desteklenen hook'lar:
  - post-checkout: Branch değiştiğinde BBC re-analyze tetikler
  - post-merge: Merge sonrası BBC re-analyze tetikler
"""

import os
import stat
import sys
from pathlib import Path


# Hook template — Python ile BBC çalıştırır
HOOK_TEMPLATE = '''#!/bin/sh
# BBC Auto-Reseal Hook (v1.0)
# Bu hook, git işlemi sonrası BBC context'ini güncel tutar.
# Kaldırmak için: bbc hooks --remove

BBC_DIR="{bbc_dir}"
PROJECT_DIR="{project_dir}"

if [ -f "$BBC_DIR/bbc.py" ]; then
    echo "[BBC] Auto-resealing context..."
    python "$BBC_DIR/bbc.py" start -f "$PROJECT_DIR" > /dev/null 2>&1 &
fi
'''


def install_hooks(project_path: str, bbc_dir: str = None) -> dict:
    """
    Proje .git/hooks/ klasörüne BBC hook'larını kurar.
    
    Args:
        project_path: Projenin kök dizini
        bbc_dir: BBC'nin kurulu olduğu dizin (default: script dizini)
        
    Returns:
        dict with installed hooks and any errors
    """
    project_path = str(Path(project_path).resolve())
    git_hooks_dir = os.path.join(project_path, ".git", "hooks")
    
    if not os.path.isdir(os.path.join(project_path, ".git")):
        return {"success": False, "error": "Not a git repository", "installed": []}
    
    os.makedirs(git_hooks_dir, exist_ok=True)
    
    if bbc_dir is None:
        bbc_dir = str(Path(__file__).resolve().parent.parent)
    
    hook_content = HOOK_TEMPLATE.format(
        bbc_dir=bbc_dir.replace("\\", "/"),
        project_dir=project_path.replace("\\", "/")
    )
    
    installed = []
    errors = []
    
    for hook_name in ["post-checkout", "post-merge"]:
        hook_path = os.path.join(git_hooks_dir, hook_name)
        
        # Mevcut hook varsa BBC marker kontrolü
        if os.path.exists(hook_path):
            try:
                with open(hook_path, 'r', encoding='utf-8') as f:
                    existing = f.read()
                if "BBC Auto-Reseal" in existing:
                    installed.append(f"{hook_name} (already installed)")
                    continue
                else:
                    # Mevcut hook'a BBC kısmını ekle
                    with open(hook_path, 'a', encoding='utf-8') as f:
                        f.write("\n" + hook_content)
                    installed.append(f"{hook_name} (appended)")
                    continue
            except Exception as e:
                errors.append(f"{hook_name}: {e}")
                continue
        
        # Yeni hook oluştur
        try:
            with open(hook_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(hook_content)
            # Unix'te çalıştırılabilir yap
            if os.name != 'nt':
                st = os.stat(hook_path)
                os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
            installed.append(f"{hook_name} (created)")
        except Exception as e:
            errors.append(f"{hook_name}: {e}")
    
    return {
        "success": len(errors) == 0,
        "installed": installed,
        "errors": errors,
        "hooks_dir": git_hooks_dir
    }


def remove_hooks(project_path: str) -> dict:
    """
    Proje .git/hooks/ klasöründen BBC hook'larını kaldırır.
    Sadece BBC tarafından oluşturulan kısımları temizler.
    """
    project_path = str(Path(project_path).resolve())
    git_hooks_dir = os.path.join(project_path, ".git", "hooks")
    
    if not os.path.isdir(git_hooks_dir):
        return {"success": False, "error": "No .git/hooks directory found", "removed": []}
    
    removed = []
    
    for hook_name in ["post-checkout", "post-merge"]:
        hook_path = os.path.join(git_hooks_dir, hook_name)
        if not os.path.exists(hook_path):
            continue
        
        try:
            with open(hook_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "BBC Auto-Reseal" not in content:
                continue
            
            # Sadece BBC kısmını içeriyorsa dosyayı sil
            lines = content.strip().split('\n')
            non_bbc_lines = []
            skip = False
            for line in lines:
                if "BBC Auto-Reseal" in line:
                    skip = True
                    continue
                if skip and line.strip() == "fi":
                    skip = False
                    continue
                if not skip:
                    non_bbc_lines.append(line)
            
            remaining = '\n'.join(non_bbc_lines).strip()
            if remaining and remaining != "#!/bin/sh":
                with open(hook_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(remaining + '\n')
                removed.append(f"{hook_name} (BBC section removed)")
            else:
                os.remove(hook_path)
                removed.append(f"{hook_name} (deleted)")
        except Exception as e:
            removed.append(f"{hook_name}: error - {e}")
    
    return {"success": True, "removed": removed}
