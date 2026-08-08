"""
Context Retrieval MCP Server — Tier 3 of the codified context infrastructure.

Index-driven: there is NO hand-maintained SUBSYSTEMS/AGENTS dict here.
The index is built by scanning the project's own artifacts:

  - `.claude/context/*.md`     — context docs declaring YAML front-matter
                                 (subsystem, description, keywords, files,
                                 priority, related, version, last-verified)
  - `.claude/agents/**/*.md`   — agent specs (name, description, model,
                                 optional triggers)

Writing complete front-matter IS the registration step — the server, the
drift hooks, the skills generator and the validators all read the same
index (see context_index.py). The index refreshes automatically when any
indexed file changes, so docs created mid-session are visible on the next
tool call.

Project root resolution (first hit wins): $CONTEXT_MCP_PROJECT_ROOT →
$CLAUDE_PROJECT_DIR → walk up from cwd to a `.git`/`.claude` marker → cwd.
Call `get_index_status()` from a session to verify what got indexed.

Launch modes: `context-retrieval-mcp` (console script after pip install),
`python -m context_retrieval_mcp`, or direct `python3 server.py` (only
`pip install mcp` needed — this is how the Claude Code plugin runs it).
`--print-index` dumps the resolved index as JSON (smoke test + escape
hatch for non-MCP consumers).
"""

import argparse
import json
import logging
import sys
from pathlib import Path

try:  # MCP SDK v2 (mcp>=2.0): same decorator surface, new location/name
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:  # MCP SDK v1
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        # SDK absent: keep the CLI modes (--print-index, --version) alive —
        # they only need the stdlib index. Serving requires the real SDK.
        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, _name):
                pass

            def tool(self, *_a, **_k):
                return lambda fn: fn

            def resource(self, *_a, **_k):
                return lambda fn: fn

            def run(self, *_a, **_k):
                raise SystemExit(
                    "The mcp SDK is required to serve: pip install mcp"
                )

try:  # package mode (pip install / python -m)
    from .matching import tokenize, term_counts, score_terms, description_bonus
    from .context_index import load_index
except ImportError:  # direct-run mode (python3 server.py)
    from matching import tokenize, term_counts, score_terms, description_bonus
    from context_index import load_index

VERSION = "2.0.0"

# Suppress verbose MCP logging
logging.getLogger("mcp").setLevel(logging.ERROR)

# Optional compatibility hook for adopters of the v1 template: entries added
# here sit UNDER the front-matter index (front-matter wins on key collision).
EXTRA_SUBSYSTEMS: dict = {}
EXTRA_AGENTS: dict = {}

INDEX = load_index(extra_subsystems=EXTRA_SUBSYSTEMS, extra_agents=EXTRA_AGENTS)

# Create the FastMCP server
mcp = FastMCP("Context Retrieval")


# =============================================================================
# Retrieval tools
# =============================================================================

@mcp.tool()
def list_subsystems() -> dict:
    """
    List all architectural subsystems with brief descriptions.

    Returns:
        Dictionary of subsystem keys with name, description, and keywords
    """
    INDEX.refresh()
    return {
        key: {
            "name": info["name"],
            "description": info["description"],
            "keywords": info["keywords"],
        }
        for key, info in INDEX.subsystems.items()
    }


@mcp.tool()
def get_files_for_subsystem(subsystem: str) -> dict:
    """
    Get key file paths for a specific subsystem.

    Args:
        subsystem: Subsystem key (e.g., 'networking', 'save-system')

    Returns:
        Dictionary with subsystem info and project-root-relative file paths
    """
    INDEX.refresh()
    if subsystem not in INDEX.subsystems:
        return {
            "error": f"Unknown subsystem: {subsystem}",
            "available": list(INDEX.subsystems.keys()),
        }

    info = INDEX.subsystems[subsystem]
    return {
        "subsystem": subsystem,
        "name": info["name"],
        "description": info["description"],
        "files": info["files"],
        "related": info.get("related", []),
    }


@mcp.tool()
def find_relevant_context(task_description: str) -> dict:
    """
    Find relevant architecture sections and files for a given task.

    Args:
        task_description: Description of the task to find context for

    Returns:
        Dictionary with relevant subsystems and suggested files
    """
    INDEX.refresh()
    task_lower = task_description.lower()
    task_words = tokenize(task_description)

    # Keyword uniqueness across subsystems (same philosophy as suggest_agent)
    keyword_counts = term_counts(
        info["keywords"] for info in INDEX.subsystems.values()
    )

    matches = []
    for key, info in INDEX.subsystems.items():
        score, matched_keywords = score_terms(
            task_lower, task_words, info["keywords"], keyword_counts
        )
        if info["name"].lower() in task_lower:
            score += 2

        if score > 0:
            matches.append({
                "subsystem": key,
                "name": info["name"],
                "score": score,
                "matched_keywords": matched_keywords,
                "files": info["files"],
            })

    matches.sort(key=lambda x: x["score"], reverse=True)

    suggested_files = []
    for match in matches[:3]:
        for f in match["files"]:
            if f not in suggested_files:
                suggested_files.append(f)

    return {
        "task": task_description,
        "relevant_subsystems": matches[:5],
        "suggested_files": suggested_files[:10],
    }


@mcp.tool()
def get_context_files() -> dict:
    """
    List all available context documents in .claude/context/.

    Returns:
        Dictionary with context file names, descriptions, and metadata
    """
    INDEX.refresh()
    if not INDEX.context_dir.is_dir():
        return {
            "error": "Context directory not found",
            "expected": str(INDEX.context_dir),
        }

    files = []
    for key, info in INDEX.subsystems.items():
        files.append({
            "subsystem": key,
            "file": info["doc"],
            "description": info["description"],
            "priority": info["priority"],
            "last_verified": info["last_verified"],
            "resource_uri": f"context://{key}",
        })
    return {"count": len(files), "context_files": files}


@mcp.tool()
def search_context_documents(query: str) -> dict:
    """
    Full-text search across all context documents.

    Args:
        query: Text to search for (case-insensitive)

    Returns:
        Dictionary with matching documents and surrounding context lines
    """
    INDEX.refresh()
    query_lower = query.lower()
    results = []

    if INDEX.context_dir.is_dir():
        for doc in sorted(INDEX.context_dir.glob("*.md")):
            try:
                lines = doc.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue

            doc_matches = []
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    doc_matches.append({
                        "line_number": i + 1,
                        "context": "\n".join(lines[start:end]),
                    })
                    if len(doc_matches) >= 10:
                        break

            if doc_matches:
                results.append({
                    "file": f".claude/context/{doc.name}",
                    "match_count": len(doc_matches),
                    "matches": doc_matches,
                })

    # Also match subsystem names/descriptions/keywords
    subsystem_matches = [
        {"subsystem": key, "name": info["name"], "description": info["description"]}
        for key, info in INDEX.subsystems.items()
        if query_lower in info["name"].lower()
        or query_lower in info["description"].lower()
        or any(query_lower in k for k in info["keywords"])
    ]

    return {
        "query": query,
        "document_matches": results,
        "subsystem_matches": subsystem_matches,
    }


# =============================================================================
# Agent routing tools
# =============================================================================

@mcp.tool()
def suggest_agent(task_description: str) -> dict:
    """
    Suggest which specialized agent to invoke for a given task.

    Args:
        task_description: Description of the task you're about to perform

    Returns:
        Dictionary with recommended agent(s), matched triggers, and confidence
    """
    INDEX.refresh()
    task_lower = task_description.lower()
    task_words = tokenize(task_description)

    trigger_counts = term_counts(
        info["triggers"] for info in INDEX.agents.values()
    )

    matches = []
    for agent_id, info in INDEX.agents.items():
        score, matched_triggers = score_terms(
            task_lower, task_words, info["triggers"], trigger_counts
        )
        score += description_bonus(task_words, info["description"])

        if score > 0:
            matches.append({
                "agent": agent_id,
                "name": info["name"],
                "description": info["description"],
                "model": info["model"],
                "score": score,
                "matched_triggers": matched_triggers,
            })

    matches.sort(key=lambda x: x["score"], reverse=True)

    top_score = matches[0]["score"] if matches else 0
    confidence = (
        "high" if top_score >= 4
        else "medium" if top_score >= 2
        else "low" if top_score >= 1
        else "none"
    )

    result = {
        "task": task_description,
        "recommendation": matches[0]["agent"] if matches else None,
        "confidence": confidence,
        "suggested_agents": matches[:3],
        "should_invoke": confidence in ["high", "medium"],
    }

    if len(matches) >= 2 and matches[0]["score"] == matches[1]["score"]:
        tied = [m["agent"] for m in matches if m["score"] == matches[0]["score"]]
        result["disambiguation"] = (
            f"Tied between {', '.join(tied)}. "
            "Check which files you're modifying to decide."
        )

    return result


@mcp.tool()
def list_agents() -> dict:
    """
    List all available specialized agents with their descriptions.

    Returns:
        Dictionary of agent names, descriptions, models, and triggers
    """
    INDEX.refresh()
    return {
        agent_id: {
            "name": info["name"],
            "description": info["description"],
            "model": info["model"],
            "triggers": info["triggers"],
        }
        for agent_id, info in INDEX.agents.items()
    }


# =============================================================================
# Introspection
# =============================================================================

@mcp.tool()
def get_index_status() -> dict:
    """
    Report what the server indexed: resolved project root, doc/agent counts,
    and any parse warnings. Call this to debug an empty or surprising index
    (e.g. to check the server resolved YOUR project, not its own directory).

    Returns:
        Dictionary with paths, counts, and warnings
    """
    INDEX.refresh()
    return {"version": VERSION, **INDEX.status()}


# =============================================================================
# Resources
# =============================================================================

@mcp.resource("context://index")
def get_index_resource() -> str:
    """The full resolved index as JSON."""
    INDEX.refresh()
    return json.dumps(
        {"subsystems": INDEX.subsystems, "agents": INDEX.agents}, indent=2
    )


@mcp.resource("context://{subsystem}")
def get_subsystem_doc(subsystem: str) -> str:
    """Full context document for a subsystem."""
    INDEX.refresh()
    info = INDEX.subsystems.get(subsystem)
    if not info:
        return f"Unknown subsystem: {subsystem}. Available: {', '.join(INDEX.subsystems)}"
    doc_path = INDEX.project_root / info["doc"]
    try:
        return doc_path.read_text(encoding="utf-8")
    except OSError:
        return f"Context document not found: {info['doc']}"


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """CLI entry point: run the MCP server, or inspect the index."""
    parser = argparse.ArgumentParser(
        prog="context-retrieval-mcp",
        description="Context Retrieval MCP server (codified context infrastructure).",
    )
    parser.add_argument(
        "--print-index",
        action="store_true",
        help="Dump the resolved SUBSYSTEMS/AGENTS index as JSON and exit "
             "(smoke test and escape hatch for non-MCP consumers).",
    )
    parser.add_argument(
        "--project-root",
        help="Index this directory instead of auto-resolving "
             "(equivalent to $CONTEXT_MCP_PROJECT_ROOT).",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    args = parser.parse_args()

    global INDEX
    if args.project_root:
        INDEX = load_index(
            Path(args.project_root).resolve(),
            extra_subsystems=EXTRA_SUBSYSTEMS,
            extra_agents=EXTRA_AGENTS,
        )

    if args.version:
        print(VERSION)
        return
    if args.print_index:
        try:
            json.dump(
                {
                    "version": VERSION,
                    **INDEX.status(),
                    "subsystems": INDEX.subsystems,
                    "agents": INDEX.agents,
                },
                sys.stdout,
                indent=2,
            )
            print()
        except BrokenPipeError:  # e.g. piped into `head`
            sys.stderr.close()
        return

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
