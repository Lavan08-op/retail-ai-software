"""ORM table definitions. This is the schema I own — the teammate's
pipeline writes into Cameras/Detections/Tracks via storage/writer.py; my
analytics engine writes into everything else.

Kept intentionally flat and un-clever: this is a hackathon prototype, not a
place to demonstrate advanced SQLAlchemy patterns.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # camera_id, e.g. "queue-cam-1"
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    label: Mapped[str] = mapped_column(String(120))
    online: Mapped[bool] = mapped_column(default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    class_id: Mapped[int] = mapped_column(Integer)
    class_name: Mapped[str] = mapped_column(String(60))
    confidence: Mapped[float] = mapped_column(Float)
    bbox_json: Mapped[str] = mapped_column(JSON)  # [x1,y1,x2,y2]


class Track(Base):
    __tablename__ = "tracks"

    track_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    class_name: Mapped[str] = mapped_column(String(60))
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EntryExitEvent(Base):
    __tablename__ = "entries_exits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    direction: Mapped[str] = mapped_column(String(10))  # "in" or "out"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class QueueMetric(Base):
    __tablename__ = "queue_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    queue_length: Mapped[int] = mapped_column(Integer)
    avg_wait_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class OccupancyMetric(Base):
    __tablename__ = "occupancy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    current_count: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class ShelfMetric(Base):
    __tablename__ = "shelf_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    event_label: Mapped[str] = mapped_column(String(120))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    products_json: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class VisibilityMetric(Base):
    __tablename__ = "visibility_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(60))
    value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class MonetizationMetric(Base):
    __tablename__ = "monetization_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(60))
    value: Mapped[float] = mapped_column(Float)
    is_estimate: Mapped[bool] = mapped_column(default=True)  # always True unless real POS data backs it
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class EventRecord(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    camera_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    message: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AlertRecord(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    camera_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    message: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(30))  # CORE, DATABASE, ANALYTICS, ALERT, RABBITMQ, STREAM, SYSTEM
    message: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
