import functools
import json
import logging
from typing import Any

from PySide2 import QtCore, QtGui, QtWidgets
import mincepy

from . import common
from . import db
from . import utils

__all__ = 'QueryModel', 'QueryController'

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class QueryModel(QtCore.QAbstractTableModel):
    # Signals
    type_restriction_changed = QtCore.Signal(object)
    sort_changed = QtCore.Signal(dict)
    query_changed = QtCore.Signal(dict)

    def __init__(self, db_model: db.DatabaseModel, executor=common.default_executor, parent=None):
        super().__init__(parent)
        self._db_model = db_model
        self._query = {}
        self._results = None
        self._sort = None
        self._type_restriction = None
        self._column_names = mincepy.DataRecord._fields
        self._update_future = None
        self._init()

        self._executor = executor
        self._new_results.connect(self._inject_results)

        # If the historian changes then we get invalidated
        self._db_model.historian_changed.connect(lambda hist: self._invalidate_results())

    def _init(self):
        self.set_show_current(True)

    @property
    def db_model(self):
        return self._db_model

    @property
    def column_names(self):
        return self._column_names

    def get_query(self):
        return self._query

    def set_query(self, query: dict):
        """Set the query that will be passed to historian.find()"""
        if query == self._query:
            return

        self._query = query
        self.query_changed.emit(query)
        self._invalidate_results()

    def update_query(self, update: dict):
        new_query = self.get_query().copy()
        new_query.update(update)
        self.set_query(new_query)

    def set_type_restriction(self, type_id):
        if type_id == self.get_type_restriction():
            return

        restriction = {'obj_type': type_id}
        self.update_query(restriction)
        self.type_restriction_changed.emit(self.get_type_restriction())

    def get_type_restriction(self):
        return self.get_query().get('obj_type', None)

    def set_show_current(self, show: bool):
        """Set the query such that it only show current objects i.e. the latest versions of objects
        that have not been deleted"""
        if self.get_show_current() == show:
            return

        if show:
            self._query['version'] = -1
        else:
            self._query.pop('version')

        self.query_changed.emit(self._query)

    def get_show_current(self) -> bool:
        """Get whether we are only showing current objects i.e. the latest version and not deleted
        """
        return self._query.get('version', None) == -1

    def set_sort(self, sort):
        """Set the sort criterion"""
        if sort == self.get_sort():
            return

        self.update_query({'sort': sort})
        self.sort_changed.emit(self.get_sort())

    def get_sort(self):
        return self._query.get('sort', None)

    def get_records(self):
        return self._results

    def refresh(self):
        self._invalidate_results()

    def rowCount(self, _parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if self._results is None:
            return 0

        return len(self._results)

    def columnCount(self, _parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.column_names)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> Any:
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            return self.column_names[section]

        return str(self._results[section])

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> Any:
        if role == QtCore.Qt.DisplayRole:
            value = getattr(self._results[index.row()], self.column_names[index.column()])
            return str(value)

        return None

    def _update_results(self):
        if self._query is None or self._db_model.historian is None:
            self._results = []
        else:
            self._results = []
            self._update_future = self._executor(functools.partial(self._perform_query,
                                                                   self.get_query()),
                                                 msg="Querying...",
                                                 blocking=False)

    def _invalidate_results(self):
        self.beginResetModel()
        self._results = None
        self.endResetModel()
        self._update_results()

    def _perform_query(self, query, batch_size=4):
        logging.debug("Starting query: %s", query)

        total = 0
        batch = []
        for result in self._db_model.historian.find_records(**query):
            batch.append(result)
            if len(batch) == batch_size:
                self._new_results.emit(batch)
                batch = []
            total += 1

        if batch:
            # Emit the last batch
            self._new_results.emit(batch)

        logging.debug('Finished query, got %s results', total)

    _new_results = QtCore.Signal(list)

    @QtCore.Slot(list)
    def _inject_results(self, batch: list):
        """As a query is executed batches of results as emitted and passed to this callback for
        insertion"""
        first = len(self._results)
        last = first + len(batch) - 1
        self.beginInsertRows(QtCore.QModelIndex(), first, last)
        self._results.extend(batch)
        self.endInsertRows()


class QueryController(QtCore.QObject):
    """Controls the query that is being applied on the database"""

    def __init__(self, query_model: QueryModel, query_line: QtWidgets.QLineEdit, parent=None):
        super().__init__(parent)
        self._query_model = query_model
        self._query_line = query_line

        def set_query_edited():
            palette = self._query_line.palette()
            palette.setColor(palette.Base, QtGui.QColor(192, 212, 192))
            query_line.setPalette(palette)

        def reset_query_edited():
            palette = self._query_line.palette()
            palette.setColor(palette.Base, QtGui.QColor(255, 255, 255))
            query_line.setPalette(palette)

        def handle_query_changed(new_query: dict):
            new_text = self._query_to_str(new_query)
            if new_text != self._query_line.text():
                self._query_line.setText(new_text)
            reset_query_edited()

        def handle_query_submitted():
            new_text = self._query_line.text()
            try:
                query = json.loads(new_text, cls=utils.UUIDDecoder)
            except json.decoder.JSONDecodeError as exc:
                QtWidgets.QErrorMessage().showMessage(str(exc))
            else:
                self._query_model.set_query(query)

        def handle_text_edited(_text):
            try:
                current_query = json.dumps(self._query_model.get_query(), cls=utils.UUIDEncoder)
            except json.decoder.JSONDecodeError:
                pass
            else:
                if _text != current_query:
                    set_query_edited()
                else:
                    reset_query_edited()

        self._query_model.query_changed.connect(handle_query_changed)
        self._query_line.returnPressed.connect(handle_query_submitted)
        self._query_line.textEdited.connect(handle_text_edited)

        self._query_line.setText(self._query_to_str(self._query_model.get_query()))

    @staticmethod
    def _query_to_str(query: dict) -> str:
        return json.dumps(query, cls=utils.UUIDEncoder)
