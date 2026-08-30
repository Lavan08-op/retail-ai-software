"""ShelfMonitor tested with synthetic Track data directly."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.shelf_monitor import ShelfMonitor  # noqa: E402
from core.models import Track  # noqa: E402


def _track(track_id: str, zone_id: str | None, dwell_seconds: float,
           camera_id: str = "shelf-cam-1", class_name: str = "person") -> Track:
    now = datetime.now(timezone.utc)
    return Track(
        track_id=track_id,
        camera_id=camera_id,
        class_name=class_name,
        bbox=(0, 0, 50, 100),
        confidence=0.9,
        first_seen=now - timedelta(seconds=dwell_seconds),
        last_seen=now,
        zone_id=zone_id,
    )


def test_flags_prolonged_dwell():
    monitor = ShelfMonitor(shelf_zone_ids=["shelf-zone-1"], dwell_seconds_warning=300)
    activities = monitor.update([_track("trk_1", "shelf-zone-1", dwell_seconds=400)])
    assert len(activities) == 1
    assert activities[0].event_label == "prolonged_dwell"
    assert activities[0].zone_id == "shelf-zone-1"


def test_does_not_flag_short_dwell():
    monitor = ShelfMonitor(shelf_zone_ids=["shelf-zone-1"], dwell_seconds_warning=300)
    activities = monitor.update([_track("trk_1", "shelf-zone-1", dwell_seconds=30)])
    assert activities == []


def test_ignores_non_shelf_zone():
    monitor = ShelfMonitor(shelf_zone_ids=["shelf-zone-1"], dwell_seconds_warning=300)
    activities = monitor.update([_track("trk_1", "checkout-1", dwell_seconds=400)])
    assert activities == []


def test_flags_once_per_continuous_visit():
    monitor = ShelfMonitor(shelf_zone_ids=["shelf-zone-1"], dwell_seconds_warning=300)
    t = _track("trk_1", "shelf-zone-1", dwell_seconds=400)
    first = monitor.update([t])
    second = monitor.update([t])  # still there, already flagged
    assert len(first) == 1
    assert second == []


def test_reflagged_after_leaving_and_returning():
    monitor = ShelfMonitor(shelf_zone_ids=["shelf-zone-1"], dwell_seconds_warning=300)
    t = _track("trk_1", "shelf-zone-1", dwell_seconds=400)
    monitor.update([t])       # flagged
    monitor.update([])        # leaves the zone
    second_visit = monitor.update([t])  # returns, same dwell (test data, not realistic timing)
    assert len(second_visit) == 1
