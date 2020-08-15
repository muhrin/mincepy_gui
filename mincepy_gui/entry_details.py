"""Module for display details about a database entry"""
from abc import ABCMeta, abstractmethod
import operator
import typing
from typing import Sequence, Mapping, Optional

from PySide2 import QtCore, QtWidgets, QtGui
import mincepy

from . import common
from . import entry_table
from . import utils


class BaseTreeItem(metaclass=ABCMeta):

    def __init__(self, column_data: Sequence, parent=None):
        self._data = column_data
        self._strings = tuple(
            utils.pretty_format(datum, single_line=True, max_length=300) for datum in column_data)
        self._parent = parent

    def data(self, column: int):
        """Get the data at the given column"""
        if column < 0 or column >= self.column_count():
            return None

        return self._data[column]

    def string(self, column: int):
        """Get the string representation for the given column"""
        if column < 0 or column >= self.column_count():
            return None

        return self._strings[column]

    def row(self) -> int:
        """Get the row of this item within its parent"""
        if self._parent is None:
            return 0

        return self._parent.child_row(self)

    def column_count(self) -> int:
        """Get the number of columns in this item"""
        return len(self._data)

    def parent(self):
        """Get the parent of this tree item"""
        return self._parent

    @abstractmethod
    def child(self, row: int):
        """Get the child at the given row"""

    @abstractmethod
    def child_count(self) -> int:
        """Get the number of children this item has"""

    @abstractmethod
    def child_row(self, tree_item) -> int:
        """Get the row number given a child item"""


class DataTreeItem(BaseTreeItem):
    """Tree item that directly sores the required data internally"""

    def __init__(self, column_data: Sequence, parent=None):
        super().__init__(column_data, parent)
        self._children = []

    def append_child(self, child):
        self._children.append(child)

    def child(self, row: int):
        if row < 0 or row >= self.child_count():
            return None

        return self._children[row]

    def child_count(self) -> int:
        return len(self._children)

    def child_row(self, tree_item) -> int:
        return self._children.index(tree_item)


class LazyMappingItem(BaseTreeItem):

    def __init__(self, column_data: Sequence, raw_data, child_builder, num_children, parent=None):
        super(LazyMappingItem, self).__init__(column_data, parent)
        self._raw_data = raw_data
        self._child_builder = child_builder
        self._num_children = num_children
        self._children = {}

    def child_count(self) -> int:
        return self._num_children

    def child(self, row: int):
        if row < 0 or row >= self.child_count():
            return None

        if row not in self._children:
            self._children[row] = self._child_builder(self._raw_data, row, self)
            if len(self._children) == self._num_children:
                # Can discard the raw data and builder now
                self._raw_data = None
                self._child_builder = None

        return self._children[row]

    def child_row(self, tree_item) -> int:
        for row, child in self._children.items():
            if tree_item is child:
                return row
        raise ValueError("'{}' is not a child".format(tree_item))


class EntryDetails(QtCore.QAbstractItemModel):
    COLUMN_HEADERS = 'Property', 'Type', 'Value'

    object_activated = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_item = DataTreeItem(self.COLUMN_HEADERS)
        self._data_record = None  # type: typing.Optional[mincepy.DataRecord]

    @QtCore.Slot(QtCore.QModelIndex)
    def activate_entry(self, index: QtCore.QModelIndex):
        obj = self.data(index, role=common.DataRole)
        if obj:
            self.object_activated.emit(obj)

    def index(self,
              row: int,
              column: int,
              parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> \
            QtCore.QModelIndex:
        if parent.isValid():
            parent_item = parent.internalPointer()  # type: BaseTreeItem
        else:
            parent_item = self._root_item

        child_item = parent_item.child(row)
        if child_item is not None:
            return self.createIndex(row, column, child_item)

        return QtCore.QModelIndex()

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not child.isValid():
            return QtCore.QModelIndex()

        child_item = child.internalPointer()  # type: DataTreeItem
        parent_item = child_item.parent()  # type: DataTreeItem

        if parent_item is self._root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, _parent: QtCore.QModelIndex = ...) -> int:
        return self._root_item.column_count()

    def data(self, index: QtCore.QModelIndex, role: int = ...) -> typing.Any:
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole:
            item = index.internalPointer()  # type: BaseTreeItem
            return item.string(index.column())
        if role == common.DataRole:
            return index.internalPointer().data(index.column())

        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return super(EntryDetails, self).flags(index)

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: int = ...) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._root_item.data(section)

        return None

    def set_record(self, record: mincepy.DataRecord, obj: object = None, snapshot: object = None):
        """Set the data to visualise, the object instance can optionally be provided"""
        self.beginResetModel()
        self._data_record = record
        # Now build the three
        if self._data_record is None:
            self._root_item = DataTreeItem(self.COLUMN_HEADERS)
        else:
            tree_dict = {'record': record._asdict()}
            if obj is not None:
                tree_dict['obj'] = obj
            if obj is not None:
                tree_dict['snapshot'] = snapshot

            self._root_item = LazyMappingItem(self.COLUMN_HEADERS, tree_dict, self._item_builder,
                                              len(tree_dict))
        self.endResetModel()

    def reset(self):
        if self._data_record is not None:
            self.beginResetModel()
            self._root_item = DataTreeItem(self.COLUMN_HEADERS)
            self._data_record = None
            self.endResetModel()

    def _item_builder(self, build_from, row, parent=None) -> BaseTreeItem:
        if isinstance(build_from, Sequence):
            key = str(row)
            try:
                child = build_from[row]
            except Exception as exc:  # pylint: disable=broad-except
                child = "Error getting child: {}".format(exc)
        elif isinstance(build_from, Mapping):
            entry = sorted(build_from.items(), key=operator.itemgetter(0))[row]
            key, child = str(entry[0]), entry[1]
        else:
            raise TypeError("Type '{}' does not support children")

        column_data = (key, utils.pretty_type_string(type(child)), child)

        # Is the child nested?
        nested_child_data = None
        if isinstance(child, str):
            pass
        elif isinstance(child, (Sequence, Mapping)):
            # We have a sequence or mapping
            nested_child_data = child
        else:
            try:
                nested_child_data = utils.obj_dict(child)
            except TypeError:
                pass

        if nested_child_data is not None:
            # We have a nested child so get a lazy item
            return LazyMappingItem(column_data, nested_child_data, self._item_builder,
                                   len(nested_child_data), parent)

        # Fall back to a plain unnested item
        return DataTreeItem(column_data, parent)


class EntryDetailsController(QtCore.QObject):
    """Controller that set what is displayed in the details tree"""

    context_menu_requested = QtCore.Signal(dict, QtCore.QPoint)

    def __init__(self,
                 entries_table: entry_table.ConstEntryTable,
                 entries_table_view: QtWidgets.QTableView,
                 entry_details_view: QtWidgets.QTreeWidget,
                 details_tree: EntryDetails = None,
                 parent=None):
        super().__init__(parent)
        self._entries_table = entries_table
        self._entries_table_view = entries_table_view
        self._details_tree_view = entry_details_view
        self._details_tree = details_tree or EntryDetails(self)
        self._historian = None

        # Configure the view
        self._details_tree_view.setContextMenuPolicy(QtGui.Qt.CustomContextMenu)
        self._details_tree_view.customContextMenuRequested.connect(self._entry_context_menu)

        # Connect everything
        self._entries_table_view.selectionModel().currentRowChanged.connect(
            self._handle_row_changed)

    def handle_copy(self, copier: callable):
        objects = self._get_currently_selected_objects()
        if not objects:
            return

        objects = objects if len(objects) > 1 else objects[0]
        copier(objects)

    @QtCore.Slot(QtCore.QPoint)
    def _entry_context_menu(self, point: QtCore.QPoint):
        objects = self._get_currently_selected_objects()
        if objects:
            groups = {}
            groups['Objects'] = objects if len(objects) > 1 else objects[0]
            self.context_menu_requested.emit(groups, self._details_tree_view.mapToGlobal(point))

    def _get_currently_selected_objects(self):
        # We just want the value, we don't care about the other columns
        value_col = EntryDetails.COLUMN_HEADERS.index('Value')
        selected = tuple(
            index for index in self._details_tree_view.selectionModel().selectedIndexes()
            if index.column() == value_col)

        return tuple(self._details_tree.data(index, role=common.DataRole) for index in selected)

    def reset(self, historian: Optional[mincepy.Historian]):
        self._historian = historian
        self._details_tree.reset()

    def _handle_row_changed(self, current, _previous):
        record = self._entries_table.get_record(current.row())
        if record is None:
            self._details_tree.reset()
            return

        obj = snapshot = None
        if self._historian is not None:
            try:
                obj = self._historian.load(record.obj_id)
            except TypeError:
                pass
            try:
                snapshot = self._historian.load_snapshot(record.snapshot_id)
            except TypeError:
                pass

        self._details_tree.set_record(record, obj, snapshot)
