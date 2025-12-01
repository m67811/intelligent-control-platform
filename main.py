"""Entry point for the furnace digital twin."""

import sys

from PyQt5 import QtWidgets

from gui.main_window import MainWindow


def main() -> None:
    """Launch the PyQt application."""
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
