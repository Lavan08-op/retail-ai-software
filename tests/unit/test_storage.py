"""Storage layer tests. Run with: pytest tests/unit/test_storage.py -v

Uses a throwaway SQLite file per test run (via the RETAIL_AI_DB_PATH env var
set in conftest-less fashion here for simplicity) so tests never touch the
real dev database.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

TEST_DB = Path(f"data/test_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from storage.database import SessionReader, init_db  # noqa: E402
from storage.models import SystemEvent  # noqa: E402
from storage import repositories, writer  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    init_db()
    yield
    # Dispose engines first so SQLite file handles are released — on
    # Windows, deleting a file that's still open raises PermissionError.
    from storage.database import engine, reader_engine

    engine.dispose()
    reader_engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()
    for suffix in ("-wal", "-shm"):
        p = Path(str(TEST_DB) + suffix)
        if p.exists():
            p.unlink()


def test_camera_write_and_read():
    writer.upsert_camera("test-cam-1", "Test Camera", zone_id="zone-a", online=True, last_seen=datetime.now(timezone.utc))
    cams = repositories.list_cameras()
    assert any(c.id == "test-cam-1" for c in cams)


def test_queue_metric_write_and_read():
    writer.write_queue_metric("test-cam-1", "zone-a", queue_length=7, avg_wait_seconds=300)
    metrics = repositories.recent_queue_metrics()
    assert any(m.queue_length == 7 for m in metrics)


def test_entry_exit_counts():
    writer.write_entry_exit("test-cam-1", "zone-a", "in")
    writer.write_entry_exit("test-cam-1", "zone-a", "in")
    writer.write_entry_exit("test-cam-1", "zone-a", "out")
    counts = repositories.entry_exit_counts()
    assert counts["in"] >= 2
    assert counts["out"] >= 1


def test_event_and_alert_roundtrip():
    event_id = writer.write_event("QUEUE_THRESHOLD_EXCEEDED", "warning", "test alert")
    alert_id = writer.upsert_alert("QUEUE_THRESHOLD_EXCEEDED", "warning", "test alert")
    assert event_id.startswith("evt-")
    assert alert_id.startswith("alrt-")
    assert any(a.alert_id == alert_id for a in repositories.active_alerts())
    assert any(e.event_id == event_id for e in repositories.recent_events())


def test_reader_session_cannot_write():
    """This is the whole point of the single-writer design — enforced, not
    just documented. If this test ever fails, the concurrency model is
    broken."""
    with pytest.raises(Exception):
        with SessionReader() as session:
            session.add(SystemEvent(category="TEST", message="should be blocked"))
            session.commit()
