"""Shared index over the codified context infrastructure.

Single source of truth: each context document under `.claude/context/*.md`
declares its own metadata in YAML front-matter, and each agent under
`.claude/agents/**/*.md` declares its own front-matter. This module scans
those files and builds the SUBSYSTEMS/AGENTS index that the MCP server, the
drift hooks, the skills generator and the validators all share — no
hand-maintained dict anywhere.

STDLIB-ONLY by contract: session hooks import this module under a bare
python3, so it must never import `mcp` (or anything else non-stdlib).

Front-matter schema for context documents (all fields optional except that a
doc with no front-matter at all is only indexed if it carries the legacy
line-1 header `<!-- vN | last-verified: DATE -->`, and then with a warning):

    ---
    subsystem: save-system        # index key; defaults to the filename stem
    name: Save System             # defaults to the first H1
    description: Two-tier save architecture (disk + memory)
    keywords: [save, persistence, autosave]
    files:                        # project-root-relative; trailing "/" = dir
      - src/Services/SaveService.py
      - src/Services/Implementation/
    priority: high                # high | medium | low   (default: medium)
    related: [item-system]        # other subsystem keys
    version: 2
    last-verified: 2026-08-08
    ---

Agent front-matter: the four classic fields (name, description, tools,
model) plus an optional `triggers: [...]` list used for task routing.
"""

import os
import re
from pathlib import Path

PRIORITIES = ("high", "medium", "low")

_LEGACY_HEADER = re.compile(
    r"^<!--\s*v(?P<version>\d+)\s*\|\s*last-verified:\s*(?P<date>[0-9-]+)\s*-->"
)
_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


# =============================================================================
# Front-matter parsing (deliberately small YAML subset)
# =============================================================================

def _parse_scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.lstrip("-").isdigit():
        return int(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value

def _parse_inline_list(value: str) -> list:
    inner = value.strip()[1:-1]
    if not inner.strip():
        return []
    return [_parse_scalar(item) for item in inner.split(",")]


def parse_front_matter(text: str):
    """Parse leading YAML front-matter from a markdown document.

    Returns (meta, body, warnings). Supports: `key: scalar`, `key: [a, b]`,
    and block lists (`key:` followed by indented `- item` lines). Anything
    fancier is rejected with a warning rather than silently half-parsed.

    Fallback: a legacy line-1 header `<!-- vN | last-verified: DATE -->`
    yields {"version": N, "last-verified": DATE, "_legacy_header": True}.
    """
    warnings = []

    legacy = _LEGACY_HEADER.match(text)
    if legacy:
        meta = {
            "version": int(legacy.group("version")),
            "last-verified": legacy.group("date"),
            "_legacy_header": True,
        }
        body = text[legacy.end():].lstrip("\n")
        return meta, body, warnings

    if not text.startswith("---"):
        return {}, text, warnings

    end = text.find("\n---", 3)
    if end == -1:
        warnings.append("front-matter opened with '---' but never closed")
        return {}, text, warnings

    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")

    meta: dict = {}
    current_list_key = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Block-list item under the current key
        if line.lstrip().startswith("- "):
            if current_list_key is None:
                warnings.append(f"list item outside any key: {line.strip()!r}")
                continue
            meta[current_list_key].append(_parse_scalar(line.lstrip()[2:]))
            continue

        # `key:` or `key: value` at top level
        match = re.match(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)$", line)
        if not match or raw_line.startswith((" ", "\t")):
            warnings.append(f"unsupported front-matter line: {line.strip()!r}")
            current_list_key = None
            continue

        key, value = match.group("key"), match.group("value").strip()
        if not value:
            meta[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            meta[key] = _parse_inline_list(value)
            current_list_key = None
        else:
            meta[key] = _parse_scalar(value)
            current_list_key = None

    return meta, body, warnings


# =============================================================================
# Loaders
# =============================================================================

def _first_h1(body: str) -> str:
    match = _H1.search(body)
    return match.group(1).strip() if match else ""

def _as_str_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def load_subsystems(context_dir: Path):
    """Scan context docs into a {key: subsystem_dict} index.

    Docs with YAML front-matter index fully; docs with only the legacy
    header index minimally (warning); docs with neither are skipped
    (warning) so stray markdown never pollutes the index.
    """
    subsystems: dict = {}
    warnings: list = []
    if not context_dir.is_dir():
        return subsystems, warnings

    for doc in sorted(context_dir.glob("*.md")):
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError as exc:
            warnings.append(f"{doc.name}: unreadable ({exc})")
            continue

        meta, body, doc_warnings = parse_front_matter(text)
        warnings.extend(f"{doc.name}: {w}" for w in doc_warnings)

        if not meta:
            warnings.append(f"{doc.name}: no front-matter and no legacy header — skipped")
            continue
        if meta.get("_legacy_header"):
            warnings.append(f"{doc.name}: legacy header only — indexed without keywords/files")

        key = str(meta.get("subsystem") or doc.stem)
        if key in subsystems:
            warnings.append(f"{doc.name}: duplicate subsystem key {key!r} — kept first")
            continue

        priority = str(meta.get("priority", "medium")).lower()
        if priority not in PRIORITIES:
            warnings.append(f"{doc.name}: unknown priority {priority!r} — using 'medium'")
            priority = "medium"

        subsystems[key] = {
            "name": str(meta.get("name") or _first_h1(body) or doc.stem),
            "description": str(meta.get("description", "")),
            "keywords": [str(k).lower() for k in _as_str_list(meta.get("keywords"))],
            "files": _as_str_list(meta.get("files")) + [f".claude/context/{doc.name}"],
            "priority": priority,
            "related": _as_str_list(meta.get("related")),
            "doc": f".claude/context/{doc.name}",
            "version": meta.get("version"),
            "last_verified": str(meta.get("last-verified", "")) or None,
        }

    return subsystems, warnings


def load_agents(agents_dir: Path):
    """Scan agent specs (recursively — both flat `{name}.md` and legacy
    `{id}/AGENT.md` layouts) into a {name: agent_dict} index."""
    agents: dict = {}
    warnings: list = []
    if not agents_dir.is_dir():
        return agents, warnings

    for spec in sorted(agents_dir.rglob("*.md")):
        try:
            text = spec.read_text(encoding="utf-8")
        except OSError as exc:
            warnings.append(f"{spec.name}: unreadable ({exc})")
            continue

        meta, _body, doc_warnings = parse_front_matter(text)
        rel = spec.relative_to(agents_dir)
        warnings.extend(f"agents/{rel}: {w}" for w in doc_warnings)

        name = str(meta.get("name") or "")
        if not name:
            # Not an agent spec (README, notes...) — skip silently unless it
            # looks like one (has a description).
            if meta.get("description"):
                warnings.append(f"agents/{rel}: has description but no name — skipped")
            continue
        if name in agents:
            warnings.append(f"agents/{rel}: duplicate agent name {name!r} — kept first")
            continue

        agents[name] = {
            "name": name,
            "description": str(meta.get("description", "")),
            "model": str(meta.get("model", "inherit")),
            "triggers": [str(t).lower() for t in _as_str_list(meta.get("triggers"))],
            "path": f".claude/agents/{rel}",
        }

    return agents, warnings


# =============================================================================
# Project root resolution + live index
# =============================================================================

def resolve_project_root() -> Path:
    """Resolution chain (first hit wins):
    1. $CONTEXT_MCP_PROJECT_ROOT   (explicit override)
    2. $CLAUDE_PROJECT_DIR         (set by Claude Code for hooks)
    3. walk up from cwd to the first directory containing .git or .claude
    4. cwd
    """
    for env_var in ("CONTEXT_MCP_PROJECT_ROOT", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(env_var)
        if value and Path(value).is_dir():
            return Path(value).resolve()

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").is_dir():
            return candidate
    return cwd


class Index:
    """Live view over the project's context docs and agent specs.

    `refresh()` is cheap (one stat per indexed file) and is meant to be
    called at the top of every tool invocation: the MCP server is
    long-lived, and factory agents create docs mid-session.
    """

    def __init__(self, project_root: Path,
                 extra_subsystems: dict | None = None,
                 extra_agents: dict | None = None):
        self.project_root = Path(project_root)
        self.context_dir = self.project_root / ".claude" / "context"
        self.agents_dir = self.project_root / ".claude" / "agents"
        self._extra_subsystems = extra_subsystems or {}
        self._extra_agents = extra_agents or {}
        self.subsystems: dict = {}
        self.agents: dict = {}
        self.warnings: list = []
        self._snapshot = None
        self.refresh(force=True)

    def _scan_snapshot(self):
        entries = []
        for directory in (self.context_dir, self.agents_dir):
            if not directory.is_dir():
                entries.append((str(directory), None))
                continue
            for f in sorted(directory.rglob("*.md")):
                try:
                    entries.append((str(f), f.stat().st_mtime_ns))
                except OSError:
                    entries.append((str(f), None))
        return tuple(entries)

    def refresh(self, force: bool = False) -> bool:
        """Rebuild the index if any indexed file changed. Returns True if
        a rebuild happened."""
        snapshot = self._scan_snapshot()
        if not force and snapshot == self._snapshot:
            return False
        self._snapshot = snapshot

        subsystems, sub_warnings = load_subsystems(self.context_dir)
        agents, agent_warnings = load_agents(self.agents_dir)

        # Extra dicts (v1-template compat) sit underneath: front-matter wins.
        self.subsystems = {**self._extra_subsystems, **subsystems}
        self.agents = {**self._extra_agents, **agents}
        self.warnings = sub_warnings + agent_warnings
        return True

    def status(self) -> dict:
        return {
            "project_root": str(self.project_root),
            "context_dir": str(self.context_dir),
            "agents_dir": str(self.agents_dir),
            "subsystem_count": len(self.subsystems),
            "agent_count": len(self.agents),
            "warnings": self.warnings,
        }


def load_index(project_root: Path | None = None, **kwargs) -> Index:
    return Index(project_root or resolve_project_root(), **kwargs)
