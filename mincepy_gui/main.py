# File: main.py

from pathlib import Path
import sys

from PySide2.QtUiTools import QUiLoader
from PySide2 import QtWidgets
from PySide2.QtCore import QFile

from . import main_controller

RESOURCES = Path('../res/')

if __name__ == "__main__":
    # pylint: disable=invalid-name

    app = QtWidgets.QApplication(sys.argv)

    ui_file = QFile(str(RESOURCES / "mainwindow.ui"))
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    main_controller = main_controller.MainController(window)

    window.show()

    sys.exit(app.exec_())
