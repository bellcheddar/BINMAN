"""Shared fixtures. Nothing here touches the network."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def config():
    from pipeline.common import load_config

    return load_config()


@pytest.fixture(scope="session")
def atlas_path() -> Path:
    return ROOT / "data" / "atlas" / "binman.sqlite"


@pytest.fixture
def atlas(atlas_path):
    if not atlas_path.exists():
        pytest.skip("atlas not built")
    connection = sqlite3.connect(f"file:{atlas_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()
