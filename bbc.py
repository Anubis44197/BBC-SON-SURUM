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

    def serve(self, port=3333):
        """Start HTTP API Server"""
        print(f"[BBC] Starting API Server on port {port}...")
        os.environ["BBC_API_PORT"] = str(port)
        from bbc_core.http_server import app
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=port)

def main():
    parser = argparse.ArgumentParser(description="BBC Master CLI - v8.3 STABLE", prog="bbc")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start
    start_parser = subparsers.add_parser("start", help="Full Verify + Analyze + Inject")
    start_parser.add_argument("path", nargs="?", default=".", help="Project path")
    start_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
    start_parser.add_argument("--force", "-f", action="store_true", help="Force refresh")

    # Analyze (Direct)
    analyze_parser = subparsers.add_parser("analyze", help="Deep Project Scan")
    analyze_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Verify
    verify_parser = subparsers.add_parser("verify", help="Check Structural Integrity")
    verify_parser.add_argument("path", nargs="?", default=".", help="Project path")

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

    # Watch (IDE Terminal Monitor)
    watch_parser = subparsers.add_parser("watch", help="Watch AI operations and show HMPU reports in IDE terminal")
    watch_parser.add_argument("path", nargs="?", default=".", help="Project path")

    stop_parser = subparsers.add_parser("stop", help="Stop BBC Daemon")
    stop_parser.add_argument("path", nargs="?", default=".", help="Project path")

    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.add_argument("path", nargs="?", default=".", help="Project path")

    args = parser.parse_args()
    cli = BBCCLI()

    if args.command == "start":
        cli.start(args.path, args.background, args.force)
    elif args.command == "analyze":
        cli.run_command(["analyze", args.path])
    elif args.command == "verify":
        ctx_file = str(Path(args.path).resolve() / ".bbc" / "bbc_context.json")
        if Path(ctx_file).exists():
            cli.run_command(["verify", ctx_file])
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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
