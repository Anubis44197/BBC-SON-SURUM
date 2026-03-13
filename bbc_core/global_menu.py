import os
import sys
import json
import subprocess

# --- WINDOWS ENCODING FIX ---
# Bu blok, konsol CP1254 olsa bile Python'un UTF-8 basmasini zorlar.
if sys.platform == 'win32':
    try:
        # Python 3.7+
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Eski Python surumleri icin fallback
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
# -----------------------------

def load_token_stats(project_path):
    try:
        ctx_path = os.path.join(project_path, '.bbc', 'bbc_context.json')
        if os.path.exists(ctx_path):
            with open(ctx_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                metrics = data.get('metrics', {})
                unified_used = metrics.get('unified_tokens_used')
                unified_saved = metrics.get('unified_tokens_saved')
                unified_normal = metrics.get('unified_tokens_normal')
                status = metrics.get('unified_status', 'IDLE')
                source = metrics.get('unified_source', 'analyze')

                if unified_used is not None and unified_saved is not None:
                    savings = int(unified_saved)
                    normal = int(unified_normal) if unified_normal is not None else int(unified_used) + int(unified_saved)
                    percent = metrics.get('unified_savings_pct')
                    if percent is None:
                        percent = (savings / normal * 100) if normal > 0 else 0.0
                    return savings, float(percent), status, source

                raw = metrics.get('raw_tokens')
                optimized = metrics.get('context_tokens')
                if raw is None or optimized is None:
                    return 0, 0.0, status, source
                savings = int(raw) - int(optimized)
                percent = metrics.get('savings_pct', 0.0)
                return savings, float(percent), status, source
    except Exception:
        pass
    return 0, 0.0, 'IDLE', 'none'

def main(project_path, loop: bool = False):
    # BBC home directory (where run_bbc.py lives)
    bbc_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_bbc_script = os.path.join(bbc_home, "run_bbc.py")
    python_exe = sys.executable

    context_file = os.path.join(project_path, ".bbc", "bbc_context.json")

    while True:
        print("")
        print("=" * 62)
        savings, savings_pct, status, source = load_token_stats(project_path)

        print("  BBC GLOBAL - PROJECT INTERFACE")
        print("=" * 62)
        print(f"  [STATUS]  {status}")
        print(f"  [SOURCE]  {source}")
        if savings > 0:
            print(f"  [COMPRESS] {savings:,} tokens ({savings_pct:.1f}%) reduction")
        else:
            print(f"  [COMPRESS] N/A (run Analyze first)")
        print(f"  [TARGET]  {project_path}")
        print("-" * 62)
        print("  [1] ANALYZE   (Re-analyze project)")
        print("  [2] VERIFY    (Validate project before commit)")
        print("  [3] PURGE     (Remove BBC from project)")
        print("  [0] EXIT")
        print("-" * 62)

        choice = input("  Select option: ").strip()

        if choice == '1':
            print("\n  [*] Analyzing project...")
            subprocess.call([python_exe, run_bbc_script, "analyze", project_path, "--out", context_file])
            if os.environ.get("BBC_MENU_AUTO_INJECT", "0") == "1":
                print("\n  [*] Injecting AI configurations...")
                subprocess.call([python_exe, run_bbc_script, "inject", project_path, "--allow-stale"])
            else:
                print("\n  [INFO] Skipping AI config injection (BBC_MENU_AUTO_INJECT=0)")
            if loop:
                input("\n  [DONE] Press Enter to return...")
            else:
                return

        elif choice == '2':
            print("\n  [*] Validating for Git...")
            recipe_path = context_file
            if not os.path.exists(recipe_path):
                print("  [!] bbc_context.json not found. Run Analyze first.")
                if loop:
                    input("  Press Enter to return...")
                    continue
                return
            subprocess.call([python_exe, run_bbc_script, "verify", recipe_path])
            if loop:
                input("\n  [DONE] Press Enter to return...")
            else:
                return

        elif choice == '3':
            confirm = input("\n  [!] WARNING: Remove all BBC traces? (y/n): ")
            if confirm.lower() == 'y':
                subprocess.call([python_exe, run_bbc_script, "purge", project_path, "--force"])
                print("\n  [INFO] Project purged.")
                if loop:
                    input("  Press Enter...")
            if not loop:
                return

        elif choice == '0':
            print("  [BBC] Exiting...")
            return

        if not loop:
            return

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        # Debug modu: Eger arguman yoksa mevcut klasoru kullan
        main(os.getcwd())