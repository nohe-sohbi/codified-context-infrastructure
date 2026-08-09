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
- **Versionability**: does `.gitignore` ignore `.claude/` (or `.claude/*`, or the context/skills subpaths)? If yes, say it LOUDLY: a context infrastructure that is not versioned serves one machine and dies at the next clone. Propose the narrowing (e.g. ignore `.claude/settings.local.json`, keep `context/`, `skills/`, `agents/` tracked) — the user decides.

## 2. Constitution — create only if missing

- **Nothing exists** → invoke the `constitution-factory` agent. Its 3 questions
  (what is the project / maturity / priorities) are answered **by the user,
  never by you or a subagent** — self-answering them produces a constitution
  nobody arbitrated. The generated file is shown to the user before any
  commit; a constitution the user has never read is not a deliverable.
  Format is toolset-driven: `CLAUDE.md` canonical if every harness in use reads it.
- **A real constitution exists** → **do not touch its content.** Say explicitly: "Your CLAUDE.md/AGENTS.md stays as is — the infrastructure works with it." (Migration/restructuring is a separate, optional task the user must ask for.)

  One exception, offered — never imposed: if the constitution predates the
  plugin, it lacks the standing instructions that make retrieval and drift
  handling *systematic* instead of left to the model's discretion. Show this
  block as an append-only diff and let the user approve:

  ```markdown
  ## Codified context
  - Before exploring unfamiliar code: call `find_relevant_context(task)` and `suggest_agent(task)` (context-retrieval MCP) first.
  - CONTEXT DRIFT warning at session start: HIGH → update the doc before anything else; MEDIUM → mention it to the user.
  - Spec deltas proposed at session end: apply after the user's yes.
  ```

  Without these lines the MCP tools still work, but their use depends on the
  model noticing them — the weak link on any project whose constitution
  predates the plugin.

## 2b. Existing agents — wire them into the router

Do NOT create new agents at init: agents are born from repeated failure
patterns, never speculatively (a doc captures *state*; an agent embeds
*judgment* and drifts unwatched — create one only when a domain keeps
failing despite its context doc).

But if the project already HAS agents in `.claude/agents/` whose
front-matter lacks `triggers:`, offer to enrich them: for each, read its
description and body, add 7-15 routing keywords (single words and phrases,
distinctive to its domain), then verify with `suggest_agent("<typical
task>")` that routing matches. Listed-but-unroutable agents are wasted
infrastructure.

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
2. Run the other two plugin scripts: `validate_architecture.py --project-root .` (must end 0 errors) and `generate_reference_table.py --project-root .` (no-op without GENERATED markers — that is fine, say so).
3. Call `get_index_status()` → it must report this project's root and the new doc count, with no warnings about the new docs.

## 5. Completeness self-audit — mandatory before declaring done

The user should never need to ask "were you complete?" — ask it yourself,
answer it honestly, and print the answer. The audit:

- **Scope**: every subsystem you identified but did NOT document is listed
  at the TOP of the final report as a **decision for the user** ("in scope
  next wave? yes/no") — never as a footnote. Silently reducing the scope is
  the single most common failure of this sequence.
- **Depth**: the coverage table (files read in full vs declared) is printed,
  including partial coverage confessed per doc.
- **Template compliance**: each doc has the template's sections — including
  **Testing** when the project has test rigs/harnesses (find them; a doc
  that ignores the project's own oracle is incomplete).
- **Artifacts the user never saw**: any generated file the user has not
  reviewed (constitution above all) is flagged for review before commit.
- **Housekeeping**: leftover placeholders (`.gitkeep` in a now-populated
  directory), uncommitted deliverables, and the versionability finding from
  step 1 are restated with a proposed commit message.

Close by telling the user the operating loop, in two lines:
- the drift guardian will propose spec updates at session end on its own — just answer yes/no;
- create a NEW doc whenever they catch themselves explaining the same thing twice.
