"""Proves the zone-assignment gap flagged after Phase 4 is actually closed:
wiring PipelineRunner with config.loader.load_camera_zone_map() makes
Track.zone_id get populated, which lights up the zone-based analytics
modules (queue_monitor here) that stayed silent on plain mock data.
"""

import os
import sys
import uuid
from pathlib import Path

TEST_DB = Path(f"data/test_zones_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from adapters.inference.mock_inference_engine import MockInferenceEngine  # noqa: E402
from adapters.tracking.mock_tracker import MockTracker  # noqa: E402
from adapters.video.mock_video_source import MockVideoSource  # noqa: E402
from config.loader import load_camera_zone_map  # noqa: E402
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


def test_zone_mapped_pipeline_produces_queue_metrics():
    zone_map = load_camera_zone_map()
    assert zone_map["queue-cam-1"] == "checkout-1"  # sanity-check config didn't drift

    runner = PipelineRunner(
        video_source=MockVideoSource("queue-cam-1"),
        inference_engine=MockInferenceEngine(min_people=2, max_people=2, seed=7),
        tracker=MockTracker(),
        analytics_service=AnalyticsService(queue_zone_ids=["checkout-1", "checkout-2"]),
        camera_zone_map=zone_map,
    )

    runner.run_n(3)

    metrics = repositories.recent_queue_metrics()
    checkout_metrics = [m for m in metrics if m.zone_id == "checkout-1"]
    assert len(checkout_metrics) >= 1
    assert all(m.queue_length == 2 for m in checkout_metrics)


def test_pipeline_without_zone_map_stays_silent_on_queue(monkeypatch):
    # Same setup, but no camera_zone_map passed -> zone_id stays None ->
    # queue_monitor produces nothing, matching Phase 4's documented
    # limitation before this fix.
    runner = PipelineRunner(
        video_source=MockVideoSource("queue-cam-2"),
        inference_engine=MockInferenceEngine(min_people=1, max_people=1, seed=9),
        tracker=MockTracker(),
        analytics_service=AnalyticsService(queue_zone_ids=["checkout-1", "checkout-2"]),
    )
    runner.run_n(3)

    metrics = repositories.recent_queue_metrics()
    checkout_2_metrics = [m for m in metrics if m.camera_id == "queue-cam-2"]
    assert checkout_2_metrics == []


def test_zone_mapped_pipeline_produces_visibility_and_monetization_metrics():
    # Uses a shelf camera so OccupancyTracker actually produces a zone
    # reading (shelf zones aren't queue zones, so this also proves
    # visibility/monetization aren't accidentally gated behind queue logic).
    zone_map = load_camera_zone_map()
    assert zone_map["shelf-cam-1"] == "shelf-zone-1"

    runner = PipelineRunner(
        video_source=MockVideoSource("shelf-cam-1"),
        inference_engine=MockInferenceEngine(min_people=1, max_people=2, seed=3),
        tracker=MockTracker(),
        analytics_service=AnalyticsService(),
        camera_zone_map=zone_map,
    )
    runner.run_n(3)

    visibility = repositories.recent_visibility_metrics()
    monetization = repositories.recent_monetization_metrics()
    shelf_visibility = [m for m in visibility if m.zone_id == "shelf-zone-1"]
    shelf_monetization = [m for m in monetization if m.zone_id == "shelf-zone-1"]

    assert len(shelf_visibility) >= 1
    assert shelf_visibility[0].metric_name == "visibility_score"
    assert len(shelf_monetization) >= 1
    assert shelf_monetization[0].metric_name == "monetization_opportunity_score"
    assert shelf_monetization[0].is_estimate is True
