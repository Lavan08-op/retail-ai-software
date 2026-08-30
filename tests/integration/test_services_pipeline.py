"""Proves Phase 3 ties everything together: PipelineRunner (mock video,
mock inference, mock tracker) driving a real AnalyticsService, which
writes real occupancy data into real SQLite — plus a direct test that
process_queue_reading correctly produces a persisted alert when the queue
crosses threshold, with cooldown respected.
"""

import os
import sys
import uuid
from pathlib import Path

TEST_DB = Path(f"data/test_pipeline_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from adapters.inference.mock_inference_engine import MockInferenceEngine  # noqa: E402
from adapters.tracking.mock_tracker import MockTracker  # noqa: E402
from adapters.video.mock_video_source import MockVideoSource  # noqa: E402
from pipeline.runner import PipelineRunner  # noqa: E402
from services.analytics_service import AnalyticsService  # noqa: E402
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


def test_pipeline_runner_drives_real_service_into_real_storage():
    runner = PipelineRunner(
        video_source=MockVideoSource("entry-cam"),
        inference_engine=MockInferenceEngine(min_people=2, max_people=2, seed=5),
        tracker=MockTracker(),
        analytics_service=AnalyticsService(),
    )

    runner.run_n(4)

    occupancy = repositories.recent_occupancy()
    assert len(occupancy) == 4
    assert all(o.current_count == 2 for o in occupancy)


def test_queue_reading_over_threshold_creates_alert_with_cooldown():
    service = AnalyticsService(queue_warning=5, queue_critical=8)

    # First over-threshold reading -> should create an alert
    service.process_queue_reading("queue-cam-1", "checkout-1", queue_length=6)
    alerts_after_first = repositories.active_alerts()
    assert any(a.camera_id == "queue-cam-1" for a in alerts_after_first)

    # Immediately repeating it should be suppressed by cooldown -> no NEW
    # alert (count shouldn't grow for this camera)
    count_before = len(repositories.active_alerts())
    service.process_queue_reading("queue-cam-1", "checkout-1", queue_length=6)
    count_after = len(repositories.active_alerts())
    assert count_after == count_before

    # Queue metric itself should still be recorded every time regardless
    metrics = repositories.recent_queue_metrics()
    assert len(metrics) >= 2
