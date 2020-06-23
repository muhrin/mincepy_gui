import json
import logging

from PySide2 import QtCore, QtGui, QtWidgets

from . import utils

__all__ = 'QueryView', 'QueryController'

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class QueryView(QtCore.QObject):
    """Read-only view on the query model"""
    # Signals
    type_restriction_changed = QtCore.Signal(object)
    sort_changed = QtCore.Signal(dict)
    query_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = {}
        self._sort = None
        self._type_restriction = None

    def get_query(self):
        return self._query

    def get_type_restriction(self):
        return self.get_query().get('obj_type', None)

    def get_sort(self):
        return self._query.get('sort', None)


class QueryModel(QueryView):
    """Mutable query model"""

    def set_query(self, query: dict):
        """Set the query that will be passed to historian.find()"""
        if query == self._query:
            return

        self._query = query
        self.query_changed.emit(query)

    def set_sort(self, sort):
        """Set the sort criterion"""
        if sort == self.get_sort():
            return

        self.update_query({'sort': sort})
        self.sort_changed.emit(self.get_sort())

    def set_type_restriction(self, type_id):
        """Restrict the query to this type only"""
        if type_id == self.get_type_restriction():
            return

        restriction = {'obj_type': type_id}
        self.update_query(restriction)
        self.type_restriction_changed.emit(self.get_type_restriction())

    def update_query(self, update):
        new_query = self.get_query().copy()
        new_query.update(update)
        self.set_query(new_query)


class QueryController(QtCore.QObject):
    """Controller for the query model"""

    # Signals
    type_restriction_changed = QtCore.Signal(object)
    sort_changed = QtCore.Signal(dict)
    query_changed = QtCore.Signal(dict)

    def __init__(self, query_model: QueryModel, query_line: QtWidgets.QLineEdit, parent=None):
        super().__init__(parent)

        self._query_model = query_model
        self._query_line = query_line

        # Connect everything
        self._query_model.query_changed.connect(self._handle_query_changed)
        self._query_line.returnPressed.connect(self._handle_query_submitted)
        self._query_line.textEdited.connect(self._handle_text_edited)

        self._query_line.setText(self._query_to_str(self._query_model.get_query()))

    @property
    def query_model(self) -> QueryView:
        """Returns a read-only view of the query model"""
        return self._query_model

    def set_query(self, query: dict):
        """Set the query that will be passed to historian.find()"""
        self._query_model.set_query(query)

    def set_sort(self, sort):
        """Set the sort criterion"""
        self._query_model.set_sort(sort)

    def set_type_restriction(self, type_id):
        """Restrict the query to this type only"""
        self._query_model.set_type_restriction(type_id)

    def update_query(self, update: dict):
        """Update the query dictionary"""
        self._query_model.update_query(update)

    @staticmethod
    def _query_to_str(query: dict) -> str:
        return json.dumps(query, cls=utils.UUIDEncoder)

    def _set_query_edited(self):
        palette = self._query_line.palette()
        palette.setColor(palette.Base, QtGui.QColor(192, 212, 192))
        self._query_line.setPalette(palette)

    def _reset_query_edited(self):
        palette = self._query_line.palette()
        palette.setColor(palette.Base, QtGui.QColor(255, 255, 255))
        self._query_line.setPalette(palette)

    def _handle_query_changed(self, new_query: dict):
        new_text = self._query_to_str(new_query)
        if new_text != self._query_line.text():
            self._query_line.setText(new_text)
        self._reset_query_edited()

    def _handle_query_submitted(self, *_args):
        new_text = self._query_line.text()
        try:
            query = json.loads(new_text, cls=utils.UUIDDecoder)
        except json.decoder.JSONDecodeError as exc:
            QtWidgets.QErrorMessage().showMessage(str(exc))
        else:
            self._query_model.set_query(query)

    def _handle_text_edited(self, _text):
        try:
            current_query = json.dumps(self._query_model.get_query(), cls=utils.UUIDEncoder)
        except json.decoder.JSONDecodeError:
            pass
        else:
            if _text != current_query:
                self._set_query_edited()
            else:
                self._reset_query_edited()
