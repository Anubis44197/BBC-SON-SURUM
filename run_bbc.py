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

# --- 2. VISUAL LIBRARY CHECK ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_INSTALLED = True
except ImportError:
    RICH_INSTALLED = False

# --- 3. MOTOR YÜKLEME (bbc_core) ---
try:
    from bbc_core.cli import main as run_engine_cli
except ImportError:
    def run_engine_cli():
        print(f"\033[31m[CRITICAL] BBC Engine (bbc_core) not found in '{script_dir}'\033[0m")


# --- 4. GHOST FEATURES ACTIVATION ---
def run_post_analysis_checks(project_path="."):
    """Analiz sonrası tüm BBC doğrulama ve stabilite kontrollerini çalıştırır."""
    # 1. Verifier — Syntax & Structural Integrity
    try:
        from bbc_core.verifier import BBCVerifier
        from bbc_core.config import BBCConfig

        ctx_path = BBCConfig.get_context_path(project_path)
        if os.path.exists(ctx_path):
            verifier = BBCVerifier(ctx_path)
            errors = verifier.verify_syntax_only()
            if errors:
                print(f"\n\033[33m[!] BBC Verifier: Found {len(errors)} potential logic issues.\033[0m")
            else:
                print(f"\n\033[32m[OK] BBC Verifier: Project structural integrity confirmed.\033[0m")
    except Exception: pass

    # 2. Telemetry Matrix — Operational Stability
    try:
        from _analyze_telemetry_matrix import analyze as telemetry_analyze
        telemetry_analyze()
    except Exception: pass

    # 3. Symbol Pipeline — Verify symbols are extracted
    try:
        from bbc_core.config import BBCConfig
        ctx_path = BBCConfig.get_context_path(project_path)
        if os.path.exists(ctx_path):
            with open(ctx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sa = data.get("symbol_analysis", {})
            total = sa.get("total_symbols", 0)
            calls = sa.get("total_calls", 0)
            critical = len(sa.get("critical_symbols", []))
            if total > 0:
                print(f"\033[32m[OK] Symbol Pipeline: {total} symbols, {calls} calls, {critical} critical\033[0m")
            else:
                print(f"\033[33m[!] Symbol Pipeline: No symbols found\033[0m")
    except Exception: pass

# --- 5. TRANSACTION REPORT (MODERN GAUGE v8.3) ---
def _resolve_project_path():
    """sys.argv'den hedef proje yolunu çıkar, yoksa '.' kullan."""
    for arg in sys.argv[2:]:
        if not arg.startswith("-") and os.path.isdir(arg):
            return arg
    return "."


def print_transaction_report():
    """
    Print a deep-data visual report with cost savings and Aura stability.
    """
    tokens_used = 0
    token_savings = 0
    tokens_mode = "Aura-v8.3"
    savings_confidence = 0.0
    baseline_tokens = 0
    files_count = 0
    aura_state = "STABLE"
    stability_score = 0.0

    # 1. DATA EXTRACTION
    try:
        from bbc_core.config import BBCConfig
        project_path = _resolve_project_path()
        ctx_path = BBCConfig.get_context_path(project_path)
        if os.path.exists(ctx_path):
            with open(ctx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metrics = data.get("metrics", {})
            files_count = metrics.get("files_scanned", 0)

            tokens_used = metrics.get("unified_tokens_used", 0)
            token_savings = metrics.get("unified_tokens_saved", 0)
            savings_confidence = metrics.get("unified_savings_confidence", 0.0)
            baseline_tokens = metrics.get("unified_tokens_normal", tokens_used + token_savings)

            # Mathematical Stability Check
            from bbc_core.hmpu_core import HMPU_Governor
            gov = HMPU_Governor()
            stability_score = gov.get_field_stability()
            if stability_score < 10.0: aura_state = "STABLE"
            elif stability_score < 25.0: aura_state = "WEAK"
            else: aura_state = "UNSTABLE"
    except Exception: pass

    # 2. CALCULATE DEEP METRICS
    savings_pct = (token_savings / baseline_tokens * 100) if baseline_tokens > 0 else 0
    cost_saved = (token_savings / 1000) * 0.03  # GPT-4 average input cost
    efficiency_factor = baseline_tokens / tokens_used if tokens_used > 0 else 1.0

    # 3. VISUAL RENDERING (RICH)
    if RICH_INSTALLED:
        console = Console()

        # Color Logic
        color = "green"
        state_icon = "🟢"
        if aura_state == "STABLE":
            color = "bright_magenta"
            state_icon = "💎"
        elif aura_state == "WEAK":
            color = "yellow"
            state_icon = "🟡"
        else:
            color = "red"
            state_icon = "🔴"

        # Bar Construction
        gauge_width = 50
        filled = int((savings_pct / 100) * gauge_width)
        bar = f"[{color}]{'█' * filled}[/][dim]{'░' * (gauge_width - filled)}[/]"

        # Final Panel
        summary = (
            f"[bold {color}]BBC HMPU v8.3 Aura Insights[/] {state_icon} [bold {color}]{aura_state}[/]\n"
            f"{bar} [bold]{savings_pct:.1f}%[/]\n"
            f"[white]Saved:[/][bold green] {token_savings:,} Tokens [/][white]|[/][bold yellow] ${cost_saved:.2f} [/][white]|[/][bold cyan] {efficiency_factor:.1f}x Faster[/]\n"
            f"[dim]Stability: {stability_score:.2f} (Cond) | Confidence: {savings_confidence:.0%} | Files: {files_count}[/]"
        )

        try:
            console.print(Panel(summary, expand=False, border_style=color, padding=(1, 2)))
        except Exception:
            print(f"\n[BBC v8.3] {aura_state} | Savings: {savings_pct:.1f}% | Saved: {token_savings:,} Tokens")
    else:
        print(f"\n[BBC v8.3] {aura_state} | Savings: {savings_pct:.1f}% | Saved: {token_savings:,} Tokens")

# --- 6. MAIN EXECUTION ---
if __name__ == "__main__":
    should_print_report = False

    if len(sys.argv) > 1:
        command = sys.argv[1]

        # Start Real-Time Counter if needed
        try:
            from bbc_core.realtime_token_counter import start_monitoring
            start_monitoring()
        except Exception: pass

        should_print_report = True
        try:
            run_engine_cli()

            # Post-Analysis Ghost Features
            if command in ["analyze", "bootstrap", "inject"]:
                run_post_analysis_checks(_resolve_project_path())

        except SystemExit: pass
        except Exception as e:
            print(f"Engine Error: {e}")

        # End Real-Time Counter
        try:
            from bbc_core.realtime_token_counter import end_monitoring
            end_monitoring()
        except Exception: pass

    if should_print_report:
        print_transaction_report()
