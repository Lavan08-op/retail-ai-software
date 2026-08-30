"""AlertManager tested with synthetic Event objects — proves the cooldown
mechanism actually suppresses repeat alerts, which is the entire point of
this module (prevent alert-per-frame spam)."""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from alerts.alert_manager import AlertManager  # noqa: E402
from core.enums import EventType, Severity  # noqa: E402
from core.models import Event  # noqa: E402


def _event(camera_id: str, ts: datetime) -> Event:
    return Event(
        event_id=f"evt-{uuid.uuid4().hex[:8]}",
        event_type=EventType.QUEUE_THRESHOLD_EXCEEDED,
        camera_id=camera_id,
        zone_id="checkout-1",
        severity=Severity.WARNING,
        message="Queue too long",
        timestamp=ts,
    )


def test_first_event_always_fires_an_alert():
    manager = AlertManager(default_cooldown_seconds=60)
    now = datetime.now(timezone.utc)
    alert = manager.process(_event("queue-cam-1", now))
    assert alert is not None
    assert alert.status == "active"


def test_second_event_within_cooldown_is_suppressed():
    manager = AlertManager(default_cooldown_seconds=60)
    now = datetime.now(timezone.utc)
    first = manager.process(_event("queue-cam-1", now))
    second = manager.process(_event("queue-cam-1", now + timedelta(seconds=10)))
    assert first is not None
    assert second is None


def test_event_after_cooldown_fires_again():
    manager = AlertManager(default_cooldown_seconds=60)
    now = datetime.now(timezone.utc)
    first = manager.process(_event("queue-cam-1", now))
    later = manager.process(_event("queue-cam-1", now + timedelta(seconds=61)))
    assert first is not None
    assert later is not None


def test_different_cameras_have_independent_cooldowns():
    manager = AlertManager(default_cooldown_seconds=60)
    now = datetime.now(timezone.utc)
    alert_a = manager.process(_event("queue-cam-1", now))
    alert_b = manager.process(_event("queue-cam-2", now))
    assert alert_a is not None
    assert alert_b is not None  # different camera_id -> different cooldown key


def test_custom_cooldown_per_event_type():
    manager = AlertManager(cooldowns={"QUEUE_THRESHOLD_EXCEEDED": 5})
    now = datetime.now(timezone.utc)
    first = manager.process(_event("queue-cam-1", now))
    still_suppressed = manager.process(_event("queue-cam-1", now + timedelta(seconds=3)))
    fires_again = manager.process(_event("queue-cam-1", now + timedelta(seconds=6)))
    assert first is not None
    assert still_suppressed is None
    assert fires_again is not None
