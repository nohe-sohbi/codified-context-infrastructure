#!/usr/bin/env python3
"""Context drift advisor — Stop hook (fires when Claude finishes responding).

The cheapest moment to update a spec is the session that changed the code,
while the context is still hot. This hook reads the session transcript,
maps files edited this session to subsystems via the shared front-matter
index, and — if a subsystem's code changed without its context doc — injects
advisory feedback asking Claude to propose targeted spec deltas now.

Advisory by default (never blocks the stop). Set DRIFT_STOP_BLOCK=1 to turn
the advisory into a blocking exit-2 (use sparingly: a blocking Stop hook on
every session is how hooks get uninstalled).

Payload contract (stdin JSON): session_id, transcript_path, cwd,
stop_hook_active. Exits silently on stop_hook_active (loop guard), on
missing/unparseable payload, and when the same session was already notified
about the same subsystems.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from drift_common import (
    project_root, subsystem_patterns, flag_drift, load_state, save_state,
)

MAX_TRANSCRIPT_LINES = 5000
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def session_touched_files(transcript_path: str, root: Path):
    """(code_files, touched_doc_basenames) edited this session, project-relative."""
    code_files, touched_docs = set(), set()
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if line_num >= MAX_TRANSCRIPT_LINES:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                content = obj.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_use":
                        continue
                    if item.get("name") not in EDIT_TOOLS:
                        continue
                    file_path = item.get("input", {}).get("file_path") \
                        or item.get("input", {}).get("notebook_path")
                    if not file_path:
                        continue
                    try:
                        # as_posix(): forward slashes on every OS, matching
                        # the front-matter path convention
                        rel = Path(file_path).resolve().relative_to(root).as_posix()
                    except ValueError:
                        continue  # outside the project
                    if rel.startswith(".claude/context/") and rel.endswith(".md"):
                        touched_docs.add(os.path.basename(rel))
                    elif not rel.endswith(".md"):
                        code_files.add(rel)
    except (OSError, UnicodeDecodeError):
        pass
    return code_files, touched_docs


def build_message(drift: list) -> str:
    lines = ["Context drift in THIS session (code changed without its spec):"]
    for item in drift[:3]:
        code = ", ".join(os.path.basename(f) for f in item["code_files"][:2])
        docs = ", ".join(f".claude/context/{d}" for d in item["expected_docs"][:2])
        lines.append(
            f"- subsystem '{item['subsystem']}' (priority {item['priority'].upper()}): "
            f"touched {code} but not {docs}"
        )
    lines.append(
        "While the context is hot: propose targeted deltas to the affected "
        "spec(s) — update tables/flows that changed, bump `last-verified` — "
        "or state explicitly why no spec change is needed."
    )
    return "\n".join(lines)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return

    if payload.get("stop_hook_active"):
        return  # loop guard: we already injected feedback this turn

    try:
        cwd = payload.get("cwd")
        if cwd and Path(cwd).is_dir():
            os.chdir(cwd)
        root = project_root()
        if root is None:
            return

        transcript = payload.get("transcript_path")
        if not transcript or not Path(transcript).is_file():
            return

        patterns = subsystem_patterns(root)
        if not patterns:
            return

        code_files, touched_docs = session_touched_files(transcript, root)
        if not code_files:
            return

        drift = flag_drift(patterns, code_files, touched_docs)
        if not drift:
            return

        # Once per (session, subsystem set)
        session_id = str(payload.get("session_id", ""))
        flagged_keys = sorted(d["subsystem"] for d in drift)
        state = load_state(root)
        stop_state = state.get("stop_hook", {})
        if stop_state.get("session_id") == session_id and \
                stop_state.get("notified") == flagged_keys:
            return
        state["stop_hook"] = {"session_id": session_id, "notified": flagged_keys}
        save_state(root, state)

        message = build_message(drift)
        if os.environ.get("DRIFT_STOP_BLOCK") == "1":
            print(message, file=sys.stderr)
            sys.exit(2)  # block the stop; stderr is fed back to Claude
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": message,
            }
        }))
    except SystemExit:
        raise
    except Exception:
        # Advisory hook: never break a session on our own bugs
        pass


if __name__ == "__main__":
    main()
