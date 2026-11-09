"""Shared pytest fixtures.

Every test runs fully offline against the placeholder image provider and a
temporary SQLite database, so no paid API or network access is required.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, storage  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    base = config.load_settings()
    return dataclasses.replace(
        base,
        database_path=tmp_path / "test.db",
        media_dir=tmp_path / "media",
        image_provider="placeholder",
        fallback_provider="placeholder",
        require_approval=True,
        auto_publish=False,
        fb_page_id="",
        fb_page_access_token="",
        dashboard_password="",
        phash_threshold=6,
        image_width=512,
        image_height=512,
    )


@pytest.fixture
def store(settings):
    return storage.Storage(settings.database_path, settings.media_dir)


@pytest.fixture
def fb_settings(settings):
    return dataclasses.replace(
        settings,
        fb_page_id="1234567890",
        fb_page_access_token="test-token",
    )
