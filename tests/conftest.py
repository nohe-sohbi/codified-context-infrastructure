import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))
sys.path.insert(0, str(REPO_ROOT / "hooks"))

FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "demo-project"


@pytest.fixture
def fixture_project() -> Path:
    return FIXTURE_PROJECT


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
