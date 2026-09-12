"""Read-only access to the database. PySide6, Streamlit, and services/ call
these — never storage.writer, and never open a raw session of their own."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from storage.database import SessionReader
from storage.models import (
    AlertRecord,
    Camera,
    EntryExitEvent,
    EventRecord,
    InventorySnapshot,
    Detection,
    MonetizationMetric,
    OccupancyMetric,
    QueueMetric,
    ShelfMetric,
    VisibilityMetric,
)


def list_cameras() -> list[Camera]:
    with SessionReader() as session:
        return list(session.scalars(select(Camera)))


def recent_queue_metrics(limit: int = 20) -> list[QueueMetric]:
    with SessionReader() as session:
        stmt = select(QueueMetric).order_by(QueueMetric.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def latest_queue_metric() -> QueueMetric | None:
    rows = recent_queue_metrics(limit=1)
    return rows[0] if rows else None


def recent_occupancy(limit: int = 20) -> list[OccupancyMetric]:
    with SessionReader() as session:
        stmt = select(OccupancyMetric).order_by(OccupancyMetric.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def entry_exit_counts(since: datetime | None = None) -> dict[str, int]:
    since = since or (datetime.now(timezone.utc) - timedelta(hours=24))
    with SessionReader() as session:
        stmt = select(EntryExitEvent).where(EntryExitEvent.timestamp >= since)
        rows = list(session.scalars(stmt))
    counts = {"in": 0, "out": 0}
    for row in rows:
        counts[row.direction] = counts.get(row.direction, 0) + 1
    return counts


def active_alerts() -> list[AlertRecord]:
    with SessionReader() as session:
        stmt = select(AlertRecord).where(AlertRecord.status == "active").order_by(AlertRecord.created_at.desc())
        return list(session.scalars(stmt))


def recent_events(limit: int = 50) -> list[EventRecord]:
    with SessionReader() as session:
        stmt = select(EventRecord).order_by(EventRecord.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def recent_shelf_events(limit: int = 20) -> list[ShelfMetric]:
    with SessionReader() as session:
        stmt = select(ShelfMetric).order_by(ShelfMetric.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def recent_inventory_snapshots(limit: int = 20) -> list[InventorySnapshot]:
    with SessionReader() as session:
        stmt = select(InventorySnapshot).order_by(InventorySnapshot.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def recent_detections(limit: int = 100) -> list[Detection]:
    with SessionReader() as session:
        stmt = select(Detection).order_by(Detection.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def recent_visibility_metrics(limit: int = 20) -> list[VisibilityMetric]:
    with SessionReader() as session:
        stmt = select(VisibilityMetric).order_by(VisibilityMetric.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))


def recent_monetization_metrics(limit: int = 20) -> list[MonetizationMetric]:
    with SessionReader() as session:
        stmt = select(MonetizationMetric).order_by(MonetizationMetric.timestamp.desc()).limit(limit)
        return list(session.scalars(stmt))
