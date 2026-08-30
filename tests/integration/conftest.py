"""Shared fixture for every integration test in this directory.

ROOT CAUSE of the bug this fixes: storage/database.py resolves
RETAIL_AI_DB_PATH from the environment at MODULE IMPORT TIME
(`DB_PATH = Path(os.environ.get("RETAIL_AI_DB_PATH", ...))`, a top-level
constant). Python only imports a module once per process, so whichever
integration test file pytest happens to import FIRST in a given session
is the only one whose `os.environ["RETAIL_AI_DB_PATH"] = ...` line has
any real effect — every other test file's env var assignment is silently
ignored, and all integration tests in the run end up sharing one single
physical SQLite file/engine, regardless of each file's own TEST_DB
naming. This was already true before this fixture existed; it just never
surfaced as a visible failure until enough occupancy-writing tests
existed in the same session for the accumulated row count to diverge
from what an individual test expected.

The correct, low-risk fix is not to change storage/database.py's binding
behavior (that file's engine/WAL/read-only design is foundational and
already proven — not worth the risk of touching for this) but to
guarantee every table starts EMPTY before each test FUNCTION runs, no
matter which physical file is actually in play. That's what this
autouse fixture does. Individual test files' own module-scoped
init_db()/teardown fixtures are still harmless and can stay as-is.
"""

from __future__ import annotations

import pytest

from storage.database import SessionWriter, engine
from storage.models import Base


@pytest.fixture(autouse=True)
def _clean_tables():
    Base.metadata.create_all(engine)
    with SessionWriter() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    yield
