# Context Retrieval MCP Server

An **index-driven** context-retrieval MCP (Model Context Protocol) server that implements **Tier 3** of the codified context infrastructure. It gives AI coding agents on-demand access to project architecture knowledge without loading everything into the prompt — and without any hand-maintained registry.

## What It Does

The server exposes 8 tools via the MCP protocol:

| Tool | Purpose |
|------|---------|
| `list_subsystems()` | Enumerate all architectural subsystems |
| `get_files_for_subsystem(subsystem)` | Get key files and docs for a subsystem |
| `find_relevant_context(task_description)` | Match a task to relevant subsystems and files |
| `get_context_files()` | List all context documents with metadata |
| `search_context_documents(query)` | Full-text search across all context documents |
| `suggest_agent(task_description)` | Recommend which specialized agent to invoke |
| `list_agents()` | Enumerate all agents with descriptions and triggers |
| `get_index_status()` | Debug probe: resolved project root, counts, parse warnings |

Resources: `context://index` (the resolved index as JSON) and `context://{subsystem}` (the full context document).

## The Index: Front-Matter as Single Source of Truth

There is **no SUBSYSTEMS/AGENTS dict to maintain**. The server scans the project's own artifacts at startup and rebuilds automatically whenever they change:

- **`.claude/context/*.md`** — each context doc declares its own metadata:

```yaml
---
subsystem: save-system        # index key; defaults to the filename stem
name: Save System             # defaults to the first H1
description: Two-tier save architecture (disk + memory)
keywords: [save, persistence, autosave]
files:                        # project-root-relative; trailing "/" = directory
  - src/Services/SaveService.py
  - src/Services/Implementation/
priority: high                # drift-warning tier: high | medium | low
related: [item-system]        # other subsystem keys (bidirectional)
version: 2
last-verified: 2026-08-08
---
```

- **`.claude/agents/**/*.md`** — each agent spec declares `name`, `description`, `model`, and an optional `triggers: [...]` list that powers `suggest_agent()` routing.

Writing complete front-matter **is** the registration step. Documents carrying only the legacy `<!-- v1 | last-verified: ... -->` header still index (minimally, with a warning); markdown files with neither are skipped.

Matching uses word-boundary matching for single-word terms (the keyword `ai` does not match "maintain"), substring matching for multi-word phrases, and a uniqueness bonus for terms declared by few entries (see `context_retrieval_mcp/matching.py`).

## Setup

### Prerequisites

- Python 3.10+
- `mcp` package (`pip install mcp`) — SDK v1 and v2 both supported

### Installation

```bash
# From the mcp-server/ directory
pip install -e .
```

### Running

Three launch modes:

```bash
context-retrieval-mcp                       # console script (after pip install)
python -m context_retrieval_mcp             # module mode (after pip install)
python3 context_retrieval_mcp/server.py     # direct run from mcp-server/, or by absolute
                                            # path as the plugin does (only `pip install mcp` needed)
```

CLI flags: `--print-index` dumps the resolved index as JSON (works even
without the `mcp` SDK installed — the escape hatch for pi.dev tooling, CI,
debugging), `--project-root DIR` overrides root resolution, `--version`.

```bash
context-retrieval-mcp --print-index [--project-root DIR]
```

### Project Root Resolution

The server indexes the **project it runs in**, resolved as (first hit wins):

1. `$CONTEXT_MCP_PROJECT_ROOT` (explicit override)
2. `$CLAUDE_PROJECT_DIR` (set by Claude Code)
3. Walk up from the current directory to the first `.git`/`.claude` marker
4. The current directory

If the index looks wrong from inside a session, call `get_index_status()` — it reports the resolved root, counts, and every parse warning.

### Claude Code Integration

Add to your project's `.mcp.json` (at project root):

```json
{
  "mcpServers": {
    "context-retrieval": {
      "type": "stdio",
      "command": "context-retrieval-mcp"
    }
  }
}
```

Or, with no pip install (the way the codified-context plugin runs it):

```json
{
  "mcpServers": {
    "context-retrieval": {
      "type": "stdio",
      "command": "python3",
      "args": ["<path-to>/context_retrieval_mcp/server.py"]
    }
  }
}
```

## Migrating From the v1 Template

If you adopted the earlier dict-based template (shipped as `quickstart/mcp-server/` through v1.x, removed in v2): move each `SUBSYSTEMS` entry into the front-matter of its context doc (`keywords`, `files`, description) and each `AGENTS` entry into its agent spec's front-matter (`triggers:`). As a stopgap, the `EXTRA_SUBSYSTEMS`/`EXTRA_AGENTS` dicts at the top of `server.py` are merged *under* the front-matter index (front-matter wins on collision), so you can migrate incrementally.

The original dict-based case-study server is preserved verbatim in `case-study/mcp-server/` (see `case-study/FROZEN.md`).

## How It Fits in the Architecture

```
Tier 1: Constitution (AGENTS.md / CLAUDE.md)
    ↓ always loaded, references Tier 3 tools
Tier 2: Specialized Agents (.claude/agents/*.md)
    ↓ suggest_agent() routes tasks to agents
Tier 3: Context Retrieval (THIS SERVER over .claude/context/*.md)
    ↑ find_relevant_context() discovers docs
```

The constitution instructs the AI agent to call MCP tools *first* when exploring unfamiliar code. This creates a pull-based retrieval pattern where the agent requests exactly the context it needs, rather than having everything loaded upfront.

## File Structure

```
mcp-server/
├── pyproject.toml                # Package configuration
├── README.md                     # This file
└── context_retrieval_mcp/
    ├── __init__.py               # Deliberately light (see stdlib-only contract)
    ├── __main__.py               # python -m entry point
    ├── context_index.py          # Front-matter parser + index (stdlib-only)
    ├── matching.py               # Unified keyword/trigger scoring (stdlib-only)
    ├── skills_gen.py             # Context-doc → Agent Skill adapter generator
    └── server.py                 # The MCP server (imports the modules above)
```

**Stdlib-only contract**: `context_index.py` and `matching.py` never import `mcp` — session hooks and generator scripts import them under a bare `python3`.
