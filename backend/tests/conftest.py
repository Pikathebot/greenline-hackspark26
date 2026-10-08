from __future__ import annotations

from pathlib import Path

import pytest

from greenline.events.bus import EventBus
from greenline.persistence.db import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()
