# Frozen artifacts

This directory contains **verbatim artifacts from the case study** of
*"Codified Context: Infrastructure for AI Agents in a Complex Codebase"*
([arXiv:2602.20478](https://arxiv.org/abs/2602.20478)) and is kept frozen for
paper fidelity. Known quirks are preserved deliberately: the inconsistent
keyword matching in `mcp-server/server.py` (`find_relevant_context` uses plain
substring matching), the hardcoded `GameProject/...` paths, and the
`hooks-config.json`/`scripts/` assuming the original project layout.

The **maintained, installable implementation** lives at the repository root:
`mcp-server/` (index-driven server), `hooks/`, `agents/`, `scripts/`.
