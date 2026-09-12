"""Bridges the hardware team's already-computed sensor output (JSON status
files from entry_counter.py / queue_monitor.py) into our storage layer.

This is NOT plugging into VideoSource/InferenceEngine/Tracker — their side
already does detection, tracking, AND analytics itself, producing final
numbers (entry_count, exit_count, queue_length). Re-running our own
analytics/ on top of that would be redundant. This bridge reads their
final output and writes it straight into storage via storage.writer,
letting our dashboards display it.

Camera naming differs between the two sides (their "entry"/"queue_1"/
"queue_2" vs our "entry-cam"/"queue-cam-1"/"queue-cam-2" + zone_id) —
CAMERA_ID_MAP below is the one place that translation happens.

Field shapes below match their REAL code exactly (verified by reading
entry_counter.py and queue_monitor.py directly), not guessed:

entry_status.json:
    {"camera": str, "connected": bool, "entry_count": int, "exit_count": int,
     "last_event": str, "people_detected": int, "detections": [...],
     "timestamp": "YYYY-MM-DD HH:MM:SS"}

queue_status.json:
    {"timestamp": "YYYY-MM-DD HH:MM:SS", "queue_length": int,
     "status": "CONGESTED"|"NORMAL", "threshold": int,
     "congestion_level": "Low"|"Medium"|"High", "connected": bool,
     "cameras": {...}}
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from storage import writer

# Their camera name -> (our camera_id, our zone_id). This is the one place
# the naming mismatch between the two sides' configs gets resolved.
CAMERA_ID_MAP = {
    "entry": ("entry-cam", "entrance"),
    "queue_1": ("queue-cam-1", "checkout-1"),
    "queue_2": ("queue-cam-2", "checkout-2"),
}

STOCK_CAMERA_ID_MAP = {
    "stock_camera_1": ("shelf-cam-1", "shelf-zone-1"),
    "stock_camera_2": ("shelf-cam-2", "shelf-zone-2"),
    "stock_camera_3": ("shelf-cam-3", "shelf-zone-3"),
}

# If a status file's timestamp is older than this, treat it as stale (the
# sensor may be disconnected/dead) and skip processing it rather than
# silently acting on old data. Mirrors their own health_monitor's
# STALE_SECONDS=15 pattern.
STALE_SECONDS = 30


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _parse_health_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError, TypeError):
        return None


def _is_fresh(status: dict) -> bool:
    ts = _parse_timestamp(status.get("timestamp", ""))
    if ts is None:
        return False
    age_seconds = (datetime.now() - ts).total_seconds()
    return age_seconds <= STALE_SECONDS


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


class HardwareMetricsBridge:
    """Polls the hardware side's JSON status files and feeds already-
    computed metrics into our storage. Tracks last-seen cumulative
    entry/exit counts per camera so it can emit the DIFFERENCE as
    individual events — their side reports running totals, our
    storage.writer.write_entry_exit() records one discrete event at a
    time."""

    def __init__(self, runtime_dir: str | Path):
        self.runtime_dir = Path(runtime_dir)
        self._last_entry_count: dict[str, int] = {}
        self._last_exit_count: dict[str, int] = {}

    def sync_entry_status(self) -> int:
        """Reads entry_status.json, writes any NEW entry/exit events since
        last poll. Returns the number of individual events written (0 if
        the file is missing, stale, or unchanged)."""

        status = _read_json(self.runtime_dir / "entry_status.json")
        if status is None or not _is_fresh(status):
            return 0

        hw_camera_name = status.get("camera", "entry")
        camera_id, zone_id = CAMERA_ID_MAP.get(hw_camera_name, (hw_camera_name, None))

        current_entries = int(status.get("entry_count", 0))
        current_exits = int(status.get("exit_count", 0))

        prev_entries = self._last_entry_count.get(hw_camera_name, 0)
        prev_exits = self._last_exit_count.get(hw_camera_name, 0)

        new_entries = max(0, current_entries - prev_entries)
        new_exits = max(0, current_exits - prev_exits)

        for _ in range(new_entries):
            writer.write_entry_exit(camera_id, zone_id, "in")
        for _ in range(new_exits):
            writer.write_entry_exit(camera_id, zone_id, "out")

        self._last_entry_count[hw_camera_name] = current_entries
        self._last_exit_count[hw_camera_name] = current_exits

        return new_entries + new_exits

    def sync_queue_status(self) -> bool:
        """Reads queue_status.json, writes the current queue reading.
        Returns True if a reading was written, False if the file is
        missing or stale."""

        status = _read_json(self.runtime_dir / "queue_status.json")
        if status is None or not _is_fresh(status):
            return False

        # queue_status.json covers queue_camera_1 by default (per
        # queue_monitor.py's VIDEO_URL default) — queue_camera_2 support
        # can be added once their side actually reports it separately.
        hw_camera_name = "queue_1"
        camera_id, zone_id = CAMERA_ID_MAP[hw_camera_name]

        queue_length = int(status.get("queue_length", 0))
        writer.write_queue_metric(camera_id, zone_id, queue_length, avg_wait_seconds=None)
        return True

    def sync_stock_status(self) -> int:
        """Reads stock_status.json and stores one product snapshot per camera."""

        status = _read_json(self.runtime_dir / "stock_status.json")
        if status is None or not _is_fresh(status):
            return 0

        cameras = status.get("cameras")
        if not isinstance(cameras, dict) or not cameras:
            cameras = {"stock_camera_1": {"stock": status.get("products", {})}}

        timestamp = _parse_timestamp(status.get("timestamp", ""))
        written = 0
        for hardware_name, camera_status in cameras.items():
            if not isinstance(camera_status, dict):
                continue
            camera_id, zone_id = STOCK_CAMERA_ID_MAP.get(hardware_name, (hardware_name, None))
            products = camera_status.get("stock", {})
            if not isinstance(products, dict):
                continue
            normalized = {}
            for product, quantity in products.items():
                try:
                    normalized[str(product)] = int(quantity)
                except (TypeError, ValueError):
                    continue
            connected = camera_status.get("connected") is True
            writer.upsert_camera(
                camera_id,
                label=camera_id,
                zone_id=zone_id,
                online=connected,
                last_seen=timestamp,
            )
            writer.write_inventory_snapshot(camera_id, normalized, timestamp=timestamp)
            written += 1
        return written

    def read_health_status(self) -> dict | None:
        """Reads the hardware health report without creating a second monitor."""

        report = _read_json(self.runtime_dir / "edge_health.json")
        if report is None:
            return None
        timestamp = _parse_health_timestamp(report.get("timestamp", ""))
        if timestamp is None:
            return None
        report["fresh"] = (datetime.now() - timestamp).total_seconds() <= STALE_SECONDS
        return report

    def poll_once(self) -> dict:
        """Runs one full poll cycle. Returns a small summary dict, mainly
        useful for logging/tests."""
        entry_events_written = self.sync_entry_status()
        queue_written = self.sync_queue_status()
        stock_snapshots_written = self.sync_stock_status()
        health = self.read_health_status()
        return {
            "entry_exit_events_written": entry_events_written,
            "queue_reading_written": queue_written,
            "stock_snapshots_written": stock_snapshots_written,
            "health_available": health is not None,
        }

    def run_forever(self, interval_seconds: float = 2.0) -> None:
        print(f"Bridging hardware metrics from {self.runtime_dir} every {interval_seconds}s. Ctrl+C to stop.")
        try:
            while True:
                result = self.poll_once()
                print(result)
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nBridge stopped.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Bridge hardware team's JSON sensor output into our storage.")
    parser.add_argument("--runtime-dir", required=True, help="Path to the hardware side's .runtime directory")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    args = parser.parse_args()

    from storage.database import init_db

    init_db()
    bridge = HardwareMetricsBridge(args.runtime_dir)
    bridge.run_forever(interval_seconds=args.interval_seconds)


if __name__ == "__main__":
    main()
