import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATE = REPO_ROOT / "scripts" / "validate_architecture.py"


def _run_validate(project, *args):
    return subprocess.run(
        [sys.executable, str(VALIDATE), "--project-root", str(project), *args],
        capture_output=True, text=True, timeout=60,
    )


def test_fixture_validates_with_warnings_but_no_errors(fixture_project):
    out = _run_validate(fixture_project)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "ERROR" not in out.stdout
    assert "warning:" in out.stdout          # broken.md / notes.md / ui-legacy.md
    assert "0 error(s)" in out.stdout


def test_missing_file_and_bad_related_are_errors(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    (project / ".claude/context/bad.md").write_text(
        "---\nsubsystem: bad\ndescription: broken refs\nkeywords: [bad]\n"
        "files:\n  - src/does_not_exist.py\nrelated: [ghost-subsystem]\n---\n# Bad\n"
    )
    out = _run_validate(project)
    assert out.returncode == 1
    assert "does not exist" in out.stdout
    assert "ghost-subsystem" in out.stdout


def test_non_bidirectional_related_is_warning(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    doc = project / ".claude/context/networking.md"
    doc.write_text(doc.read_text().replace("related: [save-system]", "related: []"))
    out = _run_validate(project)
    assert out.returncode == 0
    assert "not bidirectional" in out.stdout
    # --strict promotes it
    assert _run_validate(project, "--strict").returncode == 1


def test_stale_generated_table_is_warning(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    (project / ".claude/context/extra.md").write_text(
        "---\nsubsystem: extra\ndescription: new subsystem\nkeywords: [extra]\n---\n# Extra\n"
    )
    out = _run_validate(project)
    assert "generated tables are stale" in out.stdout


def test_module_launch_modes(repo_root, fixture_project):
    env = {**os.environ, "PYTHONPATH": str(repo_root / "mcp-server")}
    out = subprocess.run(
        [sys.executable, "-m", "context_retrieval_mcp", "--version"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert out.returncode == 0 and out.stdout.strip(), out.stderr

    server = repo_root / "mcp-server" / "context_retrieval_mcp" / "server.py"
    out2 = subprocess.run(
        [sys.executable, str(server), "--project-root", str(fixture_project), "--print-index"],
        capture_output=True, text=True, timeout=30,
    )
    assert out2.returncode == 0, out2.stderr
    assert '"save-system"' in out2.stdout
