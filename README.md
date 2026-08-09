# codified-context

**Your coding agent forgets everything. Give it a memory it can trust.**

[![CI](https://github.com/nohe-sohbi/codified-context-infrastructure/actions/workflows/ci.yml/badge.svg)](https://github.com/nohe-sohbi/codified-context-infrastructure/actions/workflows/ci.yml) · MIT · Companion to [arXiv:2602.20478](https://arxiv.org/abs/2602.20478)

## Get started (2 minutes)

In Claude Code:

```
/plugin marketplace add nohe-sohbi/codified-context-infrastructure
/plugin install codified-context@codified-context-marketplace
```

Then, **in the project you want to equip**:

```
/codified-context:init
```

That's it. `init` detects what already exists (an existing `CLAUDE.md` is never touched), creates a constitution only if missing, then proposes your ~5 most critical subsystems and writes their context docs — you approve the list and review. One session, and your agent has a memory.

Only prerequisite: `python3` 3.10+ (the MCP server provisions its own SDK on first run). Not on Claude Code? See [Manual setup](#manual-setup-any-harness).

## After init: the daily workflow

You work normally — the infrastructure acts on its own at four moments:

1. **While coding**: touch a file listed in a doc's `files:` → its `ctx-*` skill auto-loads; explore unfamiliar ground → `find_relevant_context()` returns the right docs instead of a codebase crawl. You explain nothing.
2. **At session end**: changed a subsystem's code without its doc? The Stop hook proposes targeted spec deltas. **You answer yes/no — that's the daily gesture.**
3. **When you catch yourself explaining something for the second time** (the only manual trigger): *"create a context doc for X"*. Indexed instantly, skill generated.
4. **When a domain keeps failing despite its doc** (rare): *"use the agent-factory to create a `<domain>-reviewer` with the known pitfalls embedded"*. Routed automatically from then on.

What you never do: hand-maintain the index/tables/skills (all derived from front-matter), re-read docs "just in case" (the guardian watches every commit), or write docs speculatively (never before the second explanation). The payoff compounds: week 1 you answer yes/no's; month 3 your prompts are one line and cheaper models handle the spec-covered tasks.

## Why

AI coding agents have broad programming knowledge and zero project memory. Every session starts from scratch: conventions forgotten, hard-won bug fixes re-learned, the same mistakes repeated. One instructions file fixes that on a small repo — past ~20k lines it stops scaling.

**codified-context** turns your project's knowledge into plain markdown files that load themselves at exactly the right moment, and stay true as the code changes. Claude Code plugin first-class; the knowledge files are portable to any [AGENTS.md](https://agents.md) harness.

## How it works

Knowledge is split by loading frequency — a memory hierarchy, like your CPU has — plus a guardian that keeps all of it honest:

| Tier | Artifact | Loading |
|------|----------|---------|
| **1 — Constitution** | Your instructions file — `CLAUDE.md` if all your harnesses read it (Claude Code and pi do), or `AGENTS.md` canonical + `CLAUDE.md` shim when your toolset needs the vendor-neutral standard | Every session |
| **2 — Specialist agents** | `.claude/agents/{name}.md` — domain experts with embedded project knowledge, routed by `triggers:` | Per task |
| **3 — Knowledge base** | `.claude/context/{topic}.md` — one deep spec per subsystem, served via MCP retrieval + auto-loading skills | On demand |
| **Drift guardian** | `hooks/drift_*.py` — compares code changes against specs, asks for updates while context is hot | Every session |

**One block of YAML runs everything.** Each context doc declares its own metadata; the MCP server, the auto-loading skills, the drift hooks, the reference tables and the validator all derive from that same index — there is no registry to maintain, and the index rebuilds live when files change:

```yaml
---
subsystem: save-system
description: Two-tier save architecture (disk + memory)   # powers retrieval
keywords: [save, persistence, autosave]
files:                                                    # auto-loads on touch
  - src/services/save_service.py
  - src/services/                                         # trailing slash = directory
priority: high                                            # drift-warning tier
related: [item-system]
last-verified: 2026-08-08
---
```

**Stale docs are worse than no docs** — agents trust them blindly. When you change `save_service.py` without touching its spec, the session-end hook says so and asks for targeted deltas while everything is still fresh. That drift loop is what turns "documentation" into "memory".

## What actually changes for you

- **Your prompts shrink.** "Add an ice nova ability" is enough — conventions, file map and known pitfalls are already in context. In the original study, 80% of prompts were under 100 words.
- **The AI writes and maintains the docs**, under your review, with a detector telling you when and what.
- **Cheap models become viable** for mechanical tasks covered by a good spec — the spec compensates for the model. Keep your strongest model for architecture and debugging.
- **One rule of thumb:** if you've explained something to the AI twice, codify it. Never write docs speculatively.

## Where this comes from

The architecture is from *"Codified Context: Infrastructure for AI Agents in a Complex Codebase"* ([arXiv:2602.20478](https://arxiv.org/abs/2602.20478), Vasilopoulos 2026): a 108,000-line C# multiplayer game built in 70 part-time days with AI as the sole code generator, on ~26,000 lines of codified knowledge.

| Metric | Value |
|--------|-------|
| Knowledge-to-code ratio | ~24% (1 line of documentation per 4 lines of code) |
| Context infrastructure | ~26,000 lines across constitution + 34 specs + 19 agents |
| Agent amplification | 2,801 prompts → 1,197 agent invocations → 16,522 agent turns |
| Coordination proof | 74 sessions used the save-system spec — zero persistence bugs |

This repository is a modernized overhaul of the paper's companion framework: single-source front-matter index, auto-loading skills, session-end drift detection, installable plugin, test suite and CI.

## What the plugin installs

Three factory agents (`constitution-factory`, `context-factory`, `agent-factory`), the `codified-context` skill and the **`/codified-context:init`** command, the index-driven `context-retrieval` MCP server (it provisions the `mcp` SDK into a private venv on first serve, see `mcp-server/README.md`), and the drift-detection hooks. After `init`, sanity-check with the `get_index_status()` MCP tool — it must report **your** project's root.

## Manual setup (any harness)

1. **Factories** — Copy `agents/*.md` into your project's `.claude/agents/` and let your assistant bootstrap (start with `constitution-factory`)
2. **Context documents** — Create `.claude/context/{topic}.md` files with YAML front-matter (see `tests/fixtures/demo-project/` for the format, `case-study/context-docs/` for real-world content)
3. **Agent specs** — Create `.claude/agents/{name}.md` files with front-matter incl. `triggers:`
4. **MCP server** — Copy `mcp-server/`, `pip install -e .` — it indexes your front-matter automatically (see `mcp-server/README.md`)
5. **Scripts** — Copy `scripts/` (generators + validator); keep `scripts/`, `hooks/` and `mcp-server/` as siblings — they import the shared index by relative path
6. **Drift detection** — Copy `hooks/`; note `hooks/hooks.json` is written for plugin installs (`${CLAUDE_PLUGIN_ROOT}`) — manual installs adapt the `$CLAUDE_PROJECT_DIR` variant shown in `quickstart/README.md`

See `quickstart/README.md` for the full bootstrapping sequence and the front-matter contract.

> **Layout note:** the recommended layout is flat — `.claude/agents/{name}.md` and `.claude/context/{topic}.md`. The legacy nested `.claude/agents/{id}/AGENT.md` layout remains discovered for backward compatibility. Hooks and plugin MCP config invoke `python3` (macOS/Linux convention); on native Windows, adapt the commands to your Python launcher, or point the server at one with `CONTEXT_MCP_PYTHON`.

## Harness & Model Compatibility

The knowledge artifacts are plain markdown with YAML front-matter — portable by construction. What each harness can consume:

| Capability | Claude Code | pi / Codex / Gemini CLI | Cursor | Any CI/shell |
|---|---|---|---|---|
| Constitution | `CLAUDE.md` shim (`@AGENTS.md`) | `AGENTS.md` natively | `AGENTS.md` natively | — |
| Context docs (Tier 3) | MCP tools + generated `ctx-*` skills (auto-load by `paths:`) | MCP server (`.mcp.json`-style config) or `--print-index` JSON | MCP server | `--print-index` JSON |
| Specialized agents (Tier 2) | `.claude/agents/*.md` subagents | Convert front-matter to the tool's persona format | Rules/modes | — |
| Drift detection | SessionStart + Stop hooks | Run `hooks/drift_check.py` manually or via the tool's hook system | — | `validate_architecture.py` + `drift_check.py` in CI |

**Model routing intent** (encode it in your constitution; map per harness): judgment-heavy work — architecture, debugging, cross-cutting review — to your strongest model; pattern-following work *covered by a spec* to fast/economical models. Rich context docs are what make the cheaper tier viable: the spec compensates for the model.

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
.github/workflows/      CI (Linux py3.10/3.12 + MCP SDK v1/v2 + Windows)
quickstart/             Setup guide (plugin install + manual copy)

case-study/             FROZEN verbatim artifacts from the paper's project
  CLAUDE.md                   The actual constitution (679 lines, sanitized)
  context-docs/               5 representative knowledge base documents
  agent-specs/                5 real agent specifications
  mcp-server/                 The original dict-based MCP server
  scripts/                    Original validation and drift detection

data/                   Interaction data and analysis
paper/                  Paper reference, abstract, and citation
docs/                   Analysis and perspectives (2026 research/tooling watch)
```

## Design Principles

1. **Documentation as infrastructure.** Context documents are load-bearing artifacts that AI agents depend on to produce correct output — living specifications, not passive reference material.
2. **Written for AI, not humans.** Tables, code blocks, and explicit patterns rather than prose. Agents parse structured content more reliably than natural language descriptions.
3. **Hot/cold memory separation.** The constitution is always present; specifications load on demand. Token-efficient, depth available when needed.
4. **Single source of truth.** Front-matter is the registration; everything else — index, skills, tables, drift checks — is derived and regenerated, never hand-maintained.
5. **Iteratively grown, not designed upfront.** Documents were created when agents made mistakes, not as a planning exercise. Start small and add context as patterns emerge.
6. **Freshness is enforced, not hoped for.** Drift detection runs at session start and session end; stale specs are the failure mode the whole design guards against.

## Links

- **Paper:** [arXiv:2602.20478](https://arxiv.org/abs/2602.20478) — *Codified Context: Infrastructure for AI Agents in a Complex Codebase*, Aris Vasilopoulos
- **Original companion repo:** [arisvas4/codified-context-infrastructure](https://github.com/arisvas4/codified-context-infrastructure)
- **Research & tooling watch (2026):** [`docs/analyse-et-perspectives-2026.md`](docs/analyse-et-perspectives-2026.md) · [`docs/grille-facteurs-comprehension.md`](docs/grille-facteurs-comprehension.md)

## License

MIT
