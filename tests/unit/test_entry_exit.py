"""EntryExitTracker tested with synthetic Track data directly — no
database, no video, no mocks, per the phased build order."""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.entry_exit import EntryExitTracker  # noqa: E402
from core.models import Track  # noqa: E402


def _track(track_id: str, camera_id: str = "entry-cam", class_name: str = "person",
           zone_id: str | None = None) -> Track:
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


def test_new_track_generates_entry():
    tracker = EntryExitTracker()
    readings = tracker.update([_track("trk_1")])
    assert len(readings) == 1
    assert readings[0].direction == "in"
    assert readings[0].camera_id == "entry-cam"


def test_disappeared_track_generates_exit():
    tracker = EntryExitTracker()
    tracker.update([_track("trk_1")])
    readings = tracker.update([])  # trk_1 no longer present
    assert len(readings) == 1
    assert readings[0].direction == "out"
    assert readings[0].camera_id == "entry-cam"


def test_no_change_generates_nothing():
    tracker = EntryExitTracker()
    tracker.update([_track("trk_1")])
    readings = tracker.update([_track("trk_1")])  # same track, still present
    assert readings == []


def test_non_person_class_ignored():
    tracker = EntryExitTracker()
    readings = tracker.update([_track("trk_1", class_name="shopping_cart")])
    assert readings == []


def test_exit_uses_last_known_camera_and_zone():
    tracker = EntryExitTracker()
    tracker.update([_track("trk_1", camera_id="queue-cam-1", zone_id="checkout-1")])
    readings = tracker.update([])
    assert readings[0].camera_id == "queue-cam-1"
    assert readings[0].zone_id == "checkout-1"


def test_can_be_reflagged_on_a_later_visit():
    tracker = EntryExitTracker()
    tracker.update([_track("trk_1")])  # entry
    tracker.update([])                  # exit
    readings = tracker.update([_track("trk_1")])  # same id returns -> entry again
    assert len(readings) == 1
    assert readings[0].direction == "in"
