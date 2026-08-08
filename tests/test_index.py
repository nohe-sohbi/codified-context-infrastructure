import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from context_retrieval_mcp.context_index import Index, load_subsystems, load_agents, resolve_project_root


def test_fixture_scan(fixture_project):
    subsystems, warnings = load_subsystems(fixture_project / ".claude" / "context")
    assert set(subsystems) == {"save-system", "networking", "ui-legacy", "broken-doc"}

    save = subsystems["save-system"]
    assert save["priority"] == "high"
    assert save["files"][-1] == ".claude/context/save-system.md"
    assert save["related"] == ["networking"]

    # Legacy-header doc: indexed minimally, name from H1
    legacy = subsystems["ui-legacy"]
    assert legacy["name"] == "UI Legacy Doc"
    assert legacy["keywords"] == []

    joined = "\n".join(warnings)
    assert "notes.md" in joined and "skipped" in joined
    assert "ui-legacy.md" in joined and "legacy header" in joined
    assert "broken.md" in joined


def test_agent_scan_flat_and_nested(fixture_project):
    agents, _ = load_agents(fixture_project / ".claude" / "agents")
    assert set(agents) == {"code-reviewer", "legacy-agent"}
    assert "code quality" in agents["code-reviewer"]["triggers"]
    assert agents["legacy-agent"]["path"].endswith("legacy-agent/AGENT.md")


def test_mtime_lazy_reload(fixture_project, tmp_path):
    # Work on a copy so the shipped fixture stays pristine
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    index = Index(project)
    assert "hotload" not in index.subsystems

    (project / ".claude" / "context" / "hotload.md").write_text(
        "---\nsubsystem: hotload\ndescription: runtime doc\nkeywords: [hotload]\n---\n# Hot\n"
    )
    assert index.refresh() is True
    assert "hotload" in index.subsystems

    # No change -> no rebuild
    assert index.refresh() is False

    (project / ".claude" / "context" / "hotload.md").unlink()
    assert index.refresh() is True
    assert "hotload" not in index.subsystems


def test_hostile_docs_warn_but_never_crash(fixture_project, tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(fixture_project, project)
    ctx = project / ".claude" / "context"
    # Non-UTF8 doc
    (ctx / "latin1.md").write_bytes(b"---\nsubsystem: latin\n---\n# Caf\xe9\n")
    # Unicode "digit" scalar that would crash int()
    (ctx / "unicode.md").write_text(
        "---\nsubsystem: unicode-doc\ndescription: ok\nversion: ²\n---\n# U\n"
    )
    index = Index(project)  # must not raise
    assert "unicode-doc" in index.subsystems
    joined = "\n".join(index.warnings)
    assert "latin1.md" in joined and "unreadable" in joined


def test_extra_dicts_normalized_missing_keys(fixture_project):
    # v1-compat extras with missing keys must not KeyError any consumer
    index = Index(fixture_project, extra_subsystems={"bare": {}},
                  extra_agents={"bare-agent": {"description": "only desc"}})
    sub = index.subsystems["bare"]
    assert sub["keywords"] == [] and sub["files"] == [] and sub["priority"] == "medium"
    agent = index.agents["bare-agent"]
    assert agent["triggers"] == [] and agent["model"] == "inherit"


def test_extra_dicts_sit_under_front_matter(fixture_project):
    extra = {
        "save-system": {"name": "OVERRIDDEN", "description": "", "keywords": [],
                        "files": [], "priority": "low", "related": [],
                        "doc": "", "version": None, "last_verified": None},
        "v1-only": {"name": "V1 Only", "description": "from EXTRA dict",
                    "keywords": ["v1"], "files": [], "priority": "medium",
                    "related": [], "doc": "", "version": None, "last_verified": None},
    }
    index = Index(fixture_project, extra_subsystems=extra)
    # front-matter wins on collision, extras still present
    assert index.subsystems["save-system"]["name"] == "Save System"
    assert index.subsystems["v1-only"]["description"] == "from EXTRA dict"


def test_resolve_project_root_env_override(fixture_project, monkeypatch):
    monkeypatch.setenv("CONTEXT_MCP_PROJECT_ROOT", str(fixture_project))
    assert resolve_project_root() == fixture_project.resolve()


def test_resolve_project_root_walks_up_to_marker(tmp_path, monkeypatch):
    monkeypatch.delenv("CONTEXT_MCP_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert resolve_project_root() == root.resolve()


def test_stdlib_only_import_without_mcp(repo_root):
    """context_index and matching must import under a bare python3 even when
    the mcp SDK is not installed (hooks contract)."""
    code = (
        "import sys; sys.modules['mcp'] = None\n"  # simulate absent SDK harder below
        "del sys.modules['mcp']\n"
        "import builtins\n"
        "real_import = builtins.__import__\n"
        "def guard(name, *a, **k):\n"
        "    if name == 'mcp' or name.startswith('mcp.'):\n"
        "        raise ModuleNotFoundError(name)\n"
        "    return real_import(name, *a, **k)\n"
        "builtins.__import__ = guard\n"
        "import context_retrieval_mcp.context_index\n"
        "import context_retrieval_mcp.matching\n"
        "print('ok')\n"
    )
    env = dict(os.environ, PYTHONPATH=str(repo_root / "mcp-server"))
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
