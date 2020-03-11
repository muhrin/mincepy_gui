# File: main.py

from pathlib import Path
import sys

from PySide2.QtUiTools import QUiLoader
from PySide2 import QtWidgets
from PySide2.QtCore import QFile

from . import main_controllers

__all__ = ('start',)

RESOURCES = Path(__file__).parent / 'res'


def start():
    app = QtWidgets.QApplication(sys.argv)

    ui_file = QFile(str(RESOURCES / "mainwindow.ui"))
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    main_controllers.MainController(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    start()
