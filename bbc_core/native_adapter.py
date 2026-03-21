import sys
import json
import os
import asyncio
import hashlib
from collections import Counter
from .hmpu_engine import HMPUEngine
from .state_manager import StateManager
from .hmpu_indexer import HMPUIndexer
from .config import BBCConfig

# Import the Polyglot Quantizer (tek dogruluk kaynagi: bbc_core)
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

    def _summarize_hierarchy(self, files: list):
        """Keep only a preview list to avoid bloated context payloads on huge repos."""
        raw_limit = os.environ.get("BBC_HIERARCHY_PREVIEW_LIMIT", "200").strip()
        try:
            preview_limit = int(raw_limit)
        except ValueError:
            preview_limit = 200
        preview_limit = max(0, min(preview_limit, 5000))

        sorted_files = sorted(files)
        if preview_limit == 0:
            return [], True, len(sorted_files), preview_limit
        if len(sorted_files) <= preview_limit:
            return sorted_files, False, len(sorted_files), preview_limit
        return sorted_files[:preview_limit], True, len(sorted_files), preview_limit

    async def analyze_project(self, target_root, output_file=None, silent: bool = False):
        root_to_scan = os.path.abspath(target_root) if target_root else os.getcwd()
        output_file_abs = os.path.abspath(output_file) if output_file else None
        
        files_found = []
        project_recipes = []
        total_raw_bytes = 0
        total_lines = 0
        total_code_lines = 0
        
        # Shared scan policy
        exts = BBCConfig.get_scan_extensions()
        forbidden_dirs = BBCConfig.get_forbidden_scan_dirs()
        max_scan_files_raw = os.environ.get("BBC_MAX_SCAN_FILES", "").strip()
        try:
            max_scan_files = int(max_scan_files_raw) if max_scan_files_raw else int(BBCConfig.MAX_FILES)
        except Exception:
            max_scan_files = int(BBCConfig.MAX_FILES)
        max_scan_files = max(1, max_scan_files)

        enable_symbol_pipeline = os.environ.get("BBC_ENABLE_SYMBOL_PIPELINE", "1").strip().lower() in {"1", "true", "yes", "on"}
        symbol_max_files_raw = os.environ.get("BBC_SYMBOL_MAX_FILES", "").strip()
        try:
            symbol_max_files = int(symbol_max_files_raw) if symbol_max_files_raw else max_scan_files
        except Exception:
            symbol_max_files = max_scan_files
        symbol_max_files = max(1, symbol_max_files)

        comment_prefixes = ('#', '//', '/*', '*')
        skipped_dirs_count = 0
        skipped_non_source_files = 0
        skipped_output_file = 0
        discovered_total_files = 0
        scan_limit_hit = False
        top_level_skip_counts = Counter()
        
        if not silent:
            print(f"[*] Polyglot Scan Started: {root_to_scan}")

        # RECURSIVE SCAN & QUANTIZATION
        for root, dirs, files in os.walk(root_to_scan):
            original_dirs = list(dirs)
            dirs[:] = [d for d in dirs if d not in forbidden_dirs]
            removed_dirs = [d for d in original_dirs if d not in dirs]
            skipped_dirs_count += len(removed_dirs)
            if removed_dirs:
                rel_root = os.path.relpath(root, root_to_scan)
                root_prefix = "" if rel_root == "." else rel_root.replace("\\", "/") + "/"
                for d in removed_dirs:
                    top_level_skip_counts[root_prefix + d] += 1
            
            for file in files:
                discovered_total_files += 1
                if file.lower().endswith(exts):
                    file_path = os.path.join(root, file)
                    
                    # Skip the output file itself (Self-Reference Prevention)
                    if output_file_abs and os.path.abspath(file_path) == output_file_abs:
                        skipped_output_file += 1
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
                else:
                    skipped_non_source_files += 1
                if len(files_found) >= max_scan_files:
                    scan_limit_hit = True
                    if not silent:
                        print(f"[WARN] File limit reached ({max_scan_files:,}). Remaining files skipped.")
                    break
            if len(files_found) >= max_scan_files: break

        if not silent:
            print(f"[*] Scan complete: {len(files_found)} files found.")

        # Build dependency graph from import statements
        dependency_graph = self._build_dependency_graph(project_recipes, files_found)

        # Build Context JSON
        import time as _time
        _generated_at = _time.strftime("%Y-%m-%dT%H:%M:%S")

        hierarchy_preview, hierarchy_truncated, hierarchy_total, preview_limit = self._summarize_hierarchy(files_found)

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
                "hierarchy": hierarchy_preview,
                "hierarchy_total": hierarchy_total,
                "hierarchy_truncated": hierarchy_truncated,
                "hierarchy_preview_limit": preview_limit,
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

        context_json["scan_report"] = {
            "source_extensions": list(exts),
            "excluded_dirs": sorted(forbidden_dirs),
            "max_scan_files": max_scan_files,
            "scan_limit_hit": scan_limit_hit,
            "files_discovered": discovered_total_files,
            "files_scanned": len(files_found),
            "files_skipped_non_source": skipped_non_source_files,
            "files_skipped_output_file": skipped_output_file,
            "excluded_dirs_hits": skipped_dirs_count,
            "top_excluded_paths": [
                {"path": key, "hits": value}
                for key, value in top_level_skip_counts.most_common(20)
            ],
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

        # ─── SYMBOL PIPELINE (Opsiyonel — error verirse ana akisi bozmaz) ───
        if enable_symbol_pipeline:
            try:
                from .symbol_extractor import SymbolExtractor
                from .symbol_graph import SymbolGraphBuilder

                if not silent:
                    print("[*] Symbol Pipeline: Extracting symbols...")

                extractor = SymbolExtractor()
                symbol_results = extractor.extract_from_directory(
                    root_to_scan, max_files=symbol_max_files
                )

                if symbol_results:
                    # Sembol verilerini dict formatina cevir
                    symbols_data = [sr.to_dict() for sr in symbol_results]

                    # Kaynak files topla (only Python — AST call analysis for)
                    source_mapping = {}
                    for sr in symbol_results:
                        fpath = os.path.join(root_to_scan, sr.file) if not os.path.isabs(sr.file) else sr.file
                        if os.path.exists(fpath) and sr.language == "python":
                            try:
                                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                                    source_mapping[sr.file] = f.read()
                            except Exception:
                                pass

                    # Symbol Graph create
                    builder = SymbolGraphBuilder()
                    if source_mapping:
                        graph = builder.build_with_source_mapping(symbols_data, source_mapping)
                    else:
                        graph = builder.build_simple(symbols_data)

                    graph_data = graph.to_dict()
                    graph_stats = graph_data.get("graph_stats", {})

                    # Context'e symbol analysis sonuclarini ekle
                    context_json["symbol_analysis"] = {
                        "total_symbols": graph_stats.get("total_symbols", len(symbols_data)),
                        "total_calls": graph_stats.get("total_calls", 0),
                        "internal_calls": graph_stats.get("internal_calls", 0),
                        "external_calls": graph_stats.get("external_calls", 0),
                        "files_with_symbols": len(symbol_results),
                        "extractor_stats": extractor.get_stats(),
                    }

                    # Kritik symbols tespit et (en cok called ilk 20)
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
        else:
            context_json["symbol_analysis"] = {
                "enabled": False,
                "reason": "disabled_by_default_set_BBC_ENABLE_SYMBOL_PIPELINE=1_to_enable"
            }

        # ── SECRET SIGNAL DETECTION (opsiyonel — flag ile aktif) ───────────
        detect_secrets = getattr(self, '_detect_secrets', False) or BBCConfig.BBC_ENABLE_SECRET_DETECT
        if detect_secrets:
            try:
                from .secret_detector import scan_project, compute_secret_risk_score, compute_aura_secret_adjustment
                if not silent:
                    print("[*] Secret Signal Detection: Scanning...")
                scan_result = scan_project(
                    root_to_scan,
                    min_confidence=BBCConfig.SECRET_MIN_CONFIDENCE,
                    entropy_threshold=BBCConfig.SECRET_ENTROPY_THRESHOLD,
                    file_list=files_found,
                    silent=silent,
                )
                risk_score = compute_secret_risk_score(scan_result)
                aura_adj = compute_aura_secret_adjustment(risk_score, BBCConfig.SECRET_AURA_MAX_INFLUENCE)
                context_json["secrets_scan"] = {
                    **scan_result.to_summary_dict(),
                    "risk_score": round(risk_score, 4),
                    "aura_adjustment": round(aura_adj, 4),
                }
                # Inject risk into active governor instance used by the engine.
                try:
                    if getattr(self.engine, "governor", None):
                        self.engine.governor.set_secret_risk(
                            risk_score,
                            BBCConfig.SECRET_AURA_MAX_INFLUENCE,
                        )
                except Exception:
                    pass
                if not silent:
                    total = scan_result.total_findings
                    risk_pct = round(risk_score * 100, 1)
                    print(f"[*] Secret Signal Detection: {total} signal(s), risk={risk_pct}%, aura_adj={aura_adj:+.4f}")
            except Exception as e:
                if not silent:
                    print(f"[WARN] Secret Detection skipped: {e}")
                context_json["secrets_scan"] = {"enabled": False, "reason": str(e)}
        else:
            context_json["secrets_scan"] = {"enabled": False}

        return context_json

    async def analyze_project_incremental(self, target_root, output_file=None, silent: bool = False):
        """
        Incremental Analysis — only re-processes files that changed since
        the last full/incremental analyze.  Falls back to full analysis when
        no previous change index exists.
        """
        from .change_tracker import ChangeTracker
        from .config import BBCConfig
        import time as _time

        root_to_scan = os.path.abspath(target_root) if target_root else os.getcwd()
        output_file_abs = os.path.abspath(output_file) if output_file else None

        tracker = ChangeTracker(root_to_scan)
        has_prev = tracker.load_previous_index()
        tracker.scan_current_state(output_file_abs)

        if not has_prev:
            if not silent:
                print("[*] No previous index found — running full analysis.")
            ctx = await self.analyze_project(target_root, output_file=output_file, silent=silent)
            tracker.save_index()
            segments = {}
            for recipe in ctx.get("code_structure", []):
                path = recipe.get("path", "")
                if path:
                    segments[path] = recipe
            tracker.save_segments(segments)
            ctx["incremental"] = {"mode": "full", "reason": "no_previous_index"}
            return ctx

        diff = tracker.compute_diff()
        affected = tracker.get_affected_files()

        if not silent:
            print(f"[*] Incremental Scan: {tracker.diff_summary(diff)}")

        if not affected and not diff["removed"]:
            if not silent:
                print("[*] No changes — loading cached context.")
            ctx_path = BBCConfig.get_context_path(root_to_scan)
            if os.path.exists(ctx_path):
                with open(ctx_path, "r", encoding="utf-8") as f:
                    ctx = json.load(f)
                ctx["incremental"] = {"mode": "cached", "changes": 0}
                return ctx
            if not silent:
                print("[*] Cache missing — running full analysis.")
            ctx = await self.analyze_project(target_root, output_file=output_file, silent=silent)
            tracker.save_index()
            return ctx

        exts = ('.py', '.md', '.json', '.js', '.jsx', '.ts', '.tsx',
                '.html', '.css', '.sql', '.rs', '.go', '.c', '.cpp',
                '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt')
        comment_prefixes = ('#', '//', '/*', '*')

        new_recipes = []
        inc_raw_bytes = 0

        for rel_path in affected:
            abs_path = os.path.join(root_to_scan, rel_path)
            if not os.path.exists(abs_path):
                continue
            ext = os.path.splitext(rel_path)[1].lower()
            if not ext or ext not in exts:
                continue
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                content_bytes = content.encode('utf-8')
                inc_raw_bytes += len(content_bytes)
                file_total_lines = 0
                file_code_lines = 0
                for line in content.splitlines():
                    file_total_lines += 1
                    stripped = line.strip()
                    if stripped and not stripped.startswith(comment_prefixes):
                        file_code_lines += 1

                analysis = self.quantizer.process_content(content, file_ext=ext)
                file_hash = hashlib.sha256(content_bytes).hexdigest()
                self.indexer.add_to_index(content, {"path": rel_path, "hash": file_hash})

                new_recipes.append({
                    "path": rel_path,
                    "structure": analysis["structure"],
                    "stats": {**analysis["stats"], "lines": file_total_lines,
                              "code_lines": file_code_lines, "hash": file_hash}
                })
            except Exception:
                continue

        if not silent:
            print(f"[*] Incremental: {len(new_recipes)} file(s) re-analyzed.")

        old_segments = tracker.load_segments()
        merged = tracker.merge_segments(old_segments, new_recipes, diff["removed"])
        tracker.save_segments(merged)
        tracker.save_index()

        all_recipes = list(merged.values())
        all_files = list(merged.keys())

        dependency_graph = self._build_dependency_graph(all_recipes, all_files)
        _generated_at = _time.strftime("%Y-%m-%dT%H:%M:%S")

        total_lines = 0
        total_code_lines = 0
        for recipe in all_recipes:
            stats = recipe.get("stats", {})
            total_lines += stats.get("lines", 0)
            total_code_lines += stats.get("code_lines", 0)

        hierarchy_preview, hierarchy_truncated, hierarchy_total, preview_limit = self._summarize_hierarchy(all_files)

        context_json = {
            "bbc_instructions_version": "1.0",
            "context_schema_version": "8.5",
            "generated_at": _generated_at,
            "context_fresh": True,
            "fail_policy": "fail_closed",
            "enforcement_level": "strict",
            "project_skeleton": {
                "root": root_to_scan,
                "file_count": len(all_files),
                "hierarchy": hierarchy_preview,
                "hierarchy_total": hierarchy_total,
                "hierarchy_truncated": hierarchy_truncated,
                "hierarchy_preview_limit": preview_limit,
            },
            "code_structure": all_recipes,
            "dependency_graph": dependency_graph,
            "constraint_status": "verified",
            "metrics": {
                "files_scanned": len(all_files),
                "total_lines": total_lines,
                "code_lines": total_code_lines,
                "raw_bytes": inc_raw_bytes,
                "context_bytes": 0,
                "compression_ratio": 0.0,
                "unified_savings_confidence": self.engine.get_aura_confidence()
            },
            "incremental": {
                "mode": "incremental",
                "added": len(diff["added"]),
                "changed": len(diff["changed"]),
                "removed": len(diff["removed"]),
                "reanalyzed": len(new_recipes),
                "cached": len(all_files) - len(new_recipes),
            }
        }

        context_json["scan_report"] = {
            "mode": "incremental",
            "source_extensions": list(BBCConfig.get_scan_extensions()),
            "excluded_dirs": sorted(BBCConfig.get_forbidden_scan_dirs()),
            "files_total": len(all_files),
            "files_reanalyzed": len(new_recipes),
            "files_cached": len(all_files) - len(new_recipes),
            "files_added": len(diff["added"]),
            "files_changed": len(diff["changed"]),
            "files_removed": len(diff["removed"]),
        }

        est_recipe_bytes = len(all_recipes) * 200
        est_skeleton_bytes = len(all_files) * 50
        context_bytes = est_recipe_bytes + est_skeleton_bytes + 500
        context_json["metrics"]["context_bytes"] = context_bytes

        # ── SECRET SIGNAL DETECTION — Incremental (sadece değişen dosyalar) ──
        detect_secrets = getattr(self, '_detect_secrets', False) or BBCConfig.BBC_ENABLE_SECRET_DETECT
        if detect_secrets and affected:
            try:
                from .secret_detector import scan_project, compute_secret_risk_score, compute_aura_secret_adjustment
                if not silent:
                    print("[*] Secret Signal Detection (incremental): Scanning changed files...")
                scan_result = scan_project(
                    root_to_scan,
                    min_confidence=BBCConfig.SECRET_MIN_CONFIDENCE,
                    entropy_threshold=BBCConfig.SECRET_ENTROPY_THRESHOLD,
                    file_list=list(affected),
                    silent=silent,
                )
                risk_score = compute_secret_risk_score(scan_result)
                aura_adj = compute_aura_secret_adjustment(risk_score, BBCConfig.SECRET_AURA_MAX_INFLUENCE)
                context_json["secrets_scan"] = {
                    **scan_result.to_summary_dict(),
                    "risk_score": round(risk_score, 4),
                    "aura_adjustment": round(aura_adj, 4),
                    "mode": "incremental",
                    "files_checked": len(affected),
                }
                try:
                    if getattr(self.engine, "governor", None):
                        self.engine.governor.set_secret_risk(
                            risk_score,
                            BBCConfig.SECRET_AURA_MAX_INFLUENCE,
                        )
                except Exception:
                    pass
                if not silent:
                    total = scan_result.total_findings
                    print(f"[*] Secret Signal Detection (incremental): {total} signal(s) in {len(affected)} changed file(s)")
            except Exception as e:
                if not silent:
                    print(f"[WARN] Secret Detection (incremental) skipped: {e}")
                context_json["secrets_scan"] = {"enabled": False, "reason": str(e)}
        elif not detect_secrets:
            context_json["secrets_scan"] = {"enabled": False}

        return context_json

    def _build_dependency_graph(self, project_recipes: list, files_found: list) -> dict:
        """
        Build a dependency graph from import statements.
        Maps each file to what it imports (depends_on) and what imports it (depended_by).
        v7.2 Optimized: Uses suffix-based lookup instead of O(N) scan per import.
        """
        import re

        def normalize(path):
            return path.replace('\\', '/').rsplit('.', 1)[0]

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

                    candidates = suffix_map.get(module_suffix, [])
                    for known_norm, known_path in candidates:
                        if known_path != file_path and (known_norm.endswith(module) or module.endswith(module_suffix)):
                            depends_on.append(known_path)
                            break

            graph[file_path] = {
                "depends_on": list(set(depends_on)),
                "depended_by": []
            }

        for file_path, info in graph.items():
            for dep in info["depends_on"]:
                if dep in graph:
                    graph[dep]["depended_by"].append(file_path)

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