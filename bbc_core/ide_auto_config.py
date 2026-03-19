#!/usr/bin/env python3
"""
BBC v8.3 - Automatic IDE and AI Extension Detection System
Detects all installed IDEs and AI extensions for BBC context injection.
"""

import os
import sys
import json
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class IDEAutoConfigurator:
    """Otomatik IDE ve eklenti algilama/yapilandirma"""
    
    def __init__(self):
        self.system = platform.system()
        self.detected_ides = []
        self.detected_plugins = []
        self.configs_created = []
    
    def detect_active_ide(self) -> Optional[str]:
        """Aktif operation ortamindaki IDE'yi tespit eder."""
        # 1. Ortam Degiskenleri ile Kesin Tespit
        if os.environ.get("ANTIGRAVITY_SESSION") or os.environ.get("GEMINI_API_KEY"):
            return "antigravity"
        elif os.environ.get("VSCODE_PID") or os.environ.get("VSCODE_IPC_HOOK_CLI"):
            return "vscode"
        elif os.environ.get("CURSOR_SESSION") or os.environ.get("CURSOR_CRASH_REPORTER"):
            return "cursor"
        elif os.environ.get("WINDSURF_SESSION"):
            return "windsurf"
        elif os.environ.get("CLINE_SESSION"):
            return "cline"
            
        # 2. Process Agaci Analizi (Dis terminalden calistirildiysa IDE'yi bul)
        try:
            import psutil
            current_process = psutil.Process(os.getpid())
            parent = current_process.parent()
            while parent:
                p_name = parent.name().lower()
                if "cursor" in p_name:
                    return "cursor"
                elif "windsurf" in p_name:
                    return "windsurf"
                elif "code" in p_name or "vscode" in p_name:
                    return "vscode"
                elif "devenv" in p_name or "visual studio" in p_name:
                    return "visualstudio"
                elif "idea" in p_name or "pycharm" in p_name or "webstorm" in p_name or "rider" in p_name:
                    return "jetbrains"
                elif "antigravity" in p_name or "gemini" in p_name:
                    return "antigravity"
                parent = parent.parent()
        except ImportError:
            pass
        except Exception:
            pass
            
        return None
        
    def detect_vscode(self) -> bool:
        """VS Code tespiti"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code Insiders" / "Code - Insiders.exe",
            Path("/usr/bin/code"),
            Path("/usr/local/bin/code"),
            Path("/Applications/Visual Studio Code.app"),
        ]
        
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({
                    "name": "Visual Studio Code",
                    "type": "vscode",
                    "path": str(path)
                })
                return True
        return False
    
    def detect_cursor(self) -> bool:
        """Cursor IDE tespiti"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "cursor" / "Cursor.exe",
            Path("/Applications/Cursor.app"),
            Path("/usr/bin/cursor"),
        ]
        
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({
                    "name": "Cursor",
                    "type": "cursor",
                    "path": str(path)
                })
                return True
        return False
    
    def detect_windsurf(self) -> bool:
        """Windsurf IDE tespiti (Codeium IDE)"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "windsurf" / "Windsurf.exe",
            Path.home() / "AppData" / "Local" / "Windsurf" / "Windsurf.exe",
            Path("/Applications/Windsurf.app"),
            Path("/usr/bin/windsurf"),
        ]
        
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({
                    "name": "Windsurf",
                    "type": "windsurf",
                    "path": str(path)
                })
                return True
        return False
    
    def detect_jetbrains(self) -> List[Dict]:
        """JetBrains IDElari tespiti"""
        jetbrains_products = [
            ("IntelliJ IDEA", "idea"),
            ("PyCharm", "pycharm"),
            ("WebStorm", "webstorm"),
            ("PhpStorm", "phpstorm"),
            ("CLion", "clion"),
            ("GoLand", "goland"),
            ("Rider", "rider"),
            ("Android Studio", "studio"),
        ]
        
        found = []
        
        # Windows
        if self.system == "Windows":
            base_path = Path.home() / "AppData" / "Local" / "JetBrains"
            if base_path.exists():
                for product_name, cmd in jetbrains_products:
                    for folder in base_path.iterdir():
                        if cmd.lower() in folder.name.lower():
                            found.append({
                                "name": product_name,
                                "type": "jetbrains",
                                "product": cmd,
                                "path": str(folder)
                            })
        
        # macOS
        elif self.system == "Darwin":
            apps_path = Path("/Applications")
            for product_name, cmd in jetbrains_products:
                app_path = apps_path / f"{product_name}.app"
                if app_path.exists():
                    found.append({
                        "name": product_name,
                        "type": "jetbrains",
                        "product": cmd,
                        "path": str(app_path)
                    })
        
        # Linux
        else:
            for product_name, cmd in jetbrains_products:
                linux_paths = [
                    Path(f"/usr/bin/{cmd}"),
                    Path(f"/usr/local/bin/{cmd}"),
                    Path.home() / ".local" / "share" / "JetBrains" / "Toolbox" / "apps",
                ]
                for path in linux_paths:
                    if path.exists():
                        found.append({
                            "name": product_name,
                            "type": "jetbrains",
                            "product": cmd,
                            "path": str(path)
                        })
                        break
        
        self.detected_ides.extend(found)
        return found
    
    def detect_vim(self) -> bool:
        """Vim/Neovim tespiti"""
        vim_found = False
        nvim_found = False
        
        # Vim check
        for path in [Path("/usr/bin/vim"), Path("/usr/local/bin/vim")]:
            if path.exists():
                self.detected_ides.append({
                    "name": "Vim",
                    "type": "vim",
                    "path": str(path)
                })
                vim_found = True
                break
        
        # Neovim check
        for path in [Path("/usr/bin/nvim"), Path("/usr/local/bin/nvim"),
                     Path.home() / "AppData" / "Local" / "nvim"]:
            if path.exists():
                self.detected_ides.append({
                    "name": "Neovim",
                    "type": "neovim",
                    "path": str(path)
                })
                nvim_found = True
                break
        
        return vim_found or nvim_found

    def detect_trae(self) -> bool:
        """Trae IDE (VS Code derivative, AI-first)"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "trae" / "Trae.exe",
            Path("/Applications/Trae.app"),
            Path("/usr/bin/trae"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Trae", "type": "trae", "path": str(path)})
                return True
        return False

    def detect_eclipse_theia(self) -> bool:
        """Eclipse Theia (AI-supported IDE platform)"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "theia" / "Theia.exe",
            Path("/Applications/Eclipse Theia.app"),
            Path("/usr/bin/theia"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Eclipse Theia", "type": "theia", "path": str(path)})
                return True
        return False

    def detect_fleet(self) -> bool:
        """JetBrains Fleet"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "JetBrains" / "Fleet",
            Path("/Applications/Fleet.app"),
            Path.home() / ".local" / "share" / "JetBrains" / "Toolbox" / "apps" / "Fleet",
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "JetBrains Fleet", "type": "fleet", "path": str(path)})
                return True
        return False

    def detect_sublime(self) -> bool:
        """Sublime Text"""
        paths_to_check = [
            Path("C:/Program Files/Sublime Text/sublime_text.exe"),
            Path("C:/Program Files/Sublime Text 3/sublime_text.exe"),
            Path("/Applications/Sublime Text.app"),
            Path("/usr/bin/subl"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Sublime Text", "type": "sublime", "path": str(path)})
                return True
        return False

    def detect_notepadpp(self) -> bool:
        """Notepad++"""
        paths_to_check = [
            Path("C:/Program Files/Notepad++/notepad++.exe"),
            Path("C:/Program Files (x86)/Notepad++/notepad++.exe"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Notepad++", "type": "notepadpp", "path": str(path)})
                return True
        return False

    def detect_eclipse(self) -> bool:
        """Eclipse IDE"""
        paths_to_check = [
            Path("C:/eclipse/eclipse.exe"),
            Path.home() / "eclipse" / "eclipse.exe",
            Path("/Applications/Eclipse.app"),
            Path("/usr/bin/eclipse"),
            Path("/usr/local/bin/eclipse"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Eclipse", "type": "eclipse", "path": str(path)})
                return True
        return False

    def detect_xcode(self) -> bool:
        """Xcode (macOS only)"""
        path = Path("/Applications/Xcode.app")
        if path.exists():
            self.detected_ides.append({"name": "Xcode", "type": "xcode", "path": str(path)})
            return True
        return False

    def detect_visual_studio(self) -> bool:
        """Visual Studio (full IDE, not VS Code)"""
        vs_base = Path("C:/Program Files/Microsoft Visual Studio")
        if vs_base.exists():
            for year in ["2022", "2019", "2017"]:
                for edition in ["Enterprise", "Professional", "Community"]:
                    devenv = vs_base / year / edition / "Common7" / "IDE" / "devenv.exe"
                    if devenv.exists():
                        self.detected_ides.append({
                            "name": f"Visual Studio {year}",
                            "type": "visualstudio",
                            "path": str(devenv)
                        })
                        return True
        return False

    def detect_zed(self) -> bool:
        """Zed editor (AI/editor hybrid)"""
        paths_to_check = [
            Path.home() / "AppData" / "Local" / "Programs" / "Zed" / "Zed.exe",
            Path("/Applications/Zed.app"),
            Path("/usr/bin/zed"),
            Path("/usr/local/bin/zed"),
        ]
        for path in paths_to_check:
            if path.exists():
                self.detected_ides.append({"name": "Zed", "type": "zed", "path": str(path)})
                return True
        return False

    def detect_vscode_extensions(self) -> List[Dict]:
        """VS Code eklentilerini tespit et"""
        extensions = []
        
        # VS Code extension klasorleri
        extension_paths = []
        
        if self.system == "Windows":
            extension_paths = [
                Path.home() / ".vscode" / "extensions",
                Path.home() / "AppData" / "Roaming" / "Code" / "User" / "globalStorage",
            ]
        elif self.system == "Darwin":
            extension_paths = [
                Path.home() / ".vscode" / "extensions",
                Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage",
            ]
        else:  # Linux
            extension_paths = [
                Path.home() / ".vscode" / "extensions",
                Path.home() / ".config" / "Code" / "User" / "globalStorage",
            ]
        
        # Cursor for de ayni yollar (VS Code tabanli)
        cursor_paths = []
        if self.system == "Windows":
            cursor_paths = [
                Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage",
            ]
        elif self.system == "Darwin":
            cursor_paths = [
                Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage",
            ]
        else:
            cursor_paths = [
                Path.home() / ".config" / "Cursor" / "User" / "globalStorage",
            ]
        
        all_paths = extension_paths + cursor_paths
        
        # Known AI extensions (35+ assistants)
        ai_extensions = {
            # Tier 1: Full Native Support
            "github.copilot": "GitHub Copilot",
            "github.copilot-chat": "GitHub Copilot Chat",
            "saoudrizwan.claude-dev": "Cline",
            "kilocode.kilo-code": "Kilo Code",
            "continue.continue": "Continue",

            # Tier 2: Custom Config Support
            "codeium.codeium": "Codeium",
            "tabnine.tabnine-vscode": "Tabnine",
            "amazonwebservices.amazon-q-vscode": "Amazon Q",
            "amazonwebservices.codewhisperer-for-command-line-companion": "CodeWhisperer",
            "blackboxapp.blackbox": "Blackbox AI",

            # Tier 3: Extended Support
            "promptshell.promptshell": "CodeGPT",
            "danielsanmedium.dscodegpt": "CodeGPT (Daniel San)",
            "pieces.pieces-vscode": "Pieces for Developers",
            "aminer.codegeex": "CodeGeeX",
            "sourcegraph.cody-ai": "Sourcegraph Cody",
            "supermaven.supermaven": "Supermaven",
            "codium.codium": "CodiumAI",
            "codiumai.codiumate": "CodiumAI Codiumate",
            "mintlify.document": "Mintlify Doc Writer",
            "askcodi.askcodi": "AskCodi",
            "sourcery.sourcery": "Sourcery",
            "fauxpilot.fauxpilot": "FauxPilot",

            # Tier 4: New AI Assistants (2025-2026)
            "rooveterinaryinc.roo-cline": "Roo Code",
            "smallcloudai.refact": "Refact.ai",
            "maboroshi.mutableai": "MutableAI",
            "codiga.codiga": "Codiga",
            "visualstudioexptteam.vscodeintellicode": "Intellicode",
            "deepseekai.deepseek-coder": "DeepSeek Coder",
            "qodo.qodo-gen": "Qodo Gen",
            "replit.replit": "Replit Ghostwriter",

            # Terminal/External AI
            "warp.warp-terminal": "Warp Terminal AI",
        }
        
        for ext_path in all_paths:
            if ext_path.exists():
                for folder in ext_path.iterdir():
                    if folder.is_dir():
                        ext_id = folder.name.split("-")[0]  # publisher.name-1.2.3 formati
                        if ext_id in ai_extensions:
                            extensions.append({
                                "name": ai_extensions[ext_id],
                                "id": ext_id,
                                "type": "vscode_extension",
                                "path": str(folder)
                            })
        
        self.detected_plugins.extend(extensions)
        return extensions
    
    def detect_jetbrains_plugins(self) -> List[Dict]:
        """JetBrains eklentilerini tespit et"""
        plugins = []
        
        # JetBrains plugin klasorleri
        plugin_paths = []
        
        if self.system == "Windows":
            base_path = Path.home() / "AppData" / "Roaming" / "JetBrains"
        elif self.system == "Darwin":
            base_path = Path.home() / "Library" / "Application Support" / "JetBrains"
        else:
            base_path = Path.home() / ".local" / "share" / "JetBrains"
        
        if base_path.exists():
            for product_folder in base_path.iterdir():
                if product_folder.is_dir():
                    plugins_folder = product_folder / "plugins"
                    if plugins_folder.exists():
                        plugin_paths.append(plugins_folder)
        
        # Bilinen AI eklentileri
        ai_plugins = {
            "github-copilot": "GitHub Copilot (JetBrains)",
            "ai-assistant": "JetBrains AI Assistant",
            "codeium": "Codeium (JetBrains)",
            "tabnine": "Tabnine (JetBrains)",
            "continue": "Continue (JetBrains)",
            "codewhisperer": "Amazon CodeWhisperer (JetBrains)",
            "amazonq": "Amazon Q (JetBrains)",
            "cody": "Sourcegraph Cody (JetBrains)",
            "supermaven": "Supermaven (JetBrains)",
        }
        
        for plugin_path in plugin_paths:
            for folder in plugin_path.iterdir():
                if folder.is_dir():
                    plugin_name = folder.name.lower()
                    for key, value in ai_plugins.items():
                        if key in plugin_name:
                            plugins.append({
                                "name": value,
                                "id": key,
                                "type": "jetbrains_plugin",
                                "path": str(folder)
                            })
        
        self.detected_plugins.extend(plugins)
        return plugins
    
    def detect_all(self, silent: bool = False, force_global: bool = False) -> Tuple[List[Dict], List[Dict]]:
        """Tum IDElari ve eklentileri tespit et"""
        if not silent:
            print("[SCAN] Active IDE Context Evaluation...")
            print()
            
        active_ide = self.detect_active_ide()
        if active_ide and not force_global:
            if not silent:
                print(f"[IDE] Using active IDE context: {active_ide}")
            self.detected_ides.append({"name": active_ide.title(), "type": active_ide, "path": "active_session"})
            # Detect extensions only for the active IDE family if needed
            if active_ide in ["vscode", "cursor", "windsurf", "cline"]:
                self.detect_vscode_extensions()
            elif active_ide == "jetbrains":
                self.detect_jetbrains_plugins()
                
            if not silent:
                print(f"[OK] Bound to {active_ide.title()}. Skipping global OS scan to prevent workspace pollution.")
            return self.detected_ides, self.detected_plugins

        if not silent:
            print("[IDE] Detecting IDEs globally...")
        self.detect_vscode()
        self.detect_cursor()
        self.detect_windsurf()
        self.detect_jetbrains()
        self.detect_vim()
        self.detect_trae()
        self.detect_eclipse_theia()
        self.detect_fleet()
        self.detect_sublime()
        self.detect_notepadpp()
        self.detect_eclipse()
        self.detect_xcode()
        self.detect_visual_studio()
        self.detect_zed()
        
        if not silent:
            if self.detected_ides:
                print(f"[OK] Detected {len(self.detected_ides)} IDE(s):")
                for ide in self.detected_ides:
                    print(f"   - {ide['name']}")
            else:
                print("[WARN] No IDEs detected")
            
            print()
        
        # Eklentileri tespit et
        if not silent:
            print("[EXT] Detecting AI extensions/plugins...")
        self.detect_vscode_extensions()
        self.detect_jetbrains_plugins()
        
        if not silent:
            if self.detected_plugins:
                print(f"[OK] Detected {len(self.detected_plugins)} AI extension(s)/plugin(s):")
                for plugin in self.detected_plugins:
                    print(f"   - {plugin['name']}")
            else:
                print("[INFO] No AI extensions/plugins detected (manual installation may be required)")
        
        return self.detected_ides, self.detected_plugins
    
    def configure_vscode(self, project_root: Path, create_missing: bool = False, silent: bool = False) -> bool:
        """VS Code yapilandirmasi"""
        vscode_dir = project_root / ".vscode"
        if not vscode_dir.exists():
            if not create_missing:
                return False
            vscode_dir.mkdir(exist_ok=True)
        
        # Copilot ve diger eklentiler for settings.json
        settings = {
            "github.copilot.chat.codeGeneration.instructions": [
                {
                    "text": "Use BBC (Bitter Brain Context) - Read bbc_context.json first, only use verified symbols from code_structure. Never hallucinate functions."
                }
            ]
        }
        
        # Diger eklentiler for ozel ayarlar
        for plugin in self.detected_plugins:
            if plugin["type"] == "vscode_extension":
                if plugin["id"] == "continue.continue":
                    settings["continue"] = {
                        "enableTabAutocomplete": True,
                        "customInstructions": "Use BBC context. Read bbc_context.json before generating code."
                    }
                elif plugin["id"] == "codeium.codeium":
                    settings["codeium"] = {
                        "enableExplain": True,
                        "customInstructions": "BBC Mode: Only use verified symbols from bbc_context.json"
                    }
        
        settings_file = vscode_dir / "settings.json"
        
        try:
            # Mevcut ayarlari koru
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                for key, val in settings.items():
                    if key not in existing:
                        existing[key] = val
                settings = existing
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            self.configs_created.append(".vscode/settings.json (VS Code)")
            return True
        except Exception as e:
            if not silent:
                print(f"[ERROR] VS Code configuration error: {e}")
            return False
    
    def configure_cursor(self, project_root: Path, create_missing: bool = False, silent: bool = False) -> bool:
        """Cursor yapilandirmasi"""
        cursorrules = project_root / ".cursorrules"
        if cursorrules.exists():
            self.configs_created.append(".cursorrules (Cursor) - Zaten var")
            return True
        if not create_missing:
            return False
        return False
    
    def configure_jetbrains(self, project_root: Path, ide_info: Dict, create_missing: bool = False, silent: bool = False) -> bool:
        """JetBrains yapilandirmasi"""
        idea_dir = project_root / ".idea"
        if not idea_dir.exists():
            if not create_missing:
                return False
            idea_dir.mkdir(exist_ok=True)
        
        # AI Assistant ve diger eklentiler for XML config
        ai_assistant_present = any(
            p["type"] == "jetbrains_plugin" and "AI Assistant" in p["name"]
            for p in self.detected_plugins
        )
        
        copilot_present = any(
            p["type"] == "jetbrains_plugin" and "Copilot" in p["name"]
            for p in self.detected_plugins
        )
        
        plugins_list = []
        if ai_assistant_present:
            plugins_list.append("<option value=\"JetBrains AI Assistant - Use BBC context\" />")
        if copilot_present:
            plugins_list.append("<option value=\"GitHub Copilot - Read bbc_context.json first\" />")
        
        plugins_xml = "\n        ".join(plugins_list)
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="BBCAIAssistant">
    <option name="enabled" value="true" />
    <option name="useRecipeContext" value="true" />
    <option name="recipePath" value="bbc_context.json" />
    <option name="instructions">
      <list>
        <option value="Read bbc_context.json before generating code" />
        <option value="Only use verified symbols from code_structure" />
        <option value="Never hallucinate functions not in recipe" />
        {plugins_xml}
      </list>
    </option>
  </component>
</project>"""
        
        try:
            ai_config = idea_dir / "bbc-ai-assistant.xml"
            with open(ai_config, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            self.configs_created.append(f".idea/bbc-ai-assistant.xml ({ide_info['name']})")
            return True
        except Exception as e:
            if not silent:
                print(f"[ERROR] JetBrains configuration error: {e}")
            return False
    
    def configure_vim(self, project_root: Path, create_missing: bool = False, silent: bool = False) -> bool:
        """Vim/Neovim yapilandirmasi"""
        vim_config = project_root / ".bbc-vim-config"

        if not create_missing and not vim_config.exists():
            return False
        
        # Tespit edilen eklentilere gore icerik
        copilot_vim = any("copilot" in p["name"].lower() for p in self.detected_plugins)
        
        vim_content = """" BBC HMPU v7.2 - Vim/Neovim Configuration
" Before using AI assistance, read bbc_context.json
" Only use functions listed in code_structure
" Never hallucinate new symbols

let g:bbc_enabled = 1
let g:bbc_context_path = 'bbc_context.json'
"""
        
        if copilot_vim:
            vim_content += """
" GitHub Copilot BBC Integration
let g:copilot_filetypes = {'*': v:true}
autocmd BufRead * let b:copilot_enabled = 1
"""
        
        try:
            with open(vim_config, 'w', encoding='utf-8') as f:
                f.write(vim_content)
            self.configs_created.append(".bbc-vim-config (Vim/Neovim)")
            return True
        except Exception as e:
            if not silent:
                print(f"[ERROR] Vim configuration error: {e}")
            return False
    
    def configure_all(self, project_root: str = ".", create_missing: bool = False, silent: bool = False) -> List[str]:
        """Tespit edilen all IDElari ve eklentileri yapilandir"""
        root = Path(project_root).resolve()
        if not silent:
            print(f"\n[CONFIG] Configuration starting: {root}")
        
        for ide in self.detected_ides:
            ide_type = ide['type']
            
            if ide_type == 'vscode':
                self.configure_vscode(root, create_missing=create_missing, silent=silent)
            elif ide_type == 'cursor':
                self.configure_cursor(root, create_missing=create_missing, silent=silent)
            elif ide_type == 'jetbrains':
                self.configure_jetbrains(root, ide, create_missing=create_missing, silent=silent)
            elif ide_type in ('vim', 'neovim'):
                self.configure_vim(root, create_missing=create_missing, silent=silent)
        
        return self.configs_created
    
    def print_summary(self):
        """Ozet rapor"""
        print("\n" + "="*60)
        print("BBC v8.3 - IDE and Extension Configuration Summary")
        print("="*60)
        
        if self.detected_ides:
            print(f"\n[OK] Detected {len(self.detected_ides)} IDE(s):")
            for ide in self.detected_ides:
                print(f"   - {ide['name']}")
        
        if self.detected_plugins:
            print(f"\n[OK] Detected {len(self.detected_plugins)} AI extension(s)/plugin(s):")
            for plugin in self.detected_plugins:
                print(f"   - {plugin['name']}")
        
        if self.configs_created:
            print(f"\n[FILE] Created {len(self.configs_created)} configuration file(s):")
            for config in self.configs_created:
                print(f"   - {config}")
        else:
            print("\n[WARN] No configuration files were created")
        
        print("\n[TIP] Your IDEs and extensions can now use BBC automatically")
        print("="*60)

def main():
    """Ana fonksiyon"""
    print("BBC v8.3 - Automatic IDE and Extension Configuration")
    print("="*60)
    
    configurator = IDEAutoConfigurator()
    
    # IDElari ve eklentileri tespit et
    configurator.detect_all()
    
    # Yapilandir
    if configurator.detected_ides:
        configurator.configure_all()
        configurator.print_summary()
    else:
        print("\n[WARN] No IDE detected for configuration")
        print("[DOC] For manual setup: IDE_SETUP_README.md")
    
    return len(configurator.detected_ides)

if __name__ == "__main__":
    sys.exit(main())
