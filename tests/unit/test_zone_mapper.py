"""assign_zones tested with synthetic Track data directly."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.models import Track  # noqa: E402
from pipeline.zone_mapper import assign_zones  # noqa: E402


def _track(track_id: str, camera_id: str, zone_id: str | None = None) -> Track:
    now = datetime.now(timezone.utc)
    return Track(
        track_id=track_id,
        camera_id=camera_id,
        class_name="person",
        bbox=(0, 0, 50, 100),
        confidence=0.9,
        first_seen=now,
        last_seen=now,
        zone_id=zone_id,
    )


def test_assigns_zone_from_map():
    tracks = [_track("trk_1", camera_id="entry-cam")]
    result = assign_zones(tracks, {"entry-cam": "entrance"})
    assert result[0].zone_id == "entrance"


def test_leaves_unmapped_camera_untouched():
    tracks = [_track("trk_1", camera_id="unknown-cam")]
    result = assign_zones(tracks, {"entry-cam": "entrance"})
    assert result[0].zone_id is None


def test_does_not_mutate_original_track():
    original = _track("trk_1", camera_id="entry-cam")
    assign_zones([original], {"entry-cam": "entrance"})
    assert original.zone_id is None  # Pydantic model_copy doesn't mutate in place


def test_empty_map_leaves_all_tracks_untouched():
    tracks = [_track("trk_1", camera_id="entry-cam"), _track("trk_2", camera_id="queue-cam-1")]
    result = assign_zones(tracks, {})
    assert result[0].zone_id is None
    assert result[1].zone_id is None


def test_multiple_cameras_mapped_independently():
    tracks = [_track("trk_1", camera_id="entry-cam"), _track("trk_2", camera_id="queue-cam-1")]
    result = assign_zones(tracks, {"entry-cam": "entrance", "queue-cam-1": "checkout-1"})
    zones = {t.camera_id: t.zone_id for t in result}
    assert zones["entry-cam"] == "entrance"
    assert zones["queue-cam-1"] == "checkout-1"
