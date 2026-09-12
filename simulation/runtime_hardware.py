"""Development hardware producer using the same runtime JSON contract."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path


class RuntimeHardwareSimulator:
    def __init__(self, runtime_dir: str | Path, interval_seconds: float = 1.0) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.interval_seconds = interval_seconds
        self.entry_count = 0
        self.exit_count = 0

    def write_once(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.entry_count += 1
        self.exit_count += int(self.entry_count % 3 == 0)
        payloads = {
            "entry_status.json": {
                "camera": "entry",
                "connected": True,
                "entry_count": self.entry_count,
                "exit_count": self.exit_count,
                "last_event": "simulated",
                "people_detected": 2,
                "detections": [],
                "timestamp": timestamp,
            },
            "queue_status.json": {
                "timestamp": timestamp,
                "queue_length": 2 + self.entry_count % 5,
                "status": "CONGESTED" if self.entry_count % 5 >= 3 else "NORMAL",
                "threshold": 3,
                "congestion_level": "Medium",
                "connected": True,
                "cameras": {"queue_camera_1": {"connected": True}, "queue_camera_2": {"connected": False}},
            },
            "stock_status.json": {
                "timestamp": timestamp,
                "products": {"cola": 4, "water": 2},
                "cameras": {"stock_camera_1": {"connected": True, "stock": {"cola": 4, "water": 2}}},
            },
            "edge_health.json": {
                "timestamp": datetime.now().isoformat(),
                "edge_node_id": "development",
                "services": {"simulator": {"running": True, "uptime_seconds": 0}},
                "status_files": {},
                "system": {},
                "network": {"online": True, "gateway": "development"},
                "overall_health": {"healthy": True, "services_ok": True, "files_ok": True, "network_ok": True},
            },
        }
        for name, payload in payloads.items():
            temporary = self.runtime_dir / f"{name}.{os.getpid()}.tmp"
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            target = self.runtime_dir / name
            for attempt in range(5):
                try:
                    temporary.replace(target)
                    break
                except PermissionError:
                    if attempt == 4:
                        temporary.unlink(missing_ok=True)
                    else:
                        time.sleep(0.01)

    def run(self, stop_event) -> None:
        while not stop_event.is_set():
            self.write_once()
            stop_event.wait(self.interval_seconds)