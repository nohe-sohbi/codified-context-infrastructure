# Codified Context: Infrastructure for AI Agents in a Complex Codebase

A *codified context infrastructure* — structured, machine-readable project knowledge that AI coding agents depend on to maintain coherence across sessions, follow conventions, and avoid repeating mistakes.

Companion repository to: *"Codified Context: Infrastructure for AI Agents in a Complex Codebase"* by Aris Vasilopoulos ([arXiv:2602.20478](https://arxiv.org/abs/2602.20478)).

## The Problem

LLM-based coding agents lack persistent memory: each session begins without awareness of prior sessions, established conventions, or past mistakes. Single-file manifests (`.cursorrules`, `CLAUDE.md`) help with small projects, but they do not scale beyond modest codebases — a 1,000-line prototype can be fully described in a single prompt, but a 100,000-line system cannot. Without structured knowledge transfer, agents on large projects:
- Forget architectural conventions and repeat known mistakes
- Lose context about subsystem interactions across files
- Require lengthy re-explanations of project structure
- Make inconsistent decisions that drift from established patterns

## The Solution: Three-Tier Context Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: CONSTITUTION (Hot Memory — always loaded)          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ CLAUDE.md                                             │  │
│  │ • Conventions, build commands, naming standards       │  │
│  │ • System registration checklists                      │  │
│  │ • Agent trigger table (when to invoke which agent)    │  │
│  │ • Key file reference map                              │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Tier 2: SPECIALIZED AGENTS                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Code     │ │ Network  │ │ Debug    │ │ UI/UX    │      │
│  │ Reviewer │ │ Protocol │ │ Profiler │ │ Designer │  ... │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  Domain experts with focused prompts + context access       │
├─────────────────────────────────────────────────────────────┤
│  Tier 3: KNOWLEDGE BASE + RETRIEVAL (Cold Memory)           │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ .claude/context/*.md │  │ MCP Retrieval Service     │    │
│  │ • Subsystem specs    │  │ • list_subsystems()       │    │
│  │ • Architecture docs  │  │ • find_relevant_context()  │    │
│  │ • Protocol docs      │  │ • search_context_docs()    │    │
│  │ • Pattern guides     │  │ • suggest_agent()          │    │
│  │                      │  │ • + 3 more (see mcp-server)│    │
│  └──────────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Tier 1** (hot memory) is loaded into every agent session automatically. It contains project conventions, checklists, and orchestration protocols that route tasks to specialized agents.

**Tier 2** consists of specialized agents — domain-expert personas with focused prompts and embedded project knowledge. They are invoked automatically based on trigger conditions in the constitution.

**Tier 3** (cold memory) contains detailed specification documents loaded on demand. An MCP retrieval service maps tasks to relevant files, so agents only load what they need.

## Key Findings (from the Paper)

| Metric | Value |
|--------|-------|
| Knowledge-to-code ratio | ~24% (1 line of documentation per 4 lines of code) |
| Context infrastructure | ~26,000 lines across constitution + 34 specs + 19 agents |
| Agent amplification | 2,801 prompts → 1,197 agent invocations → 16,522 agent turns |

## Paper-to-Repo Mapping

| Paper Section | Repo Directory |
|---------------|----------------|
| §3.1 Constitution | `case-study/CLAUDE.md` |
| §3.2 Specialized Agents | `case-study/agent-specs/` |
| §3.3 Knowledge Base & MCP | `case-study/context-docs/`, `mcp-server/` (maintained), `case-study/mcp-server/` (frozen original) |
| §4.2–4.3 Evaluation Metrics | `data/` (scripts, methodology, sample data) |
| §4.4 Case Studies | `data/case-study-excerpts/` |
| §5.1 Factory Agents | `agents/` |
| §5.2 Drift Detector | `hooks/` (maintained), `case-study/scripts/context-drift-check.py` (frozen original) |
| Appendix B (coordinate-wizard) | `case-study/agent-specs/coordinate-wizard.md` |

> `case-study/` is kept **frozen** as verbatim paper artifacts (see `case-study/FROZEN.md`); the maintained, installable implementation lives at the repository root.

## Repository Structure

```
.claude-plugin/         Claude Code plugin manifest + self-hosted marketplace
agents/                 The three factory agents (flat, self-registering format)
  constitution-factory.md     Generate a constitution for any project
  agent-factory.md            Generate specialized agents
  context-factory.md          Generate context base documents
skills/                 The codified-context meta-skill (plugin front door)
hooks/                  Drift detection: SessionStart check + Stop advisor + hooks.json

mcp-server/             Index-driven MCP retrieval service (Tier 3, maintained)
  context_retrieval_mcp/      Server + front-matter index + matching + skills generator
  pyproject.toml              Package configuration
  README.md                   Setup, front-matter schema, migration notes

scripts/                Generators and validation
  generate_skills.py          Context docs → path-triggered .claude/skills adapters
  generate_reference_table.py Regenerate constitution tables from the index
  validate_architecture.py    Cross-reference and front-matter validation

tests/                  Pytest suite + fixtures/demo-project (living format example)
quickstart/             Setup guide (plugin install + manual copy)

case-study/             FROZEN verbatim artifacts from the paper's project
  CLAUDE.md                   The actual constitution (~660 lines, sanitized)
  context-docs/               5 representative knowledge base documents
  agent-specs/                5 real agent specifications
  mcp-server/                 The original dict-based MCP server
  scripts/                    Original validation and drift detection

data/                   Interaction data and analysis
paper/                  Paper reference, abstract, and citation
docs/                   Analysis and perspectives (2026 research/tooling watch)
```

> **Note:** The `case-study/` directory mirrors what would live under `.claude/` in a real project. The recommended production layout is `.claude/agents/{id}/AGENT.md` for agent specs and `.claude/context/{topic}.md` for knowledge base documents.

## Quick Start

### As a Claude Code Plugin (Recommended)

```
/plugin marketplace add nohe-sohbi/codified-context-infrastructure
/plugin install codified-context@codified-context-marketplace
```

This installs the three factory agents, the `codified-context` skill, the index-driven `context-retrieval` MCP server (requires `python3` + `pip install mcp`), and the drift-detection hooks. Then, in your project:

> *"Use the codified-context skill and help me set up the context infrastructure for this project."*

### Manual Setup (any harness)

1. **Factories** — Copy `agents/*.md` into your project's `.claude/agents/` and let your assistant bootstrap (start with `constitution-factory`)
2. **Context documents** — Create `.claude/context/{topic}.md` files with YAML front-matter (see `tests/fixtures/demo-project/` for the format, `case-study/context-docs/` for real-world content)
3. **Agent specs** — Create `.claude/agents/{name}.md` files with front-matter incl. `triggers:`
4. **MCP server** — Copy `mcp-server/`, `pip install -e .` — it indexes your front-matter automatically (see `mcp-server/README.md`)
5. **Drift detection** — Copy `hooks/` (keep it a sibling of `mcp-server/`) and wire `hooks.json` into your settings

See `quickstart/README.md` for the full bootstrapping sequence and the front-matter contract.

## Harness & Model Compatibility

The knowledge artifacts are plain markdown with YAML front-matter — portable by construction. What each harness can consume:

| Capability | Claude Code | pi / Codex / Gemini CLI | Cursor | Any CI/shell |
|---|---|---|---|---|
| Constitution | `CLAUDE.md` shim (`@AGENTS.md`) | `AGENTS.md` natively | `AGENTS.md` natively | — |
| Context docs (Tier 3) | MCP tools + generated `ctx-*` skills (auto-load by `paths:`) | MCP server (`.mcp.json`-style config) or `--print-index` JSON | MCP server | `--print-index` JSON |
| Specialized agents (Tier 2) | `.claude/agents/*.md` subagents | Convert front-matter to the tool's persona format | Rules/modes | — |
| Drift detection | SessionStart + Stop hooks | Run `hooks/drift_check.py` manually or via the tool's hook system | — | `validate_architecture.py` + `drift_check.py` in CI |

**Model routing intent** (encode it in your constitution; map per harness): judgment-heavy work — architecture, debugging, cross-cutting review — to your strongest model; pattern-following work *covered by a spec* to fast/economical models. Rich context docs are what make the cheaper tier viable: the spec compensates for the model.

## Design Principles

1. **Documentation as infrastructure.** Context documents are load-bearing artifacts that AI agents depend on to produce correct output — living specifications, not passive reference material. When a specification goes stale, agents generate code based on outdated information.

2. **Written for AI, not humans.** Context documents use tables, code blocks, and explicit patterns rather than prose. Agents parse structured content more reliably than natural language descriptions.

3. **Hot/cold memory separation.** The constitution (hot memory) is always present. Specifications (cold memory) are loaded on demand via MCP retrieval. This keeps token usage efficient while making deep context available when needed.

4. **Cross-referenced and validated.** The constitution references context docs, context docs reference source files, and the MCP server indexes both. A validation script checks all cross-references on every session start.

5. **Iteratively grown, not designed upfront.** The infrastructure emerged from real development needs. Documents were created when agents made mistakes, not as a planning exercise. Start small and add context as patterns emerge.

6. **Agents as domain experts.** Specialized agents carry focused prompts and embedded domain knowledge, invoked automatically by trigger conditions. A code reviewer is invoked after every system modification; a network specialist is invoked for any sync-related work.

## Links

- **Paper:** [arXiv:2602.20478](https://arxiv.org/abs/2602.20478)
- **Author:** [Aris Vasilopoulos](https://github.com/arisvas4)

## License

MIT
