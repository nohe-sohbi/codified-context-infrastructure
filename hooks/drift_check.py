#!/usr/bin/env python3
"""Context drift detection — SessionStart hook (project-agnostic).

Compares recent git commits against the shared front-matter index: when a
subsystem's code changed without its context doc, a prioritized warning is
printed to stdout (which Claude Code injects into session context). Also
flags debugging-heavy previous sessions as a codify-the-lessons signal.

Replaces the case-study script (`case-study/scripts/context-drift-check.py`,
frozen — see case-study/FROZEN.md) that parsed a SUBSYSTEMS dict out of
server.py via AST and hardcoded the project's paths — here everything comes
from `.claude/context/*.md` front-matter (`files:`, `priority:`).

Environment overrides:
    DRIFT_MAX_COMMITS    how many commits to scan (default 10)
    DRIFT_BUILD_CMDS     comma-separated substrings counting as build/test
                         commands for the debug-session heuristic
    DRIFT_PROJECT_NAME   substring to locate Claude session logs for this
                         project under ~/.claude/projects (default: derived
                         from the project path)

Usage:
    python3 hooks/drift_check.py             # normal (SessionStart) run
    python3 hooks/drift_check.py --dismiss   # silence current warnings
Output: empty = no warnings (silent). Never blocks session start.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from drift_common import (
    project_root, subsystem_patterns, flag_drift, load_state, save_state,
)

try:
    MAX_COMMITS = int(os.environ.get("DRIFT_MAX_COMMITS", "10"))
except ValueError:  # garbage env var must not break session start
    MAX_COMMITS = 10
MAX_SESSIONS = 3
MAX_LINES_PER_SESSION = 5000
DEBUG_SCORE_THRESHOLD = 50
DISMISS_MAX_SHOWS = 2

DEBUG_KEYWORDS = [
    "fix", "bug", "wrong", "broken", "doesn't work", "not working",
    "still not", "why does", "why is", "issue", "crash", "exception",
    "error", "null ref",
]

DEFAULT_BUILD_CMDS = [
    "dotnet build", "dotnet run", "npm run", "npm test", "yarn", "pnpm",
    "cargo build", "cargo test", "go build", "go test", "make", "pytest",
    "mvn", "gradle",
]


def build_cmds() -> list:
    env = os.environ.get("DRIFT_BUILD_CMDS")
    return [c.strip() for c in env.split(",") if c.strip()] if env else DEFAULT_BUILD_CMDS


def git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, cwd=root,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def recent_commit_files(root: Path):
    """(code_files, touched_doc_basenames) across the last MAX_COMMITS."""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={MAX_COMMITS}", "--name-only", "--format="],
            capture_output=True, text=True, timeout=3, cwd=root,
        )
        if result.returncode != 0:
            return set(), set()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return set(), set()

    code_files, touched_docs = set(), set()
    for line in result.stdout.splitlines():
        f = line.strip()
        if not f:
            continue
        if f.startswith(".claude/context/") and f.endswith(".md"):
            touched_docs.add(os.path.basename(f))
        elif not f.endswith(".md"):
            code_files.add(f)

    # Uncommitted docs (new or modified) count as touched: a doc created or
    # refreshed this session is fresh content even before it lands in a
    # commit — otherwise a just-backfilled project fires pure false positives
    # until the docs are committed.
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all",
             "--", ".claude/context"],
            capture_output=True, text=True, timeout=3, cwd=root,
        )
        if status.returncode == 0:
            for line in status.stdout.splitlines():
                path = line[3:].split(" -> ")[-1].strip().strip('"')
                if path.endswith(".md"):
                    touched_docs.add(os.path.basename(path))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return code_files, touched_docs


# ---------------------------------------------------------------------------
# Debug-heavy session detection (~/.claude/projects session logs)
# ---------------------------------------------------------------------------

def find_project_log_dirs(root: Path) -> list:
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.is_dir():
        return []
    override = os.environ.get("DRIFT_PROJECT_NAME")
    if override:  # user-supplied needle: substring match
        return [d for d in claude_projects.iterdir()
                if d.is_dir() and override in d.name]
    # Derived from the project path: exact match only, so /home/u/proj never
    # picks up /home/u/proj-other's session logs
    derived = str(root).replace("/", "-").replace("\\", "-")
    return [d for d in claude_projects.iterdir()
            if d.is_dir() and d.name == derived]


def analyze_last_sessions(log_dirs: list) -> dict | None:
    file_mtimes = []
    for d in log_dirs:
        for f in d.glob("*.jsonl"):
            if f.name.startswith("agent-"):
                continue
            try:
                st = f.stat()
            except OSError:
                continue
            if st.st_size < 1024:
                continue
            file_mtimes.append((f, st.st_mtime))
    file_mtimes.sort(key=lambda x: x[1], reverse=True)

    # Skip the newest file if it is likely the current session
    if file_mtimes and (time.time() - file_mtimes[0][1]) < 60:
        file_mtimes = file_mtimes[1:]

    best = None
    for session_file, _mtime in file_mtimes[:MAX_SESSIONS]:
        info = _analyze_single_session(session_file)
        if info and (best is None or info["score"] > best["score"]):
            best = info
    return best


def _analyze_single_session(filepath: Path) -> dict | None:
    edit_count = build_count = debug_prompts = edit_build_cycles = 0
    recent_tools: list = []
    cmds = build_cmds()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if line_num >= MAX_LINES_PER_SESSION:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")
                if msg_type == "user":
                    content = obj.get("message", {}).get("content", [])
                    text = ""
                    if isinstance(content, str):
                        text = content.lower()
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = item.get("text", "")
                                if not t.startswith("<ide_") and not t.startswith("<system"):
                                    text = t.lower()
                                    break
                    if text and any(kw in text for kw in DEBUG_KEYWORDS):
                        debug_prompts += 1

                elif msg_type == "assistant":
                    content = obj.get("message", {}).get("content", [])
                    if not isinstance(content, list):
                        continue
                    for item in content:
                        if not isinstance(item, dict) or item.get("type") != "tool_use":
                            continue
                        name = item.get("name", "")
                        if name in ("Edit", "Write"):
                            edit_count += 1
                            recent_tools.append("edit")
                        elif name == "Bash":
                            cmd = item.get("input", {}).get("command", "")
                            if any(c in cmd for c in cmds):
                                build_count += 1
                                if "edit" in recent_tools[-5:]:
                                    edit_build_cycles += 1
                                recent_tools.append("build")
                            else:
                                recent_tools.append("other")
                        else:
                            recent_tools.append("other")
    except (OSError, UnicodeDecodeError):
        return None

    score = min(100,
                (edit_build_cycles * 10) +
                (debug_prompts * 5) +
                (30 if build_count > 5 else 0))
    return {
        "score": score,
        "edit_build_cycles": edit_build_cycles,
        "debug_prompts": debug_prompts,
        "build_count": build_count,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_output(drift: list, session_info: dict | None, times_shown: int) -> str:
    parts = []
    if drift:
        remaining = max(0, DISMISS_MAX_SHOWS - times_shown)
        note = f"(showing {times_shown}/{DISMISS_MAX_SHOWS} — auto-dismisses after {remaining} more)"
        for tier, label, verb in (
            ("high", "HIGH — auto-update recommended", "update"),
            ("medium", "MEDIUM — mention to user", "consider"),
        ):
            items = [d for d in drift if d["priority"] == tier]
            if not items:
                continue
            lines = [f"CONTEXT DRIFT [{label}] {note}:"]
            for item in items[:3]:
                code = ", ".join(os.path.basename(f) for f in item["code_files"][:2])
                docs = ", ".join(item["expected_docs"][:3])
                lines.append(f"  - {item['subsystem']} ({code}) -> {verb}: {docs}")
            parts.append("\n".join(lines))

    if session_info and session_info["score"] >= DEBUG_SCORE_THRESHOLD:
        s = session_info
        parts.append(
            f"DEBUGGING SESSION: Last session was debugging-heavy "
            f"({s['edit_build_cycles']} edit-build cycles, "
            f"{s['debug_prompts']} debug prompts, score {s['score']}/100). "
            f"If bugs revealed gaps in documentation, consider updating "
            f"relevant context docs or agent specs with lessons learned."
        )
    return "\n\n".join(parts)


def main():
    try:
        root = project_root()
        if root is None:
            return

        if "--dismiss" in sys.argv:
            head = git_head(root)
            if head:
                state = load_state(root)
                state.update({"head_sha": head, "times_shown": DISMISS_MAX_SHOWS})
                save_state(root, state)
                print(f"Drift warnings dismissed at {head[:8]}.")
            return

        patterns = subsystem_patterns(root)
        drift = []
        if patterns:
            code_files, touched_docs = recent_commit_files(root)
            drift = flag_drift(patterns, code_files, touched_docs)

        # Auto-dismiss: warn at most DISMISS_MAX_SHOWS times per HEAD
        head = git_head(root)
        state = load_state(root)
        times_shown = 0
        if drift and head:
            if state.get("head_sha") == head:
                times_shown = state.get("times_shown", 0)
                if times_shown >= DISMISS_MAX_SHOWS:
                    drift = []
                else:
                    times_shown += 1
                    state.update({"head_sha": head, "times_shown": times_shown})
                    save_state(root, state)
            else:
                times_shown = 1
                state.update({"head_sha": head, "times_shown": 1})
                save_state(root, state)
        elif not drift and state.get("head_sha"):
            state.pop("head_sha", None)
            state.pop("times_shown", None)
            save_state(root, state)

        session_info = analyze_last_sessions(find_project_log_dirs(root))

        output = format_output(drift, session_info, times_shown)
        if output:
            print(output)
    except Exception:
        # Never block session start
        pass


if __name__ == "__main__":
    main()
