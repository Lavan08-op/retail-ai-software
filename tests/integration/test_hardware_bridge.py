"""Tests the hardware bridge using fixture JSON files that match the
REAL schema from entry_counter.py / queue_monitor.py exactly (verified by
reading their actual code) — not invented shapes. These fixtures stand in
for the hardware team's real running sensors; once their sensors are
live, the same bridge code points at their real .runtime directory with
zero changes.

Table isolation between test functions is handled by
tests/integration/conftest.py's autouse fixture.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integrations.hardware_bridge import HardwareMetricsBridge  # noqa: E402
from storage import repositories  # noqa: E402


def _now_str(offset_seconds: float = 0) -> str:
    return (datetime.now() + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S")


def _write_entry_status(runtime_dir: Path, entry_count: int, exit_count: int, fresh: bool = True) -> None:
    payload = {
        "camera": "entry",
        "connected": True,
        "entry_count": entry_count,
        "exit_count": exit_count,
        "last_event": "",
        "people_detected": 1,
        "detections": [],
        "timestamp": _now_str(0 if fresh else -120),
    }
    (runtime_dir / "entry_status.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_queue_status(runtime_dir: Path, queue_length: int, fresh: bool = True) -> None:
    payload = {
        "timestamp": _now_str(0 if fresh else -120),
        "queue_length": queue_length,
        "status": "CONGESTED" if queue_length >= 3 else "NORMAL",
        "threshold": 3,
        "congestion_level": "High" if queue_length >= 6 else "Medium" if queue_length >= 3 else "Low",
        "connected": True,
        "cameras": {"queue_camera_1": {"connected": True}, "queue_camera_2": {"connected": False}},
    }
    (runtime_dir / "queue_status.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_stock_status(runtime_dir: Path, fresh: bool = True) -> None:
    payload = {
        "timestamp": _now_str(0 if fresh else -120),
        "products": {"cola": 4, "water": 2},
        "cameras": {
            "stock_camera_1": {
                "connected": True,
                "stock": {"cola": 4, "water": 2},
            }
        },
    }
    (runtime_dir / "stock_status.json").write_text(json.dumps(payload), encoding="utf-8")


def test_bridge_emits_individual_entry_exit_events_from_cumulative_counts(tmp_path):
    runtime_dir = tmp_path
    bridge = HardwareMetricsBridge(runtime_dir)

    # First poll: hardware side reports 3 entries, 1 exit since it started
    _write_entry_status(runtime_dir, entry_count=3, exit_count=1)
    result = bridge.poll_once()
    assert result["entry_exit_events_written"] == 4  # 3 in + 1 out

    counts = repositories.entry_exit_counts()
    assert counts["in"] == 3
    assert counts["out"] == 1

    # Second poll: 2 MORE entries happened (5 total), exits unchanged
    _write_entry_status(runtime_dir, entry_count=5, exit_count=1)
    result2 = bridge.poll_once()
    assert result2["entry_exit_events_written"] == 2  # only the delta

    counts2 = repositories.entry_exit_counts()
    assert counts2["in"] == 5
    assert counts2["out"] == 1


def test_bridge_writes_queue_readings(tmp_path):
    runtime_dir = tmp_path
    bridge = HardwareMetricsBridge(runtime_dir)

    _write_queue_status(runtime_dir, queue_length=6)
    result = bridge.poll_once()
    assert result["queue_reading_written"] is True

    metrics = repositories.recent_queue_metrics()
    assert metrics[0].queue_length == 6
    assert metrics[0].camera_id == "queue-cam-1"
    assert metrics[0].zone_id == "checkout-1"


def test_bridge_skips_stale_data(tmp_path):
    runtime_dir = tmp_path
    bridge = HardwareMetricsBridge(runtime_dir)

    _write_entry_status(runtime_dir, entry_count=10, exit_count=2, fresh=False)  # 2 min old
    result = bridge.poll_once()

    assert result["entry_exit_events_written"] == 0  # stale data correctly ignored


def test_bridge_handles_missing_files_gracefully(tmp_path):
    runtime_dir = tmp_path  # empty, no JSON files at all
    bridge = HardwareMetricsBridge(runtime_dir)

    result = bridge.poll_once()  # must not raise
    assert result["entry_exit_events_written"] == 0
    assert result["queue_reading_written"] is False


def test_bridge_writes_hardware_inventory_snapshots(tmp_path):
    runtime_dir = tmp_path
    bridge = HardwareMetricsBridge(runtime_dir)

    _write_stock_status(runtime_dir)
    result = bridge.poll_once()

    assert result["stock_snapshots_written"] == 1
    snapshots = repositories.recent_inventory_snapshots()
    assert snapshots[0].camera_id == "shelf-cam-1"
    assert snapshots[0].products_json == {"cola": 4, "water": 2}


def test_bridge_reads_existing_edge_health_report(tmp_path):
    runtime_dir = tmp_path
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_health": {"healthy": True},
    }
    (runtime_dir / "edge_health.json").write_text(json.dumps(report), encoding="utf-8")

    result = HardwareMetricsBridge(runtime_dir).poll_once()

    assert result["health_available"] is True
