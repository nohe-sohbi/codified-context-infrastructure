"""Serve-path SDK bootstrap: the decision is pure, so it is tested as data.

A plugin install runs no dependency step — without this the server exits before
the JSON-RPC handshake and the client only ever sees an opaque -32000.
"""

import os
import subprocess
import sys
from pathlib import Path

from context_retrieval_mcp.server import (
    BOOTSTRAP_GUARD,
    NO_BOOTSTRAP,
    PYTHON_OVERRIDE,
    plan_serve,
    venv_python,
)

SERVER = Path(__file__).resolve().parent.parent / "mcp-server" / "context_retrieval_mcp" / "server.py"


def test_sdk_present_serves_in_place():
    assert plan_serve(True, {}) == ("serve", None)


def test_sdk_present_ignores_every_override():
    env = {PYTHON_OVERRIDE: "/nope/python", NO_BOOTSTRAP: "1", BOOTSTRAP_GUARD: "1"}
    assert plan_serve(True, env) == ("serve", None)


def test_missing_sdk_bootstraps():
    assert plan_serve(False, {}) == ("bootstrap", None)


def test_override_wins_over_bootstrap():
    action, detail = plan_serve(False, {PYTHON_OVERRIDE: "/opt/venv/bin/python"})
    assert (action, detail) == ("reexec", "/opt/venv/bin/python")


def test_opt_out_fails_loudly_instead_of_provisioning():
    action, reason = plan_serve(False, {NO_BOOTSTRAP: "1"})
    assert action == "fail"
    assert NO_BOOTSTRAP in reason and PYTHON_OVERRIDE in reason


def test_guard_stops_the_reexec_loop():
    # Second pass without the SDK: hand-over failed, do not hand over again.
    action, reason = plan_serve(False, {BOOTSTRAP_GUARD: "1"})
    assert action == "fail"
    assert "after bootstrap" in reason


def test_guard_outranks_the_override():
    env = {BOOTSTRAP_GUARD: "1", PYTHON_OVERRIDE: "/opt/venv/bin/python"}
    assert plan_serve(False, env)[0] == "fail"


def test_venv_python_lands_in_the_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    python = venv_python()
    assert python.parent.parent == tmp_path / "codified-context-mcp" / "venv"
    assert python.name.startswith("python")


def test_cli_modes_never_bootstrap(fixture_project, tmp_path):
    """--print-index must stay stdlib-only: no SDK, no venv, exit 0."""
    nomcp = tmp_path / "nomcp"
    subprocess.run([sys.executable, "-m", "venv", str(nomcp)], check=True, capture_output=True)
    cache = tmp_path / "cache"
    out = subprocess.run(
        [str(venv_python(nomcp)), str(SERVER),
         "--print-index", "--project-root", str(fixture_project)],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "XDG_CACHE_HOME": str(cache)},
    )
    assert out.returncode == 0, out.stderr
    assert not cache.exists(), "CLI mode provisioned a venv it does not need"


def test_serving_without_sdk_and_without_bootstrap_is_explicit(tmp_path):
    """Opt-out path: fail with an actionable message, not a silent exit."""
    nomcp = tmp_path / "nomcp"
    subprocess.run([sys.executable, "-m", "venv", str(nomcp)], check=True, capture_output=True)
    out = subprocess.run(
        [str(venv_python(nomcp)), str(SERVER)],
        capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
        env={**os.environ, NO_BOOTSTRAP: "1", "XDG_CACHE_HOME": str(tmp_path / "cache")},
    )
    assert out.returncode != 0
    assert PYTHON_OVERRIDE in out.stderr
