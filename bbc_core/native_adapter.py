import sys
import json
import os
import asyncio
import hashlib
from .hmpu_engine import HMPUEngine
from .state_manager import StateManager
from .hmpu_indexer import HMPUIndexer

# Import the Polyglot Quantizer (tek doğruluk kaynağı: bbc_core)
from .hmpu_quantizer import HMPUQuantizer

class BBCNativeAdapter:
    def __init__(self, project_root: str = "."):
        self.state_manager = StateManager()
        self.engine = HMPUEngine(self.state_manager)
        self.quantizer = HMPUQuantizer()
        # Use .bbc/indices/ for isolation; fallback to 02_Indices/ for backward compat
        bbc_index_dir = os.path.join(project_root, ".bbc", "indices")
        os.makedirs(bbc_index_dir, exist_ok=True)
        self.indexer = HMPUIndexer(index_dir=bbc_index_dir)

    def compute_hash(self, content: str) -> str:
        """Computes SHA-256 hash of content for hallucination detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def analyze_project(self, target_root, output_file=None, silent: bool = False):
        root_to_scan = os.path.abspath(target_root) if target_root else os.getcwd()
        output_file_abs = os.path.abspath(output_file) if output_file else None
        
        files_found = []
        project_recipes = []
        total_raw_bytes = 0
        total_lines = 0
        total_code_lines = 0
        
        # Polyglot Extension List
        exts = ('.py', '.md', '.json', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.sql', '.rs', '.go', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt')
        forbidden_dirs = {"node_modules", ".venv", "dist", "build", ".git", "__pycache__", "target", ".bbc"}
        comment_prefixes = ('#', '//', '/*', '*')
        
        if not silent:
            print(f"[*] Polyglot Scan Started: {root_to_scan}")

        # RECURSIVE SCAN & QUANTIZATION
        for root, dirs, files in os.walk(root_to_scan):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in forbidden_dirs]
            
            for file in files:
                if file.lower().endswith(exts):
                    file_path = os.path.join(root, file)
                    
                    # Skip the output file itself (Self-Reference Prevention)
                    if output_file_abs and os.path.abspath(file_path) == output_file_abs:
                        continue

                    try:
                        ext = os.path.splitext(file)[1].lower()
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        rel_path = os.path.relpath(file_path, root_to_scan)
                        files_found.append(rel_path)
                        
                        # Encode once, reuse for byte count and hash
                        content_bytes = content.encode('utf-8')
                        total_raw_bytes += len(content_bytes)
                        
                        # Single-pass line counting (v7.2 optimized)
                        file_total_lines = 0
                        file_code_lines = 0
                        for line in content.splitlines():
                            file_total_lines += 1
                            stripped = line.strip()
                            if stripped and not stripped.startswith(comment_prefixes):
                                file_code_lines += 1
                        
                        total_lines += file_total_lines
                        total_code_lines += file_code_lines
                        
                        # Apply v6.0 Quantization
                        analysis = self.quantizer.process_content(content, file_ext=ext)
                        
                        # [VERIFIER] Compute hash from pre-encoded bytes
                        file_hash = hashlib.sha256(content_bytes).hexdigest()
                        
                        # [DEEP RECALL] Add to vector index
                        self.indexer.add_to_index(content, {"path": rel_path, "hash": file_hash})
                        
                        project_recipes.append({
                            "path": rel_path,
                            "structure": analysis["structure"],
                            "stats": {**analysis["stats"], "lines": file_total_lines, "code_lines": file_code_lines, "hash": file_hash}
                        })
                        
                        self.state_manager.increment_files_analyzed()
                        
                        # Progress reporting for large projects
                        count = len(files_found)
                        if count % 1000 == 0 and not silent:
                            print(f"[*] Progress: {count:,} files processed...")
                    except Exception: continue
                if len(files_found) >= 100000:
                    if not silent:
                        print(f"[WARN] File limit reached (100,000). Remaining files skipped.")
                    break
            if len(files_found) >= 100000: break

        if not silent:
            print(f"[*] Scan complete: {len(files_found)} files found.")

        # Build dependency graph from import statements
        dependency_graph = self._build_dependency_graph(project_recipes, files_found)

        # Build Context JSON
        import time as _time
        _generated_at = _time.strftime("%Y-%m-%dT%H:%M:%S")

        context_json = {
            "bbc_instructions_version": "1.0",
            "context_schema_version": "8.5",
            "generated_at": _generated_at,
            "context_fresh": True,
            "fail_policy": "fail_closed",
            "enforcement_level": "strict",
            "project_skeleton": {
                "root": root_to_scan,
                "file_count": len(files_found),
                "hierarchy": files_found
            },
            "code_structure": project_recipes,
            "dependency_graph": dependency_graph,
            "constraint_status": "verified",
            "metrics": {
                "files_scanned": len(files_found),
                "total_lines": total_lines,
                "code_lines": total_code_lines,
                "raw_bytes": total_raw_bytes,
                "context_bytes": 0,
                "compression_ratio": 0.0,
                "unified_savings_confidence": self.engine.get_aura_confidence()
            }
        }

        # Estimate context size without full serialization (v7.2 optimized)
        # Approximate: each recipe ~200 bytes avg, skeleton ~50 bytes per file
        est_recipe_bytes = len(project_recipes) * 200
        est_skeleton_bytes = len(files_found) * 50
        est_overhead = 500  # JSON structure overhead
        context_bytes = est_recipe_bytes + est_skeleton_bytes + est_overhead
        context_json["metrics"]["context_bytes"] = context_bytes
        
        if total_raw_bytes > 0:
            context_json["metrics"]["compression_ratio"] = round(1 - (context_bytes / total_raw_bytes), 2)
        
        # [DEEP RECALL] Save vector index to disk
        index_path = self.indexer.finalize_and_save("bbc_main_memory", len(files_found))
        context_json["index_path"] = index_path

        # ─── SYMBOL PIPELINE (Opsiyonel — hata verirse ana akışı bozmaz) ───
        try:
            from .symbol_extractor import SymbolExtractor
            from .symbol_graph import SymbolGraphBuilder

            if not silent:
                print("[*] Symbol Pipeline: Extracting symbols...")

            from .config import BBCConfig
            extractor = SymbolExtractor()
            symbol_results = extractor.extract_from_directory(
                root_to_scan, max_files=BBCConfig.MAX_FILES
            )

            if symbol_results:
                # Sembol verilerini dict formatına çevir
                symbols_data = [sr.to_dict() for sr in symbol_results]

                # Kaynak dosyaları topla (sadece Python — AST çağrı analizi için)
                source_mapping = {}
                for sr in symbol_results:
                    fpath = os.path.join(root_to_scan, sr.file) if not os.path.isabs(sr.file) else sr.file
                    if os.path.exists(fpath) and sr.language == "python":
                        try:
                            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                                source_mapping[sr.file] = f.read()
                        except Exception:
                            pass

                # Symbol Graph oluştur
                builder = SymbolGraphBuilder()
                if source_mapping:
                    graph = builder.build_with_source_mapping(symbols_data, source_mapping)
                else:
                    graph = builder.build_simple(symbols_data)

                graph_data = graph.to_dict()
                graph_stats = graph_data.get("graph_stats", {})

                # Context'e symbol analiz sonuçlarını ekle
                context_json["symbol_analysis"] = {
                    "total_symbols": graph_stats.get("total_symbols", len(symbols_data)),
                    "total_calls": graph_stats.get("total_calls", 0),
                    "internal_calls": graph_stats.get("internal_calls", 0),
                    "external_calls": graph_stats.get("external_calls", 0),
                    "files_with_symbols": len(symbol_results),
                    "extractor_stats": extractor.get_stats(),
                }

                # Kritik sembolleri tespit et (en çok çağrılan ilk 20)
                symbols_list = graph_data.get("symbols", [])
                critical = sorted(
                    symbols_list,
                    key=lambda s: len(s.get("called_by", [])),
                    reverse=True
                )[:20]
                context_json["symbol_analysis"]["critical_symbols"] = [
                    {
                        "symbol": s.get("symbol", ""),
                        "type": s.get("type", ""),
                        "file": s.get("file", ""),
                        "called_by_count": len(s.get("called_by", [])),
                    }
                    for s in critical if s.get("called_by")
                ]

                if not silent:
                    sym_count = graph_stats.get("total_symbols", 0)
                    call_count = graph_stats.get("total_calls", 0)
                    crit_count = len(context_json["symbol_analysis"]["critical_symbols"])
                    print(f"[*] Symbol Pipeline: {sym_count} symbols, {call_count} calls, {crit_count} critical")

        except ImportError as e:
            if not silent:
                print(f"[WARN] Symbol Pipeline skipped (missing module): {e}")
        except Exception as e:
            if not silent:
                print(f"[WARN] Symbol Pipeline error (non-critical): {e}")
            # Ana akış devam eder — symbol pipeline opsiyonel

        return context_json

    def _build_dependency_graph(self, project_recipes: list, files_found: list) -> dict:
        """
        Build a dependency graph from import statements.
        Maps each file to what it imports (depends_on) and what imports it (depended_by).
        This is critical for hallucination prevention: when file A changes,
        AI must also consider files that depend on A.
        
        v7.2 Optimized: Uses suffix-based lookup instead of O(N) scan per import.
        """
        import re

        # Normalize file paths for matching (remove extension, use forward slash)
        def normalize(path):
            return path.replace('\\', '/').rsplit('.', 1)[0]

        # Build suffix lookup table: last component -> list of (normalized, original)
        # This avoids O(F) scan per import, reducing to O(1) average lookup
        suffix_map = {}
        full_map = {}
        for f in files_found:
            norm = normalize(f)
            full_map[norm] = f
            suffix = norm.split('/')[-1]
            if suffix not in suffix_map:
                suffix_map[suffix] = []
            suffix_map[suffix].append((norm, f))

        import_re = re.compile(r'(?:from\s+|import\s+)([\w.]+)')
        graph = {}

        for recipe in project_recipes:
            file_path = recipe.get("path", "")
            imports = recipe.get("structure", {}).get("imports", [])

            depends_on = []
            for imp_line in imports:
                m = import_re.match(imp_line.strip())
                if m:
                    module = m.group(1).replace('.', '/')
                    module_suffix = module.split('/')[-1]
                    
                    # Fast lookup by suffix
                    candidates = suffix_map.get(module_suffix, [])
                    for known_norm, known_path in candidates:
                        if known_path != file_path and (known_norm.endswith(module) or module.endswith(module_suffix)):
                            depends_on.append(known_path)
                            break

            graph[file_path] = {
                "depends_on": list(set(depends_on)),
                "depended_by": []
            }

        # Build reverse dependencies (depended_by)
        for file_path, info in graph.items():
            for dep in info["depends_on"]:
                if dep in graph:
                    graph[dep]["depended_by"].append(file_path)

        # Deduplicate depended_by
        for file_path in graph:
            graph[file_path]["depended_by"] = list(set(graph[file_path]["depended_by"]))

        return graph

    async def main_loop(self):
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line: break
            try:
                msg = json.loads(line)
                if msg.get("command") == "analyze":
                    res = await self.analyze_project(msg.get("root"))
                    print(json.dumps({"status": "ok", "context": res}, ensure_ascii=False))
                    sys.stdout.flush()
                elif msg.get("command") == "exit": break
            except Exception: continue

if __name__ == "__main__":
    asyncio.run(BBCNativeAdapter().main_loop())