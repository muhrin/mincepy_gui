from functools import partial
import json

from PySide2.QtCore import QObject, Signal, Slot, QPoint
from PySide2 import QtWidgets, QtGui
import mincepy

from . import common
from . import models
from . import tree_models
from . import utils


class DatabaseController(QObject):
    """Controls the connection to the database"""

    _historian_created = Signal(mincepy.Historian)

    def __init__(self,
                 db_model: models.DbModel,
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

        self._historian_created.connect(self._db_model.set_historian)
        self._connect_button.clicked.connect(self._handle_connect)
        self._uri_line.returnPressed.connect(self._handle_connect)

    def _handle_connect(self):
        uri = self._uri_line.text()
        self._executor(partial(self._connect, uri), "Connecting", blocking=True)

    def _connect(self, uri):
        try:
            historian = mincepy.historian(uri)
        except Exception as exc:
            err_msg = "Error creating historian with uri '{}':\n{}".format(uri, exc)
            raise RuntimeError(err_msg)
        else:
            self._historian_created.emit(historian)

        return "Connected to {}".format(uri)


class QueryController(QObject):
    """Controls the query that is being applied on the database"""

    def __init__(self,
                 query_model: models.DataRecordQueryModel,
                 query_line: QtWidgets.QLineEdit,
                 parent=None):
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


class EntryDetailsController(QObject):
    """Controller that set what is displayed in the details tree"""

    context_menu_requested = Signal(dict, QPoint)

    def __init__(self,
                 entries_table: models.EntriesTable,
                 entries_table_view: QtWidgets.QTableView,
                 entry_details_view: QtWidgets.QTreeWidget,
                 entry_details: tree_models.RecordTree = None,
                 parent=None):
        super().__init__(parent)
        self._entries_table = entries_table
        self._entries_table_view = entries_table_view
        self._entry_details_view = entry_details_view
        self._entry_details = entry_details or tree_models.RecordTree(self)

        # Configure the view
        self._entry_details_view.setContextMenuPolicy(QtGui.Qt.CustomContextMenu)
        self._entry_details_view.customContextMenuRequested.connect(self._entry_context_menu)

        def handle_row_changed(current, _previous):
            record = self._entries_table.get_record(current.row())
            snapshot = self._entries_table.get_snapshot(current.row())
            self._entry_details.set_record(record, snapshot)

        self._entries_table_view.selectionModel().currentRowChanged.connect(handle_row_changed)

    def handle_copy(self, copier: callable):
        objects = self._get_currently_selected_objects()
        if not objects:
            return

        objects = objects if len(objects) > 1 else objects[0]
        copier(objects)

    @Slot(QPoint)
    def _entry_context_menu(self, point: QPoint):
        objects = self._get_currently_selected_objects()
        if objects:
            groups = {}
            groups['Objects'] = objects if len(objects) > 1 else objects[0]
            self.context_menu_requested.emit(groups, self._entry_details_view.mapToGlobal(point))

    def _get_currently_selected_objects(self):
        # We just want the value, we don't care about the other columns
        value_col = tree_models.RecordTree.COLUMN_HEADERS.index('Value')
        selected = tuple(
            index for index in self._entry_details_view.selectionModel().selectedIndexes()
            if index.column() == value_col)

        return tuple(self._entry_details.data(index, role=common.DataRole) for index in selected)


class EntriesTableController(QObject):
    """Controller for the table showing database entries"""
    DATA_RECORDS = 'Data Record(s)'
    VALUES = 'Values(s)'

    context_menu_requested = Signal(dict, QPoint)

    def __init__(self,
                 entries_table: models.EntriesTable,
                 entries_table_view: QtWidgets.QTableView,
                 parent=None):
        """
        :param entries_table: the entries table model
        :param entries_table_view: the entries table view
        :param parent: the parent widget
        """
        super().__init__(parent)
        self._entries_table = entries_table
        self._entries_table_view = entries_table_view

        # Configure the view
        self._entries_table_view.setContextMenuPolicy(QtGui.Qt.CustomContextMenu)
        self._entries_table_view.customContextMenuRequested.connect(self._entries_context_menu)

    def get_selected(self) -> dict:
        groups = {}
        selected = self._entries_table_view.selectionModel().selectedIndexes()

        rows = {index.row() for index in selected}
        rows = sorted(tuple(rows))
        data_records = tuple(self._entries_table.get_record(row) for row in rows)

        if data_records:
            groups[self.DATA_RECORDS] = data_records if len(data_records) > 1 else data_records[0]

        objects = tuple(self._entries_table.data(index, role=common.DataRole) for index in selected)
        if objects:
            groups[self.VALUES] = objects if len(objects) > 1 else objects[0]

        return groups

    def handle_copy(self, copier: callable):
        if not copier:
            return

        selected = self._entries_table_view.selectionModel().selectedIndexes()
        if selected:
            rows = {index.row() for index in selected}
            data_records = tuple(self._entries_table.get_record(row) for row in rows)
            # Convert to scalar if needed
            data_records = data_records if len(data_records) > 1 else data_records[0]
            copier(data_records)

    @Slot(QPoint)
    def _entries_context_menu(self, point: QPoint):
        groups = self.get_selected()
        self.context_menu_requested.emit(groups, self._entries_table_view.mapToGlobal(point))
