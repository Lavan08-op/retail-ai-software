"""Main control-room window. Contains NO business logic — per architecture
rule 4 (PySide6 must not contain business logic), everything shown here is
just a rendering of what DataPoller reads from storage.repositories."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from control_room.workers import DataPoller


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retail AI — Control Room")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        kpi_box = QGroupBox("Live Metrics")
        kpi_layout = QGridLayout(kpi_box)
        self.occupancy_label = QLabel("—")
        self.queue_label = QLabel("—")
        self.entries_label = QLabel("—")
        self.exits_label = QLabel("—")
        for row, (title, value_label) in enumerate(
            [
                ("Latest Occupancy", self.occupancy_label),
                ("Latest Queue Length", self.queue_label),
                ("Entries (24h)", self.entries_label),
                ("Exits (24h)", self.exits_label),
            ]
        ):
            kpi_layout.addWidget(QLabel(title), row, 0)
            value_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            kpi_layout.addWidget(value_label, row, 1)
        layout.addWidget(kpi_box)

        alerts_box = QGroupBox("Active Alerts")
        alerts_layout = QVBoxLayout(alerts_box)
        self.alerts_list = QListWidget()
        alerts_layout.addWidget(self.alerts_list)
        layout.addWidget(alerts_box)

        self.status_label = QLabel("Waiting for first data refresh…")
        layout.addWidget(self.status_label)

        # Local audio/visual alert only — deliberately NOT dependent on
        # RabbitMQ (per the master prompt: local computer alerts must work
        # even if RabbitMQ is unavailable). Tracks which alert_ids we've
        # already beeped for so a still-active alert doesn't beep every
        # single poll tick.
        self._beeped_alert_ids: set[str] = set()

        # The poller runs on its own thread; this window only ever reacts
        # to its data_ready signal, which Qt delivers back on the UI
        # thread automatically — no manual locking needed here.
        self.poller = DataPoller(interval_seconds=2.0)
        self.poller.data_ready.connect(self.on_data_ready)
        self.poller.start()

    def on_data_ready(self, snapshot: dict) -> None:
        occupancy = snapshot["occupancy"]
        queue = snapshot["queue"]
        alerts = snapshot["alerts"]
        entry_exit = snapshot["entry_exit"]

        self.occupancy_label.setText(str(occupancy[0].current_count) if occupancy else "—")
        self.queue_label.setText(str(queue[0].queue_length) if queue else "—")
        self.entries_label.setText(str(entry_exit.get("in", 0)))
        self.exits_label.setText(str(entry_exit.get("out", 0)))

        self.alerts_list.clear()
        new_critical_alert = False
        for alert in alerts:
            self.alerts_list.addItem(QListWidgetItem(f"[{alert.severity.upper()}] {alert.message}"))
            if alert.severity == "critical" and alert.alert_id not in self._beeped_alert_ids:
                new_critical_alert = True
            self._beeped_alert_ids.add(alert.alert_id)

        if new_critical_alert:
            QApplication.beep()

        self.status_label.setText(f"Last updated — {len(alerts)} active alert(s)")

    def closeEvent(self, event) -> None:
        self.poller.stop()
        self.poller.wait(3000)
        super().closeEvent(event)
