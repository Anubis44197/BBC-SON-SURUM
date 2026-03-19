# BBC User Guide v8.3

## 📚 Table of Contents

1. [Installation](#installation)
2. [First Steps](#first-steps)
3. [Commands Reference](#commands-reference)
4. [IDE Integration](#ide-integration)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

## 🚀 Installation

### Method 1: Clean Model (Recommended)
```bash
git clone https://github.com/Anubis44197/BBC-SON-SURUM.git <BBC_HOME>
pip install -r <BBC_HOME>/requirements.txt
python <BBC_HOME>/bbc.py start /path/to/your/project
```

### Method 2: pip Install (Development)
```bash
git clone https://github.com/Anubis44197/BBC-SON-SURUM.git
cd BBC
pip install -e .
python bbc.py start /path/to/your/project
```

### Method 3: Legacy Embedded (Backward Compatibility)
```bash
cd /path/to/your/project
git clone https://github.com/Anubis44197/BBC-SON-SURUM.git
python BBC/bbc.py start .
```

## 🎯 First Steps

### Start Using BBC
```bash
# From the BBC directory, point to your project
python bbc.py start /path/to/your/project

# Or use current directory
python bbc.py start .
```

### What Happens When You Start BBC
1. **Verify** - Checks existing BBC context integrity
2. **Analyze** - Scans your entire codebase (classes, functions, imports, dependencies)
3. **Inject** - Creates IDE-specific config files for all detected AI assistants
4. **Seal** - Marks context as VERIFIED (sealing)

## 🛠️ Commands Reference

### Main Commands (bbc.py)
| Command | Description |
|---------|-------------|
| `python bbc.py start [path]` | Full pipeline: Verify + Analyze + Inject |
| `python bbc.py start -b [path]` | Run in background (daemon mode) |
| `python bbc.py start -f [path]` | Force refresh (re-analyze everything) |
| `python bbc.py analyze [path]` | Deep project scan only |
| `python bbc.py verify [path]` | Check structural integrity |
| `python bbc.py menu [path]` | Interactive BBC menu |
| `python bbc.py serve --port 3333` | Start REST API server |
| `python bbc.py audit [path]` | Audit BBC traces in project |
| `python bbc.py purge [path]` | Complete BBC removal |
| `python bbc.py uninstall [path]` | One-command uninstall (project cleanup + optional global remove) |
| `python bbc.py migrate-clean [path]` | Migrate legacy in-project BBC folder to clean model |
| `python bbc.py stop [path]` | Stop BBC daemon |
| `python bbc.py status [path]` | Show system status |

Uninstall examples:
```bash
# Preview only
python bbc.py uninstall . --dry-run

# Remove BBC traces from project
python bbc.py uninstall . --force

# Also try global package uninstall
python bbc.py uninstall . --force --global

# Migrate old in-project BBC folder to clean model
python bbc.py migrate-clean .                # preview (dry-run)
python bbc.py migrate-clean . --apply --force
```

### Engine Commands (run_bbc.py)
| Command | Description |
|---------|-------------|
| `python run_bbc.py analyze [path]` | Analyze project |
| `python run_bbc.py inject [path]` | Inject IDE configs |
| `python run_bbc.py bootstrap [path] --yes` | Analyze + Inject in one step |
| `python run_bbc.py verify [recipe]` | Verify context file |
| `python run_bbc.py audit [path]` | Audit BBC traces |
| `python run_bbc.py cleanup [path] --force` | Remove injected files |
| `python run_bbc.py purge [path] --force` | Complete removal |
| `python run_bbc.py adaptive [query]` | Adaptive mode query |

## 🎮 IDE Integration

### How It Works
When BBC runs `inject`, it:
1. Detects installed IDEs using `ide_auto_config.py`
2. Detects installed AI extensions (plugins)
3. Creates config files **only for detected IDEs/extensions**

### Supported IDEs
| IDE | Detection | Config File |
|-----|-----------|-------------|
| VS Code | Binary path check | `.github/copilot-instructions.md` |
| Cursor | Binary path check | `.cursorrules` |
| Windsurf | Binary path check | `.windsurf/bbc_rules.md` |
| JetBrains (PyCharm, IntelliJ, etc.) | `.idea/` folder | `.idea/bbc-ai-assistant.xml` |
| Zed | Binary path check | `.zed/settings.json` |
| Replit | `.replit/` folder | `.replit/ai.json` |

### Supported AI Extensions
| Extension | Config File |
|-----------|-------------|
| GitHub Copilot | `.github/copilot-instructions.md` |
| Continue | `.continue/config.json` |
| Codiumai / Qodo | `.codiumai/config.json` |
| Codeium | `.codeium/config.json` |
| Tabnine | `.tabnine/config.json` |
| Amazon Q | `.amazonq/config.json` |
| Cline / Kilo Code | `.clinerules` |
| Roo Code | `.roo-code/config.json` |
| DeepSeek Coder | `.deepseek/config.json` |

### Universal Files (Always Created)
These are created regardless of IDE detection, all inside the `.bbc/` directory:
- `.bbc/bbc_context.md` — Human-readable context summary
- `.bbc/bbc_rules.md` — Project coding rules injected into AI
- `.bbc/BBC_INSTRUCTIONS.md` — Universal AI instruction manifest
- `.gitignore` — Updated with BBC patterns

## 🔒 Sealing (Mühürleme)

BBC seals the context with `constraint_status: "verified"`. This means:
- AI assistants can only use symbols from `bbc_context.json`
- Unknown symbols trigger warnings
- Code blocks marked as sealed cannot be modified

## 📊 Analysis Output

After each analysis, BBC prints concise status output (files, symbols, seal state, and context path).
Detailed metrics remain in `.bbc/bbc_context.json`.

## 🔧 Advanced Usage

### Background Mode (Daemon)
```bash
python bbc.py start -b .
# BBC runs in background, monitoring file changes
python bbc.py stop .  # Stop the daemon
```

### REST API Server
```bash
python bbc.py serve --port 3333
# API available at http://127.0.0.1:3333
# Endpoints:
#   GET  /health               → Server health + memory
#   GET  /api/project_context  → Full sealed BBC context
#   GET  /api/symbol_analysis  → Symbol graph + critical symbols
#   GET  /api/stats            → Runtime and stability stats
#   POST /api/analyze          → Analyze a single file
```

### Isolated vs Embedded Installation
- **Isolated (default):** BBC stays in its own folder, runs remotely
- **Embedded:** `BBC_INSTALL_EMBED_CORE=1 python bbc_installer.py install /path` copies BBC into project

## 🔥 Troubleshooting

### "AI assistants not using BBC"
1. Run `python bbc.py start -f .` (force refresh)
2. Restart your IDE
3. Check `.bbc/manifest/injected_files.json` for created files

### "Analysis failed"
1. Check file permissions
2. Check for syntax errors in code
3. Check logs: `.bbc/logs/`

### "BBC not found"
1. Make sure Python 3.8+ is installed
2. Make sure you're in the BBC folder or BBC is installed via pip

### Log Files
BBC logs are stored in `.bbc/logs/` inside the target project:
- `telemetry.jsonl` — Event log
- `installation_record.json` — Install info

---

**BBC v8.3** - Making AI assistants understand your code perfectly.
