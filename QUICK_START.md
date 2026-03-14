# BBC Quick Start Guide

## 🎯 Get BBC Working in 5 Minutes

### Step 1: Clone BBC into Your Project

```bash
cd your-project
git clone https://github.com/Anubis44197/BBC.git
```

### Step 2: One-Command Setup

```bash
# Windows (automatic)
BBC\setup.bat

# Linux/macOS (automatic)
bash BBC/setup.sh

# Or use the install command
python BBC/bbc.py install .
```

All three options do the same thing: install dependencies + analyze + inject + start daemon.

### Alternative: Manual Setup

```bash
pip install -r BBC/requirements.txt
python BBC/bbc.py start .
```

**BBC will:**
- Analyze your entire codebase
- Detect which IDEs and AI extensions you use
- Automatically configure everything

### Step 3: Start Coding!

Open your favorite IDE (VS Code, PyCharm, etc.) and start coding with AI assistants.

**Your AI assistants will now:**
- ✅ Only suggest code that actually exists in your project
- ✅ Never hallucinate functions or classes
- ✅ Use correct imports and dependencies
- ✅ Follow your project's patterns

## 🎮 What You'll See

When you run `bbc start`, you'll see something like:

```
======================================================================
>>> BBC ANALYSIS COMPLETE
======================================================================
[INFO] 83 Classes | 465 Functions | 398 Imports
[INFO] Normal:178,414 -> BBC:14,313 | Saved:92.0%
======================================================================
```

And a token savings report:
```
╭──────────────────────────────────╮
│  BBC HMPU v8.3 Aura Insights 💎  │
│  STABLE                          │
│  ██████████████████████████████  │
│  ███████████████░░░░░ 90.4%      │
│  Saved: 125,601 Tokens | $3.77   │
│  | 10.4x Faster                  │
╰──────────────────────────────────╯
```

## 🔧 IDE Auto-Detection

BBC automatically detects and configures:

| IDE/Extension | Config File |
|--------------|-------------|
| VS Code / Copilot | `.github/copilot-instructions.md` |
| Cursor | `.cursorrules` |
| Windsurf | `.windsurf/bbc_rules.md` |
| JetBrains | `.idea/bbc-ai-assistant.xml` |
| Continue | `.continue/config.json` |
| Codiumai | `.codiumai/config.json` |
| Zed | `.zed/settings.json` |
| Cline/Kilo | `.clinerules` |

**Only installed IDEs get configured** — BBC detects what's on your system.

Universal files (always created inside `.bbc/`):
- `.bbc/bbc_context.md` — Human-readable context summary
- `.bbc/bbc_rules.md` — AI coding rules
- `.bbc/BBC_INSTRUCTIONS.md` — Universal AI instruction manifest

## 🛠️ All Commands

```bash
python bbc.py install [path]     # One-command: deps + analyze + inject + start
python bbc.py start [path]       # Full pipeline: Verify + Analyze + Inject
python bbc.py start -b [path]    # Run in background (daemon mode)
python bbc.py start -f [path]    # Force refresh
python bbc.py analyze [path]     # Deep project scan only
python bbc.py verify [path]      # Check structural integrity
python bbc.py menu [path]        # Interactive BBC menu
python bbc.py serve --port 3333  # Start REST API server
python bbc.py audit [path]       # Audit BBC traces
python bbc.py purge [path]       # Complete BBC removal
python bbc.py stop [path]        # Stop BBC daemon
python bbc.py status [path]      # Show system status
```

## 📚 Need More Help?

- `USER_GUIDE.md` → Complete documentation
- `README.md` → Overview

---

**Happy coding with BBC! 🎉**
