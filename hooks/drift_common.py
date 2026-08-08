"""Shared plumbing for the drift hooks (stdlib-only, never raises).

Layout contract: this file lives in `hooks/` next to a sibling
`mcp-server/context_retrieval_mcp/` package — true both in the plugin
(`${CLAUDE_PLUGIN_ROOT}/hooks`) and when both directories are copied into a
project. The hooks import the shared index through that relative path, so
the subsystem index they use is exactly the one the MCP server serves.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR.parent / "mcp-server"))

try:
    from context_retrieval_mcp.context_index import load_subsystems  # noqa: E402
except Exception:  # pragma: no cover - missing sibling package
    load_subsystems = None

STATE_FILE = ".claude/.drift-state.json"


def project_root() -> Path | None:
    """$CLAUDE_PROJECT_DIR (set by Claude Code for hooks), else walk up from
    cwd to a .git/.claude marker. None if no marker is found."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").is_dir():
            return candidate
    return None


def subsystem_patterns(root: Path) -> list:
    """[{key, priority, code_patterns, docs}] from the shared index.
    `docs` are context-doc basenames; `code_patterns` are project-root-relative
    paths (trailing "/" = directory prefix)."""
    if load_subsystems is None:
        return []
    subsystems, _warnings = load_subsystems(root / ".claude" / "context")
    result = []
    for key, info in subsystems.items():
        code_patterns = []
        docs = set()
        for f in info.get("files", []):
            if f.startswith(".claude/context/") and f.endswith(".md"):
                docs.add(os.path.basename(f))
            else:
                code_patterns.append(f)
        if code_patterns and docs:
            result.append({
                "key": key,
                "priority": info.get("priority", "medium"),
                "code_patterns": code_patterns,
                "docs": docs,
            })
    return result


def match_code_file(path: str, code_patterns: list) -> bool:
    """Front-matter `files:` entries are project-root-relative by contract:
    exact match for files, prefix match for `dir/` entries. (No suffix
    matching — `vendor/src/x.py` must not satisfy pattern `src/x.py`.)"""
    for pattern in code_patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif path == pattern:
            return True
    return False


def flag_drift(patterns: list, code_files, touched_docs) -> list:
    """Subsystems whose code changed while none of their docs did.
    LOW priority is suppressed entirely."""
    flagged = []
    for sub in patterns:
        if sub["priority"] == "low":
            continue
        matched = sorted(f for f in code_files if match_code_file(f, sub["code_patterns"]))
        if not matched:
            continue
        if sub["docs"] & set(touched_docs):
            continue
        flagged.append({
            "subsystem": sub["key"],
            "priority": sub["priority"],
            "code_files": matched[:3],
            "expected_docs": sorted(sub["docs"])[:3],
        })
    # Deduplicate doc suggestions across subsystems (first wins)
    seen: set = set()
    deduped = []
    for item in flagged:
        fresh = [d for d in item["expected_docs"] if d not in seen]
        if fresh:
            seen.update(fresh)
            item["expected_docs"] = fresh
            deduped.append(item)
    return deduped


def load_state(root: Path) -> dict:
    try:
        return json.loads((root / STATE_FILE).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(root: Path, state: dict) -> None:
    try:
        path = root / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, path)  # atomic: SessionStart/Stop may race
    except OSError:
        pass
