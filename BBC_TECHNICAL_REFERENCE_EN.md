# BBC (Bitter Brain Context) v8.3 — Technical Reference Manual

**Version:** v8.3 (STABLE)  
**Architecture:** HMPU Matrix-Driven Context Engine  
**Core Philosophy:** "Zero-Hallucination via Mathematical Certainty"

---

## 1. 🏗️ Architecture Overview

BBC is not just a code scanner; it is a **Hybrid Mathematical Processing Unit (HMPU)** designed to "seal" software projects into a deterministic context for AI agents. It replaces probabilistic guessing with algebraic certainty.

### The "Aura Field" (Core Geometry)
At the heart of BBC lies a 3x3 matrix called the **Aura Field**. This matrix represents the stability of the project's logic.
- **S (Structural Anchor):** The rigidity of classes/functions.
- **C (Chaos Density):** The entropy/complexity of the code.
- **P (Pulse Alpha):** The signal strength of the dependency graph.

The system continuously calculates the **Condition Number (κ)** of this matrix.
- **κ ≈ 1.0:** Perfect geometric balance.
- **κ > 20.0:** Mathematical instability (high risk of AI hallucination).

---

## 2. 📂 File Anatomy & Mathematical Functions

Each file in `bbc_core` serves a specific mathematical or operational purpose.

### 🧠 The Mathematical Brain
| File | Role | Mathematical Logic |
| :--- | :--- | :--- |
| **`hmpu_core.py`** | **The Governor** | Manages the Aura Field matrix. Implements the **`self_heal_protocol`** which triggers the **Ω (Omega) Operator** when a scalar value enters a `DEGENERATE` state. It calculates the final **Confidence Score** using logarithmic mapping of the matrix condition number. |
| **`matrix_ops.py`** | **Linear Algebra** | Implements raw matrix operations: `matmul`, `gauss_jordan_inverse`, and `condition_number` calculation (Infinity Norm). This is the engine that proves whether the context is "stable" or "weak". |
| **`bbc_scalar.py`** | **Bitter Math** | Defines the `BBCScalar` class. Unlike standard floats, these scalars have **States** (`STABLE`, `WEAK`, `UNSTABLE`, `DEGENERATE`). Arithmetic operations (+, -, *, /) propagate these states, allowing the system to track "logic corruption" like a virus. |

### 🔍 The Scanner & Optimizer
| File | Role | Logic |
| :--- | :--- | :--- |
| **`native_adapter.py`** | **Orchestrator** | Coordinates the analysis. It runs the `SymbolExtractor` (AST) and then feeds the data into the HMPU Engine to calculate the compression ratio and stability score. |
| **`context_optimizer.py`** | **Blast Radius** | Uses graph theory to calculate the "Impact Zone" of a symbol. If you change function `A`, it finds `B` and `C` that depend on `A` using a directed acyclic graph (DAG) traversal. |
| **`symbol_extractor.py`** | **Deep Scan** | Uses Abstract Syntax Trees (AST) for Python and Regex for other languages to extract a "Skeleton" of the code (Class names, Function signatures) without the implementation noise. |

### 🛡️ Security & Integrity
| File | Role | Logic |
| :--- | :--- | :--- |
| **`agent_adapter.py`** | **Injector** | Maps the BBC Sealed Context into specific formats for 24+ IDEs (Cursor, VS Code, etc.). It implements the **"No-Trace Shield"** which automatically updates `.gitignore` to keep the repo clean. |
| **`verifier.py`** | **Health Check** | Performs static analysis to verify "Structural Integrity". It checks for syntax errors, circular dependencies, and orphan symbols before any AI interaction begins. |
| **`ide_hooks.py`** | **The Watcher** | Implements the **"Re-Sealing"** mechanism. It monitors file hashes in real-time. If a file changes (hash mismatch), it triggers an immediate re-analysis to prevent "Stale Context". |

---

## 3. 🚀 Key Features Deep Dive

### 3.1. Mathematical Stability & Confidence
BBC does not use arbitrary confidence scores.
- **Stability ($\kappa$):** Calculated via `MatrixOps.condition_number(Aura_Matrix)`.
  $$ \kappa(A) = \|A\| \cdot \|A^{-1}\| $$
- **Confidence ($C$):** Mapped from stability.
  $$ C = \frac{1}{1 + \log_{10}(\kappa)} $$
  *Example:* If $\kappa = 2.38$, then $C \approx 73\%$. This is the "Honest Confidence" of the system.

### 3.2. Aura Gradient Bend ($\nabla A$)
When the system detects instability ($\kappa > 5.0$), it performs an "Accord Tuning":
1. It calculates the gradient of the error.
2. It "bends" the diagonal weights of the Aura Matrix (`A[i][i]`) by a small `delta`.
3. This realigns the geometric planes of Logic (S), Chaos (C), and Pulse (P), minimizing mathematical noise.

### 3.3. Re-Sealing (The Mühürleme Logic)
To prevent AI hallucinations based on old code:
1. **Detection:** `ide_hooks.py` watches file system events.
2. **Verification:** `cli.py` compares the current file hash with the stored "Sealed Hash".
3. **Action:** If they differ, the system invalidates the old `bbc_context.json` and triggers a **Re-Seal**. This ensures the AI *always* sees the absolute latest truth.

### 3.4. Ghost-Killer Pipeline
The `bbc.bat` start command is now a full pipeline:
1. **Verify:** Runs `verifier.py` (Is the code broken?).
2. **Analyze:** Runs `native_adapter.py` (Extract symbols + Math check).
3. **Inject:** Runs `agent_adapter.py` (Force "Adaptive Mode" rules into AI).
   *Result:* All "sleeping" features are forced to run every time.

---

## 4. 📉 Context Reduction Reality
How does BBC reduce context size for AI workflows?

- **Boilerplate Removal:** It strips implementation details, keeping only signatures.
- **Dependency Pruning:** It only includes relevant imports in the context.
- **Compression:** High-density JSON structure reduces whitespace overhead.

Result: large projects are reduced into compact, structure-focused context artifacts.
These reduction metrics remain internal (`.bbc/bbc_context.json`) and are no longer presented as terminal token-savings banners or as a telemetry dashboard command.

---

*This document serves as the definitive technical reference for BBC v8.3.*
