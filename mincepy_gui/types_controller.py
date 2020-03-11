import mincepy
from PySide2.QtCore import QObject
from PySide2.QtWidgets import QComboBox, QCompleter
from PySide2 import QtWidgets

from . import common
from . import models


class TypeFilterController(QObject):
    """Drop down combo box that lists the types available in archive"""
    ALL = None

    def __init__(self,
                 query_model: models.DataRecordQueryModel,
                 view: QtWidgets.QComboBox = None,
                 executor=common.default_executor,
                 parent=None):
        super().__init__(parent)
        self._view = self._configure_view(view or QComboBox(self))
        self._query_model = query_model
        self._executor = executor

        query_model.db_model.historian_changed.connect(self._update)

        self._types = [None]

    def _configure_view(self, view):
        view.setEditable(True)
        view.addItem(self.ALL)

        def handle_index_changed(index):
            if index >= 0:
                restrict_type = self._types[index]
                self._query_model.set_type_restriction(restrict_type)

        view.currentIndexChanged.connect(handle_index_changed)

        return view

    @property
    def _historian(self):
        return self._query_model.db_model.historian

    def _update(self):
        self._view.clear()
        self._executor(self._gather_types, "Gathering types", blocking=False)

    def _gather_types(self):
        results = self._historian.get_archive().find()
        self._types = [None]
        self._types.extend(list(set(result.type_id for result in results)))

        type_names = self._get_type_names(self._types)

        self._view.addItems(type_names)
        completer = QCompleter(type_names)
        self._view.setCompleter(completer)

    def _get_type_names(self, types):
        type_names = []
        for type_id in types:
            try:
                helper = self._historian.get_helper(type_id)
            except TypeError:
                type_names.append(str(type_id))
            else:
                type_names.append(mincepy.analysis.get_type_name(helper.TYPE))

        return type_names
