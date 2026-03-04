# BBC Quick Start Guide

## 🎯 Get BBC Working in 5 Minutes

### Step 1: Install BBC

#### Option A: Installer (Recommended)
```bash
# Windows
python bbc_installer.py install C:\path\to\your\project

# Linux/macOS
python3 bbc_installer.py install /path/to/your/project
```

#### Option B: pip Install (Development)
```bash
cd BBC_MASTER_BBCMath
pip install -e .
```

#### Option C: Direct Run (No Install)
```bash
# Windows
python bbc.py start C:\path\to\your\project

# Linux/macOS
python3 bbc.py start /path/to/your/project
```

### Step 2: Use BBC on Your Project

```bash
cd /path/to/your/project
bbc start
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

Universal files (always created):
- `.agent/rules/bbc_rules.md`
- `.context/bbc_context.md`
- `BBC_INSTRUCTIONS.md`

## 🛠️ All Commands

```bash
bbc start [path]       # Full pipeline: Verify + Analyze + Inject
bbc start -b [path]    # Run in background (daemon mode)
bbc start -f [path]    # Force refresh
bbc analyze [path]     # Deep project scan only
bbc verify [path]      # Check structural integrity
bbc menu [path]        # Interactive BBC menu
bbc serve --port 3333  # Start REST API server
bbc audit [path]       # Audit BBC traces
bbc purge [--force]    # Complete BBC removal
bbc stop               # Stop BBC daemon
bbc status             # Show system status
```

## 📚 Need More Help?

- `USER_GUIDE.md` → Complete documentation
- `README.md` → Overview

---

**Happy coding with BBC! 🎉**
