# 🧠 BBC — Bitter Brain Context v8.3

> **Zero-Hallucination AI Coding Framework** — Analyzes your project, detects your active IDE, and provides AI assistants with a mathematically sealed context.

[![BBC CI](https://github.com/Anubis44197/BBC_MASTER_BBCMath/actions/workflows/ci.yml/badge.svg)](https://github.com/Anubis44197/BBC_MASTER_BBCMath/actions)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v8.3%20STABLE-green)](https://github.com/Anubis44197/BBC_MASTER_BBCMath)

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

### 1. Clone the Repository

```bash
git clone https://github.com/Anubis44197/BBC_MASTER_BBCMath.git
cd BBC_MASTER_BBCMath
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start BBC on Your Project

```bash
# Windows
python bbc.py start C:\path\to\your\project

# Linux / macOS
python3 bbc.py start /path/to/your/project

# Current directory
python bbc.py start .
```

> **Tip:** Add `bbc.bat` (Windows) or `bbc.sh` (Linux/macOS) to your PATH to use the shorthand `bbc start` command.

### Alternative: Self-Installing Launcher (End-User Distribution)

If you want to give BBC to someone without requiring a manual clone, use the **self-installing `bbc.bat`** from the distribution repository:

```
https://github.com/Anubis44197/BBC.git
```

The user only receives **`bbc.bat`**. On first run it:
1. Checks for Python + Git
2. Clones `BBC_MASTER_BBCMath` into `%APPDATA%\BBC\` automatically
3. Installs all dependencies
4. Runs BBC on the current project

No manual setup required on the user's side.

---

## 🎯 Features

### 🔍 Smart IDE Detection (v8.3)
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

### 📊 Mathematical Stability Engine (HMPU)
BBC measures your project's structural health using a **3×3 Aura Matrix**:

```
Condition Number (κ) < 10  →  💎 STABLE   — AI operates with high confidence
Condition Number (κ) > 20  →  ⚠️  WEAK    — High risk of AI hallucination
```

### 💾 Token Savings
```
Source: 132,000 tokens  →  Context: 14,000 tokens  |  89% savings  |  9.4x faster
```

### 🔄 Real-time Re-sealing
BBC's daemon (`bbc_daemon.py`) watches for file changes. If your code changes after AI interaction, it automatically triggers a re-analysis to prevent stale context.

### 🧠 Adaptive Mode (STRICT / RELAXED)
BBC operates in two modes depending on context match quality:

| Mode | Trigger | Behavior |
|---|---|---|
| **STRICT** | `context_match_ratio ≥ 0.8` | AI only uses verified symbols from `.bbc/bbc_context.json` |
| **RELAXED** | `context_match_ratio < 0.8` | AI may use broader knowledge with a hallucination warning |

If a symbol is not in the sealed context, BBC returns: `"Information not found in sealed context"`

### ✅ Verifier
BBC's built-in verifier (`bbc_core/verifier.py`) runs structural integrity checks on the sealed context:
- Syntax correctness of all extracted symbols
- Completeness of the call graph
- Detects orphaned or unreachable symbols

```bash
bbc verify [path]   # Run structural check manually
```

Verification also runs automatically at the end of every `bbc start` and `bootstrap` pipeline.

---

## 🛠️ Commands

```bash
# Full pipeline: Verify + Analyze + Inject + Start Daemon
bbc start [path]

# Force refresh (use after code changes)
bbc start -f [path]

# Run daemon in background
bbc start -b [path]

# Deep project analysis only
bbc analyze [path]

# Check structural integrity
bbc verify [path]

# Audit BBC traces in a project
bbc audit [path]

# Install BBC into a target project (copies engine + runs bootstrap)
bbc install [target_path]

# Start REST API + MCP server (default port 3333)
bbc serve
bbc serve --port 8080

# Show system status
bbc status

# Stop BBC daemon
bbc stop

# Remove all BBC files from a project
bbc purge [path]

# Update BBC to the latest version (self-installing bat only)
bbc update
```

---

## 📂 Project Structure

```
BBC_MASTER_BBCMath/
├── bbc.py                    # Main CLI entry point
├── bbc_daemon.py             # Real-time file watcher daemon
├── bbc_installer.py          # System-level installation engine
├── run_bbc.py                # Direct execution runner
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
│   ├── hmpu_core.py          # Mathematical stability governor
│   ├── hmpu_engine.py        # HMPU v8.3 pipeline orchestrator
│   ├── hmpu_indexer.py       # Vector index builder for similarity search
│   ├── hmpu_quantizer.py     # Token compression & quantization
│   ├── matrix_ops.py         # Linear algebra operations (Aura Matrix)
│   ├── bbc_scalar.py         # BBC scalar state logic (STABLE/WEAK/DEGENERATE)
│   ├── config.py             # Global configuration & paths
│   ├── state_manager.py      # Session & daemon state manager
│   ├── telemetry.py          # Operational telemetry & session tracking
│   ├── verifier.py           # Sealed context integrity checker
│   ├── attribution_tracer.py # Symbol attribution & call trace
│   ├── migrator_engine.py    # Legacy context migration engine
│   ├── ai_integration.py     # External AI API integration helpers
│   ├── realtime_token_counter.py # Live token usage tracker
│   ├── terminal_monitor.py   # Terminal output monitor
│   ├── http_server.py        # REST API + MCP server (FastAPI)
│   ├── global_menu.py        # Interactive TUI global menu
│   ├── global_setup.py       # First-run environment setup
│   ├── bbc_logger.py         # Structured logging system
│   └── cli.py                # CLI command handler
├── 01_Engine/
│   ├── hmpu_api_v53.py       # FastAPI industrial endpoint (v5.3)
│   ├── hmpu_core.py          # Core HMPU math engine
│   ├── hmpu_fused_pipeline.py# Fused analysis + quantization pipeline
│   ├── hmpu_indexer.py       # High-performance vector indexer
│   ├── hmpu_master_pipeline.py # Master orchestration pipeline
│   ├── hmpu_quantizer.py     # Token quantizer (production grade)
│   ├── hmpu_weights.json     # Pre-trained stability weights
│   ├── analyze_file.py       # Single-file analysis utility
│   ├── create_recipe.py      # Context recipe builder
│   └── get_stats.py          # Statistics extractor
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

## 📦 Supported Project Types

BBC works with any codebase — it uses language-agnostic AST analysis:

`Python` · `JavaScript` · `TypeScript` · `Java` · `C/C++` · `Go` · `Rust` · `PHP` · `Ruby` · `C#` · `Swift` · `Kotlin` · `and more...`

---

## 📂 Where Does BBC Install?

BBC installs **once** on your system:

```
%APPDATA%\BBC\BBC_MASTER_BBCMath\   ← BBC engine (installed automatically via bbc.bat)
```

For each project, only a small `.bbc/` folder is created in your project root:

```
YourProject\
  .bbc\
    bbc_context.json    ← Sealed context (AI's single source of truth)
    bbc_rules.md        ← Coding rules injected into AI
    BBC_INSTRUCTIONS.md ← Instruction manifest for AI assistants
    indices\            ← Vector indices for similarity search
    cache\              ← Project snapshot cache
    logs\               ← Daemon and session logs
```

> All `.bbc/` contents are automatically added to `.gitignore` — they never pollute your repository.

---

## 🌐 REST API & MCP Server

BBC can run as an HTTP server, exposing its context engine via REST API and **MCP (Model Context Protocol)**.

### Start the API Server

```bash
# Default port 3333
python bbc.py serve

# Custom port
python bbc.py serve --port 8080

# With project path
BBC_PROJECT_ROOT=/path/to/project python -m uvicorn bbc_core.http_server:app --port 3333
```

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health + memory usage |
| `GET` | `/api/project_context` | Full sealed BBC context (JSON) |
| `GET` | `/api/symbol_analysis` | Symbol graph + critical symbols |
| `GET` | `/api/stats` | Token savings, stability stats |
| `POST` | `/api/analyze` | Analyze a single file |
| `POST` | `/mcp` | MCP gateway for AI tools |

### Example: Health Check

```bash
curl http://localhost:3333/health
```
```json
{
  "status": "healthy",
  "version": "8.3.0",
  "adapter_ready": true,
  "memory_mb": 51.11,
  "uptime_seconds": 16.4
}
```

### MCP Integration (Claude Desktop, Cursor, etc.)

BBC's `/mcp` endpoint implements the **Model Context Protocol**, allowing AI tools to query BBC directly.

```bash
# List available tools
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{"type": "list_tools"}'
```

**Available MCP tools:**
- `analyze_project` — Full project analysis
- `get_stats` — System statistics  
- `symbol_radius` — Calculate impact radius of a symbol

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "bbc": {
      "url": "http://localhost:3333/mcp"
    }
  }
}
```

> **Interactive Docs:** Once running, visit `http://localhost:3333/docs` for the full Swagger UI.

---

## 🔧 Troubleshooting

**BBC not starting?**
```bash
bbc status              # Check daemon state
python bbc.py verify .  # Run structural check
python bbc.py start -f .  # Force full refresh
```

**AI assistant ignoring BBC?**
```bash
python bbc.py audit .   # Check which files were injected
python bbc.py start -f .  # Re-run IDE detection and injection
# Then restart your IDE
```

**View logs:**
```bash
# Windows
type .bbc\logs\daemon.log

# Linux / macOS
cat .bbc/logs/daemon.log
```

---

## 📐 Architecture

BBC's core is the **HMPU (Hybrid Mathematical Processing Unit)**, which provides mathematically grounded confidence scores rather than arbitrary percentages:

$$\kappa(A) = \|A\| \cdot \|A^{-1}\|$$

$$C = \frac{1}{1 + \log_{10}(\kappa)}$$

| Condition Number | Status | AI Confidence |
|---|---|---|
| κ ≈ 1.0 | 💎 STABLE | ~90%+ |
| κ = 2.38 | 💎 STABLE | ~73% |
| κ > 20.0 | ⚠️ WEAK | <50% |

For the full technical reference: [`BBC_TECHNICAL_REFERENCE_EN.md`](BBC_TECHNICAL_REFERENCE_EN.md)

For the architecture manifest: [`BBC_MASTER_MANIFEST.md`](BBC_MASTER_MANIFEST.md)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**BBC v8.3 STABLE** — Your AI assistants now see your project with mathematical certainty.

*No hallucinations. No guesswork. Only verified context.*

</div>
