import os
import json
import argparse
import asyncio
import sys
import time
from typing import Any, Dict

# Ensure bbc_core can be imported if run from root
sys.path.append(os.getcwd())

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from bbc_core.native_adapter import BBCNativeAdapter
from bbc_core.bbc_scalar import BBCEncoder
from bbc_core.config import BBCConfig

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base encoding for GPT-4/Copilot)"""
    if not TIKTOKEN_AVAILABLE:
        # Fallback to rough estimate
        return len(text) // 4
    
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


class BBCCLI:
    def __init__(self):
        self.adapter = BBCNativeAdapter()

    async def run_analysis(self, target_path, output_file, silent: bool = False):
        target_path = os.path.abspath(target_path)
        
        # Save context inside .bbc/ isolation directory
        if output_file == "bbc_context.json":
            output_file = BBCConfig.get_context_path(target_path)
        else:
            output_file = os.path.abspath(output_file)

        if not os.path.exists(target_path):
            print(f"Error: Path does not exist: {target_path}")
            sys.exit(1)

        if not silent:
            print(f"[*] Starting Analysis: {target_path}")
        
        # Start timing
        start_time = time.time()
        context = await self.adapter.analyze_project(target_path, output_file=output_file, silent=silent)
        
        # Metrics alignment with Phase 10.1 specification
        # The adapter already produces a context dict, we just need to confirm structure
        # context["metrics"] is expected to have files_scanned, raw_bytes, context_bytes, compression_ratio
        
        # Ensure the output is saved to the CWD (where command is run)
        # output_file is already relative or absolute as provided by argparse
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False, cls=BBCEncoder)

        try:
            _write_project_snapshot(target_path, output_file)
        except Exception as e:
            print(f"[WARN] Snapshot write skipped: {e}", file=sys.stderr)
        
        if not silent:
            print(f"[+] Analysis complete. Context saved to: {os.path.abspath(output_file)}")
        m = context.get("metrics", {})

        # Read actual file contents for token counting (always, regardless of silent mode)
        raw_content = ""
        context_content = ""
        
        try:
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ["node_modules", ".venv", "dist", "build", ".git", "__pycache__"]]
                for file in files:
                    if file.lower().endswith(('.py', '.md', '.json', '.js', '.ts', '.html', '.css', '.log', '.sql', '.rs', '.go', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                raw_content += f.read() + "\n"
                        except Exception:
                            continue
        except Exception as e:
            if not silent:
                print(f"[WARN] Raw content read error: {e}", file=sys.stderr)
        
        # Read context JSON
        try:
            context_content = json.dumps(context, ensure_ascii=False)
        except Exception:
            context_content = str(context)
        
        # Count tokens with tiktoken
        raw_tokens = count_tokens(raw_content) if raw_content else m.get('raw_bytes', 0) // 4
        context_tokens = count_tokens(context_content)
        saved_tokens = raw_tokens - context_tokens
        savings_pct = (saved_tokens / raw_tokens * 100) if raw_tokens > 0 else 0
        
        # Persist token metrics into bbc_context.json so other tools can read them
        context.setdefault("metrics", {})
        context["metrics"]["raw_tokens"] = raw_tokens
        context["metrics"]["context_tokens"] = context_tokens
        context["metrics"]["savings_pct"] = round(savings_pct, 1)
        context["metrics"]["unified_tokens_used"] = context_tokens
        context["metrics"]["unified_tokens_saved"] = max(0, saved_tokens)
        context["metrics"]["unified_tokens_normal"] = raw_tokens
        context["metrics"]["unified_savings_pct"] = round(savings_pct, 1)
        context["metrics"]["unified_savings_confidence"] = m.get("unified_savings_confidence", 0.95)
        context["metrics"]["unified_status"] = "IDLE"
        context["metrics"]["unified_source"] = "analyze"
        context["metrics"]["unified_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False, cls=BBCEncoder)
        except Exception as e:
            print(f"[WARN] Metrics persist error: {e}", file=sys.stderr)
        
        # Calculate time
        bbc_time = time.time() - start_time
        
        # Calculate symbols from code_structure
        total_classes = 0
        total_functions = 0
        total_imports = 0
        code_structure = context.get("code_structure", [])
        for item in code_structure:
            if isinstance(item, dict):
                structure = item.get("structure", {})
                total_classes += len(structure.get("classes", []))
                total_functions += len(structure.get("functions", []))
                total_imports += len(structure.get("imports", []))
        
        if not silent:
            # Visual output - NEW DESIGN
            print(f"\n{'='*70}")
            print(f">>> BBC ANALYSIS COMPLETE")
            print(f"{'='*70}")
            
            # Progress bar
            files_scanned = m.get('files_scanned', 0)
            print(f"[{'#'*30}] 100% ({files_scanned:,}) | {bbc_time:.2f}s")
            print(f"{'-'*70}")
            
            # Symbols line
            print(f"[INFO] {total_classes:,} Classes | {total_functions:,} Functions | {total_imports:,} Imports")
            
            # Compression line (file tokens vs context tokens - NOT real AI savings)
            print(f"[INFO] Source:{raw_tokens:,} tokens -> Context:{context_tokens:,} tokens | Compression:{savings_pct:.1f}%")
            
            # Status line
            status = "SEALED" if context.get("constraint_status") in ["sealed", "verified"] else "OPEN"
            print(f"[INFO] Status: {status} | Errors: run 'verify' to check")
            
            print(f"{'='*70}")
            
            # CLEAN MODE: BBC remains silent and only updates the bbc_context.json.
            
            print(f"\n[OK] BBC Context Secured: {os.path.abspath(output_file)}")
            print(f"[TIP] AI assistants will now see the verified logic structure.")
            print(f"{'='*70}\n")


def _is_context_stale(project_root: str, context_path: str) -> bool:
    project_root = os.path.abspath(project_root)
    context_path = os.path.abspath(context_path)
    if not os.path.isfile(context_path):
        return True

    snapshot_path = _get_project_snapshot_path(project_root)
    if os.path.isfile(snapshot_path):
        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snap = json.load(f)
            snap_ctx = os.path.abspath(snap.get("context_path", ""))
            if snap_ctx and os.path.normcase(snap_ctx) != os.path.normcase(context_path):
                return True
            snap_files = snap.get("files", {})
            if isinstance(snap_files, dict):
                current_files = _collect_project_fingerprint(project_root)
                if set(current_files.keys()) != set(snap_files.keys()):
                    return True
                for rel, meta in current_files.items():
                    old = snap_files.get(rel)
                    if not isinstance(old, dict):
                        return True
                    old_mtime = float(old.get("mtime", 0.0))
                    new_mtime = float(meta.get("mtime", 0.0))
                    if abs(old_mtime - new_mtime) > 0.01:
                        return True
                    if int(old.get("size", -1)) != int(meta.get("size", -1)):
                        return True
                return False
        except Exception:
            pass

    try:
        context_mtime = os.path.getmtime(context_path)
    except Exception:
        return True

    newest_mtime = 0.0
    try:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ["node_modules", ".venv", "dist", "build", ".git", "__pycache__", ".bbc"]]
            for file in files:
                if file.lower().endswith((
                    '.py', '.md', '.json', '.js', '.ts', '.html', '.css', '.sql', '.rs', '.go', '.c', '.cpp',
                    '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt'
                )):
                    try:
                        mtime = os.path.getmtime(os.path.join(root, file))
                        if mtime > newest_mtime:
                            newest_mtime = mtime
                    except Exception:
                        continue
    except Exception:
        return False

    return newest_mtime > context_mtime


def _get_project_snapshot_path(project_root: str) -> str:
    from bbc_core.config import BBCConfig
    bbc_dir = BBCConfig.get_bbc_dir(project_root)
    cache_dir = os.path.join(bbc_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "project_snapshot.json")


def _collect_project_fingerprint(project_root: str) -> Dict[str, Dict[str, Any]]:
    project_root = os.path.abspath(project_root)
    fingerprint: Dict[str, Dict[str, Any]] = {}

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and d not in [
                "node_modules", ".venv", "dist", "build", ".git", "__pycache__", ".bbc"
            ]
        ]

        for file in files:
            if not file.lower().endswith((
                '.py', '.md', '.json', '.js', '.ts', '.html', '.css', '.sql', '.rs', '.go', '.c', '.cpp',
                '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt'
            )):
                continue
            abs_path = os.path.join(root, file)
            try:
                st = os.stat(abs_path)
                rel_path = os.path.relpath(abs_path, project_root)
                fingerprint[rel_path] = {"mtime": float(st.st_mtime), "size": int(st.st_size)}
            except Exception:
                continue

    return fingerprint


def _write_project_snapshot(project_root: str, context_path: str) -> str:
    project_root = os.path.abspath(project_root)
    context_path = os.path.abspath(context_path)
    snapshot_path = _get_project_snapshot_path(project_root)
    payload = {
        "project_root": project_root,
        "context_path": context_path,
        "created_at": time.time(),
        "files": _collect_project_fingerprint(project_root),
    }
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, cls=BBCEncoder)
    return snapshot_path


def audit_bbc_traces(project_path: str) -> Dict[str, Any]:
    project_root = os.path.abspath(project_path)
    report = {
        "project_root": project_root,
        "exists": os.path.isdir(project_root),
        "paths": {},
    }

    # v8.3 Core artifacts (must exist for proper operation)
    check_paths = {
        ".bbc": os.path.join(project_root, ".bbc"),
        ".bbc/bbc_context.json": BBCConfig.get_context_path(project_root),
        ".bbc/bbc_rules.md": os.path.join(project_root, ".bbc", "bbc_rules.md"),
        ".bbc/bbc_context.md": os.path.join(project_root, ".bbc", "bbc_context.md"),
        ".bbc/BBC_INSTRUCTIONS.md": os.path.join(project_root, ".bbc", "BBC_INSTRUCTIONS.md"),
        ".bbc/manifest/injected_files.json": os.path.join(project_root, ".bbc", "manifest", "injected_files.json"),
        ".bbc/cache/project_snapshot.json": os.path.join(project_root, ".bbc", "cache", "project_snapshot.json"),
    }

    # Legacy / informational paths (v8.3 no longer generates these at root)
    legacy_paths = {
        "[Legacy] ai-context.json": os.path.join(project_root, "ai-context.json"),
        "[Legacy] BBC_INSTRUCTIONS.md (root)": os.path.join(project_root, "BBC_INSTRUCTIONS.md"),
        "[Legacy] BBC_CONTEXT.md": os.path.join(project_root, "BBC_CONTEXT.md"),
    }

    for k, p in check_paths.items():
        report["paths"][k] = {
            "path": p,
            "exists": os.path.exists(p),
            "is_dir": os.path.isdir(p),
            "category": "core",
        }

    for k, p in legacy_paths.items():
        report["paths"][k] = {
            "path": p,
            "exists": os.path.exists(p),
            "is_dir": os.path.isdir(p),
            "category": "legacy",
        }

    return report



def clean_system():
    """
    System cleanup function.
    Removes temporary files, caches, and old logs.
    """
    import shutil
    import glob
    
    print("[CLEAN] BBC System Cleanup starting...")
    cleaned = 0
    
    # 1. Remove __pycache__ directories
    for pycache in glob.glob("**/__pycache__", recursive=True):
        try:
            shutil.rmtree(pycache)
            cleaned += 1
            print(f"  [OK] Removed: {pycache}")
        except Exception as e:
            print(f"  [ERR] Could not remove {pycache}: {e}")
    
    # 2. Remove .pyc files
    for pyc in glob.glob("**/*.pyc", recursive=True):
        try:
            os.remove(pyc)
            cleaned += 1
            print(f"  [OK] Removed: {pyc}")
        except Exception:
            pass
    
    # 3. Remove old BBC log files (older than 7 days) - ONLY from .bbc/logs/
    import time
    from bbc_core.config import BBCConfig
    bbc_log_dir = os.path.join(BBCConfig.get_bbc_dir(), 'logs')
    current_time = time.time()
    if os.path.isdir(bbc_log_dir):
        for log in glob.glob(os.path.join(bbc_log_dir, '*.log')):
            try:
                file_time = os.path.getmtime(log)
                if (current_time - file_time) > (7 * 24 * 60 * 60):  # 7 days
                    os.remove(log)
                    cleaned += 1
                    print(f"  [OK] Removed old log: {log}")
            except Exception:
                pass
    
    print(f"\n[CLEAN] Cleanup complete. {cleaned} items removed.")
    return cleaned


def purge_bbc(project_path: str = ".", silent: bool = False):
    """
    Complete BBC removal - removes ALL BBC traces from a project.
    Use when user wants to completely stop using BBC.
    After purge, no BBC file or directory remains in the project.
    """
    import shutil
    from bbc_core.agent_adapter import cleanup_injected_configs
    
    project_root = os.path.abspath(project_path)
    removed = []
    
    if not silent:
        print(f"[PURGE] BBC Complete Removal")
        print(f"[PURGE] Target: {project_root}")
        print(f"{'-'*60}")
    
    # 1. Remove all injected AI config files
    injected = cleanup_injected_configs(project_root, dry_run=False)
    for f in injected:
        removed.append(f)
        if not silent:
            print(f"  [OK] {os.path.relpath(f, project_root)}")
    
    # 2. Remove BBC output files from project root
    bbc_root_files = [
        "ai-context.json",
        "bbc_rules.md",
        "BBC_CONTEXT.md",
        "BBC_INSTRUCTIONS.md",
        "BBC_README.md",
    ]
    for fname in bbc_root_files:
        fpath = os.path.join(project_root, fname)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                removed.append(fpath)
                if not silent:
                    print(f"  [OK] {fname}")
            except Exception as e:
                if not silent:
                    print(f"  [ERR] {fname}: {e}")
    
    # 3. Remove .bbc/ isolation directory (logs, indices, cache, weights, daemon)
    bbc_dir = os.path.join(project_root, ".bbc")
    if os.path.isdir(bbc_dir):
        try:
            shutil.rmtree(bbc_dir)
            removed.append(bbc_dir)
            if not silent:
                print(f"  [OK] .bbc/ (entire directory)")
        except Exception as e:
            if not silent:
                print(f"  [ERR] .bbc/: {e}")
    
    # 4. Remove legacy logs/ directory if it exists and is empty or BBC-only
    legacy_logs = os.path.join(project_root, "logs")
    if os.path.isdir(legacy_logs):
        try:
            # Only remove if all files inside are BBC-related
            bbc_log_names = {"state_manager.log", "bbc_math.log", "realtime_tokens.log", "chaos_test.log"}
            contents = set(os.listdir(legacy_logs))
            if contents.issubset(bbc_log_names) or len(contents) == 0:
                shutil.rmtree(legacy_logs)
                removed.append(legacy_logs)
                if not silent:
                    print(f"  [OK] logs/ (legacy BBC logs)")
        except Exception as e:
            if not silent:
                print(f"  [ERR] logs/: {e}")
    
    if not silent:
        print(f"{'-'*60}")
        print(f"[PURGE] Complete. {len(removed)} items removed.")
        print(f"[PURGE] BBC has been fully removed from this project.")
    return removed


def _ensure_init(project_root: str = "."):
    """
    System initialization check.
    Ensures .bbc/ isolation directory and subdirectories exist.
    All BBC output is contained within .bbc/ to avoid polluting the workspace.
    """
    from bbc_core.config import BBCConfig
    bbc_dir = BBCConfig.get_bbc_dir(project_root)
    
    required_subdirs = [
        os.path.join(bbc_dir, "indices"),
        os.path.join(bbc_dir, "logs"),
        os.path.join(bbc_dir, "cache"),
    ]
    
    for d in required_subdirs:
        os.makedirs(d, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="BBC Core CLI - Direct Integration Bridge")
    subparsers = parser.add_subparsers(dest="command")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("path", help="Project path to analyze")
    analyze_parser.add_argument("--out", default="bbc_context.json", help="Output JSON file name")
    analyze_parser.add_argument("--silent", action="store_true", help="Minimal output")

    # migrate command
    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("recipe", help="Path to the existing recipe JSON")
    migrate_parser.add_argument("--target", default="Rust", help="Target language (e.g. Rust, Go)")

    # verify command
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("recipe", help="Path to the recipe JSON (for root path context)")
    
    # clean command
    clean_parser = subparsers.add_parser("clean", help="Clean temporary files and caches")
    
    # purge command - Complete BBC removal
    purge_parser = subparsers.add_parser("purge", help="Completely remove ALL BBC traces from project")
    purge_parser.add_argument("path", nargs="?", default=".",
                              help="Project path to purge (default: current directory)")
    purge_parser.add_argument("--force", action="store_true",
                              help="Skip confirmation prompt")
    purge_parser.add_argument("--silent", action="store_true", help="Minimal output")
    
    # agent command - Generate IDE-specific contexts
    agent_parser = subparsers.add_parser("agent", help="Generate IDE-specific agent contexts")
    agent_parser.add_argument("recipe", nargs="?", default="bbc_context.json",
                             help="Path to BBC context JSON (default: bbc_context.json)")
    agent_parser.add_argument("--target", choices=["copilot", "cursor", "gemini", "kilo", "vscode", "all"],
                             default="all", help="Target agent format")
    agent_parser.add_argument("--out", default=".", help="Output directory for generated contexts")

    # inject command - Universal AI Context Injection
    inject_parser = subparsers.add_parser("inject", help="Inject BBC context to ALL AI assistants (native formats)")
    inject_parser.add_argument("path", nargs="?", default=".",
                              help="Project path to inject (default: current directory)")
    inject_parser.add_argument("--recipe", default=None,
                              help="Path to BBC recipe JSON (default: auto-detect in project)")
    inject_parser.add_argument("--silent", action="store_true", help="Minimal output")
    inject_parser.add_argument("--auto-analyze", action="store_true",
                              help="If context is stale, re-run analyze automatically before inject")
    inject_parser.add_argument("--allow-stale", action="store_true",
                              help="Proceed with inject even if context is detected as stale")
    inject_parser.add_argument("--force", action="store_true",
                              help="Force full re-injection and ignore checks")

    # bootstrap command - Analyze + Inject in one step
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Analyze project and inject IDE/agent instructions (one-step)")
    bootstrap_parser.add_argument("path", nargs="?", default=".",
                                 help="Project path (default: current directory)")
    bootstrap_parser.add_argument("--out", default="bbc_context.json",
                                 help="Context output file name (default: bbc_context.json in project root)")
    bootstrap_parser.add_argument("--yes", action="store_true",
                                 help="Skip confirmation prompt")
    bootstrap_parser.add_argument("--silent", action="store_true",
                                 help="Minimal output")

    # audit command - Report BBC traces in a project
    audit_parser = subparsers.add_parser("audit", help="Audit BBC traces (context/injected files/.bbc) in a project")
    audit_parser.add_argument("path", nargs="?", default=".", help="Project path to audit (default: current directory)")
    audit_parser.add_argument("--json", action="store_true", help="Output JSON only")

    # cleanup command - Remove injected AI configs
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove BBC-injected AI config files from project")
    cleanup_parser.add_argument("path", nargs="?", default=".",
                               help="Project path to cleanup (default: current directory)")
    cleanup_parser.add_argument("--force", action="store_true",
                               help="Skip confirmation prompt")
    cleanup_parser.add_argument("--silent", action="store_true", help="Minimal output")

    # adaptive command - BBC Adaptive Mode
    adaptive_parser = subparsers.add_parser("adaptive", help="BBC Adaptive Mode - Hallucination-resistant query")
    adaptive_parser.add_argument("recipe", nargs="?", default="bbc_context.json",
                                help="Path to BBC context JSON (default: bbc_context.json)")
    adaptive_parser.add_argument("--primary", required=True,
                                help="Primary symbol to query (e.g., HMPUMathChat)")
    adaptive_parser.add_argument("--direct", default="",
                                help="Direct context/question")
    adaptive_parser.add_argument("--ratio", type=float, default=0.95,
                                help="Context match ratio (0.0-1.0, default: 0.95)")
    adaptive_parser.add_argument("--json", action="store_true",
                                help="Output raw JSON only")

    # check command - Post-generation Hallucination Guard
    check_parser = subparsers.add_parser("check", help="Check AI-generated code against BBC context for hallucinations")
    check_parser.add_argument("file", help="Path to file containing AI-generated code to check")
    check_parser.add_argument("--context", default=None,
                             help="Path to bbc_context.json (default: auto-detect in project)")
    check_parser.add_argument("--strict", action="store_true", default=True,
                             help="Strict mode: flag all unknown symbols (default)")
    check_parser.add_argument("--relaxed", action="store_true",
                             help="Relaxed mode: only flag speculative language")
    check_parser.add_argument("--json", action="store_true",
                             help="Output raw JSON only")

    args = parser.parse_args()

    # Initialize system
    _ensure_init(getattr(args, 'path', '.'))

    if args.command == "analyze":
        cli = BBCCLI()
        asyncio.run(cli.run_analysis(args.path, args.out, silent=getattr(args, "silent", False)))
    elif args.command == "migrate":
        from bbc_core.migrator_engine import BBCMigratorEngine
        engine = BBCMigratorEngine(args.recipe)
        engine.plan_migration(args.target)
    elif args.command == "verify":
        from bbc_core.verifier import BBCVerifier
        verifier = BBCVerifier(args.recipe)
        report = verifier.verify_full()
        
        aura = report["aura_field"]
        freshness = report["freshness"]
        mismatch = report["symbol_mismatch"]
        
        print(f"\n{'='*60}")
        print(f" {report['verdict_icon']} BBC FULL VERIFICATION REPORT")
        print(f"{'='*60}")
        
        # Syntax
        if report["syntax_error_count"] > 0:
            print(f"\n[SYNTAX] {report['syntax_error_count']} error(s):")
            for e in report["syntax_errors"][:10]:
                print(f"  - [{e['type']}] {e['file']}:{e.get('line', '?')} -> {e.get('msg')}")
        else:
            print(f"\n[SYNTAX] No errors found.")
        
        # Freshness
        if freshness["context_fresh"]:
            print(f"[FRESH]  Context is FRESH ({freshness.get('total_files', 0)} files verified)")
        else:
            print(f"[STALE]  {freshness['stale_count']}/{freshness.get('total_files', 0)} files changed -> {freshness['recommendation']}")
            for sf in freshness["stale_files"][:5]:
                print(f"  - {sf}")
            if freshness.get("missing_count", 0) > 0:
                print(f"  ({freshness['missing_count']} file(s) missing from disk)")
        
        # Symbol Mismatch
        if mismatch["mismatch_count"] == 0:
            print(f"[MATCH]  All symbols consistent ({mismatch.get('total_context_symbols', 0)} symbols)")
        else:
            print(f"[DRIFT]  {mismatch['mismatch_count']} file(s) with symbol drift (ratio: {mismatch['mismatch_ratio']})")
            for mf in mismatch["mismatch_files"][:5]:
                added_str = f"+{mf['added_count']}" if mf['added_count'] else ""
                removed_str = f"-{mf['removed_count']}" if mf['removed_count'] else ""
                print(f"  - {mf['file']} [{added_str}{removed_str}]")
        
        # Aura Field
        print(f"\n{'─'*60}")
        print(f" AURA FIELD (BBC Mathematics)")
        print(f"{'─'*60}")
        print(f"  S (Structure):  {aura['S_structure']}")
        print(f"  C (Chaos):      {aura['C_chaos']}")
        print(f"  P (Pulse):      {aura['P_pulse']}")
        print(f"  Aura Score:     {aura['aura_score']}")
        print(f"  Field κ:        {aura['field_stability']}")
        print(f"  Confidence:     {aura['confidence']}")
        print(f"\n  VERDICT: {report['verdict_icon']} {report['verdict']}")
        print(f"{'='*60}")
    elif args.command == "clean":
        clean_system()
    elif args.command == "purge":
        project_path = os.path.abspath(args.path)
        silent = getattr(args, "silent", False)
        
        if not args.force:
            if getattr(args, "silent", False):
                print("[ERROR] Purge requires --force when used with --silent")
                sys.exit(1)
            print(f"\n{'='*60}")
            print(f"[!] WARNING: This will COMPLETELY remove ALL BBC traces from:")
            print(f"    {project_path}")
            print(f"{'='*60}")
            print(f"    - .bbc/ directory (logs, indices, cache, weights)")
            print(f"    - bbc_context.json, ai-context.json, bbc_rules.md")
            print(f"    - All injected AI config files")
            print(f"{'='*60}")
            confirm = input("[?] Are you sure? Type 'yes' to confirm: ").strip().lower()
            if confirm != 'yes':
                print("[CANCEL] Purge aborted.")
                sys.exit(0)
        
        purge_bbc(project_path, silent=silent)
    elif args.command == "agent":
        from bbc_core.agent_adapter import run_adapter_validation
        result = run_adapter_validation(args.recipe)

        if result["status"] not in ["ERROR"] and result.get("exports"):
            print(f"\n[*] Generated contexts available at:")
            for name, path in result["exports"].items():
                print(f"   [OK] {name}: {path}")

    elif args.command == "inject":
        from bbc_core.agent_adapter import inject_to_project
        
        project_path = os.path.abspath(args.path)
        silent = getattr(args, "silent", False)
        
        # Auto-detect recipe file
        if args.recipe:
            recipe_path = args.recipe
        else:
            # Try to find recipe in .bbc/ isolation directory first, then legacy root
            possible_recipes = [
                BBCConfig.get_context_path(project_path),
                os.path.join(project_path, "bbc_context.json"),
                "bbc_context.json"
            ]
            recipe_path = None
            for p in possible_recipes:
                if os.path.exists(p):
                    recipe_path = p
                    break
            
            if not recipe_path:
                if not silent:
                    print(f"[ERROR] No BBC recipe found. Run 'analyze' first or specify --recipe")
                sys.exit(1)

        stale = _is_context_stale(project_path, recipe_path)
        if stale:
            if args.auto_analyze:
                cli = BBCCLI()
                asyncio.run(cli.run_analysis(project_path, "bbc_context.json", silent=silent))
                recipe_path = BBCConfig.get_context_path(project_path)
            elif silent and not args.allow_stale:
                print("[ERROR] Context is stale. Use --auto-analyze or --allow-stale.")
                sys.exit(2)
            elif not silent and not args.allow_stale:
                confirm = input("[?] Context is stale. Run analyze now? (y/N): ").strip().lower()
                if confirm == "y":
                    cli = BBCCLI()
                    asyncio.run(cli.run_analysis(project_path, "bbc_context.json", silent=silent))
                    recipe_path = BBCConfig.get_context_path(project_path)
                else:
                    print("[ERROR] Aborting inject due to stale context. Use --allow-stale to force.")
                    sys.exit(2)
            elif not silent:
                print("[WARN] Context is stale; proceeding due to --allow-stale.")

        if not silent:
            print(f"\n{'='*70}")
            print(f">>> BBC UNIVERSAL AI CONTEXT INJECTION")
            print(f"{'='*70}")
            print(f"[*] Project: {project_path}")
            print(f"[*] Recipe: {recipe_path}")
            print(f"{'-'*70}")
        
        try:
            created_files = inject_to_project(recipe_path, project_path)

            if not silent:
                print(f"\n[OK] Successfully injected BBC context to {len(created_files)} AI assistants:\n")
                for ai_name, file_path in created_files.items():
                    rel_path = os.path.relpath(file_path, project_path)
                    print(f"   [OK] {ai_name:20} -> {rel_path}")
                
                print(f"\n{'='*70}")
                print(f"[SUCCESS] All AI assistants configured!")
                print(f"[TIP] Each AI will now read BBC context automatically")
                print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"\n[ERROR] Injection failed: {e}")
            sys.exit(1)

    elif args.command == "bootstrap":
        from bbc_core.agent_adapter import inject_to_project

        project_path = os.path.abspath(args.path)
        out_name = args.out

        if not args.yes:
            if not args.silent:
                print(f"\n{'='*70}")
                print(">>> BBC BOOTSTRAP (ANALYZE + INJECT)")
                print(f"{'='*70}")
                print(f"[*] Project: {project_path}")
                print(f"[*] Output:  {out_name}")
                print(f"{'-'*70}")
                print("This will generate/update BBC context and write IDE/agent instruction files.")
            confirm = input("[?] Continue? (y/N): ").strip().lower()
            if confirm != "y":
                if not args.silent:
                    print("[CANCEL] Bootstrap aborted.")
                sys.exit(0)

        cli = BBCCLI()
        asyncio.run(cli.run_analysis(project_path, out_name, silent=args.silent))

        context_path = BBCConfig.get_context_path(project_path) if out_name == "bbc_context.json" else os.path.abspath(out_name)
        try:
            created_files = inject_to_project(context_path, project_path)
        except Exception as e:
            print(f"[ERROR] Bootstrap inject failed: {e}")
            sys.exit(1)

        if not args.silent:
            print(f"\n[OK] Bootstrap complete.")
            print(f"[OK] Injected: {len(created_files)} target(s)")
            for ai_name, file_path in created_files.items():
                rel_path = os.path.relpath(file_path, project_path)
                print(f"   [OK] {ai_name:20} -> {rel_path}")
            print(f"{'='*70}\n")

    elif args.command == "cleanup":
        from bbc_core.agent_adapter import cleanup_injected_configs
        
        project_path = os.path.abspath(args.path)
        silent = getattr(args, "silent", False)
        
        if not silent:
            print(f"\n{'='*70}")
            print(f">>> BBC AI CONFIG CLEANUP")
            print(f"{'='*70}")
            print(f"[*] Project: {project_path}")
            print(f"{'-'*70}")
        
        # Find what would be deleted
        files_to_delete = cleanup_injected_configs(project_path, dry_run=True)
        
        if not files_to_delete:
            if not silent:
                print(f"\n[INFO] No BBC-injected config files found.")
                print(f"{'='*70}\n")
            sys.exit(0)
        
        if not silent:
            print(f"\n[!] Found {len(files_to_delete)} BBC-injected files:\n")
            for f in files_to_delete:
                rel_path = os.path.relpath(f, project_path)
                print(f"   [DEL] {rel_path}")
        
        if not args.force:
            if silent:
                print("[ERROR] Cleanup requires --force when used with --silent")
                sys.exit(1)
            print(f"\n{'-'*70}")
            confirm = input("[?] Delete these files? (y/N): ").strip().lower()
            if confirm != 'y':
                if not silent:
                    print(f"\n[CANCEL] Cleanup aborted.")
                sys.exit(0)
        
        # Actually delete
        deleted = cleanup_injected_configs(project_path, dry_run=False)
        
        if not silent:
            print(f"\n[OK] Deleted {len(deleted)} files:")
            for f in deleted:
                rel_path = os.path.relpath(f, project_path)
                print(f"   [OK] {rel_path}")
            
            print(f"\n{'='*70}")
            print(f"[SUCCESS] Cleanup complete!")
            print(f"{'='*70}\n")

    elif args.command == "audit":
        report = audit_bbc_traces(args.path)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, cls=BBCEncoder))
            sys.exit(0)

        print(f"\n{'='*70}")
        print(">>> BBC AUDIT")
        print(f"{'='*70}")
        print(f"[*] Project: {report['project_root']}")
        print(f"{'-'*70}")
        print(f"  Core Artifacts (v8.3 isolation):")
        for name, meta in report.get("paths", {}).items():
            if meta.get("category") != "core":
                continue
            status = "FOUND" if meta.get("exists") else "MISSING"
            print(f"  [{status:7}] {name}")
        print(f"{'-'*70}")
        print(f"  Legacy / Info (not required in v8.3):")
        for name, meta in report.get("paths", {}).items():
            if meta.get("category") != "legacy":
                continue
            status = "FOUND" if meta.get("exists") else "N/A"
            print(f"  [{status:7}] {name}")
        print(f"{'='*70}\n")

    elif args.command == "adaptive":
        from bbc_core.adaptive_mode import BBCAdaptiveMode

        engine = BBCAdaptiveMode(args.recipe)

        inputs = {
            "primary": args.primary,
            "direct": args.direct,
            "indirect": "",
            "safety": [],
            "context_match_ratio": args.ratio
        }

        result = engine.process_query(inputs)

        if args.json:
            print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2, cls=BBCEncoder))
        else:
            # Pretty print
            data = json.loads(result) if isinstance(result, str) else result
            print(f"\n{'='*60}")
            print(f"BBC ADAPTIVE MODE RESPONSE")
            print(f"{'='*60}")
            print(f"Mode: {data['mode'].upper()}")
            print(f"Confidence: {data['confidence']:.2f}")
            print(f"{'-'*60}")
            if data['answers']:
                print("Answers:")
                for ans in data['answers']:
                    print(f"  - {ans['statement']}")
                    print(f"    Source: [{ans['source_symbol']}]")
            if data['violations']:
                print(f"{'!'*60}")
                print("VIOLATIONS DETECTED:")
                for v in data['violations']:
                    print(f"  ! {v}")
            print(f"{'='*60}\n")

    elif args.command == "check":
        from bbc_core.hallucination_guard import HallucinationGuard

        # Context path: explicit veya auto-detect
        ctx_path = args.context
        if not ctx_path:
            # Auto-detect: dosyanın bulunduğu dizinden yukarı .bbc/bbc_context.json ara
            search_dir = os.path.dirname(os.path.abspath(args.file))
            for _ in range(10):
                candidate = os.path.join(search_dir, ".bbc", "bbc_context.json")
                if os.path.exists(candidate):
                    ctx_path = candidate
                    break
                parent = os.path.dirname(search_dir)
                if parent == search_dir:
                    break
                search_dir = parent
            if not ctx_path:
                print("[ERROR] bbc_context.json not found. Use --context to specify path.")
                sys.exit(1)

        # Dosyayı oku
        if not os.path.exists(args.file):
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)

        with open(args.file, 'r', encoding='utf-8') as f:
            generated_code = f.read()

        guard = HallucinationGuard(ctx_path)
        strict_mode = not getattr(args, "relaxed", False)
        result = guard.check(generated_code, strict=strict_mode)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            aura = result.get("aura_field", {})
            print(f"\n{'='*60}")
            print(f" BBC HALLUCINATION GUARD REPORT")
            print(f"{'='*60}")
            print(f"  File:           {args.file}")
            print(f"  Context:        {ctx_path}")
            print(f"  Mode:           {'STRICT' if strict_mode else 'RELAXED'}")
            print(f"  Match Ratio:    {result['match_ratio']} ({result['matched']}/{result['total_referenced']})")
            print(f"  Verdict:        {result['verdict']}")

            if result.get("hallucinated_symbols"):
                print(f"\n  Unknown Symbols ({len(result['hallucinated_symbols'])}):")
                for sym in result["hallucinated_symbols"][:15]:
                    print(f"    - {sym}")

            if result.get("speculative_violations"):
                print(f"\n  Speculative Language:")
                for sv in result["speculative_violations"]:
                    print(f"    ! {sv}")

            print(f"\n{'─'*60}")
            print(f" AURA FIELD (BBC Mathematics)")
            print(f"{'─'*60}")
            print(f"  S (Match):      {aura.get('S_match', 'N/A')}")
            print(f"  C (Chaos):      {aura.get('C_chaos', 'N/A')}")
            print(f"  P (Pulse):      {aura.get('P_pulse', 'N/A')}")
            print(f"  Aura Score:     {aura.get('aura_score', 'N/A')}")
            print(f"  Confidence:     {aura.get('confidence', 'N/A')}")
            print(f"{'='*60}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
