# 🧠 BBC — Bitter Brain Context v8.5

> **Zero-Hallucination AI Coding Framework** — Analyzes your project, detects your active IDE, and provides AI assistants with a verified sealed context.

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v8.5%20STABLE-green)](https://github.com/Anubis44197/BBC)

---

## 📌 What is BBC?

**BBC (Bitter Brain Context)** is a developer infrastructure tool that prevents AI coding assistants (GitHub Copilot, Cursor, Continue, etc.) from **hallucinating** — generating incorrect code based on guesswork instead of your actual codebase.

### How It Works

```
Scan Project  →  Build Sealed Context  →  Detect Active IDE  →  Inject Only Where Needed
```

1. **Scan:** Extracts all classes, functions, and imports via AST analysis
2. **Compress:** Reduces a 100,000-token project to ~10,000 tokens (**89%+ savings**)
3. **Smart Detect:** Identifies your **currently active IDE and installed AI extensions**
4. **Inject:** Writes BBC rules only to detected tools — nothing else is touched

---

## ⚡ Quick Start

### Requirements
- Python 3.8+
- Git

### Option A: One-Command Setup (Recommended)

Clone BBC into your project and run the setup script:

```bash
cd your-project
git clone https://github.com/Anubis44197/BBC.git

# Windows
BBC\setup.bat

# Linux / macOS
bash BBC/setup.sh
```

This automatically installs dependencies and starts BBC on your project.

### Option B: Manual Setup

```bash
# 1. Clone BBC into your project
cd your-project
git clone https://github.com/Anubis44197/BBC.git

# 2. Install dependencies
pip install -r BBC/requirements.txt

# 3. Start BBC
python BBC/bbc.py start .
```

### Option C: Install Command

If you've already cloned BBC, use the `install` command for one-step setup:

```bash
python BBC/bbc.py install .
```

This runs `pip install` + `analyze` + `inject` + `start daemon` in one command.

> **Tip:** Add the BBC directory to your PATH to use `python bbc.py start` from anywhere.

---

## 🎯 Features

### 🔍 Smart IDE Detection
BBC automatically detects which IDE and AI extensions you are actively using:

| Active Environment | BBC Writes |
|---|---|
| **Antigravity** | `.antigravity/rules.md` |
| **Cursor** | `.cursorrules` |
| **VS Code + GitHub Copilot** | `.github/copilot-instructions.md` |
| **VS Code + Continue** | `.continue/config.json` |
| **VS Code + Cline** | `.clinerules` |
| **Windsurf** | `.windsurf/bbc_rules.md` |
| **Not detected** | `.bbc/` folder only |

> Detection method: environment variables → process tree → VS Code extension directory

### 🤖 Full Supported AI Tools (30+)

BBC auto-detects and configures **30+ AI coding tools** across all major IDEs:

| Tool | Config File Written |
|---|---|
| GitHub Copilot (VS Code) | `.github/copilot-instructions.md` |
| Cursor | `.cursorrules` |
| Continue | `.continue/config.json` |
| Windsurf | `.windsurf/bbc_rules.md` |
| Cline | `.clinerules` |
| Kilo Code | `.clinerules` |
| Antigravity | `.antigravity/rules.md` |
| Zed | `.zed/settings.json` |
| JetBrains AI | `.idea/bbc-ai-assistant.xml` |
| Roo Code | `.roo-code/config.json` |
| Cody (Sourcegraph) | `.cody/config.json` |
| CodeGeeX | `.codegeex/config.json` |
| Supermaven | `.supermaven/config.json` |
| CodiumAI / Qodo | `.codiumai/config.json` |
| Pieces | `.pieces/config.json` |
| DeepSeek Coder | `.deepseek/config.json` |
| Refact.ai | `.refact/config.json` |
| Warp | `.warp/config.json` |
| Mintlify | `.mintlify/config.json` |
| Amazon Q | auto-detected |
| Tabnine | auto-detected |
| Codeium | auto-detected |
| IntelliCode | auto-detected |
| Replit AI | `.replit/ai.json` |
| FauxPilot | `.fauxpilot/config.json` |
| AskCodi | auto-detected |
| Codiga | `.codiga/config.json` |
| MutableAI | auto-detected |
| Qodo Gen | `.qodo/config.json` |
| BlackBox AI | auto-detected |
| CodeGPT | auto-detected |

> BBC only writes to tools you have installed. It never creates folders for tools you don't use.

### 🚫 Ghost Injection Prevention
Previous versions created config folders for 20+ tools regardless of whether they were installed. v8.3 eliminates this entirely:
- ❌ **Before:** `.codiumai/`, `.replit/`, `.tabnine/`, `.pieces/`... (20+ folders)
- ✅ **Now:** Only active IDE + installed extensions (1–3 files maximum)

### 📊 Stability Engine
BBC continuously evaluates project health and verification confidence to keep AI work aligned with the current sealed context.

### 💾 Token Savings
```
Source: 132,000 tokens  →  Context: 14,000 tokens  |  89% savings  |  9.4x faster
```

### 🔄 Real-time Re-sealing
BBC's daemon (`bbc_daemon.py`) actively monitors your project for changes every 30 seconds:
- **New files added** → automatic re-analysis + re-injection
- **Files modified** → SHA-256 hash comparison detects stale context, triggers re-seal
- **Files deleted** → context updated to remove orphaned symbols
- **Adaptive feedback (v8.4)** → successful re-seal improves stability tracking, failed re-seal lowers trust until the project is sealed again

The daemon uses `adaptive_mode.check_context_freshness()` for hash-based staleness detection and recommends `RESCAN` or `PARTIAL_RESCAN` based on the ratio of changed files.

### � Agent Integration Layer (v8.5)
BBC now exposes its operational mode directly to AI agents through the sealed context and injected instruction files.

- **Versioning / Compatibility** — `bbc_instructions_version` and `context_schema_version` are written into `.bbc/bbc_context.json` and `BBC_INSTRUCTIONS.md`
- **Freshness Gate** — `context_fresh` tracks whether the current context still matches the project on disk
- **Fail Policy** — `fail_closed` blocks code generation on stale or missing context, while `fail_open` allows continuation with a warning
- **Enforcement Profiles** — `strict`, `balanced`, and `relaxed` profiles define how aggressively BBC should enforce context-first behavior

| Profile | Behavior |
|---|---|
| **strict** | Verified symbols only, impact-first workflow, verify-after-change, patch check, stale context blocks work |
| **balanced** | Verified symbols only, verify-after-change, stale context warns but keeps workflow practical |
| **relaxed** | Context-first guidance remains active, but broader iteration is allowed with warnings |

If a symbol is not in the sealed context, BBC returns: `"Information not found in sealed context"`

### ✅ Full Verifier (v8.4)
BBC's verifier (`bbc_core/verifier.py`) runs a **4-layer verification**:

1. **Syntax Check** — AST parsing for Python, brace balancing for C-family languages
2. **Freshness Check** — SHA-256 hash comparison detects files changed since last seal
3. **Symbol Mismatch** — BBC re-scans disk files and compares against sealed context symbols
4. **Stability Report** — BBC returns project health, trust level, and final verdict

```bash
bbc verify [path]   # Full verification with stability report
```

```
💎 BBC FULL VERIFICATION REPORT
[SYNTAX] No errors found.
[FRESH]  Context is FRESH (42 files verified)
[MATCH]  All symbols consistent (187 symbols)

  AURA FIELD
   S (Structure):  1.0 [STABLE]
   C (Chaos):      0.0 [STABLE]
   P (Pulse):      1.0 [STABLE]
   Aura Score:     0.9847 [STABLE]
   Confidence:     0.726 [WEAK]
  VERDICT: 💎 SEALED_STABLE
```

Verdicts: `💎 SEALED_STABLE` · `⚠️ WEAK` · `🔴 UNSTABLE` · `💀 DEGENERATE`

### 🛡️ Hallucination Guard (v8.4)
Post-generation verification — checks AI-generated code against the sealed BBC context:

- Extracts referenced symbols from generated code
- Compares against `bbc_context.json` known symbols
- Detects speculative language patterns ("probably", "might", "could be")
- Computes verification confidence and verdict
- Reports CVP (Constraint Violation Protocol) violations

```bash
bbc check generated_file.py               # Auto-detect context
bbc check output.py --context path/to/bbc_context.json
bbc check output.py --relaxed              # Only flag speculative language
bbc check output.py --json                 # Machine-readable output
```

### 📦 Token Optimizer (v8.4)
General-purpose token compression built into BBC core (`bbc_core/token_optimizer.py`):

- **Adaptive sampling** — dense regions get more samples, repetitive data is aggressively compressed
- **Compact JSON** — field name shortening, null/empty removal, decimal rounding
- Full pipeline: `optimizer.optimize(data, target_ratio=0.1)`

### 🔍 Semantic Impact Analysis (v8.5)
BBC can estimate the blast radius of a change before you commit it:

- Maps direct dependents of a changed file
- Finds indirect downstream effects
- Tracks symbol-level impact when specific functions or classes are changed
- Ranks semantically similar files for review
- Returns a risk verdict for the proposed change

```bash
python bbc.py impact bbc_core/verifier.py --symbols verify_full
python bbc.py impact bbc_core/verifier.py --op Refactor
```

### 🔧 Auto Patcher (v8.5)
BBC can scan the project for safe cleanup opportunities and propose fixes:

- Detects silent exception handling patterns
- Detects some unused imports
- Flags symbol drift that requires resealing
- Runs in preview mode by default
- Applies only safe patches when explicitly requested

```bash
python bbc.py patch .
python bbc.py patch . --apply
```

### 🔗 Git Hooks — Team Automation (v8.4)
Automatic BBC re-sealing on `git checkout` and `git merge`:

```bash
bbc hooks [path]           # Install post-checkout + post-merge hooks
bbc hooks [path] --remove  # Remove BBC hooks
```

Every team member gets automatic context re-sealing without manual intervention.

Verification also runs automatically at the end of every `bbc start` and `bootstrap` pipeline.

---

## 🖥️ CLI Commands

All user-facing commands go through `bbc.py` — the single entry point:

| Command | Description |
|---|---|
| `bbc start [path]` | Full pipeline: analyze + verify + inject + daemon |
| `bbc analyze [path]` | Deep project scan, generate sealed context |
| `bbc verify [path]` | Check structural integrity (freshness gate + fail policy) |
| `bbc check <file>` | Hallucination guard — check AI-generated code against context |
| `bbc impact <file>` | Semantic impact analysis of a file change |
| `bbc patch [path]` | Detect and auto-fix code issues (dry-run by default) |
| `bbc inject [path]` | Inject BBC instructions into AI agent config files |
| `bbc hooks [path]` | Install/remove BBC git hooks for team automation |
| `bbc install [path]` | One-command setup: deps + analyze + inject + start |
| `bbc serve` | Start REST API server |
| `bbc status [path]` | Show system status (context + daemon) |
| `bbc watch [path]` | Watch AI operations in IDE terminal |
| `bbc stop [path]` | Stop BBC daemon |
| `bbc audit [path]` | Audit BBC traces |
| `bbc purge [path]` | Complete BBC removal |
| `bbc menu [path]` | Interactive TUI menu |

### Global Options

| Option | Values | Description |
|---|---|---|
| `--enforcement` | `strict` / `balanced` / `relaxed` | Override enforcement level |
| `--fail-policy` | `fail_closed` / `fail_open` | Override fail policy |

### CLI Architecture Note
> `bbc.py` is the **user-facing CLI** — all commands should be run through it.
> `run_bbc.py` is the **internal engine CLI** used by `bbc.py` under the hood. Users should not call it directly.

---

## 📂 Project Structure

```
BBC/
├── bbc.py                    # Main CLI entry point
├── bbc_daemon.py             # Real-time file watcher daemon
├── run_bbc.py                # Direct execution runner
├── setup.bat                 # One-command setup (Windows)
├── setup.sh                  # One-command setup (Linux/Mac)
├── bbc_core/
│   ├── agent_adapter.py      # IDE/Extension detection + Context injection
│   ├── ide_auto_config.py    # Smart IDE/plugin detection system
│   ├── ide_hooks.py          # IDE lifecycle hooks
│   ├── native_adapter.py     # Main analysis orchestrator (the bridge)
│   ├── adapter.py            # Low-level BBC adapter interface
│   ├── auto_detector.py      # Auto-detect project + start BBC pipeline
│   ├── symbol_extractor.py   # AST-based symbol extractor (deep scan)
│   ├── symbol_graph.py       # Dependency call graph builder
│   ├── context_optimizer.py  # Blast radius & context filter
│   ├── adaptive_mode.py      # STRICT / RELAXED mode switcher
│   ├── internal_engine.py    # Core processing pipeline
│   ├── internal_indexer.py   # Vector index builder for similarity search
│   ├── internal_quantizer.py # Token compression & quantization
│   ├── internal_ops.py       # Internal operations
│   ├── bbc_scalar.py         # BBC scalar state logic (STABLE/WEAK/DEGENERATE)
│   ├── config.py             # Global configuration & paths
│   ├── state_manager.py      # Session & daemon state manager
│   ├── telemetry.py          # Operational telemetry & session tracking
│   ├── verifier.py           # Full verifier (syntax, freshness, mismatch, stability)
│   ├── hallucination_guard.py # Post-generation hallucination detector
│   ├── token_optimizer.py    # Adaptive token compressor
│   ├── impact_analyzer.py    # Change impact analysis and blast-radius report
│   ├── auto_patcher.py       # Safe automatic patch preview/apply engine
│   ├── git_hooks.py          # Git hook generator for team automation
│   ├── attribution_tracer.py # Symbol attribution & call trace
│   ├── migrator_engine.py    # Legacy context migration engine
│   ├── ai_integration.py     # External AI API integration helpers
│   ├── realtime_token_counter.py # Live token usage tracker
│   ├── terminal_monitor.py   # Terminal output monitor
│   ├── http_server.py        # REST API server (FastAPI)
│   ├── global_menu.py        # Interactive TUI global menu
│   ├── global_setup.py       # First-run environment setup
│   ├── bbc_logger.py         # Structured logging system
│   └── cli.py                # CLI command handler
├── requirements.txt          # Python dependencies
├── setup.py                  # pip install support
├── pyproject.toml            # Project metadata
└── tests/                    # Unit tests
```

### Generated Files (`.bbc/` directory)
```
.bbc/
├── bbc_context.json          # Sealed project context (AI's single source of truth)
├── BBC_INSTRUCTIONS.md       # AI instruction manifest
├── bbc_context.md            # Human-readable context summary
├── bbc_rules.md              # Project coding rules
├── indices/                  # Vector indices for similarity search
├── cache/                    # Project snapshot cache
├── logs/                     # Daemon and session logs
└── manifest/                 # Injected file registry
```

All `.bbc/` files are automatically added to `.gitignore` — they never pollute your repository.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**BBC v8.5 STABLE** — Your AI assistants now see your project through a verified sealed context.

*No hallucinations. No guesswork. Only verified context.*

</div>
