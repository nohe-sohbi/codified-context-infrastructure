#!/usr/bin/env python3
"""Validate the codified context infrastructure of a project.

Cross-platform replacement for `case-study/scripts/validate-architecture.sh`
(frozen — see case-study/FROZEN.md), built on the same shared index the MCP
server and hooks use. Layout contract: `scripts/` must stay a sibling of
`mcp-server/`. Checks:

  ERRORS (exit 1):
    - a `files:` entry pointing to a nonexistent exact file
    - a `related:` entry naming an unknown subsystem
    - duplicate subsystem keys / duplicate agent names

  WARNINGS (exit 0):
    - front-matter parse issues (unsupported lines, unclosed fences)
    - docs skipped (no metadata) or indexed via the legacy header only
    - directory `files:` entries matching no file
    - non-bidirectional `related:` references
    - triggers shared by more than 3 agents (routing dilution)
    - stale generated constitution tables (if GENERATED markers exist)
    - stale generated ctx-* skills (if .claude/skills/ctx-* exist)

Usage:
    python3 scripts/validate_architecture.py [--project-root DIR] [--strict]

--strict promotes warnings to errors. Stdlib-only.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server"))
from context_retrieval_mcp.context_index import load_index  # noqa: E402
from context_retrieval_mcp.skills_gen import generate_skills, SKILL_PREFIX  # noqa: E402


def check_files(index, errors: list, warnings: list) -> None:
    root = index.project_root
    for key, info in index.subsystems.items():
        for f in info.get("files", []):
            if f.startswith(".claude/context/"):
                continue  # the doc itself, appended by the loader
            if f.endswith("/"):
                d = root / f
                if not d.is_dir() or not any(d.rglob("*")):
                    warnings.append(f"{key}: directory entry '{f}' matches no file")
            elif not (root / f).is_file():
                errors.append(f"{key}: file entry '{f}' does not exist")


def check_related(index, errors: list, warnings: list) -> None:
    for key, info in index.subsystems.items():
        for rel in info.get("related", []):
            target = index.subsystems.get(rel)
            if target is None:
                errors.append(f"{key}: related subsystem '{rel}' does not exist")
            elif key not in target.get("related", []):
                warnings.append(
                    f"{key} -> {rel}: cross-reference is not bidirectional "
                    f"(add '{key}' to {rel}'s related list)"
                )


def check_trigger_dilution(index, warnings: list, max_agents: int = 3) -> None:
    counts: dict = {}
    for name, info in index.agents.items():
        for t in info.get("triggers", []):
            counts.setdefault(t, []).append(name)
    for trigger, agents in sorted(counts.items()):
        if len(agents) > max_agents:
            warnings.append(
                f"trigger '{trigger}' is declared by {len(agents)} agents "
                f"({', '.join(sorted(agents))}) — routing signal diluted"
            )


def check_generated_tables(index, warnings: list) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_reference_table import render_subsystem_table, render_agent_table, splice
    except ImportError:
        return
    for candidate in ("AGENTS.md", "CLAUDE.md"):
        target = index.project_root / candidate
        if not target.is_file():
            continue
        original = target.read_text(encoding="utf-8")
        updated = original
        spliced_any = False
        for block, content in (
            ("subsystem-reference", render_subsystem_table(index)),
            ("agent-reference", render_agent_table(index)),
        ):
            updated, ok = splice(updated, block, content)
            spliced_any = spliced_any or ok
        if spliced_any and updated != original:
            warnings.append(f"{candidate}: generated tables are stale — run generate_reference_table.py")
        if spliced_any:
            return  # first constitution with markers wins


def check_generated_skills(index, warnings: list) -> None:
    skills_dir = index.project_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return
    if not any(d.name.startswith(SKILL_PREFIX) for d in skills_dir.iterdir() if d.is_dir()):
        return  # project doesn't use generated skills
    result = generate_skills(index, prune=True, check=True)
    for key in result["stale"]:
        warnings.append(f"generated skill stale/missing for '{key}' — run generate_skills.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors.")
    args = parser.parse_args()

    index = load_index(args.project_root.resolve() if args.project_root else None)

    errors: list = []
    warnings: list = []

    # Parse-level findings from the index itself
    for w in index.warnings:
        if "duplicate" in w:
            errors.append(w)
        else:
            warnings.append(w)

    check_files(index, errors, warnings)
    check_related(index, errors, warnings)
    check_trigger_dilution(index, warnings)
    check_generated_tables(index, warnings)
    check_generated_skills(index, warnings)

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"warning: {w}")
    print(
        f"\n{index.project_root}: {len(index.subsystems)} subsystems, "
        f"{len(index.agents)} agents — {len(errors)} error(s), {len(warnings)} warning(s)"
    )

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
