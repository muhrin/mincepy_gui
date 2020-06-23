import functools

from PySide2 import QtCore, QtWidgets
import mincepy

from . import common

__all__ = 'DatabaseModel', 'DatabaseController'


class ConstDatabaseModel(QtCore.QObject):
    # Signals
    historian_changed = QtCore.Signal(mincepy.Historian)
    objects_deleted = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._historian = None

    @property
    def historian(self) -> mincepy.Historian:
        return self._historian


class DatabaseModel(ConstDatabaseModel):

    @QtCore.Slot(mincepy.Historian)
    def set_historian(self, historian):
        self._historian = historian
        self.historian_changed.emit(self._historian)

    def delete(self, *obj_id):
        """Delete objects with the passed ids from the database"""
        deleted = []
        try:
            with self.historian.transaction():
                for entry in obj_id:
                    self.historian.delete(entry)
                    deleted.append(entry)
        finally:
            if deleted:
                self.objects_deleted.emit(deleted)


class DatabaseController(QtCore.QObject):
    """Controls the connection to the database"""

    historian_created = QtCore.Signal(mincepy.Historian)

    # pylint: disable=too-many-arguments
    def __init__(self,
                 db_model: DatabaseModel,
                 uri_line: QtWidgets.QLineEdit,
                 connect_button: QtWidgets.QPushButton,
                 default_uri='',
                 executor=common.default_executor,
                 parent=None):
        super().__init__(parent)
        self._db_model = db_model
        self._uri_line = uri_line
        self._connect_button = connect_button
        self._executor = executor

        self._uri_line.setText(default_uri)

        self.historian_created.connect(self._db_model.set_historian)
        self._connect_button.clicked.connect(self._handle_connect)
        self._uri_line.returnPressed.connect(self._handle_connect)

    @property
    def database_model(self) -> ConstDatabaseModel:
        return self._db_model

    def _handle_connect(self):
        uri = self._uri_line.text()
        self._executor(functools.partial(self._connect, uri), "Connecting", blocking=True)

    def _connect(self, uri):
        try:
            historian = mincepy.create_historian(uri)
        except Exception as exc:
            err_msg = "Error creating historian with uri '{}':\n{}".format(uri, exc)
            raise RuntimeError(err_msg)
        else:
            self.historian_created.emit(historian)

        return "Connected to {}".format(uri)

    def delete_objects(self, *obj_id):
        self._db_model.delete(*obj_id)
