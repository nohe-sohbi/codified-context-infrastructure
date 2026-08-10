# Port codified-context to pi

**If you use [pi](https://pi.dev) instead of Claude Code**, paste this single
line into pi, from inside the project you want to equip:

```
Fetch https://raw.githubusercontent.com/nohe-sohbi/codified-context-infrastructure/main/PORT-TO-PI.md and follow it.
```

(Or, from a clone of this repo: `Read PORT-TO-PI.md and follow it.`)

Everything below is addressed to the pi agent. It is a build spec: where it
says verbatim, copy verbatim; where it says ask, ask the user instead of
deciding. The knowledge artifacts themselves (constitution, context docs,
agent specs) are plain markdown with YAML front-matter — nothing about them is
Claude-specific. What you are porting is the *plumbing around them*: retrieval
tools, drift detection, factories.

---

## One decision first: keep the `.claude/` data layout

The infrastructure stores its knowledge base in `.claude/context/*.md` and
`.claude/agents/*.md`. **Keep that layout unchanged.** It is harness-neutral
data (markdown + front-matter), the MCP server and drift logic index it by
that path contract, and keeping it lets Claude Code and pi users share the
same project infrastructure with zero divergence. Do not "translate" the
directory to `.pi/`.

## Step 0 — read before writing

1. Your own extension documentation (events, `pi.sendMessage`,
   `pi.registerTool`, prompt templates, skills).
2. Clone the source to a **permanent** location (the MCP server and hooks run
   from it): ask the user where — suggest `~/.pi/agent/vendors/codified-context`.
   `git clone https://github.com/nohe-sohbi/codified-context-infrastructure <dest>`
3. Read: `README.md`, `quickstart/README.md` (front-matter contract),
   `hooks/drift_check.py`, `hooks/drift_stop.py`, `hooks/drift_common.py`
   (module docstrings = behavior contract), `mcp-server/README.md`.

## Component 1 — context retrieval (the MCP server)

Ask the user: **is `pi-mcp-adapter` installed?**

- **Yes** → do not port anything. Add this block to the project's
  `.pi/mcp.json` (create the file if absent; if it exists, **merge** the
  entry — never overwrite the user's file, show the diff first):

  ```json
  {
    "mcpServers": {
      "context-retrieval": {
        "type": "stdio",
        "command": "python3",
        "args": ["<clone>/mcp-server/context_retrieval_mcp/server.py"]
      }
    }
  }
  ```

  The server resolves the project root from cwd and provisions its own venv
  for the `mcp` SDK on first serve (`mcp-server/README.md`). Sanity-check by
  calling the `get_index_status` tool: it must report **this** project's root.

- **No** → register thin native tools instead. Escape hatch: the server's
  whole index is available without the MCP SDK via
  `python3 <clone>/mcp-server/context_retrieval_mcp/server.py --print-index
  --project-root <project>`. Register a `ctx_index` tool that runs that
  command, plus a `ctx_find` tool that greps the returned index for a task
  description. Prefix all tool names `ctx_` — never generic names.

## Component 2 — drift detection (the hooks → one extension)

One TypeScript extension, two moments:

### Session start (Claude Code `SessionStart` → pi `session_start`, reasons `startup`/`resume`)

Run `python3 <clone>/hooks/drift_check.py` with cwd = the project root and
inject its stdout as context (empty output = stay silent). The script is
standalone: it compares recent git commits against the front-matter index and
prints prioritized warnings. Respect its env overrides (`DRIFT_MAX_COMMITS`,
`DRIFT_BUILD_CMDS`). The debug-session heuristic reads Claude Code session
logs and will simply find none under pi — that degradation is expected and
silent.

### Turn end (Claude Code `Stop` → pi `agent_end`, advisory)

- Track files edited this session live via tool events (`edit`/`write` and
  overrides) — do **not** parse session files.
- Map edited code files to subsystems and flag drift with the exact rules of
  `hooks/drift_common.py` (`match_code_file`, `flag_drift` — ~40 lines, port
  them faithfully: root-relative exact match, `dir/` prefix match, `low`
  priority suppressed, doc-suggestion dedup). The index comes from the
  front-matter of `.claude/context/*.md` (`files:`, `priority:`).
- If drift is found, build the message with `build_message()` from
  `hooks/drift_stop.py` (verbatim port) and deliver it **advisory**:

  ```ts
  pi.sendMessage(
    { customType: "codified-context", content: message, display: true },
    { deliverAs: "nextTurn" },  // advisory: never triggers a turn by itself
  );
  ```

- Guards: fire at most once per (session, flagged-subsystem set) — persist via
  `pi.appendEntry`; never react to turns triggered by injected messages;
  a doc edited this session counts as touched (no false positive right after
  a backfill).

## Component 3 — the factory agents (→ prompt templates)

pi has no native subagents. Convert the three factories to prompt templates:
for each of `agents/constitution-factory.md`, `agents/context-factory.md`,
`agents/agent-factory.md`, copy the markdown **body** into
`.pi/prompts/ctx-constitution-factory.md`, `ctx-context-factory.md`,
`ctx-agent-factory.md`. Drop the Claude-specific front-matter keys (`model`,
tool lists); keep a one-line `description`. They become
`/ctx-constitution-factory` etc. — prefixed, so they collide with nothing.

If the user has the `pi-subagents` package and wants isolation, offer to wire
them there instead — ask, don't assume.

## Component 4 — the skills

`skills/init` and `skills/codified-context` follow the Agent Skills standard,
which you read natively. Copy them into `.pi/skills/` (or `.agents/skills/`)
**renamed** `ctx-init` and `ctx-codified-context` (update the front-matter
`name:` to match): `init` is far too generic a name to inject into a shared
skill namespace. Their instructions reference `.claude/context/` paths and the
`context-retrieval` tools — both remain valid after Components 1–2.

## Component 5 — the constitution

Nothing to port: you read `AGENTS.md` natively, and this infrastructure
already treats `AGENTS.md` as canonical (`CLAUDE.md` is a shim pointing at
it). When `/ctx-init` runs, it produces exactly that.

## Non-negotiable guards

- Prefix everything: tools `ctx_*`, commands/templates `/ctx-*`, injected
  messages `customType: "codified-context"`.
- Advisory means advisory: drift feedback never sets `triggerTurn`.
- Never overwrite user config (`.pi/mcp.json`, settings) — merge and show.
- Append-only on the system prompt; state only in your own `appendEntry`
  entries; every handler wrapped — an exception here must never break a
  session.

## Verify before you call it done

- (a) `get_index_status` (or `ctx_index`) reports this project's root and its
  subsystems.
- (b) Commit a code change under a subsystem's `files:` glob without touching
  its doc → next `session_start` prints a drift warning; `--dismiss` logic
  (see `drift_check.py`) silences it after two shows.
- (c) Edit a subsystem's code file in a session and end the turn → exactly one
  advisory message, delivered with the next user turn, not a self-triggered
  turn; ending another turn with the same drift stays silent.
- (d) A project with no `.claude/context/` docs produces zero warnings and
  zero errors.
- (e) `/ctx-init` walks the bootstrap sequence; `/ctx-constitution-factory`
  expands its template.
- (f) `low`-priority subsystems never produce warnings.

## Report to the user

State: where the clone lives; what was added to `.pi/` (extension, prompts,
skills, mcp.json entry); the surfaces touched (events `session_start`,
`agent_end`, tool events; tools/commands registered, all `ctx`-prefixed;
messages tagged `codified-context`); and how to uninstall (remove those files
and the mcp.json entry — the `.claude/` knowledge base itself belongs to the
project, not to this port).
