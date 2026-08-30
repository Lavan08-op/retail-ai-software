"""EventEngine tested with plain values — no database, no video, no
mocks needed at this layer either."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.event_engine import EventEngine  # noqa: E402
from core.enums import EventType, Severity  # noqa: E402


def test_no_event_below_warning_threshold():
    engine = EventEngine(queue_warning=5, queue_critical=8)
    event = engine.check_queue_length("queue-cam-1", "checkout-1", queue_length=3)
    assert event is None


def test_warning_event_at_threshold():
    engine = EventEngine(queue_warning=5, queue_critical=8)
    event = engine.check_queue_length("queue-cam-1", "checkout-1", queue_length=5)
    assert event is not None
    assert event.event_type == EventType.QUEUE_THRESHOLD_EXCEEDED
    assert event.severity == Severity.WARNING


def test_critical_event_at_critical_threshold():
    engine = EventEngine(queue_warning=5, queue_critical=8)
    event = engine.check_queue_length("queue-cam-1", "checkout-1", queue_length=8)
    assert event is not None
    assert event.severity == Severity.CRITICAL


def test_occupancy_below_threshold_gives_no_event():
    engine = EventEngine(occupancy_warning_pct=80.0)
    event = engine.check_occupancy("zone-a", current_count=5, capacity=10)  # 50%
    assert event is None


def test_occupancy_at_threshold_gives_event():
    engine = EventEngine(occupancy_warning_pct=80.0)
    event = engine.check_occupancy("zone-a", current_count=8, capacity=10)  # 80%
    assert event is not None
    assert event.event_type == EventType.HIGH_OCCUPANCY


def test_camera_offline_always_critical():
    engine = EventEngine()
    event = engine.camera_offline("entry-cam")
    assert event.event_type == EventType.CAMERA_OFFLINE
    assert event.severity == Severity.CRITICAL
