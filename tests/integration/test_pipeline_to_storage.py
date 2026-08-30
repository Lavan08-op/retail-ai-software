"""Proves the full chain works together, not just each piece in isolation:
mock video -> mock inference -> mock tracker -> PeopleCounter -> SQLite,
then read back through repositories.py. This is the first real proof that
Phase 1 (storage) and Phase 2 (adapters + analytics) actually fit together.
"""

import os
import sys
import uuid
from pathlib import Path

TEST_DB = Path(f"data/test_integration_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from adapters.inference.mock_inference_engine import MockInferenceEngine  # noqa: E402
from adapters.tracking.mock_tracker import MockTracker  # noqa: E402
from adapters.video.mock_video_source import MockVideoSource  # noqa: E402
from analytics.people_counter import PeopleCounter  # noqa: E402
from storage.database import init_db  # noqa: E402
from storage import repositories, writer  # noqa: E402


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


def test_full_pipeline_mock_video_to_real_storage():
    source = MockVideoSource("entry-cam")
    engine = MockInferenceEngine(min_people=3, max_people=3, seed=99)
    tracker = MockTracker()
    counter = PeopleCounter()

    # Simulate a few "frames" of the pipeline running
    for _ in range(3):
        frame = source.get_frame()
        detections = engine.infer(frame)
        tracks = tracker.update(detections)
        results = counter.update(tracks)

        # This is the boundary storage/writer.py owns: analytics results
        # get persisted here, exactly like the real analytics engine would.
        for result in results:
            if result.metric_name == "people_count_camera":
                writer.write_occupancy(zone_id=result.camera_id, current_count=int(result.value))

    occupancy = repositories.recent_occupancy()
    assert len(occupancy) == 3
    assert all(o.current_count == 3 for o in occupancy)
