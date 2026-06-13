import sqlite3
from pathlib import Path

import pytest

from pkb.config import Settings, get_settings


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """A fresh vault directory with the expected subdirs created."""
    (tmp_path / "wiki").mkdir()
    (tmp_path / "inbox").mkdir()
    return tmp_path


@pytest.fixture
def settings(vault: Path) -> Settings:
    return get_settings(vault)
