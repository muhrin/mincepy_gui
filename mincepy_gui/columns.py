import abc
import functools
from typing import Sequence, Union

from PySide2 import QtCore, QtGui
from pytray import tree

import mincepy
from . import common
from . import utils

__all__ = 'Column', 'DataColumn', 'OBJ_ID', 'OBJ_TYPE', 'VERSION', 'CTIME', 'MTIME'

DEFAULT_FORMATTER = functools.partial(utils.pretty_format, single_line=True, max_length=100)


class Column(metaclass=abc.ABCMeta):

    def __init__(self, name: str, formatter=DEFAULT_FORMATTER, tooltip=None):
        self.name = name
        self.formatter = formatter
        self.tooltip = tooltip

    def data(self, record: mincepy.DataRecord, role: int, historian: mincepy.Historian = None):
        # pylint: disable=unused-argument
        """Return the data corresponding to the the given record, for the given role"""
        if role == QtCore.Qt.ToolTipRole:
            return self.tooltip

        return None


class DataColumn(Column):
    """Column that returns data directly from a mincepy record itself"""

    def __init__(self,
                 name: str,
                 path: Sequence = None,
                 formatter=DEFAULT_FORMATTER,
                 tooltip: str = None):
        super().__init__(name, formatter=formatter, tooltip=tooltip)
        self._path = path or [name]

    @property
    def path(self):
        return self._path

    def data(self, record: mincepy.DataRecord, role: int, historian: mincepy.Historian = None):
        if role in [common.DataRole, QtCore.Qt.DisplayRole]:
            entry = getattr(record, self._path[0])
            if len(self._path) > 1:
                # If there is more to the path then descend using getitem()
                try:
                    entry = tree.get_by_path(entry, self._path[1:])
                except (KeyError, IndexError, TypeError):
                    return None

            if role == common.DataRole:
                return entry

            # DisplayRole
            return self.formatter(entry)

        if role == QtCore.Qt.FontRole:
            # Show the top level in italic
            if self._path[0] in mincepy.DataRecord._fields:
                font = QtGui.QFont()
                font.setItalic(True)
                return font

        return super(DataColumn, self).data(record, role, historian=historian)


class TypeColumn(DataColumn):
    """Column for getting the type id"""

    def __init__(self, name: str, tooltip: str = None):
        super(TypeColumn, self).__init__(name, [mincepy.TYPE_ID], tooltip=tooltip)

    def data(self, record: mincepy.DataRecord, role: int, historian: mincepy.Historian = None):
        if role in [common.DataRole, QtCore.Qt.DisplayRole]:
            if historian is None:
                return super(TypeColumn, self).data(record, role, historian)

            type_id = record.type_id
            try:
                obj_type = historian.get_obj_type(type_id)
            except TypeError:
                return super(TypeColumn, self).data(record, role, historian)
            else:
                if role == common.DataRole:
                    return obj_type

                # DisplayRole
                return self.formatter(obj_type)

        return super().data(record, role, historian=historian)


def data_column(path: Union[str, Sequence], name=None, **kwargs) -> DataColumn:
    """Helper for constructing columns.  Will automatically create name from a path if not supplied
    """
    if isinstance(path, str):
        path = (path,)

    if name is None:
        name = ".".join(path)
    return DataColumn(name, path=path, **kwargs)


OBJ_ID = data_column(mincepy.OBJ_ID, tooltip='Object ID')
OBJ_TYPE = TypeColumn('Obj type', tooltip="Object type")
CTIME = data_column(mincepy.CREATION_TIME, tooltip="Creation time")
MTIME = data_column(mincepy.SNAPSHOT_TIME, tooltip="Modification time")
VERSION = data_column(mincepy.VERSION, tooltip="Version")
