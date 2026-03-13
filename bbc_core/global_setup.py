"""
BBC Global Setup — v8.3
OS seviyesinde global IDE kuralları oluşturma.

bbc start çalıştığında otomatik olarak tetiklenir.
Kullanıcının ek bir komut çalıştırmasına gerek yoktur.

Windows: %APPDATA%\\BBC\\global_rules\\
Linux/Mac: ~/.config/bbc/global_rules/

Bu kurallar MÜŞTERİ projesine değil, OS seviyesinde config dizinine yazılır.
Böylece henüz bbc start çalıştırılmamış projelerde bile
IDE'ler BBC'nin temel kurallarını bilir.
"""
import os
import json
import platform
import pathlib


def get_global_rules_dir() -> pathlib.Path:
    """
    OS'a göre global BBC kural dizinini döndür.

    Windows: %APPDATA%\\BBC\\global_rules
    macOS:   ~/.config/bbc/global_rules
    Linux:   ~/.config/bbc/global_rules
    """
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return pathlib.Path(appdata) / "BBC" / "global_rules"
        return pathlib.Path.home() / "AppData" / "Roaming" / "BBC" / "global_rules"
    else:
        return pathlib.Path.home() / ".config" / "bbc" / "global_rules"


def is_setup_done() -> bool:
    """Global kurulum zaten yapılmış mı kontrol et."""
    rules_dir = get_global_rules_dir()
    marker = rules_dir / ".bbc_global_setup_done"
    return marker.exists()


def generate_rules(target_dir_str=None, force=False):
    """
    OS seviyesinde global IDE kural dosyalarını oluştur.

    Args:
        target_dir_str: Hedef dizin (None ise OS'a göre otomatik belirlenir)
        force: True ise zaten kurulmuş olsa bile yeniden oluştur

    Returns:
        str: Oluşturulan dizin yolu veya None (zaten kuruluysa)
    """
    if target_dir_str is None:
        target_dir = get_global_rules_dir()
    else:
        target_dir = pathlib.Path(target_dir_str)

    # Zaten kurulmuşsa atla (force=True değilse)
    marker = target_dir / ".bbc_global_setup_done"
    if marker.exists() and not force:
        return None

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. AI Context — BBC kimlik bilgisi
    ai_context = {
        "system": "BBC (Bitter Brain Context)",
        "version": "8.3",
        "enforcement": "STRICT",
        "rules_source": str(target_dir),
        "core_rules": [
            "Always read bbc_context.json before generating code",
            "Only use symbols verified in code_structure",
            "Never hallucinate functions, classes, or imports",
            "Respect BBC sealed blocks — do not modify sealed code",
            "Run `python run_bbc.py audit .` before commits"
        ]
    }
    (target_dir / "ai-context.json").write_text(
        json.dumps(ai_context, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 2. Cursor Rules — Cursor IDE global kuralları
    cursor_rules = """# BBC Global Rules — Cursor IDE
# These rules apply to ALL projects when BBC is active.

## Core Principles
1. **Context First**: Always read `bbc_context.json` before generating code.
2. **No Hallucination**: Only use symbols present in `code_structure`.
3. **Verification**: If a symbol is missing from context, respond: "Not in BBC context".
4. **Sealed Code**: Never modify code blocks marked as BBC sealed.
5. **Validation**: Run `python run_bbc.py audit .` before commits.

## Workflow
- Check `.context/bbc_context.md` for project structure overview.
- Check `.agent/rules/bbc_rules.md` for project-specific rules.
- Use `bbc_context.json` for detailed symbol and dependency information.
"""
    (target_dir / ".cursorrules").write_text(cursor_rules, encoding="utf-8")

    # 3. Windsurf Rules — Windsurf IDE global kuralları
    windsurf_rules = """# BBC Global Rules — Windsurf IDE

## Architecture
- Project structure is defined in `bbc_context.json`.
- Code structure summary is in `.context/bbc_context.md`.
- Enforcement: STRICT — no unauthorized modifications.

## Rules
1. Read `bbc_context.json` as the single source of truth.
2. Only use verified symbols from `code_structure`.
3. Never hallucinate functions, classes, or file paths.
4. Respect sealed blocks and project boundaries.
"""
    (target_dir / ".windsurfrules").write_text(windsurf_rules, encoding="utf-8")

    # 4. Copilot Instructions — GitHub Copilot global talimatları
    copilot_instructions = """# BBC Global Instructions — GitHub Copilot

You are a BBC-compliant AI coding assistant.

## Before generating any code:
1. Check if `bbc_context.json` exists in the project root.
2. If it exists, read `code_structure` to understand available symbols.
3. Only suggest code using verified classes, functions, and imports.

## Strict Rules:
- **Never** invent functions that don't exist in the codebase.
- **Never** import modules not listed in the project dependencies.
- **Always** check `bbc_context.json` for the correct function signatures.
- If uncertain, say: "Not verified in BBC context."
"""
    (target_dir / "copilot-instructions.md").write_text(copilot_instructions, encoding="utf-8")

    # 5. BBC Master Rules — Evrensel BBC kuralları
    bbc_rules = """# BBC Master Rules — v8.3

## Non-Negotiable Rules
1. **No unauthorized deletion** — Never delete files without explicit user confirmation.
2. **No hallucination** — Only use symbols verified in `bbc_context.json`.
3. **Validate all changes** — Run `python run_bbc.py audit .` after modifications.
4. **Context is king** — `bbc_context.json` is the single source of truth.
5. **Sealed blocks** — Code marked with BBC seals must not be modified.

## Global Impact Analysis (GIA)
Before making any change, consider:
- **Scope**: Which files will change?
- **Dependencies**: Which modules/functions could be affected?
- **Risk**: What are the possible side effects?

## Workflow
1. Read `bbc_context.json` → understand the project
2. Generate code using ONLY verified symbols
3. Run audit → verify no regressions
"""
    (target_dir / "bbc_rules.md").write_text(bbc_rules, encoding="utf-8")

    # Kurulum tamamlandı marker'ı oluştur
    marker.write_text(
        json.dumps({"installed_at": __import__("datetime").datetime.now().isoformat(), "version": "8.3"}),
        encoding="utf-8"
    )

    print(f"   [+] BBC global rules installed → {target_dir}")
    return str(target_dir)


def configure_vscode(global_rules_path=None):
    """
    VS Code'un global BBC kurallarını bulması için bilgi ver.
    Gerçek uygulamada %APPDATA%/Code/User/settings.json düzenlenir.
    """
    if global_rules_path is None:
        global_rules_path = str(get_global_rules_dir())
    print(f"   [i] VS Code: Add 'bbc.globalRulesPath': '{global_rules_path}' to User Settings.")
