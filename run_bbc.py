# BBC-VALIDATED/v8.3 (STABLE)
# --- 1. ORTAM KONTROLU ---
import os
import sys
import platform
import json

# Platform tespiti
PLATFORM = platform.system().lower()
PYTHON_CMD = "python" if PLATFORM == "windows" else "python3"

# Windows color fix (required for CMD/Powershell)
if os.name == 'nt':
    os.system('')

# Find script directory (project root where bbc_core lives)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add script directory to sys.path (bbc_core should be here)
if script_dir not in sys.path: sys.path.insert(0, script_dir)

# --- 2. MOTOR YÜKLEME (bbc_core) ---
try:
    from bbc_core.cli import main as run_engine_cli
except ImportError:
    def run_engine_cli():
        print(f"\033[31m[CRITICAL] BBC Engine (bbc_core) not found in '{script_dir}'\033[0m")


# --- 3. GHOST FEATURES ACTIVATION ---
def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def run_post_analysis_checks(project_path=".", emit_console: bool = False):
    """Analiz sonrası tüm BBC doğrulama ve stabilite kontrollerini çalıştırır."""
    # 1. Verifier — Syntax & Structural Integrity
    try:
        from bbc_core.verifier import BBCVerifier
        from bbc_core.config import BBCConfig

        ctx_path = BBCConfig.get_context_path(project_path)
        if os.path.exists(ctx_path):
            verifier = BBCVerifier(ctx_path)
            errors = verifier.verify_syntax_only()

            # Persist verifier summary so feature remains active even when terminal output is suppressed.
            try:
                with open(ctx_path, "r", encoding="utf-8") as f:
                    ctx = json.load(f)
                ctx.setdefault("metrics", {})
                ctx["metrics"]["post_verify_syntax_errors"] = len(errors)
                ctx["metrics"]["post_verify_checked"] = True
                ctx["metrics"]["post_verify_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                with open(ctx_path, "w", encoding="utf-8") as f:
                    json.dump(ctx, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            if emit_console:
                if errors:
                    print(f"\n\033[33m[!] BBC Verifier: Found {len(errors)} potential logic issues.\033[0m")
                else:
                    print(f"\n\033[32m[OK] BBC Verifier: Project structural integrity confirmed.\033[0m")
    except Exception: pass

    # 2. Symbol Pipeline — Verify symbols are extracted
    if emit_console:
        try:
            from bbc_core.config import BBCConfig
            ctx_path = BBCConfig.get_context_path(project_path)
            if os.path.exists(ctx_path):
                with open(ctx_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Support both legacy symbol_analysis key and current code_structure list
                sa = data.get("symbol_analysis")
                if sa and isinstance(sa, dict):
                    total = sa.get("total_symbols", 0)
                    calls = sa.get("total_calls", 0)
                else:
                    # Current format: code_structure is a list of per-file objects
                    cs = data.get("code_structure", [])
                    total = sum(len(f.get("structure", {}).get("classes", [])) +
                                len(f.get("structure", {}).get("functions", [])) for f in cs)
                    calls = sum(len(f.get("structure", {}).get("imports", [])) for f in cs)
                if total > 0:
                    print(f"\033[32m[OK] Symbol Pipeline: {total} symbols, {calls} imports\033[0m")
                else:
                    print("\033[33m[!] Symbol Pipeline: No symbols found\033[0m")
        except Exception:
            pass

# --- 4. ARGUMENT HELPER ---
def _resolve_project_path():
    """sys.argv'den hedef proje yolunu çıkar, yoksa '.' kullan."""
    for arg in sys.argv[2:]:
        if not arg.startswith("-") and os.path.isdir(arg):
            return arg
    return "."

# --- 5. MAIN EXECUTION ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        try:
            run_engine_cli()

            # Post-Analysis Ghost Features
            if command in ["analyze", "bootstrap", "inject"]:
                show_post_verify = _env_flag("BBC_SHOW_POST_VERIFY", default=False)
                run_post_analysis_checks(_resolve_project_path(), emit_console=show_post_verify)

        except SystemExit: pass
        except Exception as e:
            print(f"Engine Error: {e}")
