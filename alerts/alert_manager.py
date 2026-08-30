"""Alert Manager — stateful, with cooldown per (event_type, camera, zone).
Consumes Event objects and decides whether to actually raise an Alert or
suppress it because one already fired recently. Pure Python; persistence
is the caller's job via storage.writer, same separation as everywhere
else in this codebase."""

import uuid
from datetime import datetime, timedelta

from core.models import Alert, Event


def _new_alert_id() -> str:
    return f"alrt-{uuid.uuid4().hex[:12]}"


class AlertManager:
    def __init__(self, cooldowns: dict[str, int] | None = None, default_cooldown_seconds: int = 60):
        # cooldowns: event_type value -> seconds. Loaded from
        # config/settings.yaml by whoever wires this up.
        self._cooldowns = cooldowns or {}
        self._default_cooldown = default_cooldown_seconds
        self._last_fired: dict[tuple[str, str | None, str | None], datetime] = {}

    def process(self, event: Event) -> Alert | None:
        """Returns a new Alert if this event should actually fire one, or
        None if it's suppressed by cooldown. The SAME (event_type, camera,
        zone) combination won't fire twice within its cooldown window —
        this is what stops "queue too long" from spamming an alert every
        single frame."""

        key = (event.event_type.value, event.camera_id, event.zone_id)
        cooldown_seconds = self._cooldowns.get(event.event_type.value, self._default_cooldown)
        now = event.timestamp

        last = self._last_fired.get(key)
        if last is not None and (now - last) < timedelta(seconds=cooldown_seconds):
            return None

        self._last_fired[key] = now
        return Alert(
            alert_id=_new_alert_id(),
            event_type=event.event_type,
            severity=event.severity,
            camera_id=event.camera_id,
            zone_id=event.zone_id,
            message=event.message,
            status="active",
        )
