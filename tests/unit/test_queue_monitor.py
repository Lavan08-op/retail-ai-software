"""QueueMonitor tested with synthetic Track data directly."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.queue_monitor import QueueMonitor  # noqa: E402
from core.models import Track  # noqa: E402


def _track(track_id: str, zone_id: str | None, camera_id: str = "queue-cam-1",
           class_name: str = "person") -> Track:
    now = datetime.now(timezone.utc)
    return Track(
        track_id=track_id,
        camera_id=camera_id,
        class_name=class_name,
        bbox=(0, 0, 50, 100),
        confidence=0.9,
        first_seen=now,
        last_seen=now,
        zone_id=zone_id,
    )


def test_counts_people_in_queue_zone():
    monitor = QueueMonitor(queue_zone_ids=["checkout-1"])
    tracks = [_track("trk_1", "checkout-1"), _track("trk_2", "checkout-1")]
    results = monitor.update(tracks)
    assert len(results) == 1
    assert results[0].metric_name == "queue_length"
    assert results[0].value == 2.0
    assert results[0].zone_id == "checkout-1"


def test_ignores_non_queue_zone():
    monitor = QueueMonitor(queue_zone_ids=["checkout-1"])
    results = monitor.update([_track("trk_1", "shelf-zone-1")])
    assert results == []


def test_ignores_tracks_with_no_zone():
    monitor = QueueMonitor(queue_zone_ids=["checkout-1"])
    results = monitor.update([_track("trk_1", None)])
    assert results == []


def test_multiple_queue_zones_separate_results():
    monitor = QueueMonitor(queue_zone_ids=["checkout-1", "checkout-2"])
    tracks = [
        _track("trk_1", "checkout-1", camera_id="queue-cam-1"),
        _track("trk_2", "checkout-2", camera_id="queue-cam-2"),
        _track("trk_3", "checkout-2", camera_id="queue-cam-2"),
    ]
    results = {r.zone_id: r.value for r in monitor.update(tracks)}
    assert results["checkout-1"] == 1.0
    assert results["checkout-2"] == 2.0


def test_ignores_non_person_classes():
    monitor = QueueMonitor(queue_zone_ids=["checkout-1"])
    results = monitor.update([_track("trk_1", "checkout-1", class_name="cart")])
    assert results == []
