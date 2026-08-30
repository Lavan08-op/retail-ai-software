"""Export functions for the Streamlit "Reports" page and any future report
generation. Read-only on purpose: pulls from storage.repositories only,
never storage.writer — exporting data must never be able to mutate it.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from file_management.file_manager import ensure_data_tree, export_csv_path, export_json_path
from storage import repositories


def _timestamped_filename(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    ensure_data_tree()
    with open(path, "w", newline="", encoding="utf-8") as f:
        if not rows:
            f.write("")
            return path
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_json(path: Path, rows: list[dict[str, Any]]) -> Path:
    ensure_data_tree()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)
    return path


def export_queue_metrics(fmt: str = "csv", limit: int = 100) -> Path:
    rows = [
        {
            "camera_id": m.camera_id,
            "zone_id": m.zone_id,
            "queue_length": m.queue_length,
            "avg_wait_seconds": m.avg_wait_seconds,
            "timestamp": m.timestamp,
        }
        for m in repositories.recent_queue_metrics(limit=limit)
    ]
    name = _timestamped_filename("queue_metrics")
    if fmt == "json":
        return _write_json(export_json_path(name), rows)
    return _write_csv(export_csv_path(name), rows)


def export_occupancy(fmt: str = "csv", limit: int = 100) -> Path:
    rows = [
        {"zone_id": m.zone_id, "current_count": m.current_count, "timestamp": m.timestamp}
        for m in repositories.recent_occupancy(limit=limit)
    ]
    name = _timestamped_filename("occupancy")
    if fmt == "json":
        return _write_json(export_json_path(name), rows)
    return _write_csv(export_csv_path(name), rows)


def export_alerts(fmt: str = "csv") -> Path:
    rows = [
        {
            "alert_id": a.alert_id,
            "event_type": a.event_type,
            "severity": a.severity,
            "camera_id": a.camera_id,
            "zone_id": a.zone_id,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at,
        }
        for a in repositories.active_alerts()
    ]
    name = _timestamped_filename("alerts")
    if fmt == "json":
        return _write_json(export_json_path(name), rows)
    return _write_csv(export_csv_path(name), rows)


def export_events(fmt: str = "csv", limit: int = 200) -> Path:
    rows = [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "camera_id": e.camera_id,
            "zone_id": e.zone_id,
            "message": e.message,
            "timestamp": e.timestamp,
        }
        for e in repositories.recent_events(limit=limit)
    ]
    name = _timestamped_filename("events")
    if fmt == "json":
        return _write_json(export_json_path(name), rows)
    return _write_csv(export_csv_path(name), rows)
