"""The ONLY module in this codebase allowed to write to SQLite.

Everything else — analytics, alerts, PySide6, Streamlit — goes through the
functions here (writes) or through repositories.py (reads). This is what
makes the single-writer/WAL design in storage/database.py actually hold in
practice, not just on paper.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from storage.database import SessionWriter
from storage.models import (
    AlertRecord,
    Camera,
    Detection,
    EntryExitEvent,
    EventRecord,
    InventorySnapshot,
    MonetizationMetric,
    OccupancyMetric,
    QueueMetric,
    ShelfMetric,
    SystemEvent,
    Track,
    VisibilityMetric,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def upsert_camera(camera_id: str, label: str, zone_id: str | None, online: bool, last_seen: datetime | None) -> None:
    with SessionWriter() as session:
        existing = session.get(Camera, camera_id)
        if existing:
            existing.label = label
            existing.zone_id = zone_id
            existing.online = online
            existing.last_seen = last_seen
        else:
            session.add(Camera(id=camera_id, label=label, zone_id=zone_id, online=online, last_seen=last_seen))
        session.commit()


def write_detection(camera_id: str, class_id: int, class_name: str, confidence: float, bbox: tuple) -> None:
    with SessionWriter() as session:
        session.add(
            Detection(
                camera_id=camera_id,
                class_id=class_id,
                class_name=class_name,
                confidence=confidence,
                bbox_json=list(bbox),
            )
        )
        session.commit()


def upsert_track(track_id: str, camera_id: str, class_name: str, zone_id: str | None,
                  first_seen: datetime, last_seen: datetime) -> None:
    with SessionWriter() as session:
        existing = session.get(Track, track_id)
        if existing:
            existing.last_seen = last_seen
            existing.zone_id = zone_id
        else:
            session.add(
                Track(
                    track_id=track_id,
                    camera_id=camera_id,
                    class_name=class_name,
                    zone_id=zone_id,
                    first_seen=first_seen,
                    last_seen=last_seen,
                )
            )
        session.commit()


def write_entry_exit(camera_id: str, zone_id: str | None, direction: str) -> None:
    with SessionWriter() as session:
        session.add(EntryExitEvent(camera_id=camera_id, zone_id=zone_id, direction=direction))
        session.commit()


def write_queue_metric(camera_id: str, zone_id: str | None, queue_length: int, avg_wait_seconds: float | None) -> None:
    with SessionWriter() as session:
        session.add(
            QueueMetric(
                camera_id=camera_id, zone_id=zone_id, queue_length=queue_length, avg_wait_seconds=avg_wait_seconds
            )
        )
        session.commit()


def write_occupancy(zone_id: str | None, current_count: int) -> None:
    with SessionWriter() as session:
        session.add(OccupancyMetric(zone_id=zone_id, current_count=current_count))
        session.commit()


def write_shelf_event(camera_id: str, zone_id: str | None, event_label: str) -> None:
    with SessionWriter() as session:
        session.add(ShelfMetric(camera_id=camera_id, zone_id=zone_id, event_label=event_label))
        session.commit()


def write_inventory_snapshot(camera_id: str, products: dict[str, int], timestamp: datetime | None = None) -> None:
    with SessionWriter() as session:
        snapshot = InventorySnapshot(camera_id=camera_id, products_json=products)
        if timestamp is not None:
            snapshot.timestamp = timestamp
        session.add(snapshot)
        session.commit()


def write_visibility_metric(zone_id: str | None, metric_name: str, value: float) -> None:
    with SessionWriter() as session:
        session.add(VisibilityMetric(zone_id=zone_id, metric_name=metric_name, value=value))
        session.commit()


def write_monetization_metric(zone_id: str | None, metric_name: str, value: float, is_estimate: bool = True) -> None:
    with SessionWriter() as session:
        session.add(
            MonetizationMetric(zone_id=zone_id, metric_name=metric_name, value=value, is_estimate=is_estimate)
        )
        session.commit()


def write_event(event_type: str, severity: str, message: str, camera_id: str | None = None,
                 zone_id: str | None = None, metadata: dict | None = None) -> str:
    event_id = _new_id("evt")
    with SessionWriter() as session:
        session.add(
            EventRecord(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                camera_id=camera_id,
                zone_id=zone_id,
                message=message,
                metadata_json=metadata or {},
            )
        )
        session.commit()
    return event_id


def upsert_alert(event_type: str, severity: str, message: str, camera_id: str | None = None,
                  zone_id: str | None = None, status: str = "active") -> str:
    alert_id = _new_id("alrt")
    with SessionWriter() as session:
        session.add(
            AlertRecord(
                alert_id=alert_id,
                event_type=event_type,
                severity=severity,
                camera_id=camera_id,
                zone_id=zone_id,
                message=message,
                status=status,
            )
        )
        session.commit()
    return alert_id


def write_system_event(category: str, message: str) -> None:
    with SessionWriter() as session:
        session.add(SystemEvent(category=category, message=message))
        session.commit()
