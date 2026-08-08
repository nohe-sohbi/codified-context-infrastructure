import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"


def _git(project, *args):
    subprocess.run(
        ["git", *args], cwd=project, check=True, capture_output=True,
        env={**os.environ,
             "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )


def _make_git_project(fixture_project, tmp_path) -> Path:
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "init")
    return project


def _run_check(project, *args):
    # DRIFT_MAX_COMMITS=1: keep the fixture's all-files init commit out of
    # the scan window (in real repos the window is 10 commits).
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project),
           "DRIFT_MAX_COMMITS": "1"}
    env.pop("DRIFT_PROJECT_NAME", None)
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / "drift_check.py"), *args],
        cwd=project, capture_output=True, text=True, env=env, timeout=30,
    )


def test_drift_check_full_cycle(fixture_project, tmp_path):
    project = _make_git_project(fixture_project, tmp_path)

    # Change code of the save-system subsystem without touching its doc
    (project / "src/services/save_service.py").write_text("def save(p):\n    return False\n")
    _git(project, "commit", "-aqm", "change save logic")

    out1 = _run_check(project)
    assert out1.returncode == 0
    assert "CONTEXT DRIFT" in out1.stdout
    assert "save-system" in out1.stdout and "save-system.md" in out1.stdout
    assert "HIGH" in out1.stdout  # priority from front-matter

    # Second run: still shown (2/2), third run: auto-dismissed
    out2 = _run_check(project)
    assert "CONTEXT DRIFT" in out2.stdout
    out3 = _run_check(project)
    assert "CONTEXT DRIFT" not in out3.stdout

    # New commit resets the counter
    (project / "src/services/save_service.py").write_text("def save(p):\n    return None\n")
    _git(project, "commit", "-aqm", "change again")
    out4 = _run_check(project)
    assert "CONTEXT DRIFT" in out4.stdout

    # Updating the doc silences the warning and clears state
    doc = project / ".claude/context/save-system.md"
    doc.write_text(doc.read_text() + "\nUpdated.\n")
    _git(project, "commit", "-aqm", "update spec")
    out5 = _run_check(project)
    assert "CONTEXT DRIFT" not in out5.stdout


def test_drift_check_dismiss_flag(fixture_project, tmp_path):
    project = _make_git_project(fixture_project, tmp_path)
    (project / "src/network/sync.py").write_text("def send_snapshot(s):\n    return None\n")
    _git(project, "commit", "-aqm", "change networking")

    out = _run_check(project, "--dismiss")
    assert "dismissed" in out.stdout
    assert "CONTEXT DRIFT" not in _run_check(project).stdout


def _make_transcript(tmp_path, project, edited_file) -> Path:
    transcript = tmp_path / "transcript.jsonl"
    event = {
        "type": "assistant",
        "message": {"content": [{
            "type": "tool_use", "name": "Edit",
            "input": {"file_path": str(project / edited_file)},
        }]},
    }
    transcript.write_text(json.dumps(event) + "\n")
    return transcript


def _run_stop(project, payload, extra_env=None):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / "drift_stop.py")],
        input=json.dumps(payload), cwd=project,
        capture_output=True, text=True, env=env, timeout=30,
    )


def test_stop_hook_advisory_and_once_per_session(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    transcript = _make_transcript(tmp_path, project, "src/network/sync.py")
    payload = {
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(project),
        "stop_hook_active": False,
    }

    out = _run_stop(project, payload)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    ctx = data["hookSpecificOutput"]["additionalContext"]
    assert data["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "networking" in ctx and "networking.md" in ctx

    # Same session, same drift -> silent
    out2 = _run_stop(project, payload)
    assert out2.stdout.strip() == ""


def test_stop_hook_loop_guard_and_doc_updated(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)

    # stop_hook_active -> always silent
    transcript = _make_transcript(tmp_path, project, "src/network/sync.py")
    out = _run_stop(project, {
        "session_id": "s2", "transcript_path": str(transcript),
        "cwd": str(project), "stop_hook_active": True,
    })
    assert out.stdout.strip() == "" and out.returncode == 0

    # Doc edited in the same session -> no drift
    both = tmp_path / "both.jsonl"
    events = [
        {"type": "assistant", "message": {"content": [{
            "type": "tool_use", "name": "Edit",
            "input": {"file_path": str(project / "src/network/sync.py")}}]}},
        {"type": "assistant", "message": {"content": [{
            "type": "tool_use", "name": "Write",
            "input": {"file_path": str(project / ".claude/context/networking.md")}}]}},
    ]
    both.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    out2 = _run_stop(project, {
        "session_id": "s3", "transcript_path": str(both),
        "cwd": str(project), "stop_hook_active": False,
    })
    assert out2.stdout.strip() == ""


def test_stop_hook_blocking_mode(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    transcript = _make_transcript(tmp_path, project, "src/services/save_service.py")
    out = _run_stop(project, {
        "session_id": "s4", "transcript_path": str(transcript),
        "cwd": str(project), "stop_hook_active": False,
    }, extra_env={"DRIFT_STOP_BLOCK": "1"})
    assert out.returncode == 2
    assert "save-system" in out.stderr
