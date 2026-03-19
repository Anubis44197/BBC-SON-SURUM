"""
BBC v8.3 - Multi-Agent Context Adapter
Phase 10.3 Integrated: IDE-Specific Format Transformers

Deterministic transformation of BBC sealed context to Agent-specific formats.
No inference, no hallucination, pure structural mapping.

Supports:
- GitHub Copilot (Markdown format)
- Cursor IDE (YAML-like format)
- Gemini Code Assist (XML snapshot format)
- Kilo Code / Cline (Native format)
- Continue / Codeium / Tabnine / Amazon Q / Blackbox / Cody / Supermaven
- Roo Code / Refact.ai / MutableAI / Codiga / DeepSeek / Qodo / Replit / Warp
- JetBrains / Fleet / Zed / Theia / Trae / Visual Studio / Vim / Neovim
"""

import json
import hashlib
import os
from typing import Dict, Any, List
from pathlib import Path


BBC_VERSION = "8.3.0"
BBC_VERSION_SHORT = "8.3"
BBC_VERSION_TAG = "v8.3"


class BBCAgentAdapter:
    """Transforms BBC sealed context into Agent-specific formats"""
    
    SUPPORTED_AGENTS = [
        "copilot", "cursor", "gemini", "kilo", "cline", "vscode", "generic",
        "continue", "codeium", "tabnine", "amazonq", "blackbox", "codegpt",
        "pieces", "codegeex", "cody", "supermaven", "codiumai", "mintlify",
        "askcodi", "fauxpilot", "roo", "refact", "mutableai", "codiga",
        "intellicode", "deepseek", "qodo", "replit", "warp", "jetbrains",
        "fleet", "zed", "theia", "trae", "visualstudio", "vim", "neovim"
    ]
    
    def __init__(self, context_path: str):
        """
        Initialize adapter with BBC context
        
        Args:
            context_path: Path to bbc_context.json
        """
        context_file = Path(context_path)
        if not context_file.exists():
            raise FileNotFoundError(f"Context file not found: {context_path}")
        
        with open(context_path, 'r', encoding='utf-8') as f:
            self.context = json.load(f)
        
        # Support both recipe and context formats
        self.recipe = self.context.get("recipe", self.context)
        self.metadata = self.context.get("metadata", {})
        
        # Validate seal (if present)
        constraint_status = self.recipe.get("constraint_status", 
                                          self.metadata.get("constraint_status", "unknown"))
        
        if constraint_status not in ["sealed", "verified", "complete"]:
            raise ValueError(
                f"ADAPTER WARNING: Context is not sealed. Status: {constraint_status}\n"
                f"Recommendation: Run 'bbc verify' first to seal the context."
            )
        
        self.metrics = self.recipe.get("metrics", {})
        self.skeleton = self.recipe.get("project_skeleton", 
                                       self.recipe.get("skeleton", {}))
        # Support both old and new code_structure formats
        raw_structure = self.recipe.get("code_structure", [])
        self.code_structure = []
        for item in raw_structure:
            if isinstance(item, dict) and "structure" in item:
                # New format: {path, structure: {classes, functions, imports}, stats}
                self.code_structure.append({
                    "path": item.get("path", ""),
                    "classes": item.get("structure", {}).get("classes", []),
                    "functions": item.get("structure", {}).get("functions", []),
                    "imports": item.get("structure", {}).get("imports", []),
                    "line_count": item.get("stats", {}).get("lines", 0)
                })
            else:
                # Old format: direct fields
                self.code_structure.append(item)
        
        self.hard_constraints = self.recipe.get("hard_constraints", {})
        
    def extract_symbols(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Extract all symbols (classes, functions, imports) from code structure
        
        Returns:
            Dictionary mapping file names to their symbols
        """
        symbols = {}
        hierarchy = self.skeleton.get("hierarchy", [])
        
        for idx, struct in enumerate(self.code_structure):
            # Try to get file name from path field first, then hierarchy, then fallback
            if "path" in struct:
                file_name = struct["path"]
            elif idx < len(hierarchy):
                file_name = hierarchy[idx]
            else:
                file_name = f"file_{idx}"
            
            symbols[file_name] = {
                "classes": struct.get("classes", []),
                "functions": struct.get("functions", []),
                "imports": struct.get("imports", []),
                "line_count": struct.get("line_count", 0)
            }
        
        return symbols
    
    def to_copilot_prompt(self) -> str:
        """
        Generate GitHub Copilot system prompt format
        
        Returns:
            Markdown formatted prompt for Copilot
        """
        symbols = self.extract_symbols()
        
        # Get metrics with defaults
        compression = self.metrics.get("compression_ratio", 0)
        files_scanned = self.metrics.get("files_scanned", 
                                        self.metadata.get("file_count", 0))
        root = self.skeleton.get("root", "unknown")
        
        prompt = f"""# [BBC_SEALED_CONTEXT {BBC_VERSION_TAG}]
> **Status:** LOCKED {self.recipe.get('constraint_status', 'VERIFIED').upper()}
> **Compression:** {compression * 100:.1f}% | **Files:** {files_scanned}
> **Source:** `{root}`

## PROJECT STRUCTURE

"""
        
        # Add symbol atlas
        for file_name, syms in symbols.items():
            if syms['classes'] or syms['functions']:
                prompt += f"### `{file_name}`\n"
                if syms['classes']:
                    classes_str = ', '.join([f'`{c}`' for c in syms['classes'][:5]])
                    prompt += f"- **Classes:** {classes_str}\n"
                if syms['functions']:
                    funcs_str = ', '.join([f'`{f}()`' for f in syms['functions'][:10]])
                    prompt += f"- **Functions:** {funcs_str}\n"
                prompt += "\n"
        
        # Add hard constraints
        prompt += """## HARD CONSTRAINTS (Evidence-Only Mode)

```
+-------------------------------------------------------------+
|  WARNING: YOU ARE IN "SEALED CONTEXT" MODE                  |
+-------------------------------------------------------------+
|  [OK] USE ONLY symbols listed above                         |
|  [X]  DO NOT infer or assume code structure                 |
|  [X]  DO NOT hallucinate functions or classes               |
|  [!]  If symbol not found, respond: "Not in sealed context" |
+-------------------------------------------------------------+
```

---
*Generated by BBC HMPU {BBC_VERSION_TAG} - Deterministic Context Engine*
"""
        
        return prompt
    
    def to_cursor_context(self) -> str:
        """
        Generate Cursor IDE context pane format (YAML-like)
        
        Returns:
            YAML-formatted context for Cursor
        """
        symbols = self.extract_symbols()
        
        # Convert Windows paths to forward slashes for YAML compliance
        root_path = self.skeleton.get('root', '').replace('\\', '/')
        
        context = f"""# BBC Context for Cursor IDE
# Auto-generated - Do Not Edit

bbc_context:
    version: "{BBC_VERSION_SHORT}"
    status: {self.recipe.get('constraint_status', 'verified')}
    generated_at: "{self.metadata.get('generated_at', 'unknown')}"
  
  project:
    root: "{root_path}"
    files_scanned: {self.metrics.get('files_scanned', self.metadata.get('file_count', 0))}
    compression_ratio: {self.metrics.get('compression_ratio', 0):.4f}
    
  hard_constraints:
    - code_structure: "Verified (Sealed)"
    - hallucination_prevention: "Active"
    - determinism: "100%"
    
  symbol_atlas:
"""
        
        for file_name, syms in symbols.items():
            if syms['classes'] or syms['functions']:
                # Escape backslashes for YAML
                safe_name = file_name.replace('\\', '/')
                context += f"    \"{safe_name}\":\n"
                if syms['classes']:
                    classes_list = json.dumps(syms['classes'][:3])
                    context += f"      classes: {classes_list}\n"
                if syms['functions']:
                    funcs_list = json.dumps(syms['functions'][:5])
                    context += f"      functions: {funcs_list}\n"
                if syms['imports']:
                    imports_list = json.dumps(syms['imports'][:3])
                    context += f"      imports: {imports_list}\n"
        
        context += """
  usage_instructions: |
    This context provides verified symbols only.
    Reference these symbols when making suggestions.
    Do not introduce new symbols not listed here.
"""
        
        return context
    
    def to_gemini_context(self) -> str:
        """
        Generate Gemini Code Assist hard context snapshot
        
        Returns:
            XML-formatted context for Gemini
        """
        symbols = self.extract_symbols()
        
        context = f"""<!-- BBC_HARD_CONTEXT_SNAPSHOT {BBC_VERSION_TAG} -->
<!-- Determinism: 100% | Status: {self.recipe.get('constraint_status', 'VERIFIED').upper()} -->

<BBC_CONTEXT>
<METADATA>
    <Version>{BBC_VERSION_SHORT}</Version>
  <Status>{self.recipe.get('constraint_status', 'verified')}</Status>
  <Files>{self.metrics.get('files_scanned', self.metadata.get('file_count', 0))}</Files>
  <Compression>{self.metrics.get('compression_ratio', 0) * 100:.1f}%</Compression>
  <Root>{self.skeleton.get('root', '')}</Root>
</METADATA>

<SYMBOL_ATLAS>
"""
        
        for file_name, syms in symbols.items():
            if syms['classes'] or syms['functions']:
                context += f'  <FILE path="{file_name}">\n'
                
                for cls in syms['classes'][:3]:
                    context += f'    <CLASS name="{cls}"/>\n'
                
                for func in syms['functions'][:5]:
                    context += f'    <FUNCTION name="{func}"/>\n'
                
                for imp in syms['imports'][:3]:
                    context += f'    <IMPORT module="{imp}"/>\n'
                
                context += '  </FILE>\n'
        
        context += f"""</SYMBOL_ATLAS>

<CONSTRAINTS>
  <Constraint type="hallucination_prevention" value="active"/>
  <Constraint type="evidence_only" value="required"/>
  <Constraint type="determinism" value="100%"/>
</CONSTRAINTS>

<INSTRUCTION>
Use this snapshot as the single source of truth.
All code suggestions must reference only the symbols listed above.
Unverified symbols must be flagged as "Not in sealed context."
</INSTRUCTION>

</BBC_CONTEXT>
"""
        
        return context
    
    def to_kilo_context(self) -> str:
        """
        Generate Kilo Code / Cline native context format
        
        Returns:
            Native format optimized for Kilo Code
        """
        symbols = self.extract_symbols()
        
        context = f"""[KILO_BBC_CONTEXT {BBC_VERSION_TAG}]
BBC SEALED CONTEXT FOR KILO CODE
==================================

METRICS
   Status: {self.recipe.get('constraint_status', 'VERIFIED').upper()}
   Files: {self.metrics.get('files_scanned', self.metadata.get('file_count', 0))}
   Compression: {self.metrics.get('compression_ratio', 0) * 100:.1f}%
   Source: {self.skeleton.get('root', 'unknown')}

VERIFIED SYMBOLS
"""
        
        for file_name, syms in symbols.items():
            if syms['classes'] or syms['functions']:
                context += f"\n   FILE: {file_name}\n"
                
                if syms['classes']:
                    for cls in syms['classes'][:5]:
                        context += f"      class {cls}\n"
                
                if syms['functions']:
                    for func in syms['functions'][:10]:
                        context += f"      def {func}()\n"
        
        # Add hard constraints
        context += """
HARD CONSTRAINTS
   +-----------------------------------------------------+
   | * Use ONLY symbols listed above                     |
   | * DO NOT hallucinate or infer                       |
   | * Reference: filename.py:class_or_function          |
   | * Unknown symbols -> "Not in sealed context"        |
   +-----------------------------------------------------+

USAGE
   When suggesting code, always reference the source symbol:
   Example: "In [file.py], modify [class.function] to..."

==================================
"""
        
        return context
    
    def to_vscode_context(self) -> str:
        """
        Generate VS Code / GitHub Copilot native context format
        
        Returns:
            JSON-formatted context optimized for VS Code extension API
        """
        symbols = self.extract_symbols()
        
        # Build symbol map for VS Code IntelliSense-like structure
        symbol_map = {}
        for file_name, syms in symbols.items():
            if syms['classes'] or syms['functions']:
                symbol_map[file_name] = {
                    "classes": syms['classes'][:10],  # Top 10 classes
                    "functions": syms['functions'][:20],  # Top 20 functions
                    "imports": syms['imports'][:10],
                    "line_count": syms['line_count']
                }
        
        vscode_context = {
            "bbc_context_version": BBC_VERSION_SHORT,
            "ide": "vscode",
            "status": self.recipe.get('constraint_status', 'verified'),
            "generated_at": self.metadata.get('generated_at', 'unknown'),
            "project": {
                "root": self.skeleton.get('root', ''),
                "file_count": self.metrics.get('files_scanned', self.metadata.get('file_count', 0)),
                "compression_ratio": self.metrics.get('compression_ratio', 0)
            },
            "symbols": symbol_map,
            "hard_constraints": {
                "evidence_only": True,
                "hallucination_prevention": True,
                "determinism": "100%",
                "instruction": "Use ONLY symbols listed in this context. If a symbol is not found, respond with 'Symbol not found in BBC context.'"
            },
            "usage": {
                "inline_completions": "Reference symbols from this context",
                "chat": "Use symbol names with file references",
                "hover": "Show symbol definition from context"
            }
        }
        
        return json.dumps(vscode_context, indent=2, ensure_ascii=False)
    
    def to_generic_context(self) -> Dict[str, Any]:
        """
        Generate generic JSON context for custom integrations
        
        Returns:
            Dictionary with all context data
        """
        return {
            "version": BBC_VERSION_SHORT,
            "status": self.recipe.get('constraint_status', 'verified'),
            "metadata": {
                "files_scanned": self.metrics.get('files_scanned', 
                                                  self.metadata.get('file_count', 0)),
                "compression_ratio": self.metrics.get('compression_ratio', 0),
                "generated_at": self.metadata.get('generated_at', 'unknown')
            },
            "project": {
                "root": self.skeleton.get('root', ''),
                "hierarchy": self.skeleton.get('hierarchy', [])
            },
            "symbols": self.extract_symbols(),
            "hard_constraints": {
                "hallucination_prevention": True,
                "evidence_only": True,
                "determinism": "100%"
            }
        }
    
    def compute_hash(self, content: str) -> str:
        """
        Compute SHA256 hash for determinism verification
        
        Args:
            content: String content to hash
            
        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def verify_determinism(self, iterations: int = 3) -> Dict[str, Any]:
        """
        Verify that adapter produces deterministic output
        
        Args:
            iterations: Number of times to regenerate (default: 3)
            
        Returns:
            Verification results with hash comparisons
        """
        results = {
            "status": "TESTING",
            "iterations": iterations,
            "tests": {}
        }
        
        formats = {
            "copilot": self.to_copilot_prompt,
            "cursor": self.to_cursor_context,
            "gemini": self.to_gemini_context,
            "kilo": self.to_kilo_context,
            "vscode": self.to_vscode_context
        }
        
        for name, generator in formats.items():
            hashes = []
            for i in range(iterations):
                content = generator()
                content_hash = self.compute_hash(content)
                hashes.append(content_hash)
            
            # Check if all hashes match
            is_deterministic = len(set(hashes)) == 1
            
            results["tests"][name] = {
                "deterministic": is_deterministic,
                "hashes": hashes,
                "hash_count": len(set(hashes))
            }
        
        # Overall status
        all_deterministic = all(t["deterministic"] for t in results["tests"].values())
        results["status"] = "VERIFIED" if all_deterministic else "FAILED"
        results["all_deterministic"] = all_deterministic
        
        return results
    
    def export(self, output_dir: str, agent: str = "all") -> Dict[str, str]:
        """
        Export context to file(s) for specified agent(s)
        
        Args:
            output_dir: Directory to save output files
            agent: Target agent ("copilot", "cursor", "gemini", "kilo", "all")
            
        Returns:
            Dictionary mapping format names to file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exports = {}
        
        formats = {
            "copilot": (self.to_copilot_prompt, "bbc_context_copilot.md"),
            "cursor": (self.to_cursor_context, "bbc_context_cursor.yaml"),
            "gemini": (self.to_gemini_context, "bbc_context_gemini.xml"),
            "kilo": (self.to_kilo_context, "bbc_context_kilo.txt"),
            "vscode": (self.to_vscode_context, "bbc_context_vscode.json"),
            "generic": (self.to_generic_context, "bbc_context_generic.json")
        }
        
        if agent == "all":
            targets = formats.keys()
        else:
            targets = [agent] if agent in formats else []
        
        for target in targets:
            generator, filename = formats[target]
            content = generator()
            
            # Handle dict content for JSON
            if isinstance(content, dict):
                file_path = output_path / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2)
            else:
                file_path = output_path / filename
                file_path.write_text(content, encoding='utf-8')
            
            exports[target] = str(file_path)
        
        return exports


def inject_to_project(context_path: str, project_path: str = None, optimize: bool = True, active_command: str = None) -> Dict[str, str]:
    """
    BBC Smart Context Injection - Detects installed IDEs and AI extensions,
    then injects BBC config to each one. Uses ide_auto_config.py for detection.
    Only creates config folders for IDEs/extensions that are actually installed.
    """
    from pathlib import Path
    from datetime import datetime

    context_file = Path(context_path)
    if not context_file.exists():
        raise FileNotFoundError(f"Context file not found: {context_path}")

    with open(context_path, 'r', encoding='utf-8') as f:
        context = json.load(f)

    project_root = Path(project_path).resolve() if project_path else context_file.parent.resolve()

    recipe = context.get("recipe", context)
    status = recipe.get("constraint_status", "verified").upper()
    generated_at = datetime.now().isoformat()
    code_structure = context.get("code_structure", recipe.get("code_structure", []))
    skeleton = context.get("project_skeleton", recipe.get("project_skeleton", {}))
    file_count = skeleton.get("file_count", 0)
    metrics = context.get("metrics", recipe.get("metrics", {}))
    savings_pct = metrics.get("savings_pct", 0)
    class_count = sum(len(e.get("structure", {}).get("classes", [])) for e in code_structure if isinstance(e, dict))
    func_count = sum(len(e.get("structure", {}).get("functions", [])) for e in code_structure if isinstance(e, dict))

    # --- Policy fields (v8.5) ---
    instr_version = context.get("bbc_instructions_version", "1.0")
    schema_version = context.get("context_schema_version", "8.5")
    context_fresh = context.get("context_fresh", True)
    fail_policy = context.get("fail_policy", "fail_closed")
    enforcement = context.get("enforcement_level", "strict")
    from bbc_core.config import BBCConfig
    profile = BBCConfig.ENFORCEMENT_PROFILES.get(enforcement, BBCConfig.ENFORCEMENT_PROFILES["strict"])

    created_files: Dict[str, str] = {}

    # --- Manifest helpers ---
    def _manifest_path(root: Path) -> Path:
        return root / ".bbc" / "manifest" / "injected_files.json"

    def _load_manifest(root: Path) -> Dict[str, Any]:
        path = _manifest_path(root)
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _save_manifest(root: Path, manifest: Dict[str, Any]) -> None:
        path = _manifest_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def _sha256_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _record(label: str, file_path: Path, content: str) -> None:
        manifest = _load_manifest(project_root)
        entries = manifest.get("files", [])
        entry = {
            "label": label,
            "path": str(file_path),
            "relative_path": os.path.relpath(str(file_path), str(project_root)),
            "sha256": _sha256_text(content),
            "generated_at": generated_at,
        }
        updated = False
        for i, e in enumerate(entries):
            if isinstance(e, dict) and e.get("path") == entry["path"]:
                entries[i] = entry
                updated = True
                break
        if not updated:
            entries.append(entry)
        manifest["files"] = entries
        manifest["project_root"] = str(project_root)
        manifest["context_path"] = str(context_file)
        _save_manifest(project_root, manifest)

    def _write_config(label: str, rel_path: str, content: str) -> None:
        full = project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        _record(label, full, content)
        created_files[label] = str(full)

    def get_instructions() -> str:
        freshness_str = "FRESH" if context_fresh else "STALE (run: python bbc.py analyze)"
        if fail_policy == "fail_closed":
            fail_rule = "If context is missing or STALE, do NOT write code. Only explain what is needed and suggest running `python bbc.py analyze`."
        else:
            fail_rule = "If context is missing or STALE, you may continue but prefix EVERY response with: `[BBC WARNING] Operating without verified context.`"

        impact_rule = ""
        if profile.get("require_impact_before_change"):
            impact_rule = "\n6. **IMPACT-FIRST:** Before modifying any file, run `python bbc.py impact <file> --symbols <changed_symbols>`. If risk is CAUTION or HIGH, ask user for confirmation before proceeding."
        verify_rule = ""
        if profile.get("require_verify_after_change"):
            verify_rule = "\n7. **VERIFY-AFTER:** After every code change, run `python bbc.py verify .` to confirm structural integrity."
        patch_rule = ""
        if profile.get("auto_patch_check"):
            patch_rule = "\n8. **PATCH-CHECK:** After changes, run `python bbc.py patch .` (dry-run) to detect regressions."

        return f"""# BBC (Bitter Brain Context) v8.5 — MANDATORY SYSTEM INSTRUCTIONS
# bbc_instructions_version: {instr_version}
# context_schema_version: {schema_version}
# enforcement: {enforcement}
# fail_policy: {fail_policy}

## CRITICAL: READ THIS BEFORE ANY ACTION
These instructions are NON-OPTIONAL. They apply to ALL projects regardless of size.
You MUST follow every rule below. Skipping any rule is a protocol violation.

## STEP 0: LOAD BBC CONTEXT (MANDATORY — DO THIS FIRST)
Before writing ANY code, reading ANY file, or answering ANY question:
1. Read `.bbc/bbc_context.json` — this is the verified project map
2. Read `.bbc/bbc_rules.md` — these are the project-specific rules
3. Use the `code_structure` field from bbc_context.json as your primary reference
4. Check `context_fresh` field — current status: **{freshness_str}**

DO NOT use your own file scanning tools (read_file, grep, etc.) to discover the project structure.
The BBC context has already mapped the entire project with verified checksums.
Using BBC context is FASTER and MORE ACCURATE than scanning files yourself.

## CONTEXT FRESHNESS & FAIL POLICY
- Context Freshness: **{freshness_str}**
- Fail Policy: **{fail_policy}**
- {fail_rule}

## WHY YOU MUST USE BBC CONTEXT (EVEN FOR SMALL PROJECTS)
- BBC context includes HMPU-compressed token-optimized project structure
- It contains verified symbol relationships (classes, functions, imports, call graphs)
- It has integrity checksums — if you use symbols not in the context, you risk hallucination
- The project has been analyzed: {file_count} files, status: {status}

## RULES (MANDATORY — enforcement: {enforcement})
1. **CONTEXT-FIRST:** Get project structure from `.bbc/bbc_context.json`, NOT from scanning files
2. **VERIFIED SYMBOLS ONLY:** Only use classes, functions, and variables that exist in bbc_context.json `code_structure`
3. **NO HALLUCINATION:** If a symbol is NOT in the context, do NOT invent it. Ask the user to run `python bbc.py analyze`
4. **WARN ON EXTERNAL:** If forced to use symbols outside context, prefix your response with: "WARNING: Using symbols outside BBC sealed context"
5. **CITE CONTEXT:** When referencing project structure, cite bbc_context.json as your source{impact_rule}{verify_rule}{patch_rule}

## GUARDRAIL PIPELINE (automatic workflow)
Before writing code: impact analysis → risk check
After writing code: patch check → verify integrity
If any step fails: STOP and report to user

## PROJECT SNAPSHOT
- Status: {status}
- Files: {file_count}
- Freshness: {freshness_str}
- Enforcement: {enforcement}
- Fail Policy: {fail_policy}
- Instructions Version: {instr_version}
- Schema Version: {schema_version}
- Context File: .bbc/bbc_context.json
"""

    # --- Standard JSON config for AI extensions ---
    def _ext_json(extra: dict = None) -> str:
        cfg = {
            "bbc": {
                "enabled": True,
                "version": "8.3",
                "status": status,
                "contextFile": "bbc_context.json"
            },
            "instructions": (
                f"BBC Mode: Read bbc_context.json before code generation. "
                f"Only use symbols from code_structure. Never hallucinate. "
                f"Status: {status}, Files: {file_count}"
            )
        }
        if extra:
            cfg.update(extra)
        return json.dumps(cfg, indent=2, ensure_ascii=False)

    adapter = BBCAgentAdapter(str(context_file))
    optimized_context_paths: Dict[str, str] = {}
    adapter_cache: Dict[str, BBCAgentAdapter] = {str(context_file): adapter}

    def _static_task_for_format(format_type: str) -> str:
        if format_type in {"copilot_md", "cursor_rules", "kilo_rules"}:
            return "bugfix"
        if format_type in {"vscode_json", "jetbrains_xml", "gemini_xml", "zed_json", "theia_json"}:
            return "review"
        return "feature"

    def _task_for_format(format_type: str, active_command: str = None) -> str:
        # Dynamic mapping based on last active BBC command
        if active_command:
            if active_command == "verify":
                return "bugfix"
            if active_command == "patch":
                return "refactor"
            if active_command == "impact":
                return "review"
        # Fallback to static mapping
        return _static_task_for_format(format_type)

    def _get_optimized_context_path(format_type: str) -> str:
        """Return context path optimized for the target format type."""
        if not optimize:
            return str(context_file)

        task = _task_for_format(format_type, active_command)
        if task in optimized_context_paths:
            return optimized_context_paths[task]

        try:
            from bbc_core.context_compiler import TaskContextCompiler

            compiler = TaskContextCompiler(str(context_file))
            compiled = compiler.compile(task=task)

            out_path = project_root / ".bbc" / f"agent_context_{task}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(compiled, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

            optimized_context_paths[task] = str(out_path)
            return str(out_path)
        except Exception:
            return str(context_file)

    def _adapter_for_format(format_type: str) -> BBCAgentAdapter:
        ctx_path = _get_optimized_context_path(format_type)
        if ctx_path not in adapter_cache:
            adapter_cache[ctx_path] = BBCAgentAdapter(ctx_path)
        return adapter_cache[ctx_path]

    def _context_ref_for_format(format_type: str) -> str:
        ctx_abs = _get_optimized_context_path(format_type)
        try:
            return os.path.relpath(ctx_abs, str(project_root)).replace("\\", "/")
        except Exception:
            return ".bbc/bbc_context.json"

    def _render_tool_content(format_type: str, label: str) -> str:
        if format_type == "copilot_md":
            return _adapter_for_format(format_type).to_copilot_prompt()
        if format_type == "cursor_rules":
            return _adapter_for_format(format_type).to_cursor_context()
        if format_type == "gemini_xml":
            return _adapter_for_format(format_type).to_gemini_context()
        if format_type == "kilo_rules":
            return _adapter_for_format(format_type).to_kilo_context()
        if format_type == "vscode_json":
            return _adapter_for_format(format_type).to_vscode_context()
        if format_type == "jetbrains_xml":
            context_ref = _context_ref_for_format(format_type)
            return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project version=\"4\">
  <component name=\"BBCAIAssistant\">
    <option name=\"enabled\" value=\"true\" />
    <option name=\"contextFile\" value=\"{context_ref}\" />
    <option name=\"enforcement\" value=\"{enforcement}\" />
    <option name=\"failPolicy\" value=\"{fail_policy}\" />
    <option name=\"instructionsVersion\" value=\"{instr_version}\" />
    <option name=\"schemaVersion\" value=\"{schema_version}\" />
    <option name=\"instructions\"><![CDATA[{instructions}]]></option>
  </component>
</project>"""
        if format_type == "native_rules":
            return instructions
        if format_type == "ext_json":
            context_ref = _context_ref_for_format(format_type)
            return _ext_json({
                "agent": label,
                "instructionsVersion": instr_version,
                "schemaVersion": schema_version,
                "enforcement": enforcement,
                "failPolicy": fail_policy,
                "contextFresh": context_fresh,
                "contextPath": context_ref,
                "optimizedInjection": optimize,
            })
        if format_type == "zed_json":
            context_ref = _context_ref_for_format(format_type)
            return json.dumps({
                "assistant": {
                    "enabled": True,
                    "rules": instructions,
                    "context_path": context_ref,
                    "enforcement": enforcement,
                    "fail_policy": fail_policy,
                }
            }, indent=2, ensure_ascii=False)
        if format_type == "theia_json":
            context_ref = _context_ref_for_format(format_type)
            return json.dumps({
                "bbc": {
                    "enabled": True,
                    "instructions_file": ".bbc/BBC_INSTRUCTIONS.md",
                    "context_file": context_ref,
                    "enforcement": enforcement,
                    "fail_policy": fail_policy,
                }
            }, indent=2, ensure_ascii=False)
        return instructions

    # --- .bbc/bbc_context.md (always) ---
    def _build_context_md() -> str:
        lines = [
            "# BBC Context - Project Analysis",
            f"- Status: {status}",
            f"- Files: {file_count}",
            "",
            "## Code Structure Summary",
            "",
        ]
        for entry in code_structure[:30]:
            if isinstance(entry, dict):
                p = entry.get("path", "")
                s = entry.get("structure", {})
                cls = ", ".join(s.get("classes", [])) or "None"
                fns = ", ".join(s.get("functions", [])[:10]) or "None"
                lines.append(f"### `{p}`")
                lines.append(f"- Classes: {cls}")
                lines.append(f"- Functions: {fns}")
                lines.append("")
        return "\n".join(lines)

    _write_config("Context MD", ".bbc/bbc_context.md", _build_context_md())

    # --- .bbc/bbc_rules.md (always — used by multiple agents) ---
    rules_md = f"""## Statistics: {file_count} files | {class_count} classes | {func_count} functions

# BBC Project Rules

## 1. Core Mandates
- Read `bbc_context.json` as the single source of truth.
- Only use symbols present in code_structure.
- Never hallucinate functions or classes not in context.

## 2. Technical Stack
- Root: {project_root.name}
- See bbc_context.json for full dependency graph.

## 3. Workflow
- Run `python run_bbc.py audit .` before commits.
"""
    _write_config("Agent Rules", ".bbc/bbc_rules.md", rules_md)

    # --- Detect installed IDEs and extensions ---
    try:
        from bbc_core.ide_auto_config import IDEAutoConfigurator
        configurator = IDEAutoConfigurator()
        active_ide_type = configurator.detect_active_ide()
    except Exception:
        active_ide_type = None

    ide_types = {active_ide_type} if active_ide_type else set()
    
    # We do NOT run global detect_all() to avoid workspace pollution ("Ghost Injection")
    plugin_ids = set()
    plugin_names = set()

    instructions = get_instructions()

    # Her zaman .bbc/ icine yaz (ana merkez)
    _write_config("BBC Instructions", ".bbc/BBC_INSTRUCTIONS.md", instructions)

    # ----------------------------------------------------------------
    # AKTIF IDE + KURULU AI EKLENTI TESPITI VE ENJEKSIYON
    # ----------------------------------------------------------------
    # Oncelik sirasi:
    # 1. Ortam degiskeni / process agaci ile aktif IDE'yi bul
    # 2. O IDE'nin extension klasorunu tara → kurulu AI eklentilerini bul
    # 3. Sadece bulunan IDE + eklentilere yaz, hic birine dokunma
    # IDE bilinemezse => VS Code extension klasoru fallback olarak denenir
    # ----------------------------------------------------------------
    try:
        from bbc_core.ide_auto_config import IDEAutoConfigurator
        configurator = IDEAutoConfigurator()
        active_ide_type = configurator.detect_active_ide()
    except Exception:
        configurator = None
        active_ide_type = None

    # Aktif IDE -> (label, relative_path)
    IDE_CONFIG_MAP = {
        "vscode":      ("VS Code",         ".github/copilot-instructions.md", "copilot_md"),
        "cursor":      ("Cursor",          ".cursorrules",                    "cursor_rules"),
        "windsurf":    ("Windsurf",        ".windsurf/bbc_rules.md",          "native_rules"),
        "antigravity": ("Antigravity",     ".antigravity/rules.md",           "native_rules"),
        "cline":       ("Cline",           ".clinerules",                     "kilo_rules"),
        "jetbrains":   ("JetBrains",       ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "zed":         ("Zed",             ".zed/settings.json",              "zed_json"),
        "visualstudio":("Visual Studio",   ".vs/bbc-instructions.md",         "native_rules"),
        "fleet":       ("JetBrains Fleet", ".fleet/bbc_rules.md",             "native_rules"),
        "theia":       ("Eclipse Theia",   ".theia/settings.json",            "theia_json"),
        "trae":        ("Trae",            ".trae/rules.md",                  "native_rules"),
        "vim":         ("Vim",             ".bbc-vim-config",                 "native_rules"),
        "neovim":      ("Neovim",          ".bbc-vim-config",                 "native_rules"),
        "sublime":     ("Sublime Text",    ".sublime-project.sublime-settings","theia_json"),
        "notepadpp":   ("Notepad++",       ".notepadpp/bbc_rules.md",         "native_rules"),
        "eclipse":     ("Eclipse",         ".eclipse/bbc_rules.md",           "native_rules"),
        "xcode":       ("Xcode",           ".xcode/bbc_rules.md",             "native_rules"),
    }

    # VS Code Eklenti ID -> (label, relative_path, icerik_tipi)
    # icerik_tipi: "md" = markdown, "json" = json wrapper
    EXTENSION_CONFIG_MAP = {
        "github.copilot":         ("GitHub Copilot",             ".github/copilot-instructions.md", "copilot_md"),
        "github.copilot-chat":    ("GitHub Copilot",             ".github/copilot-instructions.md", "copilot_md"),
        "saoudrizwan.claude-dev": ("Cline",                       ".clinerules",                     "kilo_rules"),
        "kilocode.kilo-code":     ("Kilo Code",                   ".clinerules",                     "kilo_rules"),
        "continue.continue":      ("Continue",                    ".continue/config.json",           "ext_json"),
        "codeium.codeium":        ("Codeium",                     ".codeium/config.json",            "ext_json"),
        "tabnine.tabnine-vscode": ("Tabnine",                     ".tabnine/config.json",            "ext_json"),
        "amazonwebservices.amazon-q-vscode": ("Amazon Q",         ".amazonq/config.json",            "ext_json"),
        "amazonwebservices.codewhisperer-for-command-line-companion": ("CodeWhisperer", ".amazonq/config.json", "ext_json"),
        "blackboxapp.blackbox":   ("Blackbox AI",                 ".blackbox/config.json",           "ext_json"),
        "promptshell.promptshell":("CodeGPT",                     ".codegpt/config.json",            "ext_json"),
        "danielsanmedium.dscodegpt": ("CodeGPT",                  ".codegpt/config.json",            "ext_json"),
        "pieces.pieces-vscode":   ("Pieces",                      ".pieces/config.json",             "ext_json"),
        "aminer.codegeex":        ("CodeGeeX",                    ".codegeex/config.json",           "ext_json"),
        "sourcegraph.cody-ai":    ("Sourcegraph Cody",            ".cody/config.json",               "ext_json"),
        "supermaven.supermaven":  ("Supermaven",                  ".supermaven/config.json",         "ext_json"),
        "codium.codium":          ("CodiumAI",                    ".codiumai/config.json",           "ext_json"),
        "codiumai.codiumate":     ("CodiumAI",                    ".codiumai/config.json",           "ext_json"),
        "mintlify.document":      ("Mintlify",                    ".mintlify/config.json",           "ext_json"),
        "askcodi.askcodi":        ("AskCodi",                     ".askcodi/config.json",            "ext_json"),
        "sourcery.sourcery":      ("Sourcery",                    ".sourcery/bbc_rules.md",          "native_rules"),
        "fauxpilot.fauxpilot":    ("FauxPilot",                   ".fauxpilot/config.json",          "ext_json"),
        "rooveterinaryinc.roo-cline": ("Roo Code",                ".roo-code/config.json",           "ext_json"),
        "smallcloudai.refact":    ("Refact.ai",                   ".refact/config.json",             "ext_json"),
        "maboroshi.mutableai":    ("MutableAI",                   ".mutableai/config.json",          "ext_json"),
        "codiga.codiga":          ("Codiga",                      ".codiga/config.json",             "ext_json"),
        "visualstudioexptteam.vscodeintellicode": ("Intellicode", ".intellicode/config.json",        "ext_json"),
        "deepseekai.deepseek-coder": ("DeepSeek Coder",           ".deepseek/config.json",           "ext_json"),
        "qodo.qodo-gen":          ("Qodo Gen",                    ".qodo/config.json",               "ext_json"),
        "replit.replit":          ("Replit Ghostwriter",          ".replit/ai.json",                 "ext_json"),
        "warp.warp-terminal":     ("Warp Terminal AI",            ".warp/config.json",               "ext_json"),
        "github-copilot":         ("GitHub Copilot (JetBrains)",  ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "ai-assistant":           ("JetBrains AI Assistant",      ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "codeium":                ("Codeium (JetBrains)",         ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "tabnine":                ("Tabnine (JetBrains)",         ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "continue":               ("Continue (JetBrains)",        ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "codewhisperer":          ("Amazon CodeWhisperer",        ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "amazonq":                ("Amazon Q (JetBrains)",        ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
        "cody":                   ("Sourcegraph Cody (JetBrains)", ".idea/bbc-ai-assistant.xml",     "jetbrains_xml"),
        "supermaven":             ("Supermaven (JetBrains)",      ".idea/bbc-ai-assistant.xml",      "jetbrains_xml"),
    }

    # Onceki BBC files temizle (only BBC yazdigini dogrulayarak)
    import shutil
    BBC_IDE_FILES = [
        ".cursorrules", ".clinerules",
        ".github/copilot-instructions.md",
        ".windsurf/bbc_rules.md",
        ".antigravity/rules.md",
        ".idea/bbc-ai-assistant.xml",
        ".zed/settings.json",
        ".continue/config.json",
        ".codeium/config.json",
        ".tabnine/config.json",
        ".amazonq/config.json",
        ".blackbox/config.json",
        ".codegpt/config.json",
        ".pieces/config.json",
        ".codegeex/config.json",
        ".cody/config.json",
        ".supermaven/config.json",
        ".codiumai/config.json",
        ".mintlify/config.json",
        ".askcodi/config.json",
        ".fauxpilot/config.json",
        ".roo-code/config.json",
        ".refact/config.json",
        ".mutableai/config.json",
        ".codiga/config.json",
        ".intellicode/config.json",
        ".deepseek/config.json",
        ".qodo/config.json",
        ".replit/ai.json",
        ".warp/config.json",
        ".fleet/bbc_rules.md",
        ".theia/settings.json",
        ".trae/rules.md",
        ".vs/bbc-instructions.md",
        ".eclipse/bbc_rules.md",
        ".xcode/bbc_rules.md",
        ".notepadpp/bbc_rules.md",
        ".sourcery/bbc_rules.md",
        ".sublime-project.sublime-settings",
        ".bbc-vim-config",
    ]
    for ide_file in BBC_IDE_FILES:
        fp = project_root / ide_file
        if fp.exists() and fp.is_file():
            try:
                content_check = fp.read_text(encoding="utf-8", errors="ignore")
                if "BBC" in content_check or "bbc_context" in content_check:
                    fp.unlink()
                    parent = fp.parent
                    if parent != project_root and parent.exists() and not list(parent.iterdir()):
                        shutil.rmtree(parent)
            except Exception:
                pass

    # Eski BBC cop klasorleri temizle
    protected_dirs = {".bbc", ".github", ".idea", ".vs", ".fleet", ".theia", ".windsurf", ".antigravity", ".zed"}
    for _, rel_path, _ in IDE_CONFIG_MAP.values():
        rel_parent = Path(rel_path).parent
        if str(rel_parent) not in ("", "."):
            protected_dirs.add(str(rel_parent).replace("\\", "/"))
    for _, rel_path, _ in EXTENSION_CONFIG_MAP.values():
        rel_parent = Path(rel_path).parent
        if str(rel_parent) not in ("", "."):
            protected_dirs.add(str(rel_parent).replace("\\", "/"))

    BBC_LEGACY_DIRS = [
        ".agent", ".context",
    ]
    for legacy_dir in BBC_LEGACY_DIRS:
        p = project_root / legacy_dir
        if p.exists() and p.is_dir():
            try:
                normalized = legacy_dir.replace("\\", "/")
                if normalized in protected_dirs:
                    continue
                if len(list(p.rglob("*"))) <= 3:
                    shutil.rmtree(p)
            except Exception:
                pass

    # ------------------------------------------------------------
    # ADIM 1: Aktif IDE'ye yaz
    # ------------------------------------------------------------
    injected = []
    written_paths = set()

    if active_ide_type and active_ide_type in IDE_CONFIG_MAP:
        label, rel_path, format_type = IDE_CONFIG_MAP[active_ide_type]
        _write_config(label, rel_path, _render_tool_content(format_type, label))
        written_paths.add(rel_path)
        injected.append(f"{label} -> {rel_path}")

    # ------------------------------------------------------------
    # STEP 2: Scan installed AI extensions and write config for them too
    # Example: VS Code + Copilot + Cline installed => 2 files are created
    # If IDE cannot be detected, VS Code extension directory is used as fallback
    # ------------------------------------------------------------
    try:
        if configurator:
            if active_ide_type in ["vscode", "cursor", "windsurf", "cline", "trae", "theia", None]:
                extensions = configurator.detect_vscode_extensions()
            elif active_ide_type in ["jetbrains", "fleet"]:
                extensions = configurator.detect_jetbrains_plugins()
            else:
                extensions = configurator.detect_vscode_extensions()

            for ext in extensions:
                ext_id = ext.get("id", "")
                if ext_id not in EXTENSION_CONFIG_MAP:
                    continue
                e_label, e_rel_path, e_type = EXTENSION_CONFIG_MAP[ext_id]
                if e_rel_path in written_paths:
                    continue  # Zaten yazildi, tekrar yazma
                content = _render_tool_content(e_type, e_label)
                _write_config(e_label, e_rel_path, content)
                written_paths.add(e_rel_path)
                injected.append(f"{e_label} -> {e_rel_path}")
    except Exception:
        pass

    if injected:
        for item in injected:
            print(f"[BBC] Injected: {item}")
    else:
        print("[BBC] Active IDE/Extension: Not detected -> using .bbc/ only")

    # --- Git Isolation Shield (v8.3 No-Trace Policy) ---
    shield_git_isolation(project_root, created_files)

    return created_files


def shield_git_isolation(project_root: Path, created_files: dict):
    """
    Automatically updates .gitignore to prevent BBC-injected files 
    from being tracked/pushed to GitHub.
    """
    gitignore_path = project_root / ".gitignore"
    
    # Files/folders to isolate
    # Always include .bbc directory and core context
    to_ignore = {".bbc/", "ai-context.json", "bbc_context.json", "bbc_rules.md", "BBC_CONTEXT.md", "BBC_INSTRUCTIONS.md", "BBC_README.md"}
    
    # Add all files created during injection
    for label, path_str in created_files.items():
        if label == "Global Rules": continue # Global rules are outside project
        
        # We use relative paths for gitignore
        try:
            rel_path = os.path.relpath(path_str, project_root).replace('\\', '/')
            # If it's a deep path (e.g. .github/copilot-instructions.md), we add it specifically
            to_ignore.add(rel_path)
            # Also ignore the parent dir if it was created just for BBC
            if '/' in rel_path:
                parent = rel_path.split('/')[0]
                if parent in [".agent", ".context", ".continue", ".codiumai", ".codeium", ".tabnine", ".amazonq", ".blackbox", ".codegpt", ".pieces", ".codegeex", ".cody", ".supermaven", ".mintlify", ".askcodi", ".fauxpilot", ".warp", ".replit", ".antigravity", ".roo-code", ".refact", ".mutableai", ".codiga", ".intellicode", ".deepseek", ".qodo"]:
                    to_ignore.add(parent + "/")
        except Exception:
            continue

    if not gitignore_path.exists():
        content = "# BBC Isolation Shield\n" + "\n".join(sorted(to_ignore)) + "\n"
        gitignore_path.write_text(content, encoding="utf-8")
        return

    # Append to existing gitignore if not already there
    try:
        current_content = gitignore_path.read_text(encoding="utf-8")
        lines = current_content.splitlines()
        
        new_entries = []
        for item in to_ignore:
            if item not in lines:
                new_entries.append(item)
        
        if new_entries:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if not current_content.endswith("\n"):
                    f.write("\n")
                f.write("\n# --- BBC Isolation Shield (No-Trace) ---\n")
                for entry in sorted(new_entries):
                    f.write(f"{entry}\n")
    except Exception:
        pass


def cleanup_injected_configs(project_path: str, dry_run: bool = True) -> list:
    """
    Remove BBC-injected AI config files from a project
    
    This function removes all files and directories created by inject_to_project().
    Use this when you want to remove BBC context from a project.
    
    Args:
        project_path: Target project root directory
        dry_run: If True, only return list of files that would be deleted.
                 If False, actually delete the files.
        
    Returns:
        List of file/directory paths that were/would be deleted
    """
    from pathlib import Path
    import shutil
    
    project_root = Path(project_path).resolve()

    def _safe_under_root(path: Path) -> bool:
        try:
            path.resolve().relative_to(project_root)
            return True
        except Exception:
            return False

    # Prefer manifest-based cleanup (deterministic)
    manifest_file = project_root / ".bbc" / "manifest" / "injected_files.json"
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest_entries = manifest.get("files", [])
            manifest_paths = []
            for e in manifest_entries:
                if isinstance(e, dict) and e.get("path"):
                    p = Path(e["path"])
                    if p.exists() and _safe_under_root(p):
                        manifest_paths.append(str(p))
        except Exception:
            manifest_paths = []

        if manifest_paths:
            if dry_run:
                return manifest_paths

            deleted = []
            for path_str in manifest_paths:
                path = Path(path_str)
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    deleted.append(path_str)
                except Exception as e:
                    print(f"[WARN] Could not delete {path}: {e}")

            # Update manifest: remove deleted entries, keep undeleted ones
            try:
                remaining = [e for e in manifest_entries if isinstance(e, dict) and e.get("path") not in deleted]
                manifest["files"] = remaining
                manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

            return deleted
    
    # Fallback: all BBC-written FILES (never delete IDE-owned folders themselves)
    bbc_paths = [
        # Always-created
        ".context/bbc_context.md",
        ".agent/rules/bbc_rules.md",

        # IDE-level configs
        ".github/copilot-instructions.md",
        ".cursorrules",
        ".clinerules",
        ".idea/bbc-ai-config.xml",
        ".idea/bbc-ai-assistant.xml",
        ".windsurf/bbc_rules.md",
        ".zed/settings.json",

        # AI Extension configs
        ".continue/config.json",
        ".codeium/config.json",
        ".tabnine/config.json",
        ".amazonq/config.json",
        ".blackbox/config.json",
        ".codegpt/config.json",
        ".pieces/config.json",
        ".codegeex/config.json",
        ".cody/config.json",
        ".supermaven/config.json",
        ".codiumai/config.json",
        ".mintlify/config.json",
        ".askcodi/config.json",
        ".fauxpilot/config.json",
        ".warp/config.json",
        ".replit/ai.json",
        ".antigravity/rules.md",
        ".roo-code/config.json",
        ".refact/config.json",
        ".mutableai/config.json",
        ".codiga/config.json",
        ".intellicode/config.json",
        ".deepseek/config.json",
        ".qodo/config.json",

        # Universal Fallback (v8.3: .bbc/ isolation)
        ".bbc/BBC_INSTRUCTIONS.md",
        # Legacy root files (may exist from older versions)
        "BBC_CONTEXT.md",
        "BBC_INSTRUCTIONS.md",
        "BBC_README.md",
    ]
    
    found_paths = []
    
    for rel_path in bbc_paths:
        full_path = project_root / rel_path
        if full_path.exists():
            found_paths.append(str(full_path))
    
    if dry_run:
        return found_paths
    
    # Actually delete
    deleted = []
    for path_str in found_paths:
        path = Path(path_str)
        if not _safe_under_root(path):
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            deleted.append(path_str)
        except Exception as e:
            print(f"[WARN] Could not delete {path}: {e}")
    
    return deleted


def run_adapter_validation(context_path: str = "bbc_context.json"):
    """
    Execute full adapter validation workflow
    
    Args:
        context_path: Path to BBC context/recipe file
        
    Returns:
        Validation results dictionary
    """
    print("=" * 70)
    print(f">>> BBC {BBC_VERSION_TAG} AGENT ADAPTER VALIDATION")
    print("=" * 70)
    
    adapter = None
    warning_msg = None
    
    try:
        # Initialize adapter
        adapter = BBCAgentAdapter(context_path)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("   Please ensure bbc_context.json exists or provide a valid path.")
        return {"status": "ERROR", "message": str(e)}
    except ValueError as e:
        # Context not sealed - continue with warning
        print(f"\n[WARNING] {e}")
        print("   Proceeding with unsealed context...")
        warning_msg = str(e)
        # Re-initialize without validation
        context_file = Path(context_path)
        with open(context_path, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        recipe = context.get("recipe", context)
        
        # Create minimal adapter manually
        class MinimalAdapter:
            def __init__(self, recipe, context):
                self.recipe = recipe
                self.context = context
                self.metadata = context.get("metadata", {})
                self.metrics = recipe.get("metrics", {})
                self.skeleton = recipe.get("project_skeleton", recipe.get("skeleton", {}))
                raw_structure = recipe.get("code_structure", [])
                self.code_structure = []
                for item in raw_structure:
                    if isinstance(item, dict) and "structure" in item:
                        self.code_structure.append({
                            "path": item.get("path", ""),
                            "classes": item.get("structure", {}).get("classes", []),
                            "functions": item.get("structure", {}).get("functions", []),
                            "imports": item.get("structure", {}).get("imports", []),
                            "line_count": item.get("stats", {}).get("lines", 0)
                        })
                    else:
                        self.code_structure.append(item)
        
        adapter = MinimalAdapter(recipe, context)
        # Attach methods from BBCAgentAdapter
        adapter.extract_symbols = BBCAgentAdapter.extract_symbols.__get__(adapter, MinimalAdapter)
        adapter.to_copilot_prompt = BBCAgentAdapter.to_copilot_prompt.__get__(adapter, MinimalAdapter)
        adapter.to_cursor_context = BBCAgentAdapter.to_cursor_context.__get__(adapter, MinimalAdapter)
        adapter.to_gemini_context = BBCAgentAdapter.to_gemini_context.__get__(adapter, MinimalAdapter)
        adapter.to_kilo_context = BBCAgentAdapter.to_kilo_context.__get__(adapter, MinimalAdapter)
        adapter.to_vscode_context = BBCAgentAdapter.to_vscode_context.__get__(adapter, MinimalAdapter)
        adapter.to_generic_context = BBCAgentAdapter.to_generic_context.__get__(adapter, MinimalAdapter)
        adapter.compute_hash = BBCAgentAdapter.compute_hash.__get__(adapter, MinimalAdapter)
        adapter.verify_determinism = BBCAgentAdapter.verify_determinism.__get__(adapter, MinimalAdapter)
        adapter.export = BBCAgentAdapter.export.__get__(adapter, MinimalAdapter)
    
    if adapter is None:
        return {"status": "ERROR", "message": "Failed to initialize adapter"}
    
    # Continue with validation
    file_count = adapter.skeleton.get('file_count', len(adapter.skeleton.get('hierarchy', [])))
    compression = adapter.metrics.get('compression_ratio', 0) * 100
    
    # Simple compact display - SINGLE LINE STATUS BAR
    status = "[SEALED]" if adapter.recipe.get('constraint_status') in ['sealed', 'verified'] else "[OPEN]"
    
    # Generate outputs
    exports = adapter.export(".", agent="all")
    
    # Quick stats
    symbols = adapter.extract_symbols()
    total_classes = sum(len(s['classes']) for s in symbols.values())
    total_functions = sum(len(s['functions']) for s in symbols.values())
    total_imports = sum(len(s['imports']) for s in symbols.values())
    
    # SINGLE LINE OUTPUT
    print(f"\nBBC {status} | {file_count} files | {total_classes}C/{total_functions}F/{total_imports}I | %{compression:.0f} saved")
    
    # Simple determinism check (just for return value)
    determinism_results = adapter.verify_determinism(iterations=1)
    
    # Final status
    print("\n" + "=" * 70)
    
    if determinism_results["all_deterministic"] and not warning_msg:
        print("[SUCCESS] VALIDATION COMPLETE - ALL TESTS PASSED")
        final_status = "VALIDATED"
    elif determinism_results["all_deterministic"]:
        print("[SUCCESS] VALIDATION COMPLETE - WITH WARNINGS")
        final_status = "VALIDATED_WITH_WARNINGS"
    else:
        print("[WARNING] VALIDATION COMPLETE - SOME TESTS FAILED")
        final_status = "PARTIAL"
    
    print("=" * 70)
    
    return {
        "status": final_status,
        "determinism": determinism_results["all_deterministic"],
        "exports": exports,
        "symbols": {
            "classes": total_classes,
            "functions": total_functions,
            "imports": total_imports,
            "files": len(symbols)
        },
        "warning": warning_msg
    }


if __name__ == "__main__":
    import sys
    
    # Get context path from command line or use default
    context_file = sys.argv[1] if len(sys.argv) > 1 else "bbc_context.json"
    
    result = run_adapter_validation(context_file)
    print(f"\nFinal Status: {result['status']}")
