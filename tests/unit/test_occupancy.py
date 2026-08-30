"""OccupancyTracker tested with synthetic Track data directly."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.occupancy import OccupancyTracker  # noqa: E402
from core.models import Track  # noqa: E402


def _track(track_id: str, zone_id: str | None, camera_id: str = "shelf-cam-1",
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


def test_counts_per_zone():
    tracker = OccupancyTracker()
    tracks = [
        _track("trk_1", zone_id="shelf-zone-1"),
        _track("trk_2", zone_id="shelf-zone-1"),
        _track("trk_3", zone_id="shelf-zone-2"),
    ]
    results = {r.zone_id: r.value for r in tracker.update(tracks)}
    assert results["shelf-zone-1"] == 2.0
    assert results["shelf-zone-2"] == 1.0


def test_ignores_tracks_without_zone():
    tracker = OccupancyTracker()
    results = tracker.update([_track("trk_1", zone_id=None)])
    assert results == []


def test_ignores_non_person_classes():
    tracker = OccupancyTracker()
    results = tracker.update([_track("trk_1", zone_id="shelf-zone-1", class_name="cart")])
    assert results == []


def test_peak_tracked_across_calls():
    tracker = OccupancyTracker()
    tracker.update([_track("trk_1", zone_id="shelf-zone-1"), _track("trk_2", zone_id="shelf-zone-1")])
    tracker.update([_track("trk_1", zone_id="shelf-zone-1")])  # drops to 1
    assert tracker.peak("shelf-zone-1") == 2


def test_capacity_percentage_computed():
    tracker = OccupancyTracker(zone_capacities={"shelf-zone-1": 4})
    results = tracker.update([
        _track("trk_1", zone_id="shelf-zone-1"),
        _track("trk_2", zone_id="shelf-zone-1"),
    ])
    result = results[0]
    assert result.metadata["capacity"] == 4
    assert result.metadata["pct"] == 50.0


def test_no_capacity_configured_leaves_pct_none():
    tracker = OccupancyTracker()
    results = tracker.update([_track("trk_1", zone_id="shelf-zone-1")])
    assert results[0].metadata["pct"] is None
