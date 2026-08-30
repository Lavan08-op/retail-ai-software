"""Background polling for the control room. Runs on its own QThread and
reads from storage.repositories — never storage.database or storage.writer
directly, same read-only rule as Streamlit. Communicates results back to
the UI thread ONLY via the data_ready signal; never touches a Qt widget
from run() itself, which is the one rule that actually matters for Qt
thread-safety."""

from PySide6.QtCore import QThread, Signal

from storage import repositories


class DataPoller(QThread):
    data_ready = Signal(dict)

    def __init__(self, interval_seconds: float = 2.0, parent=None):
        super().__init__(parent)
        self.interval_seconds = interval_seconds
        self._running = True

    def run(self) -> None:
        while self._running:
            snapshot = {
                "occupancy": repositories.recent_occupancy(limit=10),
                "queue": repositories.recent_queue_metrics(limit=10),
                "alerts": repositories.active_alerts(),
                "entry_exit": repositories.entry_exit_counts(),
            }
            self.data_ready.emit(snapshot)
            self.msleep(int(self.interval_seconds * 1000))

    def stop(self) -> None:
        self._running = False
