"""Regression test for the LivePipeline camera-status bug: previously every
camera was written once as online=False at startup and never updated again,
so /api/v1/cameras and the dashboard showed every camera permanently
OFFLINE even while frames were flowing. _update_camera_status must reflect
the real VideoSource.is_connected() state.

Builds a LivePipeline instance without going through __init__ (which
constructs a real Ultralytics/OpenCV video source, needing heavy optional
deps) so this stays a fast, dependency-light unit test.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

TEST_DB = Path(f"data/test_live_pipeline_status_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from services.live_pipeline import LivePipeline  # noqa: E402
from storage.database import init_db  # noqa: E402
from storage import repositories  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    init_db()
    yield
    from storage.database import engine, reader_engine

    engine.dispose()
    reader_engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    for suffix in ("-wal", "-shm"):
        p = Path(str(TEST_DB) + suffix)
        if p.exists():
            p.unlink()


class _FakeVideoSource:
    def __init__(self, camera_id: str, connected: bool):
        self._camera_id = camera_id
        self._connected = connected

    def camera_id(self) -> str:
        return self._camera_id

    def is_connected(self) -> bool:
        return self._connected


def _bare_pipeline() -> LivePipeline:
    """A LivePipeline with the bookkeeping dicts initialized but no real
    runners/video sources - exactly what _update_camera_status needs."""
    pipeline = LivePipeline.__new__(LivePipeline)
    pipeline.zone_map = {"entry-cam": "entrance"}
    pipeline._last_online = {}
    pipeline._last_seen = {}
    pipeline._last_status_write = {}
    return pipeline


def test_connected_camera_is_marked_online_immediately():
    pipeline = _bare_pipeline()
    source = _FakeVideoSource("entry-cam", connected=True)

    pipeline._update_camera_status("entry-cam", source)

    camera = next(c for c in repositories.list_cameras() if c.id == "entry-cam")
    assert camera.online is True
    assert camera.last_seen is not None


def test_disconnected_camera_is_marked_offline_and_keeps_last_seen():
    pipeline = _bare_pipeline()
    source = _FakeVideoSource("entry-cam", connected=True)
    pipeline._update_camera_status("entry-cam", source)
    camera = next(c for c in repositories.list_cameras() if c.id == "entry-cam")
    seen_while_online = camera.last_seen

    # Camera drops - state change, so this must write immediately even
    # though STATUS_WRITE_INTERVAL_SECONDS hasn't elapsed.
    source_disconnected = _FakeVideoSource("entry-cam", connected=False)
    pipeline._update_camera_status("entry-cam", source_disconnected)

    camera = next(c for c in repositories.list_cameras() if c.id == "entry-cam")
    assert camera.online is False
    # last_seen reflects the last time it was actually connected, not None/now.
    assert camera.last_seen == seen_while_online


def test_unchanged_state_is_throttled():
    pipeline = _bare_pipeline()
    source = _FakeVideoSource("shelf-cam-1", connected=True)

    pipeline._update_camera_status("shelf-cam-1", source)
    first_write_time = pipeline._last_status_write["shelf-cam-1"]

    # Same state, called again immediately - should be throttled (no new
    # write timestamp) rather than hammering the DB every 50ms tick.
    pipeline._update_camera_status("shelf-cam-1", source)
    assert pipeline._last_status_write["shelf-cam-1"] == first_write_time
