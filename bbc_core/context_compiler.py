"""
BBC Task-Aware Context Compiler (Sprint 2)

Generates optimized, task-specific context from the full bbc_context.json.
Instead of sending the entire project context to an LLM, this compiler
filters and ranks files/symbols based on the task type, target file,
and dependency graph — drastically reducing token usage while keeping
the LLM focused on what matters.

Task Types:
  - bugfix   : Focus on target file + direct deps + error-prone neighbours
  - feature  : Focus on related modules + interfaces + critical symbols
  - refactor : Focus on target file + all dependents (blast radius)
  - review   : Broad view — critical symbols + high-churn files + structure
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Set

from .config import BBCConfig


# ---------------------------------------------------------------------------
# Task profile definitions
# ---------------------------------------------------------------------------

TASK_PROFILES = {
    "bugfix": {
        "description": "Bug fix — target file + direct dependencies + error context",
        "include_target": True,
        "include_direct_deps": True,
        "include_reverse_deps": True,
        "include_indirect_deps": False,
        "include_critical_symbols": False,
        "depth": 1,
        "max_files": 15,
        "priority_weight": {"target": 1.0, "direct_dep": 0.8, "reverse_dep": 0.6},
    },
    "feature": {
        "description": "New feature — related modules + interfaces + critical symbols",
        "include_target": True,
        "include_direct_deps": True,
        "include_reverse_deps": False,
        "include_indirect_deps": True,
        "include_critical_symbols": True,
        "depth": 2,
        "max_files": 25,
        "priority_weight": {"target": 1.0, "direct_dep": 0.7, "indirect_dep": 0.4, "critical": 0.5},
    },
    "refactor": {
        "description": "Refactor — target + full blast radius (all dependents)",
        "include_target": True,
        "include_direct_deps": True,
        "include_reverse_deps": True,
        "include_indirect_deps": True,
        "include_critical_symbols": False,
        "depth": 3,
        "max_files": 30,
        "priority_weight": {"target": 1.0, "direct_dep": 0.8, "reverse_dep": 0.9, "indirect_dep": 0.5},
    },
    "review": {
        "description": "Code review — broad structural view + critical symbols",
        "include_target": False,
        "include_direct_deps": False,
        "include_reverse_deps": False,
        "include_indirect_deps": False,
        "include_critical_symbols": True,
        "depth": 0,
        "max_files": 40,
        "priority_weight": {"critical": 0.8, "structure": 0.6},
    },
}


class TaskContextCompiler:
    """
    Compiles a task-specific subset of the full BBC context.
    Uses the dependency graph + symbol analysis to select only the
    files and symbols relevant to the given task.
    """

    def __init__(self, context_path: str):
        if not os.path.exists(context_path):
            raise FileNotFoundError(f"Context not found: {context_path}")
        with open(context_path, "r", encoding="utf-8") as f:
            self.full_context = json.load(f)

        self.context_path = context_path
        self.dep_graph: Dict = self.full_context.get("dependency_graph", {})
        self.code_structure: List[Dict] = self.full_context.get("code_structure", [])
        self.symbol_analysis: Dict = self.full_context.get("symbol_analysis", {})
        self.project_root: str = self.full_context.get("project_skeleton", {}).get("root", "")

        # Build path -> recipe lookup (normalize to forward slash)
        self._recipe_map: Dict[str, Dict] = {}
        for recipe in self.code_structure:
            path = recipe.get("path", "").replace("\\", "/")
            if path:
                recipe["path"] = path  # normalize in-place
                self._recipe_map[path] = recipe

        # Also normalize dep_graph keys
        normalized_graph: Dict = {}
        for k, v in self.dep_graph.items():
            nk = k.replace("\\", "/")
            normalized_graph[nk] = {
                "depends_on": [d.replace("\\", "/") for d in v.get("depends_on", [])],
                "depended_by": [d.replace("\\", "/") for d in v.get("depended_by", [])],
            }
        self.dep_graph = normalized_graph

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self, task: str, target_file: str = None,
                target_symbols: List[str] = None) -> Dict:
        """
        Compile task-aware context.

        Args:
            task: One of 'bugfix', 'feature', 'refactor', 'review'
            target_file: Relative path to the file being worked on
            target_symbols: Optional list of symbol names being changed

        Returns: Compiled context dict ready for LLM consumption
        """
        if task not in TASK_PROFILES:
            raise ValueError(f"Unknown task type '{task}'. Must be one of: {list(TASK_PROFILES.keys())}")

        profile = TASK_PROFILES[task]

        # Normalize target file path
        if target_file:
            target_file = target_file.replace("\\", "/")
            # Try to match against known paths
            if target_file not in self._recipe_map:
                # Try relative resolution
                for known in self._recipe_map:
                    if known.endswith(target_file) or target_file.endswith(known):
                        target_file = known
                        break

        # Collect relevant files with priority scores
        scored_files: Dict[str, float] = {}

        # 1. Target file
        if profile["include_target"] and target_file and target_file in self._recipe_map:
            scored_files[target_file] = profile["priority_weight"].get("target", 1.0)

        # 2. Direct dependencies (files target imports)
        if profile["include_direct_deps"] and target_file:
            for dep in self._get_direct_deps(target_file):
                w = profile["priority_weight"].get("direct_dep", 0.7)
                scored_files[dep] = max(scored_files.get(dep, 0), w)

        # 3. Reverse dependencies (files that import target)
        if profile["include_reverse_deps"] and target_file:
            for dep in self._get_reverse_deps(target_file):
                w = profile["priority_weight"].get("reverse_dep", 0.6)
                scored_files[dep] = max(scored_files.get(dep, 0), w)

        # 4. Indirect dependencies (transitive)
        if profile["include_indirect_deps"] and target_file:
            depth = profile.get("depth", 2)
            for dep in self._get_transitive_deps(target_file, depth):
                if dep not in scored_files:
                    w = profile["priority_weight"].get("indirect_dep", 0.4)
                    scored_files[dep] = max(scored_files.get(dep, 0), w)

        # 5. Critical symbols (high fan-in files)
        if profile["include_critical_symbols"]:
            critical = self.symbol_analysis.get("critical_symbols", [])
            for sym in critical:
                sym_file = sym.get("file", "")
                if sym_file and sym_file in self._recipe_map:
                    w = profile["priority_weight"].get("critical", 0.5)
                    scored_files[sym_file] = max(scored_files.get(sym_file, 0), w)

        # 6. For review task with no target, include top structure files
        if task == "review" and not scored_files:
            for recipe in self.code_structure:
                path = recipe.get("path", "")
                stats = recipe.get("stats", {})
                code_lines = stats.get("code_lines", 0)
                if code_lines > 0:
                    # Score by code complexity (lines as proxy)
                    score = min(1.0, code_lines / 500.0) * profile["priority_weight"].get("structure", 0.6)
                    scored_files[path] = max(scored_files.get(path, 0), score)

        # Sort by score and cap
        max_files = profile["max_files"]
        ranked = sorted(scored_files.items(), key=lambda x: x[1], reverse=True)[:max_files]

        # Build compiled context
        compiled_recipes = []
        compiled_files = []
        total_lines = 0
        total_code_lines = 0

        for file_path, score in ranked:
            recipe = self._recipe_map.get(file_path)
            if not recipe:
                continue
            compiled_recipes.append({
                **recipe,
                "_relevance_score": round(score, 3),
            })
            compiled_files.append(file_path)
            stats = recipe.get("stats", {})
            total_lines += stats.get("lines", 0)
            total_code_lines += stats.get("code_lines", 0)

        # Build filtered dependency graph (only compiled files)
        compiled_deps = {}
        for fp in compiled_files:
            if fp in self.dep_graph:
                entry = self.dep_graph[fp]
                compiled_deps[fp] = {
                    "depends_on": [d for d in entry.get("depends_on", []) if d in compiled_files],
                    "depended_by": [d for d in entry.get("depended_by", []) if d in compiled_files],
                }

        # Filtered critical symbols
        compiled_critical = []
        if self.symbol_analysis.get("critical_symbols"):
            compiled_file_set = set(compiled_files)
            for sym in self.symbol_analysis["critical_symbols"]:
                if sym.get("file", "") in compiled_file_set:
                    compiled_critical.append(sym)

        # Estimate token savings
        full_context_str = json.dumps(self.full_context, ensure_ascii=False, default=str)
        compiled_output = {
            "bbc_instructions_version": self.full_context.get("bbc_instructions_version", "1.0"),
            "context_schema_version": self.full_context.get("context_schema_version", "8.5"),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "context_fresh": self.full_context.get("context_fresh", True),
            "fail_policy": self.full_context.get("fail_policy", "fail_closed"),
            "enforcement_level": self.full_context.get("enforcement_level", "strict"),
            "task_context": {
                "task_type": task,
                "task_profile": profile["description"],
                "target_file": target_file,
                "target_symbols": target_symbols or [],
                "files_included": len(compiled_files),
                "files_total": len(self.code_structure),
                "file_reduction_pct": round(
                    (1 - len(compiled_files) / max(len(self.code_structure), 1)) * 100, 1
                ),
            },
            "project_skeleton": {
                "root": self.project_root,
                "file_count": len(compiled_files),
                "hierarchy": compiled_files,
            },
            "code_structure": compiled_recipes,
            "dependency_graph": compiled_deps,
            "constraint_status": self.full_context.get("constraint_status", "verified"),
            "critical_symbols": compiled_critical,
            "metrics": {
                "files_scanned": len(compiled_files),
                "total_lines": total_lines,
                "code_lines": total_code_lines,
            },
        }

        compiled_str = json.dumps(compiled_output, ensure_ascii=False, default=str)
        full_tokens_est = len(full_context_str) // 4
        compiled_tokens_est = len(compiled_str) // 4
        saved = full_tokens_est - compiled_tokens_est
        pct = (saved / full_tokens_est * 100) if full_tokens_est > 0 else 0

        compiled_output["metrics"]["full_context_tokens_est"] = full_tokens_est
        compiled_output["metrics"]["compiled_tokens_est"] = compiled_tokens_est
        compiled_output["metrics"]["task_savings_pct"] = round(pct, 1)

        return compiled_output

    # ------------------------------------------------------------------
    # Dependency helpers
    # ------------------------------------------------------------------

    def _get_direct_deps(self, file_path: str) -> List[str]:
        entry = self.dep_graph.get(file_path, {})
        return entry.get("depends_on", [])

    def _get_reverse_deps(self, file_path: str) -> List[str]:
        entry = self.dep_graph.get(file_path, {})
        return entry.get("depended_by", [])

    def _get_transitive_deps(self, file_path: str, max_depth: int = 2) -> List[str]:
        visited: Set[str] = set()
        queue = [(file_path, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            entry = self.dep_graph.get(current, {})
            for dep in entry.get("depends_on", []) + entry.get("depended_by", []):
                if dep not in visited:
                    queue.append((dep, depth + 1))
        visited.discard(file_path)
        return list(visited)

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------

    def save_compiled(self, compiled: Dict, output_path: str = None) -> str:
        if output_path is None:
            bbc_dir = BBCConfig.get_bbc_dir(self.project_root)
            task = compiled.get("task_context", {}).get("task_type", "unknown")
            output_path = os.path.join(bbc_dir, f"compiled_{task}.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(compiled, f, indent=2, ensure_ascii=False, default=str)
        return output_path
