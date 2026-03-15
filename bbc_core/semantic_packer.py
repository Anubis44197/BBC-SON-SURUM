"""
BBC Semantic Packer (Sprint 3)

Intelligent context compression that reduces token usage by:
1. Removing empty/null fields from code_structure recipes
2. Deduplicating repeated import lines across files
3. Collapsing low-value files (small, no symbols) into a summary line
4. Shortening long path prefixes via alias table
5. Stripping metadata that LLMs don't need (hashes, raw stats)

The packer operates on the full or compiled context dict and returns
a packed version with a metrics.packing_savings_pct field.

All operations are lossless in terms of semantic meaning — the LLM
still sees all symbols, structures, and dependencies it needs.
"""

import os
import json
import time
from typing import Dict, List, Set, Tuple
from collections import Counter

from .config import BBCConfig


class SemanticPacker:
    """
    Packs a BBC context dict into a smaller, semantically equivalent form.
    """

    def __init__(self, aggressive: bool = False):
        """
        Args:
            aggressive: If True, apply deeper compression (remove dependency_graph,
                        collapse all small files). Default False for safe mode.
        """
        self.aggressive = aggressive

    def pack(self, context: Dict) -> Dict:
        """
        Apply all packing stages to the context dict.
        Returns a new dict (does not mutate original).
        """
        import copy
        packed = copy.deepcopy(context)

        before_size = len(json.dumps(packed, ensure_ascii=False, default=str))

        # Stage 1: Clean empty fields from code_structure
        packed["code_structure"] = self._clean_recipes(packed.get("code_structure", []))

        # Stage 2: Deduplicate imports across files
        packed["code_structure"], import_index = self._deduplicate_imports(packed["code_structure"])

        # Stage 3: Collapse small/empty files into summary
        packed["code_structure"], collapsed = self._collapse_small_files(packed["code_structure"])

        # Stage 4: Path prefix aliasing
        packed, alias_table = self._alias_paths(packed)

        # Stage 5: Strip LLM-irrelevant metadata
        packed = self._strip_metadata(packed)

        # Stage 6 (aggressive only): Remove full dep graph, keep summary
        if self.aggressive:
            packed = self._compress_dep_graph(packed)

        after_size = len(json.dumps(packed, ensure_ascii=False, default=str))

        # Record packing metrics
        packed.setdefault("metrics", {})
        packed["metrics"]["packing_before_bytes"] = before_size
        packed["metrics"]["packing_after_bytes"] = after_size
        saved_pct = round((1 - after_size / before_size) * 100, 1) if before_size > 0 else 0
        packed["metrics"]["packing_savings_pct"] = saved_pct
        packed["metrics"]["packing_collapsed_files"] = collapsed
        packed["metrics"]["packing_mode"] = "aggressive" if self.aggressive else "safe"

        if import_index:
            packed["_shared_imports"] = import_index

        if alias_table:
            packed["_path_aliases"] = alias_table

        return packed

    # ------------------------------------------------------------------
    # Stage 1: Clean empty fields
    # ------------------------------------------------------------------

    def _clean_recipes(self, recipes: List[Dict]) -> List[Dict]:
        cleaned = []
        for recipe in recipes:
            if not isinstance(recipe, dict):
                continue
            cr = {"path": recipe.get("path", "")}

            # Structure: remove empty lists
            struct = recipe.get("structure", {})
            if isinstance(struct, dict):
                clean_struct = {}
                for k, v in struct.items():
                    if isinstance(v, list) and len(v) == 0:
                        continue
                    if v is None:
                        continue
                    clean_struct[k] = v
                if clean_struct:
                    cr["structure"] = clean_struct

            # Stats: keep only useful ones
            stats = recipe.get("stats", {})
            if isinstance(stats, dict):
                useful_stats = {}
                for k in ("lines", "code_lines"):
                    if k in stats and stats[k]:
                        useful_stats[k] = stats[k]
                if useful_stats:
                    cr["stats"] = useful_stats

            # Preserve relevance score if present (from compiler)
            if "_relevance_score" in recipe:
                cr["_relevance_score"] = recipe["_relevance_score"]

            cleaned.append(cr)
        return cleaned

    # ------------------------------------------------------------------
    # Stage 2: Deduplicate imports
    # ------------------------------------------------------------------

    def _deduplicate_imports(self, recipes: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Find imports that appear in 3+ files, extract them into a shared
        import index, and replace with a reference.
        """
        import_counter: Counter = Counter()
        for recipe in recipes:
            struct = recipe.get("structure", {})
            for imp in struct.get("imports", []):
                import_counter[imp] += 1

        # Shared imports: appear in 3+ files
        shared = {imp for imp, cnt in import_counter.items() if cnt >= 3}
        if not shared:
            return recipes, {}

        # Build index: "I0", "I1", ...
        shared_list = sorted(shared)
        import_index = {f"I{i}": imp for i, imp in enumerate(shared_list)}
        reverse_index = {imp: key for key, imp in import_index.items()}

        # Replace in recipes
        for recipe in recipes:
            struct = recipe.get("structure", {})
            if "imports" in struct:
                new_imports = []
                refs = []
                for imp in struct["imports"]:
                    if imp in reverse_index:
                        refs.append(reverse_index[imp])
                    else:
                        new_imports.append(imp)
                if refs:
                    struct["imports"] = new_imports
                    struct["_shared_import_refs"] = refs

        return recipes, import_index

    # ------------------------------------------------------------------
    # Stage 3: Collapse small files
    # ------------------------------------------------------------------

    def _collapse_small_files(self, recipes: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Files with 0 symbols and <10 code lines get collapsed into
        a single-line summary entry.
        """
        threshold = 10 if not self.aggressive else 30
        kept = []
        collapsed_count = 0

        for recipe in recipes:
            struct = recipe.get("structure", {})
            classes = struct.get("classes", [])
            functions = struct.get("functions", [])
            stats = recipe.get("stats", {})
            code_lines = stats.get("code_lines", 0)

            if not classes and not functions and code_lines < threshold:
                # Collapse to minimal entry
                kept.append({"path": recipe.get("path", ""), "_collapsed": True})
                collapsed_count += 1
            else:
                kept.append(recipe)

        return kept, collapsed_count

    # ------------------------------------------------------------------
    # Stage 4: Path prefix aliasing
    # ------------------------------------------------------------------

    def _alias_paths(self, packed: Dict) -> Tuple[Dict, Dict]:
        """
        Find common path prefixes and replace with short aliases.
        e.g. 'bbc_core/' -> '@c/'
        """
        all_paths = []
        for recipe in packed.get("code_structure", []):
            p = recipe.get("path", "")
            if "/" in p:
                prefix = p.rsplit("/", 1)[0] + "/"
                all_paths.append(prefix)

        if not all_paths:
            return packed, {}

        prefix_counts = Counter(all_paths)
        # Only alias prefixes used 3+ times
        frequent = {prefix for prefix, cnt in prefix_counts.items() if cnt >= 3}
        if not frequent:
            return packed, {}

        # Create alias table
        alias_table = {}
        for i, prefix in enumerate(sorted(frequent, key=len, reverse=True)):
            alias = f"@{chr(97 + i)}/"  # @a/, @b/, ...
            alias_table[alias] = prefix

        # Apply aliases to code_structure paths
        for recipe in packed.get("code_structure", []):
            path = recipe.get("path", "")
            for alias, prefix in alias_table.items():
                if path.startswith(prefix):
                    recipe["path"] = alias + path[len(prefix):]
                    break

        # Apply to hierarchy
        skeleton = packed.get("project_skeleton", {})
        if "hierarchy" in skeleton:
            new_hier = []
            for path in skeleton["hierarchy"]:
                replaced = path
                for alias, prefix in alias_table.items():
                    if path.startswith(prefix):
                        replaced = alias + path[len(prefix):]
                        break
                new_hier.append(replaced)
            skeleton["hierarchy"] = new_hier

        # Apply to dep graph keys
        dep = packed.get("dependency_graph", {})
        if dep:
            new_dep = {}
            for k, v in dep.items():
                nk = k
                for alias, prefix in alias_table.items():
                    if k.startswith(prefix):
                        nk = alias + k[len(prefix):]
                        break
                new_v = {}
                for rel_type in ("depends_on", "depended_by"):
                    old_list = v.get(rel_type, [])
                    new_list = []
                    for p in old_list:
                        np = p
                        for alias, prefix in alias_table.items():
                            if p.startswith(prefix):
                                np = alias + p[len(prefix):]
                                break
                        new_list.append(np)
                    new_v[rel_type] = new_list
                new_dep[nk] = new_v
            packed["dependency_graph"] = new_dep

        return packed, alias_table

    # ------------------------------------------------------------------
    # Stage 5: Strip LLM-irrelevant metadata
    # ------------------------------------------------------------------

    def _strip_metadata(self, packed: Dict) -> Dict:
        """Remove fields that waste tokens but don't help the LLM."""
        # Remove hash from stats (verifier uses it, LLM doesn't need it)
        for recipe in packed.get("code_structure", []):
            stats = recipe.get("stats", {})
            stats.pop("hash", None)
            stats.pop("raw_bytes", None)

        # Remove index_path (internal)
        packed.pop("index_path", None)

        # Remove incremental metadata
        packed.pop("incremental", None)

        # Trim metrics to essentials
        m = packed.get("metrics", {})
        keep_keys = {"files_scanned", "total_lines", "code_lines",
                      "raw_tokens", "context_tokens", "savings_pct",
                      "packing_before_bytes", "packing_after_bytes",
                      "packing_savings_pct", "packing_collapsed_files",
                      "packing_mode", "full_context_tokens_est",
                      "compiled_tokens_est", "task_savings_pct"}
        for k in list(m.keys()):
            if k not in keep_keys:
                del m[k]

        return packed

    # ------------------------------------------------------------------
    # Stage 6: Compress dependency graph (aggressive)
    # ------------------------------------------------------------------

    def _compress_dep_graph(self, packed: Dict) -> Dict:
        """Replace full dep graph with a summary for max compression."""
        dep = packed.get("dependency_graph", {})
        if not dep:
            return packed

        total_deps = sum(len(v.get("depends_on", [])) for v in dep.values())
        total_rev = sum(len(v.get("depended_by", [])) for v in dep.values())

        # Find most-depended-on files (top 5)
        dep_counts = {}
        for k, v in dep.items():
            dep_counts[k] = len(v.get("depended_by", []))
        top_deps = sorted(dep_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        packed["dependency_summary"] = {
            "total_edges": total_deps,
            "total_reverse_edges": total_rev,
            "most_depended": [{"file": f, "depended_by": c} for f, c in top_deps if c > 0],
        }
        del packed["dependency_graph"]

        return packed

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------

    def save_packed(self, packed: Dict, output_path: str = None,
                    project_root: str = None) -> str:
        if output_path is None:
            root = project_root or packed.get("project_skeleton", {}).get("root", ".")
            bbc_dir = BBCConfig.get_bbc_dir(root)
            output_path = os.path.join(bbc_dir, "packed_context.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(packed, f, indent=2, ensure_ascii=False, default=str)
        return output_path
