"""Event engine — pure Python business logic. Turns raw metric values into
standardized Event objects when configured thresholds are crossed. Does
NOT decide what happens to an event afterward (persistence is the caller's
job via storage.writer; deciding whether to actually alert-with-cooldown is
alerts/alert_manager.py's job). Never imports storage, UI, or RabbitMQ.
"""

import uuid

from core.enums import EventType, Severity
from core.models import Event


def _new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:12]}"


class EventEngine:
    """Thresholds are constructor args (loaded from config/settings.yaml by
    whoever wires this up — never hardcoded deeper than this)."""

    def __init__(
        self,
        queue_warning: int = 5,
        queue_critical: int = 8,
        occupancy_warning_pct: float = 80.0,
    ):
        self.queue_warning = queue_warning
        self.queue_critical = queue_critical
        self.occupancy_warning_pct = occupancy_warning_pct

    def check_queue_length(
        self, camera_id: str, zone_id: str | None, queue_length: int
    ) -> Event | None:
        if queue_length >= self.queue_critical:
            severity = Severity.CRITICAL
        elif queue_length >= self.queue_warning:
            severity = Severity.WARNING
        else:
            return None

        return Event(
            event_id=_new_event_id(),
            event_type=EventType.QUEUE_THRESHOLD_EXCEEDED,
            camera_id=camera_id,
            zone_id=zone_id,
            severity=severity,
            message=f"Queue length {queue_length} at {zone_id or camera_id}",
            metadata={"queue_length": queue_length},
        )

    def check_occupancy(
        self, zone_id: str | None, current_count: int, capacity: int
    ) -> Event | None:
        if capacity <= 0:
            return None
        pct = (current_count / capacity) * 100
        if pct < self.occupancy_warning_pct:
            return None

        return Event(
            event_id=_new_event_id(),
            event_type=EventType.HIGH_OCCUPANCY,
            zone_id=zone_id,
            severity=Severity.WARNING,
            message=f"Occupancy at {pct:.0f}% in {zone_id}",
            metadata={"current_count": current_count, "capacity": capacity, "pct": pct},
        )

    def camera_offline(self, camera_id: str) -> Event:
        return Event(
            event_id=_new_event_id(),
            event_type=EventType.CAMERA_OFFLINE,
            camera_id=camera_id,
            severity=Severity.CRITICAL,
            message=f"{camera_id} is offline",
        )
