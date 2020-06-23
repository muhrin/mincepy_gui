from pathlib import Path
from typing import Iterable, Optional
import tempfile

from PySide2 import QtWidgets

import mincepy

from . import action_controllers
from . import plugins
from . import utils

# pylint: disable=invalid-name


class TextActioner(plugins.Actioner):

    # pylint: disable=no-self-use

    @property
    def name(self):
        return "text-actioner"

    def probe(self, obj, _context) -> Optional[Iterable[str]]:
        if isinstance(obj, mincepy.File):
            return ('View File',)

        return None

    def do(self, action: str, obj: mincepy.File, _context: dict):
        if action == 'View File':
            folder = Path(tempfile.mkdtemp())
            obj.to_disk(folder)
            utils.open_file(folder / obj.filename)


class DataRecordActioner(plugins.Actioner):
    """Knows how to perform actions on data records"""

    # pylint: disable=no-self-use

    @property
    def name(self):
        return "data-record-actioner"

    def probe(self, obj, _context) -> Optional[Iterable[str]]:
        if isinstance(obj, mincepy.DataRecord):
            return ("Delete",)

        if isinstance(obj, Iterable) \
                and all(map(lambda val: isinstance(val, mincepy.DataRecord), obj)):
            count = len(tuple(obj))
            return ("Delete {}".format(count),)

        return None

    def do(self, _action, obj, context):
        to_delete = []
        if isinstance(obj, mincepy.DataRecord):
            to_delete.append(obj.obj_id)
        elif isinstance(obj, Iterable):
            to_delete.extend([record.obj_id for record in obj])

        parent = context[action_controllers.ActionContext.PARENT]
        db_controller = context[action_controllers.ActionContext.DATABASE]

        ret = QtWidgets.QMessageBox.warning(
            parent, "Delete confirmation", "Delete {} object(s)?".format(len(to_delete)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
        if ret == QtWidgets.QMessageBox.Yes:
            try:
                db_controller.delete_objects(*to_delete)
            except mincepy.NotFound as exc:
                QtWidgets.QMessageBox.warning(parent, "Not found", str(exc))


class CopyActioner(plugins.Actioner):
    """Knows how to copy things to the clipboard"""

    # pylint: disable=no-self-use

    @property
    def name(self):
        return "copy-actioner"

    def probe(self, obj, _context: dict) -> Optional[Iterable[str]]:
        actions = []
        if isinstance(obj, mincepy.DataRecord):
            actions.append("Copy Object ID")
        elif hasattr(obj, '__str__'):
            actions.append("Copy")

        return actions

    def do(self, _action, obj, context: dict):
        clipboard = context.get(action_controllers.ActionContext.CLIPBOARD, None)
        if clipboard is not None:
            if isinstance(obj, mincepy.DataRecord):
                clipboard.setText(str(obj.obj_id))
            else:
                clipboard.setText(str(obj))


class TestActioner(plugins.Actioner):
    enabled = False
    actions = []

    # pylint: disable=no-self-use

    @property
    def name(self):
        return "test-actioner"

    def probe(self, _obj, _context: dict) -> Optional[Iterable[str]]:
        if self.enabled:
            return self.actions

        return None

    def do(self, action, obj, context: dict):
        print("Action '{}' called with object: \n'{}' and context \n'{}'".format(
            action, obj, context))


def get_actioners():
    return (CopyActioner(), TextActioner(), DataRecordActioner(), TestActioner())
