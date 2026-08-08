# Demo Project — Constitution

Fixture constitution for the codified-context test suite.

## Subsystem Reference

<!-- BEGIN GENERATED: subsystem-reference -->
| Key | Description | Doc | Priority |
|-----|-------------|-----|----------|
| `broken-doc` | Broken Doc | `.claude/context/broken.md` | medium |
| `networking` | Host-authoritative sync with deterministic RNG | `.claude/context/networking.md` | high |
| `save-system` | Two-tier save architecture (disk JSON + in-memory run state) | `.claude/context/save-system.md` | high |
| `ui-legacy` | UI Legacy Doc | `.claude/context/ui-legacy.md` | medium |
<!-- END GENERATED: subsystem-reference -->

## Agents

<!-- BEGIN GENERATED: agent-reference -->
| Agent | Model | Primary Focus |
|-------|-------|---------------|
| `code-reviewer` | opus | Reviews changes for correctness and project conventions. |
| `legacy-agent` | sonnet | Agent kept in the legacy nested {id}/AGENT.md layout. |
<!-- END GENERATED: agent-reference -->
