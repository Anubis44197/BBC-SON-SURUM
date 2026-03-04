# BBC — Bitter Brain Context v8.3

> **The smart context engine that makes AI assistants understand your project with zero hallucinations.**

---

## What is BBC?

BBC (Bitter Brain Context) prevents AI coding tools (GitHub Copilot, Cursor, Continue, etc.) from suggesting functions or classes that do **not exist** in your project.

**The Problem:** AI assistants hallucinate in large projects — they write code that doesn't actually exist.  
**The Solution:** BBC analyzes your project, extracts the real code structure, and tells the AI "only these exist."

```
Without BBC  →  139,000 tokens  →  Slow, expensive, hallucinations
With BBC     →   14,000 tokens  →  90% faster, zero hallucinations
```

---

## Installation — One Step

### Requirements
- [Python 3.8+](https://python.org/downloads/)
- [Git](https://git-scm.com/downloads)

### How to Use

1. **Download `bbc.bat`**
2. **Copy it into your project folder**
3. **Double-click it**

On first run, BBC installs itself automatically. All subsequent runs start instantly.

```
Double-click bbc.bat
       ↓
BBC installs itself (first time only, ~30 seconds)
       ↓
Your project is analyzed
       ↓
Your AI assistants now fully understand your codebase
```

---

## Commands

You can also run `bbc.bat` from the **Command Prompt (CMD)**:

| Command | Description |
|---|---|
| `bbc.bat` | Connects current folder to BBC |
| `bbc.bat start C:\MyProject` | Connects a specific project |
| `bbc.bat status` | Shows BBC system status |
| `bbc.bat stop` | Stops BBC |
| `bbc.bat update` | Updates BBC to the latest version |
| `bbc.bat bootstrap C:\MyProject` | Full analysis + AI injection |

---

## What Does BBC Do?

When BBC runs, it automatically performs these steps:

**1. Project Scan**
```
[*] 61 files scanned
[*] 1,621 symbols | 3,952 calls | 20 critical
```

**2. Context Compression (HMPU v8.3)**
```
Source: 139,084 tokens  →  BBC Context: 13,964 tokens
Token Savings: 90%  |  10x Faster
```

**3. Automatic Injection into AI Tools**
```
[OK] VS Code / GitHub Copilot → .github/copilot-instructions.md
[OK] Cursor                   → .cursorrules
[OK] Continue                 → .continue/config.json
```

**4. Stability Report**
```
╭──────────────────────────────────────────╮
│  BBC HMPU v8.3  Aura Insights 💎 STABLE  │
│  ███████████████████████████░░░  90.0%   │
│  Saved: 125,120 Tokens | $3.75           │
│  Stability: STABLE | Confidence: 90%+    │
╰──────────────────────────────────────────╯
```

---

## Supported AI Tools

BBC auto-detects and configures all major AI coding tools:

| Tool | Status |
|---|---|
| GitHub Copilot (VS Code) | ✅ Full Support |
| Cursor | ✅ Full Support |
| Continue | ✅ Full Support |
| Windsurf | ✅ Full Support |
| JetBrains AI | ✅ Full Support |

---

## Supported Project Types

BBC works with any codebase:

`Python` · `JavaScript` · `TypeScript` · `Java` · `C/C++` · `Go` · `Rust` · `PHP` · `Ruby` · `and more...`

---

## Where Does BBC Install?

BBC installs **once** on your system:

```
%APPDATA%\BBC\BBC_MASTER_BBCMath\   ← BBC engine (automatic)
```

For each project, only a small `.bbc/` folder is created:

```
YourProject\
  .bbc\
    bbc_context.json    ← Sealed context (AI reads this)
    bbc_rules.md        ← AI rules
    BBC_INSTRUCTIONS.md ← Copilot instructions
```

---

## Troubleshooting

**Python not found:**
→ Download Python 3.8+ from [python.org](https://python.org/downloads/). During installation, check **"Add Python to PATH"**.

**Git not found:**
→ Download Git from [git-scm.com](https://git-scm.com/downloads).

**I want to update BBC:**
→ Run `bbc.bat update`.

**AI still giving wrong suggestions:**
→ Run `bbc.bat start` again to re-analyze your project.

---

## License

MIT License — Free to use.
