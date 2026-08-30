"""Queue analytics — pure Python business logic, its own module as
requested. Turns tracks currently inside a configured queue zone into a
raw queue_length reading. Deciding whether that reading crosses a
threshold is analytics/event_engine.py's job; deciding whether to
actually raise an alert on it (with cooldown) is
alerts/alert_manager.py's job — this module only measures.
"""

from __future__ import annotations

from core.models import AnalyticsResult, Track


class QueueMonitor:
    def __init__(self, queue_zone_ids: list[str], class_name: str = "person"):
        self._queue_zone_ids = set(queue_zone_ids)
        self._class_name = class_name

    def update(self, tracks: list[Track]) -> list[AnalyticsResult]:
        per_zone: dict[str, list[Track]] = {}
        for t in tracks:
            if t.class_name == self._class_name and t.zone_id in self._queue_zone_ids:
                per_zone.setdefault(t.zone_id, []).append(t)

        results: list[AnalyticsResult] = []
        for zone_id, zone_tracks in per_zone.items():
            camera_id = zone_tracks[0].camera_id
            results.append(
                AnalyticsResult(
                    metric_name="queue_length",
                    camera_id=camera_id,
                    zone_id=zone_id,
                    value=float(len(zone_tracks)),
                    unit="people",
                )
            )
        return results
