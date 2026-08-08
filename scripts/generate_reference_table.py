#!/usr/bin/env python3
"""Regenerate the constitution's reference tables from the shared index.

The constitution (AGENTS.md or CLAUDE.md) should contain marker blocks:

    <!-- BEGIN GENERATED: subsystem-reference -->
    ...replaced by this script...
    <!-- END GENERATED: subsystem-reference -->

    <!-- BEGIN GENERATED: agent-reference -->
    ...replaced by this script...
    <!-- END GENERATED: agent-reference -->

Usage:
    python3 scripts/generate_reference_table.py [--project-root DIR] [--target FILE] [--check]

--check exits 1 if the tables are stale instead of rewriting them (CI mode).
Stdlib-only. Layout contract: `scripts/` must stay a sibling of `mcp-server/`.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server"))
from context_retrieval_mcp.context_index import load_index  # noqa: E402


def render_subsystem_table(index) -> str:
    lines = [
        "| Key | Description | Doc | Priority |",
        "|-----|-------------|-----|----------|",
    ]
    for key, info in sorted(index.subsystems.items()):
        desc = info["description"] or info["name"]
        lines.append(f"| `{key}` | {desc} | `{info['doc']}` | {info['priority']} |")
    return "\n".join(lines)


def render_agent_table(index) -> str:
    lines = [
        "| Agent | Model | Primary Focus |",
        "|-------|-------|---------------|",
    ]
    for name, info in sorted(index.agents.items()):
        lines.append(f"| `{name}` | {info['model']} | {info['description']} |")
    return "\n".join(lines)


def splice(text: str, block_name: str, content: str):
    begin = f"<!-- BEGIN GENERATED: {block_name} -->"
    end = f"<!-- END GENERATED: {block_name} -->"
    start = text.find(begin)
    stop = text.find(end)
    if start == -1 or stop == -1 or stop < start:
        return text, False
    return text[: start + len(begin)] + "\n" + content + "\n" + text[stop:], True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument(
        "--target", type=Path, default=None,
        help="Constitution file (default: AGENTS.md, else CLAUDE.md, at project root)",
    )
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if tables are stale; write nothing.")
    args = parser.parse_args()

    index = load_index(args.project_root.resolve() if args.project_root else None)

    target = args.target
    if target is None:
        for candidate in ("AGENTS.md", "CLAUDE.md"):
            if (index.project_root / candidate).is_file():
                target = index.project_root / candidate
                break
    if target is None or not target.is_file():
        print("No AGENTS.md or CLAUDE.md found at project root "
              f"({index.project_root}); pass --target.", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8")
    updated = original
    spliced_any = False
    for block, content in (
        ("subsystem-reference", render_subsystem_table(index)),
        ("agent-reference", render_agent_table(index)),
    ):
        updated, ok = splice(updated, block, content)
        spliced_any = spliced_any or ok

    if not spliced_any:
        print(f"{target}: no GENERATED marker blocks found — nothing to do.",
              file=sys.stderr)
        return 2

    if updated == original:
        print(f"{target}: tables up to date.")
        return 0
    if args.check:
        print(f"{target}: tables are STALE — run generate_reference_table.py.",
              file=sys.stderr)
        return 1

    target.write_text(updated, encoding="utf-8")
    print(f"{target}: tables regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
