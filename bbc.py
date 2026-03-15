#!/usr/bin/env python3
"""
BBC CLI - User-Friendly Interface v8.3
Single command BBC launcher: bbc start
"""

import os
import sys
import argparse
import signal
import subprocess
import time
import json
from pathlib import Path

# Add BBC modules to path
sys.path.append(str(Path(__file__).parent))

from bbc_core.auto_detector import auto_start_bbc, stop_bbc_auto


def _update_context_freshness(ctx_file: str, fresh: bool) -> None:
    """Update the context_fresh field in bbc_context.json."""
    try:
        with open(ctx_file, "r", encoding="utf-8") as f:
            ctx = json.load(f)
        ctx["context_fresh"] = fresh
        with open(ctx_file, "w", encoding="utf-8") as f:
            json.dump(ctx, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _print_transaction_report(project_path: str, source: str) -> None:
    """Print BBC token savings / aura report after a completed operation."""
    try:
        from bbc_core.config import BBCConfig

        project_resolved = str(Path(project_path).resolve())
        ctx_file = BBCConfig.get_context_path(project_resolved)

        if os.path.exists(ctx_file):
            try:
                with open(ctx_file, "r", encoding="utf-8") as f:
                    ctx = json.load(f)
                ctx.setdefault("metrics", {})
                ctx["metrics"]["unified_status"] = "COMPLETED"
                ctx["metrics"]["unified_source"] = source
                ctx["metrics"]["unified_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                with open(ctx_file, "w", encoding="utf-8") as f:
                    json.dump(ctx, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        old_argv = sys.argv[:]
        try:
            sys.argv = ["run_bbc", source, project_resolved]
            from run_bbc import print_transaction_report
            print_transaction_report()
        finally:
            sys.argv = old_argv
    except Exception as e:
        print(f"[BBC] Report error: {e}")


class BBCCLI:
    """BBC Command Line Interface v8.3"""

    def __init__(self):
        self.running = False
        self.script_dir = Path(__file__).parent
        self.run_bbc_script = self.script_dir / "run_bbc.py"

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        sys.exit(0)

    def run_command(self, cmd_args):
        """Helper to run run_bbc.py commands"""
        return subprocess.call([sys.executable, str(self.run_bbc_script)] + cmd_args)

    def start(self, project_path: str = ".", background: bool = False, force: bool = False):
        """Start BBC - The Full v8.3 Pipeline"""
        project_resolved = str(Path(project_path).resolve())

        if background:
            daemon_script = self.script_dir / "bbc_daemon.py"
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                [sys.executable, str(daemon_script), "start", project_resolved],
                creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"[BBC] Daemon started (PID: {proc.pid})")
            return

        print(f"[BBC] Initializing Master v8.3 Pipeline...")

        # 1. Verify Structure (use correct .bbc/ path)
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if Path(ctx_file).exists():
            self.run_command(["verify", ctx_file])

        # 2. Analyze & Inject
        success = auto_start_bbc(force_restart=force, project_path=project_path, start_monitoring=False)

        if success:
            print(f"[BBC] Injecting Adaptive Mode Intelligence...")
            if force:
                self.run_command(["analyze", project_resolved])
                self.run_command(["inject", project_resolved, "--auto-analyze", "--silent", "--force"])
            else:
                self.run_command(["inject", project_resolved, "--auto-analyze", "--silent"])
            print(f"[BBC] System Active. Zero-Hallucination Guard Engaged.")
            
            # Otomatik daemon başlat (Arka plan servisi)
            if not background:
                print(f"[BBC] Starting Real-time Daemon in background...")
                daemon_script = self.script_dir / "bbc_daemon.py"
                creation_flags = 0
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
                try:
                    proc = subprocess.Popen(
                        [sys.executable, str(daemon_script), "start", project_resolved],
                        creationflags=creation_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    print(f"[BBC] Daemon started (PID: {proc.pid}) - Real-time monitoring active.")
                except Exception as e:
                    print(f"[WARN] Could not start daemon automatically: {e}")
            
            # Start IDE terminal watch (foreground) — shows HMPU report after each AI operation
            self._watch_and_report(project_resolved)
        else:
            print(f"[BBC] Initialization failed.")
            sys.exit(1)

    def _watch_and_report(self, project_path: str):
        """Watch .bbc/last_activity.json and print HMPU report after each AI operation in IDE terminal"""
        activity_file = Path(project_path) / ".bbc" / "last_activity.json"
        print(f"[BBC] IDE Terminal Watch active. Monitoring AI operations...")
        print(f"[BBC] Press Ctrl+C to stop watching.\n")
        
        last_epoch = 0.0
        quiet_since = None  # timestamp when activity stopped
        DEBOUNCE_SECONDS = 3.0  # wait this long after last change before printing report
        
        try:
            while True:
                try:
                    if activity_file.exists():
                        with open(activity_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        current_epoch = data.get("epoch", 0.0)
                        
                        if current_epoch > last_epoch:
                            last_epoch = current_epoch
                            quiet_since = time.time()
                    
                    # If we have pending activity and enough quiet time passed, print report
                    if quiet_since and (time.time() - quiet_since) >= DEBOUNCE_SECONDS:
                        quiet_since = None
                        # Re-read activity info for display
                        try:
                            with open(activity_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            changed_file = data.get("file", "")
                            print(f"\n[BBC] Activity detected: {changed_file}")
                        except Exception:
                            pass
                        
                        # Print HMPU transaction report
                        try:
                            sys.argv = ["run_bbc", "analyze", project_path]
                            from run_bbc import print_transaction_report
                            print_transaction_report()
                        except Exception as e:
                            print(f"[BBC] Report error: {e}")
                
                except (json.JSONDecodeError, PermissionError):
                    pass
                
                time.sleep(1.0)
        except KeyboardInterrupt:
            print(f"\n[BBC] Watch stopped.")

    def watch(self, project_path: str = "."):
        """Watch mode - monitor AI operations and print HMPU reports in IDE terminal"""
        project_resolved = str(Path(project_path).resolve())
        ctx_file = Path(project_resolved) / ".bbc" / "bbc_context.json"
        if not ctx_file.exists():
            print(f"[BBC] Project not initialized. Run 'bbc start' first.")
            sys.exit(1)
        
        # Print initial report
        try:
            sys.argv = ["run_bbc", "analyze", project_resolved]
            from run_bbc import print_transaction_report
            print_transaction_report()
        except Exception:
            pass
        
        self._watch_and_report(project_resolved)

    def stop(self, project_path: str = "."):
        project_resolved = str(Path(project_path).resolve())
        from bbc_daemon import BBCDaemon
        daemon = BBCDaemon(project_root=project_resolved)
        if daemon._is_running():
            daemon.stop()
        else:
            stop_bbc_auto()
        print(f"[BBC] Stopped")

    def purge(self, path=".", force=False):
        """Complete system purge"""
        cmd = ["purge", str(Path(path).resolve())]
        if force: cmd.append("--force")
        self.run_command(cmd)

    def install(self, project_path: str = ".", force: bool = False):
        """One-command BBC install: pip install deps + analyze + inject + start"""
        print(f"[BBC] One-Command Install starting...")
        
        # 1. Install dependencies
        req_file = self.script_dir / "requirements.txt"
        if req_file.exists():
            print(f"[BBC] Step 1/2: Installing dependencies...")
            result = subprocess.call(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"]
            )
            if result != 0:
                print(f"[BBC] Warning: Some dependencies may have failed to install.")
            else:
                print(f"[BBC] Step 1/2: Dependencies installed.")
        else:
            print(f"[BBC] Step 1/2: No requirements.txt found, skipping.")
        
        # 2. Run full start pipeline
        print(f"[BBC] Step 2/2: Starting BBC...")
        self.start(project_path, force=force)

    def serve(self, port=3333):
        """Start HTTP API Server"""
        print(f"[BBC] Starting API Server on port {port}...")
        os.environ["BBC_API_PORT"] = str(port)
        from bbc_core.http_server import app
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=port)

def main():
    parser = argparse.ArgumentParser(description="BBC Master CLI - v8.5 STABLE", prog="bbc")
    parser.add_argument("--enforcement", choices=["strict", "balanced", "relaxed"], default=None,
                        help="Override enforcement level (default: read from context or strict)")
    parser.add_argument("--fail-policy", choices=["fail_closed", "fail_open"], default=None,
                        help="Override fail policy (default: read from context or fail_closed)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start
    start_parser = subparsers.add_parser("start", help="Full Verify + Analyze + Inject")
    start_parser.add_argument("path", nargs="?", default=".", help="Project path")
    start_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
    start_parser.add_argument("--force", "-f", action="store_true", help="Force refresh")

    # Analyze (Direct)
    analyze_parser = subparsers.add_parser("analyze", help="Deep Project Scan")
    analyze_parser.add_argument("path", nargs="?", default=".", help="Project path")
    analyze_parser.add_argument("--incremental", action="store_true",
                               help="Only re-analyze files changed since last run")

    # Verify
    verify_parser = subparsers.add_parser("verify", help="Check Structural Integrity")
    verify_parser.add_argument("path", nargs="?", default=".", help="Project path")
    verify_parser.add_argument("--changed-only", action="store_true",
                               help="Only verify files that changed since last seal")

    # Serve
    serve_parser = subparsers.add_parser("serve", help="Start API Server")
    serve_parser.add_argument("--port", "-p", type=int, default=3333, help="Port (default: 3333)")

    # Audit
    audit_parser = subparsers.add_parser("audit", help="Audit BBC Traces")
    audit_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Purge
    purge_parser = subparsers.add_parser("purge", help="Complete BBC Removal")
    purge_parser.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")
    purge_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # Menu (Interactive)
    menu_parser = subparsers.add_parser("menu", help="Interactive BBC Menu")
    menu_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Install (One-command setup)
    install_parser = subparsers.add_parser("install", help="One-command install: deps + analyze + inject + start")
    install_parser.add_argument("path", nargs="?", default=".", help="Project path")
    install_parser.add_argument("--force", "-f", action="store_true", help="Force fresh install")

    # Watch (IDE Terminal Monitor)
    watch_parser = subparsers.add_parser("watch", help="Watch AI operations and show HMPU reports in IDE terminal")
    watch_parser.add_argument("path", nargs="?", default=".", help="Project path")

    stop_parser = subparsers.add_parser("stop", help="Stop BBC Daemon")
    stop_parser.add_argument("path", nargs="?", default=".", help="Project path")

    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Check (Hallucination Guard)
    check_parser = subparsers.add_parser("check", help="Check AI-generated code against sealed BBC context")
    check_parser.add_argument("file", help="Path to file containing AI-generated code to check")
    check_parser.add_argument("--path", default=".", help="Project path (default: current directory)")
    check_parser.add_argument("--strict", action="store_true", default=True, help="Strict mode: flag all unknown symbols")
    check_parser.add_argument("--relaxed", action="store_true", help="Relaxed mode: only flag speculative language")

    # Impact (Semantic Impact Analysis)
    impact_parser = subparsers.add_parser("impact", help="Analyze semantic impact of a file change (BBC Mathematics)")
    impact_parser.add_argument("file", help="Path to the changed file")
    impact_parser.add_argument("--path", default=".", help="Project path (default: current directory)")
    impact_parser.add_argument("--symbols", nargs="*", default=None, help="Changed symbol names (optional)")
    impact_parser.add_argument("--op", choices=["Refactor", "Patch", "Feature"], default="Patch",
                               help="Operation type (default: Patch)")

    # Patch (Auto Patcher)
    patch_parser = subparsers.add_parser("patch", help="Detect and fix code issues automatically (BBC Mathematics)")
    patch_parser.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")
    patch_parser.add_argument("--apply", action="store_true", help="Apply safe patches (default: dry-run only)")

    # Inject (Agent Instruction Injection)
    inject_parser = subparsers.add_parser("inject", help="Inject BBC instructions into AI agent config files")
    inject_parser.add_argument("path", nargs="?", default=".", help="Project path (default: current directory)")

    # Hooks (Git Hook Generator)
    hooks_parser = subparsers.add_parser("hooks", help="Install/remove BBC git hooks for team automation")
    hooks_parser.add_argument("path", nargs="?", default=".", help="Project path")
    hooks_parser.add_argument("--remove", action="store_true", help="Remove BBC hooks")

    # Compile (Task-Aware Context Compiler)
    compile_parser = subparsers.add_parser("compile", help="Compile task-aware context (bugfix/feature/refactor/review)")
    compile_parser.add_argument("--task", required=True,
                                choices=["bugfix", "feature", "refactor", "review"],
                                help="Task type")
    compile_parser.add_argument("--file", default=None, help="Target file (relative path)")
    compile_parser.add_argument("--symbols", nargs="*", default=None, help="Target symbol names")
    compile_parser.add_argument("--path", default=".", help="Project path (default: current directory)")
    compile_parser.add_argument("--out", default=None, help="Output path for compiled context")
    compile_parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout")

    args = parser.parse_args()
    cli = BBCCLI()

    if args.command == "start":
        cli.start(args.path, args.background, args.force)
    elif args.command == "analyze":
        cmd = ["analyze", args.path]
        if getattr(args, "incremental", False):
            cmd.append("--incremental")
        cli.run_command(cmd)
    elif args.command == "verify":
        project_resolved = str(Path(args.path).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if Path(ctx_file).exists():
            # --- Freshness gate ---
            from bbc_core.cli import _is_context_stale
            stale = _is_context_stale(project_resolved, ctx_file)
            if stale:
                _update_context_freshness(ctx_file, False)
            # --- Read policy from context (with CLI overrides) ---
            import json as _json
            with open(ctx_file, "r", encoding="utf-8") as _f:
                _ctx = _json.load(_f)
            fp = getattr(args, "fail_policy", None) or _ctx.get("fail_policy", "fail_closed")
            enf = getattr(args, "enforcement", None) or _ctx.get("enforcement_level", "strict")
            # --- Apply CLI overrides to context if provided ---
            _dirty = False
            if getattr(args, "enforcement", None) and args.enforcement != _ctx.get("enforcement_level"):
                _ctx["enforcement_level"] = args.enforcement
                _dirty = True
            if getattr(args, "fail_policy", None) and args.fail_policy != _ctx.get("fail_policy"):
                _ctx["fail_policy"] = args.fail_policy
                _dirty = True
            if _dirty:
                with open(ctx_file, "w", encoding="utf-8") as _f:
                    _json.dump(_ctx, _f, indent=2, ensure_ascii=False)
            # --- Freshness warning/block ---
            if stale:
                print(f"[BBC] Context freshness: STALE")
                if fp == "fail_closed":
                    print(f"[BBC] Fail policy: fail_closed — run 'bbc analyze {args.path}' to refresh context before proceeding.")
                else:
                    print(f"[BBC WARNING] Operating with stale context (fail_open mode).")
            else:
                print(f"[BBC] Context freshness: FRESH")
            print(f"[BBC] Enforcement: {enf} | Fail policy: {fp}")
            verify_cmd = ["verify", ctx_file]
            if getattr(args, "changed_only", False):
                verify_cmd.append("--changed-only")
            cli.run_command(verify_cmd)
        else:
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc start {args.path}' first to generate the context.")
    elif args.command == "check":
        project_resolved = str(Path(getattr(args, 'path', '.')).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if Path(ctx_file).exists():
            cmd = ["check", args.file, "--context", ctx_file]
            if getattr(args, "relaxed", False):
                cmd.append("--relaxed")
            elif getattr(args, "strict", False):
                cmd.append("--strict")
            cli.run_command(cmd)
        else:
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc start {args.path}' first to generate the context.")
    elif args.command == "serve":
        cli.serve(args.port)
    elif args.command == "audit":
        cli.run_command(["audit", args.path])
    elif args.command == "purge":
        cli.purge(args.path, args.force)
    elif args.command == "menu":
        from bbc_core.global_menu import main as menu_main
        menu_main(str(Path(args.path).resolve()), loop=True)
    elif args.command == "watch":
        cli.watch(args.path)
    elif args.command == "install":
        cli.install(args.path, args.force)
    elif args.command == "inject":
        project_resolved = str(Path(args.path).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if Path(ctx_file).exists():
            from bbc_core.agent_adapter import inject_to_project
            created = inject_to_project(ctx_file, project_resolved)
            print(f"\n[BBC] Injection complete — {len(created)} target(s):")
            for label, path in created.items():
                print(f"  [{label}] {path}")
            _print_transaction_report(project_resolved, "inject")
        else:
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc analyze {args.path}' first to generate the context.")
    elif args.command == "stop":
        cli.stop(args.path)
    elif args.command == "status":
        project_resolved = str(Path(args.path).resolve())
        daemon = __import__("bbc_daemon").BBCDaemon(project_root=project_resolved)
        daemon_active = daemon._is_running()
        
        print("\n" + "="*40)
        print(" BBC v8.3 - System Status ".center(40, "="))
        print("="*40)
        import json

        ctx_path = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if os.path.exists(ctx_path):
            print(f"[X] Context Lock:   SEALED (ACTIVE)")
        else:
            print(f"[ ] Context Lock:   MISSING (VULNERABLE)")
            
        if daemon_active:
            print(f"[~] Daemon Status:  RUNNING (Dynamic)")
            try:
                if daemon.config_file.exists():
                    with open(daemon.config_file, "r") as f:
                        cfg = json.load(f)
                    print(f"    - Monitoring:   {cfg.get('project_path', 'Unknown')}")
                    print(f"    - Started:      {cfg.get('start_time', 'Unknown')}")
            except Exception:
                pass
        else:
            print(f"[!] Daemon Status:  STOPPED (Static Mode)")
            print("    Run 'bbc start' to enable live defense.")
            
        print("="*40 + "\n")
    elif args.command == "compile":
        project_resolved = str(Path(getattr(args, 'path', '.')).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if not Path(ctx_file).exists():
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc analyze' first.")
        else:
            compile_cmd = ["compile", "--task", args.task]
            if getattr(args, "file", None):
                compile_cmd.extend(["--file", args.file])
            if getattr(args, "symbols", None):
                compile_cmd.extend(["--symbols"] + args.symbols)
            compile_cmd.extend(["--context", ctx_file])
            if getattr(args, "out", None):
                compile_cmd.extend(["--out", args.out])
            if getattr(args, "json", False):
                compile_cmd.append("--json")
            cli.run_command(compile_cmd)
    elif args.command == "impact":
        project_resolved = str(Path(getattr(args, 'path', '.')).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if not Path(ctx_file).exists():
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc analyze' first.")
        else:
            from bbc_core.impact_analyzer import ImpactAnalyzer
            analyzer = ImpactAnalyzer(ctx_file)
            report = analyzer.analyze_impact(args.file, changed_symbols=args.symbols, op_type=args.op)
            aura = report["aura_impact"]
            print(f"\n{'='*60}")
            print(f" {report['verdict_icon']} BBC SEMANTIC IMPACT ANALYSIS")
            print(f"{'='*60}")
            print(f"  Changed:   {report['changed_file']}")
            if report['changed_symbols']:
                print(f"  Symbols:   {', '.join(report['changed_symbols'])}")
            print(f"  Operation: {report['op_type']}")
            print(f"\n[DIRECT]  {report['direct_count']} file(s) directly affected:")
            for dep in report["direct_dependents"][:10]:
                print(f"  → {dep}")
            if report["indirect_count"] > 0:
                print(f"[INDIRECT] {report['indirect_count']} file(s) indirectly affected:")
                for dep in report["indirect_dependents"][:10]:
                    print(f"  ⤳ {dep}")
            if report["symbol_impacts"]:
                print(f"\n[SYMBOLS] Symbol-level impacts:")
                for si in report["symbol_impacts"][:5]:
                    print(f"  - {si['symbol']}: {si['affected_count']} file(s)")
            if report["semantic_similar"]:
                print(f"\n[FOCUS]   Semantically similar files (cos θ):")
                for ss in report["semantic_similar"][:5]:
                    sim = ss["similarity"]
                    print(f"  - {ss['file']}  sim={sim['value']} [{sim['state']}]  risk={ss['risk']}")
            print(f"\n{'─'*60}")
            print(f" AURA IMPACT (BBC Mathematics — State-Aware)")
            print(f"{'─'*60}")
            ir = aura['impact_ratio']
            cd = aura['chaos_density']
            pr = aura['pulse_risk']
            cr = aura['composite_risk']
            print(f"  Impact Ratio:    {ir['value']}  [{ir['state']}]")
            print(f"  Chaos Density:   {cd['value']}  [{cd['state']}]")
            print(f"  Pulse Risk:      {pr['value']}  [{pr['state']}]")
            print(f"  Composite Risk:  {cr['value']}  [{cr['state']}]")
            print(f"\n  VERDICT: {report['verdict_icon']} {report['verdict']}")
            print(f"{'='*60}")
            _print_transaction_report(project_resolved, "impact")
    elif args.command == "patch":
        project_resolved = str(Path(args.path).resolve())
        ctx_file = str(Path(project_resolved) / ".bbc" / "bbc_context.json")
        if not Path(ctx_file).exists():
            print(f"[BBC] Context not found: {ctx_file}")
            print(f"[BBC] Run 'bbc analyze' first.")
        else:
            from bbc_core.auto_patcher import AutoPatcher
            patcher = AutoPatcher(ctx_file, project_resolved)
            dry_run = not getattr(args, "apply", False)
            report = patcher.analyze_and_patch(dry_run=dry_run)
            mode_str = "DRY-RUN (preview)" if dry_run else "APPLY"
            oq = report["overall_quality"]
            print(f"\n{'='*60}")
            print(f" 🔧 BBC AUTO PATCHER [{mode_str}]")
            print(f"{'='*60}")
            print(f"  Total issues found: {report['total_patches']}")
            print(f"  Applied:            {report['applied']}")
            print(f"  Skipped (unsafe):   {report['skipped_unsafe']}")
            print(f"  Overall Quality:    {oq['value']}  [{oq['state']}]")
            if report["patch_results"]:
                print(f"\n{'─'*60}")
                print(f" PATCHES")
                print(f"{'─'*60}")
                for i, pr_item in enumerate(report["patch_results"], 1):
                    p = pr_item["patch"]
                    safe = "✅" if pr_item.get("safe_to_apply") else "🔴"
                    applied = " [APPLIED]" if pr_item.get("applied") else ""
                    print(f"  {i}. {safe} [{p['action']}] {p['file']}")
                    print(f"     {p['description']}{applied}")
                    if "patch_quality" in pr_item:
                        pq = pr_item["patch_quality"]
                        print(f"     Quality: {pq['value']} [{pq['state']}]")
            if report["reseal_needed"]:
                print(f"\n{'─'*60}")
                print(f" RESEAL NEEDED")
                print(f"{'─'*60}")
                for r in report["reseal_needed"]:
                    print(f"  ⚠️  {r['file']}: {r['description']}")
                print(f"\n  Run 'bbc analyze' to reseal context.")
            print(f"{'='*60}")
            if dry_run and report["total_patches"] > 0:
                print(f"\n  💡 To apply safe patches: bbc patch {args.path} --apply")
            _print_transaction_report(project_resolved, "patch")
    elif args.command == "hooks":
        from bbc_core.git_hooks import install_hooks, remove_hooks
        project_resolved = str(Path(args.path).resolve())
        if args.remove:
            result = remove_hooks(project_resolved)
            if result["removed"]:
                for r in result["removed"]:
                    print(f"[BBC] Removed: {r}")
            else:
                print("[BBC] No BBC hooks found to remove.")
        else:
            result = install_hooks(project_resolved)
            if result["success"]:
                for h in result["installed"]:
                    print(f"[BBC] Hook: {h}")
                print(f"[BBC] Hooks installed in {result['hooks_dir']}")
                _print_transaction_report(project_resolved, "hooks")
            else:
                for e in result.get("errors", []):
                    print(f"[BBC] Error: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
