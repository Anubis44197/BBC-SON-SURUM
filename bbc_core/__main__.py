import argparse
import asyncio
import json
import sys
from .native_adapter import BBCNativeAdapter

async def main():
    parser = argparse.ArgumentParser(description="BBC Platform CLI - Stage 10.1 Bridge")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze Command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a project and generate context JSON")
    analyze_parser.add_argument("path", help="Project path to analyze")
    analyze_parser.add_argument("--out", default="bbc_context.json", help="Output JSON file path")

    args = parser.parse_args()

    if args.command == "analyze":
        adapter = BBCNativeAdapter()
        print(f"[*] Analyzing project: {args.path} ...")
        
        context = await adapter.analyze_project(args.path)
        
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
            
        print(f"[+] Analysis complete. Context saved to: {args.out}")
        print(f"    - Files Analyzed: {context.get('project_skeleton', {}).get('file_count', 0)}")
        metrics = context.get('metrics', {})
        print(f"    - Savings Ratio: {metrics.get('savings_ratio', 'N/A')}%")
        print(f"    - Status: {context.get('constraint_status', 'verified')}")
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
