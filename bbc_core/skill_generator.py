"""
BBC Enhanced Skill Generator v8.3
Generates project-specific, stack-aware skills with examples and checklists
Inspired by: UI/UX Pro Max, OpenSkills, Remotion Skills
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class BBCSkillGenerator:
    """
    Generates rich, project-specific skills based on:
    - Detected tech stack
    - Project structure
    - Common patterns
    - Industry best practices
    """
    
    STACK_PATTERNS = {
        "react": ["react", "jsx", "tsx", "next.js", "gatsby", "vite"],
        "vue": ["vue", ".vue", "nuxt"],
        "angular": ["angular", "@angular"],
        "svelte": ["svelte", "sveltekit"],
        "python": [".py", "django", "flask", "fastapi", "requirements.txt"],
        "node": ["express", "koa", "nest", "package.json"],
        "rust": [".rs", "cargo.toml"],
        "go": [".go", "go.mod"],
        "swift": [".swift", "swiftui"],
        "kotlin": [".kt", "android"],
        "flutter": ["flutter", ".dart"],
        "php": [".php", "laravel", "symfony"],
        "ruby": [".rb", "rails", "gemfile"],
    }
    
    def __init__(self, context_data: dict, project_root: str):
        self.context = context_data
        self.project_root = Path(project_root)
        self.code_structure = context_data.get("code_structure", [])
        self.skeleton = context_data.get("project_skeleton", {})
        self.detected_stacks = self._detect_stacks()
        self.project_type = self._detect_project_type()
        
    def _detect_stacks(self) -> List[str]:
        """Detect tech stacks from file extensions and dependencies"""
        stacks = set()
        
        for entry in self.code_structure:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "").lower()
            
            for stack, patterns in self.STACK_PATTERNS.items():
                if any(p in path for p in patterns):
                    stacks.add(stack)
        
        deps_str = json.dumps(self.context.get("dependencies", {})).lower()
        for stack, patterns in self.STACK_PATTERNS.items():
            if any(p in deps_str for p in patterns):
                stacks.add(stack)
        
        return list(stacks)
    
    def _detect_project_type(self) -> str:
        """Detect project type (web, mobile, backend, cli, etc.)"""
        indicators = {
            "web_frontend": ["react", "vue", "angular", "svelte", "html", "css"],
            "web_backend": ["express", "flask", "django", "fastapi", "spring"],
            "mobile": ["swift", "kotlin", "flutter", "react-native"],
            "cli": ["argparse", "click", "cobra", "clap"],
            "library": ["setup.py", "cargo.toml", "package.json"],
        }
        
        deps_str = json.dumps(self.context).lower()
        
        for ptype, keywords in indicators.items():
            if any(kw in deps_str for kw in keywords):
                return ptype
        
        return "general"
    
    def _get_top_symbols(self, limit: int = 15) -> List[str]:
        """Extract top symbols for examples"""
        symbols = []
        for entry in self.code_structure[:limit]:
            if not isinstance(entry, dict):
                continue
            structure = entry.get("structure", {})
            path = entry.get("path", "")
            
            for cls in structure.get("classes", [])[:3]:
                symbols.append(f"{cls} (from {path})")
            for func in structure.get("functions", [])[:3]:
                symbols.append(f"{func}() (from {path})")
        
        return symbols[:limit]
    
    def _get_stack_specific_bugfix_guidance(self) -> str:
        """Get stack-specific bugfix best practices"""
        guidance = []
        
        if "react" in self.detected_stacks:
            guidance.append("""
**React/Next.js**:
- Check for missing `key` props in lists
- Verify `useEffect` dependencies array
- Ensure state updates are immutable
- Check for stale closures in callbacks
- Verify proper cleanup in useEffect returns
""")
        
        if "python" in self.detected_stacks:
            guidance.append("""
**Python**:
- Check for mutable default arguments
- Verify exception handling doesn't swallow errors
- Ensure proper resource cleanup (context managers)
- Check for off-by-one errors in loops
- Verify proper async/await usage
""")
        
        if "rust" in self.detected_stacks:
            guidance.append("""
**Rust**:
- Check for unwrap() calls (use proper error handling)
- Verify lifetime annotations are correct
- Ensure proper ownership transfer
- Check for panic! in production code
- Verify proper trait bounds
""")
        
        if "go" in self.detected_stacks:
            guidance.append("""
**Go**:
- Check for unchecked errors
- Verify goroutine cleanup (context cancellation)
- Ensure proper mutex usage
- Check for nil pointer dereferences
- Verify defer statements are correct
""")
        
        return "\n".join(guidance) if guidance else "**General**: Follow language-specific best practices"
    
    def _get_stack_specific_patterns(self) -> str:
        """Get stack-specific architectural patterns"""
        patterns = []
        
        if "react" in self.detected_stacks:
            patterns.append("""
**React/Next.js**:
- Components: Follow existing component structure (functional vs class)
- State Management: Use existing pattern (Context, Redux, Zustand, etc.)
- Routing: Follow existing routing setup
- API Calls: Use existing fetch/axios wrapper
- Styling: Follow existing CSS/Tailwind/styled-components pattern
""")
        
        if "python" in self.detected_stacks:
            patterns.append("""
**Python**:
- Modules: Follow existing package structure
- Classes: Use existing base classes/mixins
- Async: Match existing async/await vs sync pattern
- Error Handling: Use existing exception hierarchy
- Config: Use existing config management (env vars, files, etc.)
""")
        
        if "node" in self.detected_stacks:
            patterns.append("""
**Node.js/Express**:
- Middleware: Follow existing middleware chain
- Routes: Use existing routing pattern
- Error Handling: Use existing error middleware
- Database: Follow existing ORM/query pattern
- Authentication: Use existing auth strategy
""")
        
        return "\n".join(patterns) if patterns else "**General**: Follow existing code patterns"
    
    def generate_bugfix_skill(self) -> str:
        """Generate enhanced bugfix skill with stack-specific guidance"""
        symbols = self._get_top_symbols(10)
        symbol_examples = "\n".join(f"   - `{s}`" for s in symbols[:5])
        
        stack_guidance = self._get_stack_specific_bugfix_guidance()
        
        return f"""---
name: bbc-bugfix
description: Resolve defects with minimal behavior-preserving changes using BBC sealed context
stack: {', '.join(self.detected_stacks) or 'general'}
project_type: {self.project_type}
---

# BBC Bugfix Skill

## Purpose
Resolve defects with the smallest possible behavior-preserving changes, using verified symbols from BBC sealed context.

## Pre-Flight Checklist
Before starting any bugfix:
- [ ] Read `.bbc/bbc_context.json` (verified symbols)
- [ ] Read `.bbc/bbc_rules.md` (project rules)
- [ ] Confirm context is FRESH (check timestamp)
- [ ] Identify failing behavior precisely

## Workflow

### 1. Map Failing Behavior to Symbols
**Use BBC context to locate impacted symbols**:
```bash
# Check which symbols are affected
python bbc.py impact <file> --symbols <symbol_name>
```

**Example symbols in this project**:
{symbol_examples}

### 2. Locate Root Cause
**Use dependency graph**:
- Check `.bbc/bbc_context.json` → `code_structure` → `depends_on`
- Trace call chain backwards from symptom to root cause
- Verify all symbols exist in sealed context

**Anti-Pattern**: ❌ Don't guess at function names or imports
**Best Practice**: ✅ Only use symbols from verified context

### 3. Apply Minimal Fix
**Principles**:
- Change ONLY what's necessary
- Preserve existing contracts (function signatures, return types)
- Don't refactor while fixing bugs
- Don't add features while fixing bugs

**Stack-Specific Guidance**:
{stack_guidance}

### 4. Verify Fix
**Run verification**:
```bash
# Check structural integrity
python bbc.py verify .

# Check impact radius
python bbc.py impact <fixed_file>

# Run hallucination guard on changes
python bbc.py check <fixed_file>
```

## Pre-Delivery Checklist
Before submitting fix:
- [ ] Fix addresses root cause (not just symptom)
- [ ] No new symbols introduced (unless approved)
- [ ] All changed symbols exist in BBC context
- [ ] `python bbc.py verify .` passes
- [ ] Impact radius is minimal (LOW or SAFE)
- [ ] No speculative language in comments ("probably", "might")
- [ ] Tests added/updated (if applicable)

## Common Anti-Patterns to Avoid
❌ **Shotgun Surgery**: Changing multiple unrelated files
❌ **Speculative Fixes**: "This might fix it" without root cause analysis
❌ **Hallucinated Imports**: Adding imports not in verified context
❌ **Over-Engineering**: Adding abstraction layers for simple bugs
❌ **Silent Failures**: Catching exceptions without logging

## Example: Typical Bugfix Flow
```
1. User reports: "Function X crashes on empty input"
2. Check BBC context: Does function X exist? → Yes, in file Y
3. Read file Y, locate function X
4. Identify bug: Missing null check
5. Apply minimal fix: Add null check
6. Run: python bbc.py verify .
7. Run: python bbc.py impact Y --symbols X
8. Confirm: Impact is LOW, no dependencies broken
9. Submit fix
```

## Resources
- BBC Context: `.bbc/bbc_context.json`
- Project Rules: `.bbc/bbc_rules.md`
- Dependency Graph: Check `depends_on` field in context
- Impact Analysis: `python bbc.py impact <file>`

---
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**BBC Version**: 8.3.0
"""
    
    def generate_feature_skill(self) -> str:
        """Generate enhanced feature implementation skill"""
        symbols = self._get_top_symbols(10)
        symbol_examples = "\n".join(f"   - `{s}`" for s in symbols[:5])
        
        stack_patterns = self._get_stack_specific_patterns()
        
        return f"""---
name: bbc-feature
description: Implement new features while preserving existing architecture contracts
stack: {', '.join(self.detected_stacks) or 'general'}
project_type: {self.project_type}
---

# BBC Feature Implementation Skill

## Purpose
Implement new behavior while preserving existing architecture contracts and using only verified symbols from BBC sealed context.

## Pre-Flight Checklist
Before implementing any feature:
- [ ] Read `.bbc/bbc_context.json` (verified symbols)
- [ ] Read `.bbc/bbc_rules.md` (project rules)
- [ ] Understand existing architecture patterns
- [ ] Identify extension points (where to add new code)
- [ ] Plan impact radius

## Workflow

### 1. Locate Extension Points
**Use BBC context to find where to add new code**:
```bash
# Check existing structure
python bbc.py impact <target_file>
```

**Example extension points in this project**:
{symbol_examples}

### 2. Design Feature
**Principles**:
- Follow existing patterns (don't introduce new paradigms)
- Reuse existing symbols where possible
- Minimize new dependencies
- Keep blast radius small

**Stack-Specific Patterns**:
{stack_patterns}

### 3. Implement Feature
**Best Practices**:
- ✅ Use existing classes/functions as templates
- ✅ Follow naming conventions from BBC context
- ✅ Add proper type hints/annotations
- ✅ Include docstrings/comments
- ❌ Don't create symbols that conflict with existing ones
- ❌ Don't hallucinate imports or dependencies

### 4. Verify Implementation
**Run verification**:
```bash
# Check structural integrity
python bbc.py verify .

# Check impact radius
python bbc.py impact <new_file>

# Ensure no hallucinations
python bbc.py check <new_file>
```

## Pre-Delivery Checklist
Before submitting feature:
- [ ] Feature follows existing architecture patterns
- [ ] All new symbols follow project naming conventions
- [ ] No hallucinated imports or dependencies
- [ ] `python bbc.py verify .` passes
- [ ] Impact radius documented
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes to existing APIs

## Common Anti-Patterns to Avoid
❌ **Not Invented Here**: Reimplementing existing functionality
❌ **Gold Plating**: Adding unnecessary features
❌ **Tight Coupling**: Creating hard dependencies on new code
❌ **Breaking Changes**: Modifying existing function signatures
❌ **Inconsistent Style**: Not following project conventions

## Example: Typical Feature Flow
```
1. User requests: "Add user authentication"
2. Check BBC context: Find existing auth-related symbols
3. Identify pattern: Project uses JWT tokens
4. Design: Add new auth middleware following existing pattern
5. Implement: Create new symbols, reuse existing utilities
6. Run: python bbc.py verify .
7. Run: python bbc.py impact auth_middleware.py
8. Confirm: No breaking changes, impact is SAFE
9. Submit feature
```

## Resources
- BBC Context: `.bbc/bbc_context.json`
- Project Rules: `.bbc/bbc_rules.md`
- Architecture Patterns: Check existing similar features in context
- Impact Analysis: `python bbc.py impact <file>`

---
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**BBC Version**: 8.3.0
"""
    
    def generate_review_skill(self) -> str:
        """Generate code review skill"""
        return f"""---
name: bbc-review
description: Review code for correctness risks, regressions, and missing validations
stack: {', '.join(self.detected_stacks) or 'general'}
project_type: {self.project_type}
---

# BBC Code Review Skill

## Purpose
Review code changes for correctness risks, potential regressions, and missing validations using BBC sealed context as the source of truth.

## Pre-Flight Checklist
Before reviewing code:
- [ ] Read `.bbc/bbc_context.json` (verified symbols)
- [ ] Read `.bbc/bbc_rules.md` (project rules)
- [ ] Understand what changed (diff/PR description)
- [ ] Check if context is fresh

## Review Checklist

### 1. Symbol Verification
- [ ] All referenced symbols exist in BBC context
- [ ] No hallucinated functions or imports
- [ ] No speculative language in code/comments
- [ ] Naming follows project conventions

### 2. Structural Integrity
```bash
# Run verification
python bbc.py verify .

# Check impact
python bbc.py impact <changed_file>
```

- [ ] Verify passes (no syntax errors)
- [ ] Impact radius is acceptable
- [ ] No unintended dependencies introduced

### 3. Correctness Risks
- [ ] Error handling is comprehensive
- [ ] Edge cases are covered
- [ ] Input validation is present
- [ ] Resource cleanup is proper
- [ ] Concurrency issues addressed (if applicable)

### 4. Regression Risks
- [ ] Existing tests still pass
- [ ] No breaking changes to public APIs
- [ ] Backward compatibility maintained
- [ ] Dependencies not broken

### 5. Security Review
- [ ] No hardcoded secrets
- [ ] Input sanitization present
- [ ] SQL injection prevention (if applicable)
- [ ] XSS prevention (if applicable)
- [ ] Proper authentication/authorization

### 6. Performance Review
- [ ] No obvious performance regressions
- [ ] Efficient algorithms used
- [ ] No memory leaks
- [ ] Proper caching (if applicable)

## Anti-Patterns to Flag
❌ **Silent Failures**: Catching exceptions without logging
❌ **Magic Numbers**: Hardcoded values without constants
❌ **God Objects**: Classes doing too much
❌ **Tight Coupling**: Hard dependencies between modules
❌ **Premature Optimization**: Complex code without benchmarks

## Review Comments Template
```
**Symbol Verification**: ✅ PASS / ❌ FAIL
- Issue: [describe any hallucinated symbols]

**Structural Integrity**: ✅ PASS / ❌ FAIL
- Verify: [pass/fail]
- Impact: [LOW/SAFE/CAUTION/HIGH]

**Correctness**: ✅ PASS / ⚠️ CONCERNS / ❌ FAIL
- [list concerns]

**Security**: ✅ PASS / ⚠️ CONCERNS / ❌ FAIL
- [list concerns]

**Recommendation**: APPROVE / REQUEST_CHANGES / REJECT
```

---
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**BBC Version**: 8.3.0
"""
    
    def generate_refactor_skill(self) -> str:
        """Generate refactoring skill"""
        return f"""---
name: bbc-refactor
description: Improve structure and maintainability without altering behavior
stack: {', '.join(self.detected_stacks) or 'general'}
project_type: {self.project_type}
---

# BBC Refactor Skill

## Purpose
Improve code structure and maintainability without altering external behavior, using BBC sealed context to ensure no regressions.

## Pre-Flight Checklist
Before refactoring:
- [ ] Read `.bbc/bbc_context.json` (verified symbols)
- [ ] Read `.bbc/bbc_rules.md` (project rules)
- [ ] Define refactor boundaries (what will change)
- [ ] Ensure tests exist (or add them first)
- [ ] Document current behavior

## Workflow

### 1. Define Refactor Boundaries
**Use BBC context to understand impact**:
```bash
# Check dependencies
python bbc.py impact <target_file>
```

**Refactor Types**:
- **Extract Method**: Pull out complex logic into separate function
- **Rename**: Improve naming clarity
- **Move**: Reorganize code location
- **Simplify**: Reduce complexity
- **Remove Duplication**: DRY principle

### 2. Plan Refactor
**Principles**:
- ✅ Preserve external behavior (no API changes)
- ✅ Keep blast radius minimal
- ✅ Refactor in small steps
- ✅ Run tests after each step
- ❌ Don't mix refactoring with feature work
- ❌ Don't refactor without tests

### 3. Execute Refactor
**Best Practices**:
1. Make one change at a time
2. Run tests after each change
3. Commit frequently
4. Verify BBC context stays valid

### 4. Verify Refactor
```bash
# Check structural integrity
python bbc.py verify .

# Ensure behavior unchanged
python bbc.py impact <refactored_file>

# Check for hallucinations
python bbc.py check <refactored_file>
```

## Pre-Delivery Checklist
Before submitting refactor:
- [ ] All tests pass
- [ ] No behavior changes (external APIs unchanged)
- [ ] `python bbc.py verify .` passes
- [ ] Impact radius is acceptable
- [ ] Code is more maintainable than before
- [ ] No new technical debt introduced
- [ ] Documentation updated (if needed)

## Common Refactoring Patterns

### Extract Method
**Before**:
```python
def process_order(order):
    # 50 lines of complex logic
    ...
```

**After**:
```python
def process_order(order):
    validate_order(order)
    calculate_total(order)
    apply_discounts(order)
    finalize_order(order)
```

### Rename for Clarity
**Before**: `def calc(x, y):`
**After**: `def calculate_total_price(quantity, unit_price):`

### Remove Duplication
**Before**: Same logic in 3 places
**After**: Shared utility function

## Anti-Patterns to Avoid
❌ **Big Bang Refactor**: Changing everything at once
❌ **Refactor Without Tests**: No safety net
❌ **Scope Creep**: Adding features during refactor
❌ **Breaking APIs**: Changing function signatures
❌ **Premature Abstraction**: Over-engineering

---
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**BBC Version**: 8.3.0
"""
    
    def generate_general_skill(self) -> str:
        """Generate general BBC skill"""
        symbols = self._get_top_symbols(15)
        symbol_list = "\n".join(f"   - `{s}`" for s in symbols)
        
        return f"""---
name: bbc-general
description: Guide AI assistants to operate with BBC context-first rules
stack: {', '.join(self.detected_stacks) or 'general'}
project_type: {self.project_type}
---

# BBC Project Skill

## Purpose
Guide AI assistants to operate with BBC (Bitter Brain Context) sealed mode rules for this project.

## Critical: Read This First
**EVERY time you start a new conversation**:
1. ✅ Read `.bbc/bbc_context.json` (verified symbols)
2. ✅ Read `.bbc/bbc_rules.md` (project rules)
3. ✅ Check context freshness
4. ✅ Follow enforcement rules

## Project Overview

**Tech Stack**: {', '.join(self.detected_stacks) or 'General'}
**Project Type**: {self.project_type}
**Files Scanned**: {self.skeleton.get('file_count', 0)}
**Symbols Available**: {len(symbols)}

## Available Symbols (Top 15)
{symbol_list}

**Full symbol list**: See `.bbc/bbc_context.json` → `code_structure`

## Hard Constraints

### 1. Symbol Verification
✅ **USE ONLY** symbols from `.bbc/bbc_context.json`
❌ **DO NOT** hallucinate functions, classes, or imports

### 2. Hallucination Prevention
❌ **FORBIDDEN LANGUAGE**:
   - "probably", "might", "could be", "perhaps"
   - "I think", "I assume", "I believe"
   - "typically", "usually", "generally"

✅ **REQUIRED LANGUAGE**:
   - "According to BBC context..."
   - "Verified symbol: ..."
   - "Not found in sealed context"

### 3. Workflow Rules
**Before ANY code change**:
```bash
# Check impact
python bbc.py impact <file>

# If impact is CAUTION or HIGH, ask user for confirmation
```

**After ANY code change**:
```bash
# Verify structural integrity
python bbc.py verify .

# Check for hallucinations
python bbc.py check <changed_file>
```

## Task-Specific Skills

For specific tasks, use specialized skills:
- **Bugfix**: Read `.bbc/skills/BBC_SKILL_BUGFIX.md`
- **Feature**: Read `.bbc/skills/BBC_SKILL_FEATURE.md`
- **Review**: Read `.bbc/skills/BBC_SKILL_REVIEW.md`
- **Refactor**: Read `.bbc/skills/BBC_SKILL_REFACTOR.md`

## Resources
- **Primary Context**: `.bbc/bbc_context.json`
- **Project Rules**: `.bbc/bbc_rules.md`
- **Human Summary**: `.bbc/bbc_context.md`
- **Dependency Graph**: Check `depends_on` in context

---
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**BBC Version**: 8.3.0
"""
    
    def generate_all_skills(self) -> Dict[str, str]:
        """Generate all skills"""
        return {
            "BBC_SKILL.md": self.generate_general_skill(),
            "BBC_SKILL_BUGFIX.md": self.generate_bugfix_skill(),
            "BBC_SKILL_FEATURE.md": self.generate_feature_skill(),
            "BBC_SKILL_REVIEW.md": self.generate_review_skill(),
            "BBC_SKILL_REFACTOR.md": self.generate_refactor_skill(),
        }
