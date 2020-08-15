import json
import logging
from typing import List, Optional

from PySide2 import QtCore, QtGui, QtWidgets

from . import utils

__all__ = 'QueryView', 'QueryController'

logger = logging.getLogger(__name__)


class QueryView(QtCore.QObject):
    """Read-only view on the query model"""
    # Signals
    type_restriction_changed = QtCore.Signal(object)
    sort_changed = QtCore.Signal(dict)
    query_changed = QtCore.Signal(dict)
    obj_id_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = {}
        self._sort = None
        self._obj_id = None

    def get_query(self):
        return self._query

    def get_type_restriction(self):
        return self.get_query().get('obj_type', None)

    def get_sort(self):
        return self._query.get('sort', None)

    def get_obj_id(self) -> Optional[List]:
        return self._query.get('obj_id', None)


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

    def set_obj_id(self, obj_id: Optional[List]):
        if obj_id == self.get_obj_id():
            return

        if obj_id:
            # Don't update the query, rather reset, because if you're passing object ids you
            # probably  want to see those specific objects even if they don't match the other
            # criteria currently being used
            self.set_query({'obj_id': obj_id})
        elif 'obj_id' in self._query:
            # Just remove the object id filter from the query
            query = self._query.copy()
            query.pop('obj_id')
            self.set_query(query)

        self.obj_id_changed.emit(self.get_obj_id())

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

    def __init__(self,
                 query_model: QueryModel,
                 query_line: QtWidgets.QLineEdit,
                 obj_id_line: QtWidgets.QLineEdit,
                 parent=None):
        super().__init__(parent)

        self._query_model = query_model
        self._query_line = query_line
        self._obj_ids_line = obj_id_line

        # Initialise everything
        # Query model
        self._query_model.query_changed.connect(self._handle_query_changed)

        # Query line
        self._query_line.returnPressed.connect(self._handle_query_submitted)
        self._query_line.textEdited.connect(self._handle_text_edited)
        self._query_line.setText(self._query_to_str(self._query_model.get_query()))

        # Object IDs line
        self._obj_ids_line.returnPressed.connect(self._handle_obj_id_pressed)

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
        """Called when the query is being edited but has not yet been submitted"""
        palette = self._query_line.palette()
        palette.setColor(palette.Base, QtGui.QColor(192, 212, 192))
        self._query_line.setPalette(palette)

    def _reset_query_edited(self):
        """Called when the query has been submitted"""
        palette = self._query_line.palette()
        palette.setColor(palette.Base, QtGui.QColor(255, 255, 255))
        self._query_line.setPalette(palette)

    def _handle_query_changed(self, new_query: dict):
        """Called when the query in the query model changes"""
        new_text = self._query_to_str(new_query)
        if new_text != self._query_line.text():
            self._query_line.setText(new_text)

        obj_ids_str = self._obj_ids_to_str(new_query.get('obj_id', None))
        if obj_ids_str != self._obj_ids_line.text():
            self._obj_ids_line.setText(obj_ids_str)

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

    def _handle_obj_id_pressed(self, *_args):
        """Return was pressed on the obj id text line"""
        self._query_model.set_obj_id(self._get_obj_ids())

    def _get_obj_ids(self) -> List[str]:
        """Get the obj ids as a list from what's in the obj id line"""
        line = self._obj_ids_line.text()
        return self._str_to_obj_ids(line)

    def _set_obj_ids_line(self, obj_ids: Optional[List[str]]):
        """Set the object ids line"""
        line = '' if not obj_ids else " ".join(obj_ids)
        self._obj_ids_line.setText(line)

    @staticmethod
    def _obj_ids_to_str(obj_ids: Optional[List[str]]) -> str:
        """Convert an object ids list to a string"""
        return '' if not obj_ids else " ".join(obj_ids)

    @staticmethod
    def _str_to_obj_ids(line: str) -> Optional[List[str]]:
        """Convert a string to an object ids list"""
        if not line:
            return None

        return [entry.strip() for entry in line.split(' ')]
