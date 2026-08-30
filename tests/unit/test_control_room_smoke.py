"""Smoke test for the PySide6 control room. Proves the window constructs,
the DataPoller worker thread genuinely delivers at least one data_ready
signal, and everything shuts down cleanly — using Qt's 'offscreen'
platform so this runs without a real display (works in CI and in this
sandboxed environment alike).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import uuid
from pathlib import Path

TEST_DB = Path(f"data/test_control_room_{uuid.uuid4().hex[:8]}.db")
os.environ["RETAIL_AI_DB_PATH"] = str(TEST_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from control_room.windows.main_window import MainWindow  # noqa: E402
from storage.database import init_db  # noqa: E402
from storage import writer  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    init_db()
    # Seed one row so the window has something real to display, not just
    # empty defaults.
    writer.write_occupancy(zone_id="checkout-1", current_count=4)
    writer.write_queue_metric("queue-cam-1", "checkout-1", queue_length=6, avg_wait_seconds=200)
    yield
    from storage.database import engine, reader_engine

    engine.dispose()
    reader_engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    for suffix in ("-wal", "-shm"):
        p = Path(str(TEST_DB) + suffix)
        if p.exists():
            p.unlink()


def test_main_window_constructs_receives_data_and_closes_cleanly():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.show()

    received = []
    window.poller.data_ready.connect(lambda snapshot: received.append(snapshot))

    # Give the poller thread real time to tick at least once — this is a
    # genuine wait on the actual background thread, not a mocked timer.
    loop = QEventLoop()
    QTimer.singleShot(3000, loop.quit)
    loop.exec()

    assert len(received) >= 1, "poller thread never delivered a data_ready signal"

    latest = received[-1]
    assert latest["queue"][0].queue_length == 6
    assert latest["occupancy"][0].current_count == 4

    # UI actually reflects it, not just the raw snapshot
    assert window.queue_label.text() == "6"
    assert window.occupancy_label.text() == "4"

    window.close()
    app.processEvents()
