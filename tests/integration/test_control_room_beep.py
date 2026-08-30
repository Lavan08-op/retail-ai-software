"""Proves the control room's beep-on-new-critical-alert logic actually
works: beeps once for a genuinely new critical alert, does NOT beep again
for that same alert_id on a later poll tick, does NOT beep for
warning-severity alerts, and beeps again for a genuinely different new
critical alert. Table isolation between test functions is handled by
tests/integration/conftest.py's autouse fixture.

Each test stops the poller thread immediately and drives on_data_ready()
directly with a hand-built snapshot — deterministic, no reliance on
background-thread timing.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from control_room.windows.main_window import MainWindow  # noqa: E402
from storage import repositories, writer  # noqa: E402


def _snapshot() -> dict:
    return {
        "occupancy": repositories.recent_occupancy(),
        "queue": repositories.recent_queue_metrics(),
        "alerts": repositories.active_alerts(),
        "entry_exit": repositories.entry_exit_counts(),
    }


def test_beeps_once_for_new_critical_alert_not_again_for_same_one():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.poller.stop()

    writer.upsert_alert("QUEUE_THRESHOLD_EXCEEDED", "critical", "Queue critical", camera_id="queue-cam-1")

    with patch("control_room.windows.main_window.QApplication.beep") as mock_beep:
        window.on_data_ready(_snapshot())
        assert mock_beep.call_count == 1

        window.on_data_ready(_snapshot())  # same alert still active
        assert mock_beep.call_count == 1

    window.close()
    app.processEvents()


def test_does_not_beep_for_warning_severity():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.poller.stop()

    writer.upsert_alert("HIGH_OCCUPANCY", "warning", "Occupancy high", zone_id="zone-a")

    with patch("control_room.windows.main_window.QApplication.beep") as mock_beep:
        window.on_data_ready(_snapshot())
        assert mock_beep.call_count == 0

    window.close()
    app.processEvents()


def test_beeps_again_for_a_genuinely_new_critical_alert():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.poller.stop()

    writer.upsert_alert("QUEUE_THRESHOLD_EXCEEDED", "critical", "First critical", camera_id="queue-cam-1")

    with patch("control_room.windows.main_window.QApplication.beep") as mock_beep:
        window.on_data_ready(_snapshot())
        assert mock_beep.call_count == 1

        writer.upsert_alert("QUEUE_THRESHOLD_EXCEEDED", "critical", "Second critical", camera_id="queue-cam-2")
        window.on_data_ready(_snapshot())
        assert mock_beep.call_count == 2

    window.close()
    app.processEvents()
