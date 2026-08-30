"""Entry/exit analytics — pure Python business logic. Detects arrivals and
departures by diffing which track_ids are present between successive
update() calls, per class_name. Persistence is the caller's job via
storage.writer.write_entry_exit(camera_id, zone_id, direction) — this
module only measures, same separation as every other analytics/ module.
"""

from __future__ import annotations

from core.models import EntryExitReading, Track


class EntryExitTracker:
    """Call update() once per frame's worth of tracks. Keeps its own memory
    of which track_ids were present last call, so a genuinely new arrival
    (entry) can be told apart from a track that just disappeared (exit) —
    no per-frame line-crossing geometry needed. This fits how the tracker
    (mock now, real one later) already assigns and eventually drops
    persistent IDs, so it needs no changes when the real tracker arrives.
    """

    def __init__(self, class_name: str = "person"):
        self._class_name = class_name
        self._seen_ids: set[str] = set()
        self._last_known: dict[str, Track] = {}

    def update(self, tracks: list[Track]) -> list[EntryExitReading]:
        current = {t.track_id: t for t in tracks if t.class_name == self._class_name}
        current_ids = set(current.keys())

        entered_ids = current_ids - self._seen_ids
        exited_ids = self._seen_ids - current_ids

        readings: list[EntryExitReading] = []
        for track_id in entered_ids:
            t = current[track_id]
            readings.append(
                EntryExitReading(camera_id=t.camera_id, zone_id=t.zone_id, direction="in")
            )

        # An exited track_id is, by definition, no longer in `tracks` — use
        # the camera/zone it was last seen at, remembered from a prior call.
        for track_id in exited_ids:
            last = self._last_known.get(track_id)
            if last is not None:
                readings.append(
                    EntryExitReading(camera_id=last.camera_id, zone_id=last.zone_id, direction="out")
                )

        self._last_known.update(current)
        for track_id in exited_ids:
            self._last_known.pop(track_id, None)

        self._seen_ids = current_ids
        return readings
