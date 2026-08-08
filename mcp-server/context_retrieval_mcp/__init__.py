"""
Context Retrieval MCP Server — index-driven Tier 3 retrieval.

Deliberately does NOT import the server here: `context_index` and
`matching` are stdlib-only and must stay importable under a bare python3
(session hooks and generator scripts import them without the `mcp` SDK).
Import the server explicitly where you need it:

    from context_retrieval_mcp.server import mcp, main
"""

__all__: list = []
