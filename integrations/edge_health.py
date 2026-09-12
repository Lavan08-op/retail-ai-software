"""Read-only access to the hardware edge health report."""

from __future__ import annotations

import json
from pathlib import Path


def read_health_report(runtime_dir: str | Path) -> dict | None:
    path = Path(runtime_dir) / "edge_health.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return report if isinstance(report, dict) else None