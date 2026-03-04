# BBC — Bitter Brain Context v8.3

> **The smart context engine that makes AI assistants understand your project with zero hallucinations.**

---

## What is BBC?

**BBC (Bitter Brain Context)** is a developer tool that prevents AI coding assistants (GitHub Copilot, Cursor, Continue, etc.) from **hallucinating** — generating code that references functions, classes, or variables that don't actually exist in your project.

**The Problem:** AI assistants don't know your codebase. In large projects they invent function names, call non-existent APIs, and write code that simply doesn't work.

**The Solution:** BBC scans your entire project, extracts the real structure (every class, function, import), compresses it into a mathematically sealed context, and injects that context directly into your active AI tool. The AI can then only suggest code that actually exists.

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
| `bbc.bat` | Start BBC on the current folder |
| `bbc.bat start C:\MyProject` | Connect a specific project to BBC |
| `bbc.bat status` | Show BBC system status |
| `bbc.bat stop` | Stop the BBC daemon |
| `bbc.bat update` | Update BBC to the latest version |
| `bbc.bat bootstrap C:\MyProject` | Full analysis + AI injection (recommended first run) |
| `bbc.bat analyze C:\MyProject` | Deep project analysis only (no daemon) |
| `bbc.bat verify C:\MyProject` | Run structural integrity check on sealed context |
| `bbc.bat audit C:\MyProject` | Audit which files BBC has injected |
| `bbc.bat install C:\MyProject` | Install BBC engine into a target project |
| `bbc.bat serve` | Start REST API + MCP server on port 3333 |
| `bbc.bat purge C:\MyProject` | Remove all BBC files from a project |

---

## What Does BBC Do?

When BBC runs, it automatically performs these steps:

**1. Project Scan**

BBC performs deep AST (Abstract Syntax Tree) analysis on every source file in your project — it extracts every class, function, method, import, and inter-symbol call.

```
[*] 61 files scanned
[*] 1,621 symbols | 3,952 calls | 20 critical
```

**2. Context Compression (HMPU v8.3)**

BBC's mathematical engine (HMPU — Hybrid Mathematical Processing Unit) compresses your project's entire structure into a minimal, semantically complete context. This is not summarization — it is mathematically lossless compression of your code graph.

```
Source: 139,084 tokens  →  BBC Context: 13,964 tokens
Token Savings: 90%  |  10x Faster  |  ~$3.75 saved per session
```

**3. Smart IDE Detection — Writes Only Where Needed**

BBC detects which IDE you are actively using and which AI extensions are installed. It then writes the sealed context **only** to those tools — it never creates config folders for tools you don't have.

```
[OK] VS Code / GitHub Copilot → .github/copilot-instructions.md
[OK] Cursor                   → .cursorrules
[OK] Continue                 → .continue/config.json
```

> **Ghost Injection Prevention:** Old tools used to blindly create 20+ config folders (`.codiumai/`, `.replit/`, `.tabnine/`, `.pieces/`...) even if you never installed those tools. BBC v8.3 eliminates this entirely. At most 1–3 files are written, only to tools you actually have.

**4. Stability Report**

BBC calculates a mathematical confidence score for your project using linear algebra (condition number of the symbol matrix). This is not a made-up percentage — it is a real stability measurement.

```
╭──────────────────────────────────────────╮
│  BBC HMPU v8.3  Aura Insights 💎 STABLE  │
│  ███████████████████████████░░░  90.0%   │
│  Saved: 125,120 Tokens | $3.75           │
│  Stability: STABLE | Confidence: 90%+    │
╰──────────────────────────────────────────╯
```

| Stability Status | Meaning |
|---|---|
| 💎 STABLE | AI can work with high confidence. Context is clean and complete. |
| ⚠️ WEAK | High risk of hallucination. Consider refactoring complex areas. |
| ❌ DEGENERATE | Context is unusable. Run `bbc.bat verify` to diagnose. |

**5. Real-Time Daemon**

BBC runs a background watcher (`bbc_daemon`). If you edit your code after an AI session, the daemon automatically re-analyzes the changed files and re-seals the context. Your AI always sees the current state of your project — never stale data.

---

## Adaptive Mode (STRICT / RELAXED)

BBC operates in two intelligent modes depending on how well your project's context matches the current question:

| Mode | When It Activates | Behavior |
|---|---|---|
| **STRICT** | Context match ≥ 80% | The AI is locked to verified symbols only. Every suggestion comes from `.bbc/bbc_context.json`. Zero hallucination tolerance. |
| **RELAXED** | Context match < 80% | The AI may use broader knowledge, but BBC emits a warning: `"Symbol not in sealed context"`. |

If a function or class does not exist in your codebase, BBC returns:
```
"Information not found in sealed context"
```

This ensures AI tools never invent APIs that don't exist.

---

## Built-In Verifier

BBC includes a structural integrity verifier that runs automatically at the end of every analysis:

- Checks syntax correctness of all extracted symbols
- Validates the completeness of the call graph
- Detects orphaned or unreachable symbols
- Reports logical issues before they reach your AI

```
[OK] BBC Verifier: Project structural integrity confirmed.
```

You can also run it manually:
```
bbc.bat verify C:\MyProject
```

---

## Supported AI Tools

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

---

## Supported Project Types

BBC works with any codebase — it uses language-agnostic AST analysis:

`Python` · `JavaScript` · `TypeScript` · `Java` · `C/C++` · `Go` · `Rust` · `PHP` · `Ruby` · `C#` · `Swift` · `Kotlin` · `and more...`

---

## REST API & MCP Server

BBC can run as an HTTP server, exposing its context engine to external tools via REST API and the **MCP (Model Context Protocol)**.

Start the server:
```
bbc.bat serve
```
Default port: **3333**

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health and memory usage |
| `GET` | `/api/project_context` | Full sealed BBC context (JSON) |
| `GET` | `/api/symbol_analysis` | Symbol graph + critical symbols |
| `GET` | `/api/stats` | Token savings, stability stats |
| `POST` | `/api/analyze` | Analyze a single file |
| `POST` | `/mcp` | MCP gateway for AI tools |

### MCP Integration (Claude Desktop, Cursor, etc.)

BBC's `/mcp` endpoint implements the **Model Context Protocol**, allowing AI tools to query BBC directly.

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

> Once running, visit `http://localhost:3333/docs` for the full interactive API documentation.

---

## Where Does BBC Install?

BBC installs **once** on your system:

```
%APPDATA%\BBC\BBC_MASTER_BBCMath\   ← BBC engine (installed automatically)
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

All `.bbc/` contents are automatically added to `.gitignore` — they never pollute your repository.

---

## Troubleshooting

**Python not found:**
→ Download Python 3.8+ from [python.org](https://python.org/downloads/). During installation, check **"Add Python to PATH"**.

**Git not found:**
→ Download Git from [git-scm.com](https://git-scm.com/downloads).

**I want to update BBC:**
→ Run `bbc.bat update`.

**AI still giving wrong suggestions after BBC ran:**
→ Run `bbc.bat start` again to re-analyze and re-inject.
→ Then **restart your IDE** so it picks up the new context files.

**BBC reports WEAK or DEGENERATE stability:**
→ Run `bbc.bat verify C:\MyProject` for a detailed report.
→ This usually means there are circular imports or orphaned symbols in your codebase.

**Want to remove BBC from a project completely:**
→ Run `bbc.bat purge C:\MyProject` — removes all `.bbc/` files and IDE config files BBC created.

---

## License

MIT License — Free to use.

---

<div align="center">

**BBC v8.3 STABLE** — Your AI assistants now see your project with mathematical certainty.

*No hallucinations. No guesswork. Only verified context.*

[Source Repository](https://github.com/Anubis44197/BBC_MASTER_BBCMath) · [Report an Issue](https://github.com/Anubis44197/BBC_MASTER_BBCMath/issues)

</div>
