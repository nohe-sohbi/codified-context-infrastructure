---
name: codified-context
description: Bootstrap or maintain a codified context infrastructure in the current project — constitution (AGENTS.md/CLAUDE.md), context docs with front-matter, specialized agents, generated context skills, MCP retrieval, and doc↔code drift detection. Use when the user wants to set up project knowledge for AI agents, add/refresh context docs or agents, regenerate skills or reference tables, or react to a CONTEXT DRIFT warning.
---

# Codified Context Infrastructure

> **Setting up a project? The `/codified-context:init` command walks the
> whole sequence below (state detection → constitution → backfill →
> verification).** This skill is the reference for everything else.

You are working with the codified-context plugin (companion to
arXiv:2602.20478). This SKILL.md lives at
`<plugin-root>/skills/codified-context/SKILL.md` — the plugin root is two
directories up; scripts referenced below live under `<plugin-root>/scripts/`.

## What the infrastructure is

Three tiers, all indexed from front-matter (single source of truth):

| Tier | Artifact | Loading |
|------|----------|---------|
| 1 — Constitution | The project's instructions file — `CLAUDE.md` when every harness in use reads it; `AGENTS.md` canonical + `CLAUDE.md` shim only when the toolset needs it | Every session |
| 2 — Specialized agents | `.claude/agents/{name}.md` (front-matter incl. `triggers:`) | Routed per task |
| 3 — Knowledge base | `.claude/context/{topic}.md` (front-matter: subsystem, keywords, files, priority) | On demand via MCP tools + generated `ctx-*` skills |

Registration is automatic: the MCP server (`context-retrieval`), the drift
hooks, and the generators all scan the same front-matter. Writing a complete
front-matter block IS the registration.

## Bootstrap sequence (new project)

1. Invoke the `constitution-factory` agent — creates AGENTS.md + CLAUDE.md shim (asks 3 questions).
2. As subsystems emerge, invoke `context-factory` per subsystem — creates `.claude/context/{topic}.md` with full front-matter.
3. When failure patterns repeat in a domain, invoke `agent-factory` — creates `.claude/agents/{name}.md` with routing `triggers:`.
4. Generate the path-triggered context skills:
   `python3 <plugin-root>/scripts/generate_skills.py --project-root .`
5. Verify the index: call the `get_index_status()` MCP tool — it must report YOUR project root and list your docs/agents (legacy-header docs warn by design).

## Maintenance

- **After changing how a subsystem works**: update its context doc in the same session (tables/flows + bump `last-verified`), then rerun the skills generator if descriptions/files changed.
- **New subsystem doc or agent**: rerun `python3 <plugin-root>/scripts/generate_reference_table.py` to refresh the constitution's generated tables.
- **CONTEXT DRIFT warning (session start) or drift advisory (session end)**: read the changed code files, propose targeted deltas to the flagged spec — never a full rewrite — or state why no change is needed. `--dismiss` on `<plugin-root>/hooks/drift_check.py` silences false positives.
- **Validation**: `python3 <plugin-root>/scripts/validate_architecture.py --project-root .` checks front-matter, file references, and cross-reference bidirectionality.

## Rules of thumb (from the paper)

- If you explained it twice, write it down (as a context doc).
- When a domain keeps failing, create a specialist agent and restart the task.
- Stale specs mislead agents: updating the doc is part of the change, not an afterthought.
