#!/usr/bin/env python3
"""Generate `.claude/skills/ctx-*` adapters from context-doc front-matter.

Each indexed subsystem gets a thin skill whose `paths:` globs auto-load it
when the agent works on the subsystem's files (native replacement for
constitution trigger tables; the generated reference tables in the
constitution remain as human-readable summaries). Hand-written skills are
never touched. Layout contract: `scripts/` must stay a sibling of
`mcp-server/`.

Usage:
    python3 scripts/generate_skills.py [--project-root DIR] [--prune] [--check]

--prune  remove generated skills whose subsystem disappeared
--check  exit 1 if skills are stale/missing instead of writing (CI mode)
Stdlib-only.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server"))
from context_retrieval_mcp.context_index import load_index  # noqa: E402
from context_retrieval_mcp.skills_gen import generate_skills  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    index = load_index(args.project_root.resolve() if args.project_root else None)
    result = generate_skills(index, prune=args.prune, check=args.check)

    for warning in result["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    for bucket in ("written", "pruned", "stale"):
        for key in result[bucket]:
            print(f"{bucket}: {key}")
    print(
        f"{len(result['written'])} written, {len(result['up_to_date'])} up to date, "
        f"{len(result['stale'])} stale, {len(result['pruned'])} pruned, "
        f"{len(result['skipped'])} skipped"
    )

    if args.check and result["stale"]:
        print("skills are STALE — run generate_skills.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
