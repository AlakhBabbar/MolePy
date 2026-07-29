# molepy

An autonomous CLI software engineering agent designed to explore, plan, execute, and verify code modifications across arbitrary codebases.

---

## Overview

**molepy** is a language-agnostic and framework-agnostic AI developer tool. It accepts high-level product requests, navigates an unknown repository structure, forms an execution plan, performs targeted file edits, and verifies the resulting changes — all through an automated Reasoning + Acting (ReAct) loop.

---

## System Architecture

The project is structured into distinct, modular components within the `src/molepy/` package:

```
alakhbabbar-molepy/
├── pyproject.toml
├── README.md
└── src/
    └── molepy/
        ├── __init__.py
        ├── cli.py          # Command Line Interface entry point
        ├── agent.py        # Core ReAct loop and memory state engine
        ├── llm.py          # Provider client, API handling, and reasoning sanitization
        ├── tools.py        # Native filesystem, shell execution, and syntax verification tools
        ├── schemas.py      # OpenAPI-style function definitions for the LLM
        ├── prompts.py      # Prompt loader module
        └── prompts/
            └── system_prompt.md  # Detailed agent system prompt and guardrail rules
```

### Component Responsibilities

- **CLI Module (`cli.py`)** — Configures the command-line interface using `typer`, handles CLI parameters, validates local path targets, and enforces API key checks prior to execution.
- **Agent Engine (`agent.py`)** — Manages the iterative execution loop, history pruning, long-term working memory, system context injections, guardrail enforcement, and tool dispatching.
- **LLM Interface (`llm.py`)** — Interacts with OpenAI-compatible APIs (such as DashScope, SiliconFlow, DeepSeek, or Groq), strips reasoning tags (e.g., `<think>`), and manages model-specific parameter fallbacks.
- **Tool Set (`tools.py`)** — Implements concrete file-system traversal, targeted line reading, regex searches, code insertions, line edits, shell command execution, and automated syntax validation.
- **Tool Schemas (`schemas.py`)** — Defines JSON parameter expectations for LLM function calls.
- **Prompt System (`prompts.py` & `system_prompt.md`)** — Configures behavioral rules, phase transitions, and non-negotiable guardrails.

---

## Agent Workflow & Complete Execution Loop

The agent follows a strict four-phase methodology mandated by its system configuration:

```
                          USER REQUEST
                               │
                               ▼
        ┌───────────────────────────────────────────────┐
        │              PHASE 1: EXPLORE                  │
        │  - Call get_repo_tree() to inspect structure   │
        │  - Call search_codebase() & read_file() to     │
        │    map dependencies                            │
        └───────────────────────────────────────────────┘
                               │
                               ▼
        ┌───────────────────────────────────────────────┐
        │               PHASE 2: PLAN                    │
        │  - Output a single, complete master plan       │
        │    in plain text                                │
        │  - Map full-stack modifications prior to        │
        │    file edits                                   │
        └───────────────────────────────────────────────┘
                               │
                               ▼
        ┌───────────────────────────────────────────────┐
        │              PHASE 3: EXECUTE                  │
        │  - Read-Before-Write check                      │
        │  - Perform targeted edits via insert_code() /   │
        │    edit_file_lines()                            │
        │  - Auto-check syntax (revert if broken)         │
        │  - Record memory notes via update_scratchpad()  │
        └───────────────────────────────────────────────┘
                               │
                               ▼
        ┌───────────────────────────────────────────────┐
        │               PHASE 4: VERIFY                  │
        │  - Execute git diff / test suites via           │
        │    run_shell_command()                          │
        │  - Return final concise summary to user         │
        └───────────────────────────────────────────────┘
```

### Detailed Iteration Loop

For each turn (up to a maximum limit of 25 iterations by default):

1. **Context Pruning** — Old tool execution logs in the conversation history are truncated via `prune_history()` to preserve the LLM's active context window.
2. **Memory Injections** — A dynamic system message containing the active list of inspected files (`read_files_registry`) and persistent notes (`agent_scratchpad`) is appended to the message array.
3. **LLM Query** — The context is sent to the configured LLM API.
4. **Reasoning Sanitization** — Responses containing internal reasoning tags (such as `<think>...</think>`) are cleaned using regular expressions in `clean_reasoning_tags()`.
5. **Tool Execution & Guardrails**:
   - If `update_scratchpad` is called, notes are stored directly in the local run state.
   - If `edit_file_lines` or `insert_code` is requested without prior invocation of `read_file` on that target file path, the edit is intercepted and rejected with an error message.
   - If code edits fail post-write syntax checking, the file is automatically reverted to its pre-edit state and an error is returned to the model.
6. **Completion** — The loop finishes when the model produces a final text output without any tool calls.

---

## Codebase Exploration & Memory Strategy

### Exploration Strategy

- **Hierarchical Navigation** — The agent begins every task by generating a markdown tree representation of the codebase using `get_repo_tree()`, automatically ignoring noise directories like `.git`, `node_modules`, `__pycache__`, `dist`, and `build`.
- **Pattern Tracing** — The agent utilizes `search_codebase()` to grep keywords across all non-ignored files, tracing references between backend routes, schemas, and UI components.
- **Targeted File Inspection** — The `read_file()` tool presents code with explicit 1-indexed line numbers to ensure exact reference points for subsequent modifications.

### Dual-Tier Memory Architecture

- **Short-Term History Pruning** — Raw tool outputs exceeding 800 characters are truncated to 250 characters once they fall outside the immediate conversational tail (keeping the initial 2 messages and last 6 messages intact).
- **Long-Term Working Scratchpad** — To prevent information loss due to history truncation, the agent uses the `update_scratchpad` tool. Notes saved to the scratchpad are persistently anchored in the system instructions on every iteration.

---

## Design Decisions & Technical Guardrails

### 1. Read-Before-Write Mandate
The agent is prohibited from assuming line numbers. The `agent.py` runner enforces a strict guardrail: any edit attempted on an existing file that has not been explicitly registered in `read_files_registry` within the active session is rejected prior to execution.

### 2. Automated Syntax Checking with Auto-Rollback
When code is modified using `insert_code()` or `edit_file_lines()`, `tools.py` immediately runs `check_syntax()` on the modified file:
- **Python (`.py`)** — Validated via Python's built-in `ast.parse()`.
- **JSON (`.json`)** — Validated via `json.loads()`.
- **JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)** — Validated via `node --check`.

If a syntax error occurs, the changes are **automatically reverted** to the previous file state, and the error log is fed back to the LLM to force immediate correction.

### 3. Contextual Chameleon Rule
The agent adopts existing codebase paradigms. It refrains from introducing new framework conventions or external boilerplate unless explicit precedents exist within the repository.

### 4. API Resilience
To accommodate various provider quirks (such as strict schema validations in DashScope or custom endpoints), `llm.py` dynamically handles provider parameters — such as conditionally stripping or falling back on `parallel_tool_calls` when rejected by specific API endpoints.

---

## Assumptions and Trade-offs

- **Local Environment Execution** — The agent executes shell commands and code edits directly on the host machine. Sandboxing relies on repository boundary checks rather than containerized isolation.
- **Node.js Dependency for JS Syntax Checks** — JavaScript/TypeScript syntax validation relies on a globally available `node` executable on the host system. If `node` is absent, syntax checking for JS/TS files falls back gracefully without breaking execution.
- **In-Memory Scratchpad Scope** — The working memory scratchpad exists for the duration of a single execution command (`run_agent`) and is not persisted to disk between separate CLI runs.
- **History Truncation vs. Context Loss** — Truncating tool logs saves token budgets but relies on the LLM explicitly saving critical line numbers to its scratchpad prior to history pruning.

---

## Prerequisites and Setup

### System Requirements

- **Python** — Version 3.11 or higher.
- **Node.js** (optional, recommended) — For JavaScript/TypeScript syntax validation.
- **Git** — Installed and available on your path for verification commands.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alakhbabbar/molepy.git
   cd molepy
   ```

2. **Install the package locally:**
   ```bash
   pip install -e .
   ```

3. **Configure environment variables.**

   Set an API key for your preferred provider (DashScope, OpenAI, DeepSeek, SiliconFlow, or Groq):

   **Linux / macOS:**
   ```bash
   export DASHSCOPE_API_KEY="your_api_key_here"
   # Optional custom endpoint (defaults to DashScope international)
   export LLM_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
   export LLM_MODEL="qwen3.7-plus"
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:DASHSCOPE_API_KEY="your_api_key_here"
   $env:LLM_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
   $env:LLM_MODEL="qwen3.7-plus"
   ```

---

## How to Run

Once installed, execute `molepy` from your command line by passing the target prompt and specifying the target repository path.

### Basic Usage

```bash
molepy "Add a search endpoint for notes and connect it to the frontend UI" --repo /path/to/your/target-repository
```

### Command Line Options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `request` | Argument | *(Required)* | High-level product request or task description. |
| `--repo`, `-r` | Option | Current directory | Path to the target codebase directory. |

### Example Run

```bash
molepy "Improve error logging across all API controllers" -r ./my-express-app
```
