"""
BBC Change Tracker — Incremental Analysis Engine
Tracks file hashes between analyze runs to detect changed/added/removed files.
Uses BBC mathematics (HMPU risk weighting) to prioritize reseal order.
"""

import os
import json
import hashlib
import time
from typing import Dict, List, Tuple, Optional

from .config import BBCConfig


class ChangeTracker:
    """
    Maintains a change_index.json inside .bbc/ that stores per-file SHA-256
    hashes from the last successful analyze run.  On subsequent runs the
    tracker compares current disk state against the stored index to produce
    a minimal change-set: added / changed / removed files.
    """

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self.bbc_dir = BBCConfig.get_bbc_dir(self.project_root)
        self.index_path = os.path.join(self.bbc_dir, BBCConfig.CHANGE_INDEX_FILE)
        self.segments_path = os.path.join(self.bbc_dir, BBCConfig.CONTEXT_SEGMENTS_FILE)
        self._previous_index: Dict[str, str] = {}  # rel_path -> hash
        self._current_index: Dict[str, str] = {}

        # Polyglot extension list (same as native_adapter)
        self.exts = (
            '.py', '.md', '.json', '.js', '.jsx', '.ts', '.tsx',
            '.html', '.css', '.sql', '.rs', '.go', '.c', '.cpp',
            '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.swift', '.kt'
        )
        self.forbidden_dirs = {
            "node_modules", ".venv", "dist", "build", ".git",
            "__pycache__", "target", ".bbc"
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_previous_index(self) -> bool:
        """Load the stored change_index.json from the last run.
        Returns True if a previous index exists."""
        if not os.path.exists(self.index_path):
            return False
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._previous_index = data.get("file_hashes", {})
            return bool(self._previous_index)
        except Exception:
            return False

    def scan_current_state(self, output_file_abs: Optional[str] = None) -> Dict[str, str]:
        """Walk the project and compute SHA-256 for every source file.
        Returns the current {rel_path: hash} mapping."""
        current: Dict[str, str] = {}
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in self.forbidden_dirs]
            for file in files:
                if file.lower().endswith(self.exts):
                    file_path = os.path.join(root, file)
                    if output_file_abs and os.path.abspath(file_path) == output_file_abs:
                        continue
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                        rel_path = os.path.relpath(file_path, self.project_root)
                        current[rel_path] = file_hash
                    except Exception:
                        continue
                if len(current) >= BBCConfig.MAX_FILES:
                    break
            if len(current) >= BBCConfig.MAX_FILES:
                break
        self._current_index = current
        return current

    def compute_diff(self) -> Dict[str, List[str]]:
        """Compare previous index against current disk state.
        Returns {"added": [...], "changed": [...], "removed": [...]}."""
        prev = self._previous_index
        curr = self._current_index

        added = [p for p in curr if p not in prev]
        removed = [p for p in prev if p not in curr]
        changed = [p for p in curr if p in prev and curr[p] != prev[p]]

        return {
            "added": sorted(added),
            "changed": sorted(changed),
            "removed": sorted(removed),
        }

    def get_affected_files(self) -> List[str]:
        """Return a flat list of files that need re-analysis (added + changed)."""
        diff = self.compute_diff()
        return diff["added"] + diff["changed"]

    def save_index(self) -> str:
        """Persist the current index to .bbc/change_index.json."""
        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "project_root": self.project_root,
            "total_files": len(self._current_index),
            "file_hashes": self._current_index,
        }
        os.makedirs(self.bbc_dir, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return self.index_path

    # ------------------------------------------------------------------
    # Context Segments (per-file context cache)
    # ------------------------------------------------------------------

    def load_segments(self) -> Dict:
        """Load previously cached context segments."""
        if not os.path.exists(self.segments_path):
            return {}
        try:
            with open(self.segments_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_segments(self, segments: Dict) -> str:
        """Persist context segments to .bbc/context_segments.json."""
        os.makedirs(self.bbc_dir, exist_ok=True)
        with open(self.segments_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)
        return self.segments_path

    def merge_segments(self, old_segments: Dict, new_recipes: List[Dict],
                       removed_files: List[str]) -> Dict:
        """Merge new analysis results into existing cached segments.
        - Overwrites segments for re-analyzed files
        - Removes segments for deleted files
        - Keeps untouched segments intact
        Returns the merged segments dict keyed by rel_path."""
        merged = dict(old_segments)

        # Remove deleted
        for rm in removed_files:
            merged.pop(rm, None)

        # Upsert new/changed
        for recipe in new_recipes:
            path = recipe.get("path", "")
            if path:
                merged[path] = recipe

        return merged

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def diff_summary(self, diff: Dict[str, List[str]]) -> str:
        """Human-readable one-line summary of changes."""
        a, c, r = len(diff["added"]), len(diff["changed"]), len(diff["removed"])
        total = a + c + r
        if total == 0:
            return "No changes detected since last analysis."
        parts = []
        if a: parts.append(f"{a} added")
        if c: parts.append(f"{c} changed")
        if r: parts.append(f"{r} removed")
        return f"{total} file(s) affected: {', '.join(parts)}"

    def has_previous_index(self) -> bool:
        return bool(self._previous_index)
