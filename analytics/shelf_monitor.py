"""Shelf analytics — pure Python business logic. Flags shelf-zone activity
when a track dwells near a configured shelf zone longer than a threshold
(matches config/settings.yaml's alert_thresholds.dwell_seconds_warning).
Each track is only flagged once per continuous visit — it can be flagged
again on a later, separate visit to the shelf.
"""

from __future__ import annotations

from core.models import ShelfActivity, Track


class ShelfMonitor:
    def __init__(
        self,
        shelf_zone_ids: list[str],
        dwell_seconds_warning: float = 300.0,
        class_name: str = "person",
    ):
        self._shelf_zone_ids = set(shelf_zone_ids)
        self._dwell_seconds_warning = dwell_seconds_warning
        self._class_name = class_name
        self._flagged_this_visit: set[str] = set()

    def update(self, tracks: list[Track]) -> list[ShelfActivity]:
        current_ids: set[str] = set()
        activities: list[ShelfActivity] = []

        for t in tracks:
            if t.class_name != self._class_name or t.zone_id not in self._shelf_zone_ids:
                continue
            current_ids.add(t.track_id)
            dwell_seconds = (t.last_seen - t.first_seen).total_seconds()
            if dwell_seconds >= self._dwell_seconds_warning and t.track_id not in self._flagged_this_visit:
                activities.append(
                    ShelfActivity(camera_id=t.camera_id, zone_id=t.zone_id, event_label="prolonged_dwell")
                )
                self._flagged_this_visit.add(t.track_id)

        # Drop tracks that have left the shelf zone so they can be
        # re-flagged on a future, separate visit.
        self._flagged_this_visit &= current_ids
        return activities
