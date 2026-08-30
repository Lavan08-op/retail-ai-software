"""Entry point for the PySide6 control room. Run with:
python -m control_room.main
"""

import sys

from PySide6.QtWidgets import QApplication

from control_room.windows.main_window import MainWindow
from storage.database import init_db


def main() -> None:
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
