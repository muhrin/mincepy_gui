import functools
from typing import Optional

from PySide2 import QtWidgets, QtCore
import mincepy

from . import common
from . import utils


class TypeFilterController(QtCore.QObject):
    """Drop down combo box that lists the types available in archive"""
    ALL = None

    type_restriction_changed = QtCore.Signal(object)

    def __init__(self,
                 view: QtWidgets.QComboBox = None,
                 executor=common.default_executor,
                 parent=None):
        super().__init__(parent)
        self._view = self._configure_view(view or QtWidgets.QComboBox(self))
        self._executor = executor
        self._types = [None]
        self._updating = None
        self._view.setEnabled(False)

    def _configure_view(self, view):
        view.setEditable(True)
        view.addItem(self.ALL)

        view.currentIndexChanged.connect(self._handle_index_changed)

        return view

    def update(self, historian: Optional[mincepy.Historian]):
        self._view.clear()
        if historian is None:
            self._view.setEnabled(False)
            return

        self._updating = self._executor(functools.partial(self._gather_types, historian),
                                        "Gathering types",
                                        blocking=False)

        def on_done(fut):
            if fut is self._updating:
                self._updating = None
                if not fut.cancelled():
                    self._view.setEnabled(True)

        self._updating.add_done_callback(on_done)

    def _gather_types(self, historian: mincepy.Historian):
        """Function to get the types available in the database"""
        self._types = [None] + list(historian.find_distinct(mincepy.TYPE_ID))
        type_names = self._get_type_names(self._types, historian)

        self._view.addItems(type_names)
        completer = QtWidgets.QCompleter(type_names)
        self._view.setCompleter(completer)

    @staticmethod
    def _get_type_names(types: list, historian: mincepy.Historian):
        type_names = []
        for type_id in types:
            try:
                helper = historian.get_helper(type_id)
            except TypeError:
                type_names.append(str(type_id))
            else:
                type_names.append(utils.pretty_type_string(helper.TYPE))

        return type_names

    def _handle_index_changed(self, index: int):
        if index >= 0:
            restrict_type = self._types[index]
            self.type_restriction_changed.emit(restrict_type)
