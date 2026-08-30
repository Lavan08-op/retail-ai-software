"""Analytics tested with synthetic Track data directly — no database, no
video, no mocks even needed at this layer, per the phased build order."""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.people_counter import PeopleCounter  # noqa: E402
from core.models import Track  # noqa: E402


def _track(camera_id: str, class_name: str = "person") -> Track:
    now = datetime.now(timezone.utc)
    return Track(
        track_id=f"trk-{uuid.uuid4().hex[:8]}",
        camera_id=camera_id,
        class_name=class_name,
        bbox=(0, 0, 50, 100),
        confidence=0.9,
        first_seen=now,
        last_seen=now,
    )


def test_empty_tracks_gives_zero_count():
    counter = PeopleCounter()
    results = counter.update([])
    total = next(r for r in results if r.metric_name == "people_count_total")
    assert total.value == 0.0


def test_counts_people_only_not_other_classes():
    counter = PeopleCounter()
    tracks = [_track("entry-cam"), _track("entry-cam"), _track("entry-cam", class_name="cart")]
    results = counter.update(tracks)
    total = next(r for r in results if r.metric_name == "people_count_total")
    assert total.value == 2.0


def test_per_camera_breakdown():
    counter = PeopleCounter()
    tracks = [_track("entry-cam"), _track("entry-cam"), _track("queue-cam-1")]
    results = counter.update(tracks)

    per_camera = {r.camera_id: r.value for r in results if r.metric_name == "people_count_camera"}
    assert per_camera["entry-cam"] == 2.0
    assert per_camera["queue-cam-1"] == 1.0


def test_history_accumulates_across_updates():
    counter = PeopleCounter()
    counter.update([_track("entry-cam")])
    counter.update([_track("entry-cam"), _track("entry-cam")])

    history = counter.history()
    totals = [r.value for r in history if r.metric_name == "people_count_total"]
    assert totals == [1.0, 2.0]
