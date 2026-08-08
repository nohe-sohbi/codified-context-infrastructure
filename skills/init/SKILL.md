---
name: init
description: Initialize the codified context infrastructure in the current project — detect what already exists, create the constitution only if missing, then backfill context docs for the most critical subsystems so the plugin is useful from the first session. Use when the user wants to init, bootstrap, or set up codified-context on a project, or asks "what do I do after installing the plugin".
argument-hint: "[number of backfill docs, default 5]"
---

# Initialize codified context

Run this sequence in order. Never modify an existing file without showing
what will change first. A freshly installed plugin is an empty box — this
command fills it.

## 1. Detect the project state (report it in 3 lines)

- **Constitution**: does `CLAUDE.md` and/or `AGENTS.md` exist with real content (more than a stub)?
- **Context docs**: how many `.claude/context/*.md`? (Use the `get_index_status()` MCP tool if connected — it also verifies the server resolved THIS project's root — otherwise glob.)
- **Agents/skills**: anything in `.claude/agents/`, `.claude/skills/`?

## 2. Constitution — create only if missing

- **Nothing exists** → invoke the `constitution-factory` agent (it asks 3 questions, then generates). Format is toolset-driven: `CLAUDE.md` canonical if every harness in use reads it.
- **A real constitution exists** → **do not touch it.** Say explicitly: "Your CLAUDE.md/AGENTS.md stays as is — the infrastructure works with it." (Migration/restructuring is a separate, optional task the user must ask for.)

## 3. Backfill — the step that makes the plugin useful TODAY

If the project has fewer than 3 context docs and a non-trivial codebase:

1. Explore the codebase and propose the **N most valuable subsystems to codify** (N = the argument, default 5): the complex, critical, convention-heavy, or historically bug-prone ones — the areas where an agent without context makes mistakes or needs re-explaining.
2. Present the list with a one-line rationale each. **Wait for approval.**
3. For each approved subsystem, create `.claude/context/<topic>.md` with complete front-matter (`subsystem`, `description`, `keywords`, `files`, `priority`, `related`, `last-verified`) by reading the real code — follow the `context-factory` agent's format (tables over prose, key files, known pitfalls).

   **Depth contract (mandatory).** Breadth is selective — never document
   subsystems speculatively — but depth is total: a backfilled doc requires a
   **full read of every file it declares in `files:`**, not grep sampling.
   Parallelize with subagents when permitted (one per subsystem). If a
   subsystem's file set is too large to read fully this session, say so and
   either narrow its scope or split the backfill across sessions — never
   compensate with guesswork. Close by reporting coverage honestly
   (files read in full vs declared).
4. **Provenance rule (mandatory).** With the depth contract honored, most
   claims are read from code; what remains is knowledge that is not IN the
   code (incident history, ops lore, decisions). Every factual claim is either
   (a) **read from the current code this session** — cite the file, or
   (b) **inherited** from memory, incident notes, or older docs — then tag it
   visibly (e.g. `⚠ not re-verified against current code`).
   Never present (b) as (a). A pitfall that was already fixed but is documented
   as active sends every future agent chasing a ghost — stale knowledge at
   birth, the exact failure the drift guardian exists to prevent. Close the
   backfill by offering a **verification pass** over the tagged claims (one
   check per claim; subagents in parallel if permitted): each becomes either
   "still true" (with the code reference) or "fixed on <date>, kept for the
   record" — never silently deleted.

This is one session of work and it is the whole point: after it, retrieval,
auto-loading skills and the drift guardian are all live over real content.

## 4. Activate and verify

1. Generate the auto-loading skills: `python3 <plugin-root>/scripts/generate_skills.py --project-root .` (this SKILL.md lives at `<plugin-root>/skills/init/SKILL.md` — the plugin root is two directories up).
2. Call `get_index_status()` → it must report this project's root and the new doc count, with no warnings about the new docs.
3. Close by telling the user the operating loop, in two lines:
   - the drift guardian will propose spec updates at session end on its own — just answer yes/no;
   - create a NEW doc whenever they catch themselves explaining the same thing twice.
