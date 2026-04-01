⚠️⚠️⚠️ CRITICAL: READ THIS FILE AT THE START OF EVERY NEW CHAT SESSION ⚠️⚠️⚠️

# BBC SEALED CONTEXT - MANDATORY READING
**This file MUST be read at the beginning of EVERY conversation, including new chat windows.**

---

## 🔒 YOU ARE IN BBC SEALED MODE

**What this means**:
- This project has been analyzed and sealed by BBC (Bitter Brain Context)
- You have access to a verified, hallucination-free context
- You MUST follow the constraints below

---

## 📋 MANDATORY RULES (NEVER SKIP)

### 1. Symbol Verification
✅ **USE ONLY** symbols from verified context files:
   - `.bbc/bbc_context.json` (primary source - ALL symbols)
   - `.github/copilot-instructions.md` (for GitHub Copilot)
   - `.cursorrules` (for Cursor IDE)
   - `.clinerules` (for Cline/Kilo Code)

### 2. Hallucination Prevention
❌ **DO NOT**:
   - Infer or assume code structure
   - Create functions/classes not in verified list
   - Guess import paths or module names
   - Generate speculative code ("probably", "might", "could be")

### 3. Unknown Symbol Protocol
⚠️ **IF SYMBOL NOT FOUND**:
   - Respond exactly: "Symbol not found in BBC sealed context"
   - Do NOT attempt to create it
   - Ask user to run: `python bbc.py analyze .`

### 4. Fail Policy
If context is missing or STALE, do NOT write code. Only explain what is needed and suggest running `python bbc.py analyze`.

### 5. Enforcement Level: STRICT

6. **IMPACT-FIRST:** Before modifying any file, run `python bbc.py impact <file> --symbols <changed_symbols>`. If risk is CAUTION or HIGH, ask user for confirmation before proceeding.
7. **VERIFY-AFTER:** After every code change, run `python bbc.py verify .` to confirm structural integrity.
8. **PATCH-CHECK:** After changes, run `python bbc.py patch .` (dry-run) to detect regressions.

---

## 📊 CURRENT PROJECT STATUS

**Verification Status**: ✅ SEALED_STABLE
**Last Sealed**: 2026-03-31 20:19:10
**Files Scanned**: 81
**Symbols Verified**: 75 classes, 636 functions

**Context Fresh**: FRESH
**Enforcement Level**: STRICT
**Fail Policy**: FAIL_CLOSED

---

## 🚨 NEW CHAT SESSION CHECKLIST

**Every time you start a new conversation**:
1. ✅ Read this file (`.bbc/BBC_INSTRUCTIONS.md`)
2. ✅ Read `.bbc/bbc_context.json` (verified symbols)
3. ✅ Read `.bbc/bbc_rules.md` (project rules)
4. ✅ Check context freshness (see timestamp above)
5. ✅ If stale, ask user to run: `python bbc.py verify .`

---

## 🔍 WHERE TO FIND VERIFIED SYMBOLS

**Primary Source** (always read this):
- `.bbc/bbc_context.json` → Complete symbol list with file paths

**Human-Readable Summary**:
- `.bbc/bbc_context.md` → Project overview

**Project-Specific Skills** (read for task-specific workflows):
- `.bbc/skills/BBC_SKILL.md` → General BBC workflow
- `.bbc/skills/BBC_SKILL_BUGFIX.md` → Bugfix workflow (stack-specific)
- `.bbc/skills/BBC_SKILL_FEATURE.md` → Feature implementation workflow
- `.bbc/skills/BBC_SKILL_REVIEW.md` → Code review workflow
- `.bbc/skills/BBC_SKILL_REFACTOR.md` → Refactoring workflow

**Tool-Specific Configs** (auto-generated from context):
- `.github/copilot-instructions.md` ← GitHub Copilot
- `.cursorrules` ← Cursor IDE
- `.clinerules` ← Cline/Kilo Code

---

## 🛡️ ENFORCEMENT DETAILS

**BBC Version**: 8.3.0
**Schema Version**: 8.5
**Instructions Version**: 1.0

**What STRICT means**:
- Verified symbols ONLY
- Impact-first workflow
- Verify after every change
- Stale context blocks work

**If you violate these rules**:
- Your output will be flagged by BBC hallucination guard
- User will be notified of constraint violations
- Code may be rejected

---

## 📞 TROUBLESHOOTING

**Context seems outdated?**
→ Ask user to run: `python bbc.py verify .`

**Symbol not in context but should be?**
→ Ask user to run: `python bbc.py analyze .`

**Need to check impact of a change?**
→ Ask user to run: `python bbc.py impact <file>`

**Want to verify generated code?**
→ Ask user to run: `python bbc.py check <file>`

---

**BBC (Bitter Brain Context) v8.3 - Zero Hallucination AI Coding Framework**
**Last Updated**: 2026-03-31 20:19:10
