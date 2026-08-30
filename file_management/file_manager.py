"""File-management layer: owns the data/ directory tree. Every other
module that needs a path for a snapshot, export, report, demo file, test
fixture, or log should go through here rather than building its own
Path() by hand — keeps the on-disk layout defined in exactly one place.

    data/
    ├── database/     (SQLite lives here in production, see storage/database.py)
    ├── snapshots/
    ├── events/
    ├── exports/
    │   ├── csv/
    │   └── json/
    ├── reports/
    ├── demo/
    ├── test_data/
    ├── logs/
    └── temp/
"""

from __future__ import annotations

from pathlib import Path

DATA_ROOT = Path("data")

_SUBDIRS = (
    "database",
    "snapshots",
    "events",
    "exports/csv",
    "exports/json",
    "reports",
    "demo",
    "test_data",
    "logs",
    "temp",
)


def ensure_data_tree(root: Path | str = DATA_ROOT) -> Path:
    """Creates every folder in the tree above (idempotent — safe to call
    on every app startup). Returns the root Path."""
    root = Path(root)
    for sub in _SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def snapshot_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    return Path(root) / "snapshots" / filename


def export_csv_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    if not filename.endswith(".csv"):
        filename += ".csv"
    return Path(root) / "exports" / "csv" / filename


def export_json_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    if not filename.endswith(".json"):
        filename += ".json"
    return Path(root) / "exports" / "json" / filename


def report_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    return Path(root) / "reports" / filename


def log_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    return Path(root) / "logs" / filename


def temp_path(filename: str, root: Path | str = DATA_ROOT) -> Path:
    return Path(root) / "temp" / filename
