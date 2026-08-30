"""AnalyticsService — the orchestration layer. This is what
pipeline/runner.py, and later PySide6/Streamlit, actually call. Nothing
outside services/ should import analytics/, alerts/, or storage/ directly
— that's the seam this whole architecture depends on.

Wires: Track objects -> PeopleCounter               -> storage (occupancy, per-camera)
                      -> EntryExitTracker             -> storage (entry_exit)
                      -> ShelfMonitor                 -> storage (shelf_event)
                      -> OccupancyTracker              -> storage (occupancy, per-zone)
                                                         -> EventEngine -> AlertManager (if over capacity)
                      -> QueueMonitor                  -> storage (queue_metric)
                                                         -> EventEngine -> AlertManager (if over threshold)
       queue readings (direct, not from tracks)         -> storage (queue_metric)
                                                         -> EventEngine -> AlertManager

visibility.py and monetization.py are pure functions (not stateful
trackers) called directly by whichever caller has the traffic/dwell
numbers on hand — not wired into process_tracks, since they need
aggregated inputs process_tracks doesn't compute on its own yet.
"""

from __future__ import annotations

from core.models import Track
from analytics.event_engine import EventEngine
from analytics.people_counter import PeopleCounter
from analytics.entry_exit import EntryExitTracker
from analytics.occupancy import OccupancyTracker
from analytics.queue_monitor import QueueMonitor
from analytics.shelf_monitor import ShelfMonitor
from analytics.visibility import compute_visibility_score
from analytics.monetization import compute_opportunity_score
from alerts.alert_manager import AlertManager
from storage import writer


class AnalyticsService:
    def __init__(
        self,
        queue_warning: int = 5,
        queue_critical: int = 8,
        occupancy_warning_pct: float = 80.0,
        cooldowns: dict[str, int] | None = None,
        queue_zone_ids: list[str] | None = None,
        shelf_zone_ids: list[str] | None = None,
        zone_capacities: dict[str, int] | None = None,
        dwell_seconds_warning: float = 300.0,
    ):
        self.people_counter = PeopleCounter()
        self.entry_exit_tracker = EntryExitTracker()
        self.occupancy_tracker = OccupancyTracker(zone_capacities=zone_capacities)
        self.queue_monitor = QueueMonitor(
            queue_zone_ids=queue_zone_ids or ["checkout-1", "checkout-2"]
        )
        self.shelf_monitor = ShelfMonitor(
            shelf_zone_ids=shelf_zone_ids or ["shelf-zone-1", "shelf-zone-2", "shelf-zone-3"],
            dwell_seconds_warning=dwell_seconds_warning,
        )
        self.event_engine = EventEngine(
            queue_warning=queue_warning,
            queue_critical=queue_critical,
            occupancy_warning_pct=occupancy_warning_pct,
        )
        self.alert_manager = AlertManager(cooldowns=cooldowns)

    def process_tracks(self, tracks: list[Track]) -> None:
        """Called once per frame's worth of tracked objects. Runs every
        analytics module against the same track set and persists results;
        queue and occupancy readings additionally flow through the
        event/alert pipeline exactly like process_queue_reading does."""
        for result in self.people_counter.update(tracks):
            if result.metric_name == "people_count_camera":
                writer.write_occupancy(zone_id=result.camera_id, current_count=int(result.value))

        for reading in self.entry_exit_tracker.update(tracks):
            writer.write_entry_exit(reading.camera_id, reading.zone_id, reading.direction)

        for activity in self.shelf_monitor.update(tracks):
            writer.write_shelf_event(activity.camera_id, activity.zone_id, activity.event_label)

        for occ in self.occupancy_tracker.update(tracks):
            writer.write_occupancy(zone_id=occ.zone_id, current_count=int(occ.value))
            capacity = occ.metadata.get("capacity")
            if capacity:
                self._handle_event(
                    self.event_engine.check_occupancy(occ.zone_id, int(occ.value), int(capacity))
                )

            # Visibility/monetization are cheap to derive from the same
            # occupancy reading (traffic proxy) and the tracks currently
            # in that zone (dwell proxy) — computed here rather than as
            # their own stateful tracker, since they need no memory of
            # their own beyond what OccupancyTracker already keeps.
            zone_tracks = [t for t in tracks if t.zone_id == occ.zone_id]
            if zone_tracks:
                avg_dwell = sum(
                    (t.last_seen - t.first_seen).total_seconds() for t in zone_tracks
                ) / len(zone_tracks)
                visibility = compute_visibility_score(
                    occ.zone_id, traffic_count=int(occ.value), avg_dwell_seconds=avg_dwell
                )
                writer.write_visibility_metric(visibility.zone_id, visibility.metric_name, visibility.value)

                opportunity = compute_opportunity_score(
                    occ.zone_id, visibility_score=visibility.value, traffic_count=int(occ.value)
                )
                writer.write_monetization_metric(
                    opportunity.zone_id, opportunity.metric_name, opportunity.value,
                    is_estimate=True,
                )

        for q in self.queue_monitor.update(tracks):
            writer.write_queue_metric(q.camera_id, q.zone_id, int(q.value), None)
            self._handle_event(
                self.event_engine.check_queue_length(q.camera_id, q.zone_id, int(q.value))
            )

    def process_queue_reading(
        self,
        camera_id: str,
        zone_id: str | None,
        queue_length: int,
        avg_wait_seconds: float | None = None,
    ) -> None:
        """Direct entry point for a queue reading that didn't come from
        process_tracks (manual input now; a dedicated queue-camera signal
        later). Persists the raw metric, checks it against thresholds,
        and — respecting cooldown — raises an event + alert if too long.
        Unchanged from Phase 3."""
        writer.write_queue_metric(camera_id, zone_id, queue_length, avg_wait_seconds)
        self._handle_event(self.event_engine.check_queue_length(camera_id, zone_id, queue_length))

    def _handle_event(self, event) -> None:
        if event is None:
            return
        writer.write_event(
            event.event_type.value,
            event.severity.value,
            event.message,
            camera_id=event.camera_id,
            zone_id=event.zone_id,
            metadata=event.metadata,
        )
        alert = self.alert_manager.process(event)
        if alert is not None:
            writer.upsert_alert(
                alert.event_type.value,
                alert.severity.value,
                alert.message,
                camera_id=alert.camera_id,
                zone_id=alert.zone_id,
                status=alert.status,
            )
