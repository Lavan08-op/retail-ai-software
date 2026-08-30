"""Mock Tracker — assigns persistent-looking IDs to detections without a
real tracking algorithm. Good enough to exercise analytics modules that
expect a list[Track]; the teammate's real tracker (IOU/Kalman/etc.)
implements the same Protocol later."""

import uuid
from datetime import datetime, timezone

from core.models import Detection, Track


class MockTracker:
    """Implements the Tracker Protocol. Since there's no real matching
    algorithm here, each call to update() treats every detection as a
    continuation of the track at the same list position as the previous
    call — simplistic, but sufficient for testing analytics logic against
    a realistic list[Track] shape."""

    def __init__(self):
        self._track_ids: list[str] = []
        self._first_seen: dict[str, datetime] = {}

    def update(self, detections: list[Detection]) -> list[Track]:
        now = datetime.now(timezone.utc)

        while len(self._track_ids) < len(detections):
            new_id = f"trk-{uuid.uuid4().hex[:10]}"
            self._track_ids.append(new_id)
            self._first_seen[new_id] = now

        self._track_ids = self._track_ids[: len(detections)]

        tracks = []
        for detection, track_id in zip(detections, self._track_ids):
            tracks.append(
                Track(
                    track_id=track_id,
                    camera_id=detection.camera_id,
                    class_name=detection.class_name,
                    bbox=detection.bbox,
                    confidence=detection.confidence,
                    first_seen=self._first_seen[track_id],
                    last_seen=now,
                )
            )
        return tracks
