import itertools
import logging
from typing import Iterator, Any, List, Optional, Callable, Sequence

from PySide2 import QtCore, QtWidgets, QtGui
import mincepy

from . import columns as cols
from . import common

__all__ = ('EntryTableModel',)

logger = logging.getLogger(__name__)


class ConstEntryTable(QtCore.QAbstractTableModel):
    """Read-only view of the entries table model"""
    DEFAULT_BATCH_SIZE = 128

    sort_requested = QtCore.Signal(str, QtCore.Qt.SortOrder)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._historian = None  # type: Optional[mincepy.Historian]
        self._records = []  # type: List[mincepy.DataRecord]
        self._columns = []  # type: List[cols.Column]
        self._data_source = None  # type: Optional[Iterator[mincepy.DataRecord]]
        self.batch_size = self.DEFAULT_BATCH_SIZE

    @property
    def columns(self):
        return self._columns

    @property
    def records(self) -> List[mincepy.DataRecord]:
        return self._records

    def get_record(self, row):
        if row < 0 or row >= len(self._records):
            return None

        return self._records[row]

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...) -> Any:
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            if section < 0 or section >= len(self._columns):
                return None
            return self._columns[section].name

        if orientation == QtCore.Qt.Orientation.Vertical:
            if section < 0 or section >= len(self._records):
                return None
            return str(section)

        return None

    def rowCount(self, _parent: QtCore.QModelIndex = ...) -> int:
        return len(self._records)

    def columnCount(self, _parent: QtCore.QModelIndex = ...) -> int:
        return len(self._columns)

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None

        if index.row() >= len(self._records) or index.row() < 0:
            return None

        if index.column() >= len(self._columns) or index.column() < 0:
            return None

        col = self._columns[index.column()]
        return col.data(self._records[index.row()], role, self._historian)

    def sort(self, column: int, order: QtCore.Qt.SortOrder = ...):
        if column < 0 or column > len(self._columns):
            return

        col = self._columns[column]
        if not isinstance(col, cols.DataColumn):
            return

        self.sort_requested.emit(".".join(col.path), order)


class EntryTableModel(ConstEntryTable):
    """Mutable entries table to be used by controllers"""

    @staticmethod
    def get_default_columns() -> List[cols.Column]:
        return [cols.OBJ_TYPE, cols.CTIME, cols.MTIME, cols.VERSION]

    def __init__(self, parent=None):
        super().__init__(parent)
        # Append the default columns
        self.append_columns(*self.get_default_columns())

    def canFetchMore(self, _parent: QtCore.QModelIndex) -> bool:
        return self._data_source is not None

    def fetchMore(self, _parent: QtCore.QModelIndex):
        # Fetch the new records
        if self._data_source is None:
            return

        new_records = []
        try:
            for _ in range(self.batch_size):
                new_records.append(next(self._data_source))
        except StopIteration:
            # No more data
            self._data_source = None

        if new_records:
            # Insert the new records
            num_records = len(self._records)
            self.beginInsertRows(QtCore.QModelIndex(), num_records,
                                 num_records + len(new_records) - 1)
            self._records.extend(new_records)
            self.endInsertRows()

    def set_source(self, source: Optional[Iterator[mincepy.DataRecord]],
                   historian: Optional[mincepy.Historian]):
        """Set a new data source, can be None.  This resets the records contained in the list and
        sets it to be populated from the new source"""
        self.beginRemoveRows(QtCore.QModelIndex(), 0, len(self._records) - 1)
        self._records = []
        self._data_source = source
        self._historian = historian
        self.endRemoveRows()
        if source is not None:
            self.fetchMore(QtCore.QModelIndex())

    def append_columns(self, *columns: cols.Column):
        self.beginInsertColumns(QtCore.QModelIndex(), len(self._columns),
                                len(self._columns) + len(columns) - 1)
        self._columns.extend(columns)
        self.endInsertColumns()

    def remove_columns(self, *columns: cols.Column):
        for col in columns:
            idx = self._columns.index(col)
            self.beginRemoveColumns(QtCore.QModelIndex(), idx, idx)
            self._columns.pop(idx)
            self.endRemoveColumns()

    def set_columns(self, columns: Sequence[cols.Column]):
        self.clear_columns()
        self.append_columns(*columns)

    def clear_columns(self):
        self.beginRemoveColumns(QtCore.QModelIndex(), 0, len(self._columns) - 1)
        self._columns = []
        self.endRemoveColumns()

    def remove_records(self, index: int, count: int) -> bool:
        """Remove 'count' records starting at the given index"""
        if index < 0 or index >= len(self._records) or count <= 0:
            return False

        end_idx = min(len(self._records), index + count)
        self.beginRemoveRows(QtCore.QModelIndex(), index, end_idx - 1)
        for i in range(index, end_idx):
            del self._records[i]
        self.endRemoveRows()

        return True

    def remove_record(self, index: int) -> bool:
        """Remove the record at the given index"""
        return self.remove_records(index, 1)

    def reset(self):
        self.beginResetModel()
        self._records = []
        self._columns = self.get_default_columns()
        self._data_source = None
        self.endResetModel()


class EntryTableController(QtCore.QObject):
    """Controller for the table showing database entries"""
    DATA_RECORDS = 'Data Record(s)'
    VALUES = 'Values(s)'

    context_menu_requested = QtCore.Signal(dict, QtCore.QPoint)

    def __init__(self,
                 entries_table: EntryTableModel,
                 entries_table_view: QtWidgets.QTableView,
                 show_as_objects_checkbox: QtWidgets.QCheckBox = None,
                 parent=None):
        """
        :param entries_table: the entries table model
        :param entries_table_view: the entries table view
        :param parent: the parent widget
        """
        super().__init__(parent)
        self._entry_table = entries_table  # type: EntryTableModel
        self._entry_table_view = entries_table_view
        self._columns_to_remove = []

        # Disable for now, not supported
        show_as_objects_checkbox.setEnabled(False)

        # Configure the view
        self._entry_table_view.setModel(self._entry_table)
        self._entry_table_view.setContextMenuPolicy(QtGui.Qt.CustomContextMenu)

        # Connect everything
        self._entry_table_view.customContextMenuRequested.connect(self._entries_context_menu)
        self._entry_table.rowsInserted.connect(self._handle_rows_inserted)
        self._entry_table.rowsAboutToBeRemoved.connect(self._handle_rows_about_to_be_removed)

    @property
    def entry_table(self) -> ConstEntryTable:
        """Returns a read-only view of the entry table"""
        return self._entry_table

    def get_selected(self) -> dict:
        """Get the currently selected data records (row(s)) and values (cell(s))"""
        groups = {}
        selected = self._entry_table_view.selectionModel().selectedIndexes()

        rows = {index.row() for index in selected}
        rows = sorted(tuple(rows))
        data_records = tuple(self._entry_table.get_record(row) for row in rows)

        if data_records:
            groups[self.DATA_RECORDS] = data_records if len(data_records) > 1 else data_records[0]

        objects = tuple(self._entry_table.data(index, role=common.DataRole) for index in selected)
        if objects:
            groups[self.VALUES] = objects if len(objects) > 1 else objects[0]

        return groups

    def handle_copy(self, copier: callable):
        if not copier:
            return

        selected = self._entry_table_view.selectionModel().selectedIndexes()
        if selected:
            rows = {index.row() for index in selected}
            data_records = tuple(self._entry_table.get_record(row) for row in rows)
            # Convert to scalar if needed
            data_records = data_records if len(data_records) > 1 else data_records[0]
            copier(data_records)

    def set_source(self, source: Optional[Iterator[mincepy.DataRecord]],
                   historian: mincepy.Historian):
        """Set the source for the entry table"""
        self._entry_table.set_source(source, historian)

    def reset(self):
        self._entry_table.reset()

    def remove_matching_records(self, match_filter: Callable[[mincepy.DataRecord], bool]) -> bool:
        """Delete the records that match the given filter criteria"""
        deleted = False
        idx = 0
        while idx < len(self._entry_table.records):
            record = self._entry_table.records[idx]
            if match_filter(record):
                self._entry_table.remove_record(idx)
                deleted = True
                # Don't up the counter as everything will have shifted by one in deleting
            else:
                idx += 1
        return deleted

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def _handle_rows_inserted(self, _parent: QtCore.QModelIndex, start_row: int, end_row: int):
        """Find which new columns are needed now that these new records have been inserted"""
        state_keys = set()
        for row in range(start_row, end_row + 1):
            record = self._entry_table.get_record(row)
            if isinstance(record.state, dict):
                state_keys.update(record.state.keys())

        for col in self._entry_table.columns:
            if isinstance(col, cols.DataColumn) \
                    and len(col.path) == 2 \
                    and col.path[0] == mincepy.STATE:
                state_keys.discard(col.path[1])

        new_cols = []
        for new_state_key in state_keys:
            path = mincepy.STATE, new_state_key
            new_cols.append(cols.DataColumn(".".join(path), path))
        self._entry_table.append_columns(*new_cols)

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def _handle_rows_about_to_be_removed(self, _parent: QtCore.QModelIndex, start_row: int,
                                         end_row: int):
        """Find and remove the columns that will no longer be needed once these records are removed
        """
        to_remove = set()
        for row in range(start_row, end_row + 1):
            record = self._entry_table.get_record(row)
            if isinstance(record.state, dict):
                to_remove.update(record.state.keys())

        for row in itertools.chain(range(0, start_row),
                                   range(end_row + 1, len(self._entry_table.records))):
            record = self._entry_table.get_record(row)
            to_remove -= record.state.keys()
            if not to_remove:
                break

        for col in self._entry_table.columns:
            if isinstance(col, cols.DataColumn) \
                    and len(col.path) == 2 \
                    and col.path[0] == mincepy.STATE \
                    and col.path[1] in to_remove:
                self._columns_to_remove.append(col)
        self._entry_table.remove_columns(*self._columns_to_remove)
        self._columns_to_remove = []

    @QtCore.Slot(QtCore.QPoint)
    def _entries_context_menu(self, point: QtCore.QPoint):
        groups = self.get_selected()
        self.context_menu_requested.emit(groups, self._entry_table_view.mapToGlobal(point))
