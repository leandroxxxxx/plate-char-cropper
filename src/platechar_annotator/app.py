"""Application initialization and coordination."""

import sys

from PySide6.QtWidgets import QApplication

from platechar_annotator.ui.main_window import MainWindow


def run() -> int:
    """Create the Qt application, show the main window, and run the event loop."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()