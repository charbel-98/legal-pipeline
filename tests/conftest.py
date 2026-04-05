"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def html_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "html"


@pytest.fixture
def pdf_fixtures_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "pdf"
