"""file_management.file_manager tested against a temp directory — never
touches the project's real data/ folder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from file_management.file_manager import (  # noqa: E402
    ensure_data_tree,
    export_csv_path,
    export_json_path,
    log_path,
    report_path,
    snapshot_path,
)


def test_ensure_data_tree_creates_all_subdirs(tmp_path):
    root = ensure_data_tree(tmp_path / "data")
    for sub in ("snapshots", "events", "exports/csv", "exports/json", "reports",
                "demo", "test_data", "logs", "temp", "database"):
        assert (root / sub).is_dir()


def test_ensure_data_tree_is_idempotent(tmp_path):
    root = tmp_path / "data"
    ensure_data_tree(root)
    ensure_data_tree(root)  # should not raise
    assert (root / "snapshots").is_dir()


def test_export_csv_path_adds_extension():
    p = export_csv_path("report", root="data")
    assert p.name == "report.csv"


def test_export_csv_path_does_not_double_extension():
    p = export_csv_path("report.csv", root="data")
    assert p.name == "report.csv"


def test_export_json_path_adds_extension():
    p = export_json_path("report", root="data")
    assert p.name == "report.json"


def test_snapshot_report_log_paths_land_in_expected_subdirs():
    assert snapshot_path("x.jpg", root="data") == Path("data/snapshots/x.jpg")
    assert report_path("x.pdf", root="data") == Path("data/reports/x.pdf")
    assert log_path("x.log", root="data") == Path("data/logs/x.log")
