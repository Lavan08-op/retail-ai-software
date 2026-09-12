"""Small live tracker adapter for YOLO detections."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.models import Detection, Track


class SimpleTracker:
    """Keep stable IDs by detection position for a single camera stream."""

    def __init__(self) -> None:
        self._track_ids: list[str] = []
        self._first_seen: dict[str, datetime] = {}

    def update(self, detections: list[Detection]) -> list[Track]:
        now = datetime.now(timezone.utc)
        while len(self._track_ids) < len(detections):
            track_id = f"trk-{uuid.uuid4().hex[:10]}"
            self._track_ids.append(track_id)
            self._first_seen[track_id] = now
        self._track_ids = self._track_ids[: len(detections)]
        return [
            Track(
                track_id=track_id,
                camera_id=detection.camera_id,
                class_name=detection.class_name,
                bbox=detection.bbox,
                confidence=detection.confidence,
                first_seen=self._first_seen[track_id],
                last_seen=now,
            )
            for detection, track_id in zip(detections, self._track_ids)
        ]
