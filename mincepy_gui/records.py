"""Module containing classes for listing records in the database"""

import collections
import logging
from typing import Optional, Dict, Any, Sequence

from PySide2 import QtCore, QtGui, QtWidgets
from pytray import tree
import mincepy

from . import common
from . import query
from . import utils

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

UNSET = ''  # The value printed for records that don't have a particular attribute

TOOLTIPS = {
    mincepy.TYPE_ID: 'Object type',
    mincepy.CREATION_TIME: 'Creation time',
    mincepy.SNAPSHOT_TIME: 'Last modification time',
    mincepy.VERSION: 'Version',
}

SnapshotRecord = collections.namedtuple("SnapshotRecord", 'snapshot record')


class EntriesTable(QtCore.QAbstractTableModel):
    """A model showing records from the database"""
    DEFAULT_COLUMNS = (mincepy.TYPE_ID, mincepy.CREATION_TIME, mincepy.SNAPSHOT_TIME,
                       mincepy.VERSION, mincepy.STATE)

    object_activated = QtCore.Signal(object)

    def __init__(self, query_model: query.QueryModel, parent=None):
        super().__init__(parent)
        self._query_model = query_model
        self._query_model.modelReset.connect(self._invalidate)
        self._query_model.rowsInserted.connect(self._query_rows_inserted)

        self._columns = list(self.DEFAULT_COLUMNS)
        self._show_objects = True

        self._snapshots_cache = {}  # type: Dict[mincepy.SnapshotId, object]

    def get_records(self):
        return self._query_model.get_records()

    @property
    def query_model(self):
        return self._query_model

    def get_record(self, row) -> Optional[mincepy.DataRecord]:
        if row < 0 or row >= self.rowCount():
            return None

        return self.get_records()[row]

    def get_snapshot(self, row: int):
        ref = self.get_record(row).snapshot_id
        if ref not in self._snapshots_cache:
            historian = self._query_model.db_model.historian
            try:
                self._snapshots_cache[ref] = historian.load_snapshot(ref)
            except TypeError as exc:
                logger.info("Failed to load snapshot for reference '%s'\n%s", ref, exc)
                self._snapshots_cache[ref] = None

        return self._snapshots_cache[ref]

    def get_show_as_objects(self):
        return self._show_objects

    def set_show_as_objects(self, as_objects):
        if self._show_objects != as_objects:
            self._show_objects = as_objects
            # Remove the old columns, if there are any to be removed
            if len(self._columns) > len(self.DEFAULT_COLUMNS):
                first = len(self.DEFAULT_COLUMNS)
                last = len(self._columns) - 1

                self.beginRemoveColumns(QtCore.QModelIndex(), first, last)
                self._reset_columns()
                self.endRemoveColumns()

            # Now add the new ones
            columns = set()
            for row in range(self.rowCount()):
                columns.update(self._get_columns_for(row))

            if columns:
                # Convert to list and sort alphabetically
                new_columns = list(columns)
                new_columns.sort()
                self._insert_columns(new_columns)

    def refresh(self):
        # Ask the query to refresh from the database
        self._query_model.refresh()

    def rowCount(self, _parent: QtCore.QModelIndex = ...) -> int:
        return self._query_model.rowCount()

    def columnCount(self, _parent: QtCore.QModelIndex = ...) -> int:
        return len(self._columns)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> Any:
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            if section >= len(self._columns):
                return None
            return self._columns[section]

        if orientation == QtCore.Qt.Orientation.Vertical:
            return str(section)

        return None

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> Any:
        column_name = self._columns[index.column()]
        if role == common.DataRole:
            return self._get_value(index.row(), index.column())
        if role == QtCore.Qt.DisplayRole:
            return self._get_value_string(index.row(), index.column())
        if role == QtCore.Qt.FontRole:
            if column_name in mincepy.DataRecord._fields:
                font = QtGui.QFont()
                font.setItalic(True)
                return font
        if role == QtCore.Qt.ToolTipRole:
            try:
                return TOOLTIPS[column_name]
            except KeyError:
                pass

        return None

    def sort(self, column: int, order: QtCore.Qt.SortOrder = ...):
        column_name = self._columns[column]
        try:
            sort_criterion = column_name
        except KeyError:
            if self._show_objects:
                # We can't deal with sorting objects at the moment
                return
            sort_criterion = "state.{}".format(column_name)

        sort_dict = {
            sort_criterion:
                mincepy.ASCENDING if order == QtCore.Qt.AscendingOrder else mincepy.DESCENDING
        }
        self._query_model.set_sort(sort_dict)

    @QtCore.Slot(QtCore.QModelIndex)
    def activate_entry(self, index: QtCore.QModelIndex):
        obj = self.data(index, role=common.DataRole)
        if obj is not None and obj != UNSET:
            self.object_activated.emit(obj)

    def _invalidate(self):
        self.beginResetModel()
        self._snapshots_cache = {}
        self._reset_columns()
        self.endResetModel()

    def _get_snapshot_state(self, record):
        if self._show_objects:
            historian = self._query_model.db_model.historian
            try:
                return historian.load_snapshot(record.snapshot_id)
            except TypeError:
                pass  # Fall back to displaying the state

        return record.state

    def _get_columns_for(self, row: int) -> tuple:
        if self.get_show_as_objects():
            obj = self.get_snapshot(row)
            try:
                return utils.obj_dict(obj).keys()
            except TypeError:
                pass
        else:
            state = self.get_record(row).state
            if isinstance(state, dict):
                return tuple("state.{}".format(key) for key in state)

        return ()

    def _get_value(self, row: int, column: int) -> Any:
        """Get a value for a given row and column index"""
        column_name = self._columns[column]
        if not column_name:
            return UNSET

        column_path = column_name.split('.')
        record = self.get_record(row)

        if column_path[0] in record._fields:
            try:
                record_value = tree.get_by_path(record._asdict(), column_path)
            except (KeyError, IndexError, TypeError):
                # Probably trying to access the state using path from a different object type
                return UNSET

            # Special case to show type ids as the class name
            if column_name == mincepy.TYPE_ID:
                try:
                    historian = self._query_model.db_model.historian
                    return historian.get_obj_type(record_value)
                except TypeError:
                    pass
            return record_value

        # The column is a custom attribute of the item
        if self.get_show_as_objects():
            snapshot = self.get_snapshot(row)
            try:
                return utils.obj_dict(snapshot).get(column_name, UNSET)
            except TypeError:
                pass

        return UNSET

    def _get_value_string(self, row: int, column: int) -> str:
        value = self._get_value(row, column)
        return utils.pretty_format(value, single_line=True, max_length=100)

    def _query_rows_inserted(self, _parent: QtCore.QModelIndex, first: int, last: int):
        """Called when there are new entries inserted into the entries table"""

        self.beginInsertRows(QtCore.QModelIndex(), first, last)

        columns = set()  # Keep track of all the columns in this batch
        for row in range(first, last + 1):
            columns.update(self._get_columns_for(row))

        self.endInsertRows()

        # Check if the columns need updating
        columns -= set(self._columns)
        if columns:
            # There are new columns to insert
            cols = list(columns)
            cols.sort()
            self._insert_columns(cols)

    def _insert_columns(self, new_columns: Sequence):
        """Add new columns to our existing ones"""
        first_col = len(self._columns)
        last_col = first_col + len(new_columns) - 1
        self.beginInsertColumns(QtCore.QModelIndex(), first_col, last_col)
        self._columns.extend(new_columns)
        self.endInsertColumns()

    def _reset_columns(self):
        """Reset the columns back to the default internally.  This should only be done between
        either a model invalidation or appropriate removeColumns call
        """
        self._columns = list(self.DEFAULT_COLUMNS)


class EntriesTableController(QtCore.QObject):
    """Controller for the table showing database entries"""
    DATA_RECORDS = 'Data Record(s)'
    VALUES = 'Values(s)'

    context_menu_requested = QtCore.Signal(dict, QtCore.QPoint)

    def __init__(self,
                 entries_table: EntriesTable,
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

    @QtCore.Slot(QtCore.QPoint)
    def _entries_context_menu(self, point: QtCore.QPoint):
        groups = self.get_selected()
        self.context_menu_requested.emit(groups, self._entries_table_view.mapToGlobal(point))
