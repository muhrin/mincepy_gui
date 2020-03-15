from pathlib import Path
from typing import Iterable, Optional
import tempfile

import mincepy

from . import plugins
from . import utils


class TextActioner(plugins.Actioner):

    @property
    def name(self):
        return "text-actioner"

    def probe(self, obj, context) -> Optional[Iterable[str]]:
        if isinstance(obj, mincepy.File):
            return ('View File',)

        return None

    def do(self, action: str, obj: mincepy.File, context: dict):
        if action == 'View File':
            folder = Path(tempfile.mkdtemp())
            obj.to_disk(folder)
            utils.open_file(folder / obj.filename)


class DataRecordActioner(plugins.Actioner):
    """Knows how to perform actions on data records"""

    @property
    def name(self):
        return "data-record-actioner"

    def probe(self, obj, context) -> Optional[Iterable[str]]:
        if isinstance(obj, mincepy.DataRecord):
            return ("Delete",)
        if isinstance(obj, Iterable) \
                and all(map(lambda val: isinstance(val, mincepy.DataRecord), obj)):
            count = len(tuple(obj))
            return ("Delete {}".format(count),)

        return None

    def do(self, action, obj, context):
        pass


class CopyActioner(plugins.Actioner):
    """Knows how to copy things to the clipboard"""

    @property
    def name(self):
        return "copy-actioner"

    def probe(self, obj, context: dict) -> Optional[Iterable[str]]:
        actions = []
        if isinstance(obj, mincepy.DataRecord):
            actions.append("Copy Object ID")
        elif hasattr(obj, '__str__'):
            actions.append("Copy")

        return actions

    def do(self, action, obj, context: dict):
        clipboard = context.get('clipboard', None)
        if isinstance(obj, mincepy.DataRecord):
            clipboard.setText(str(obj.obj_id))
        else:
            clipboard.setText(str(obj))


class TestActioner(plugins.Actioner):
    enabled = False
    actions = []

    @property
    def name(self):
        return "test-actioner"

    def probe(self, obj, context: dict) -> Optional[Iterable[str]]:
        if self.enabled:
            return self.actions

    def do(self, action, obj, context: dict):
        print("Action '{}' called with object: \n'{}' and context \n'{}'".format(
            action, obj, context))


def get_actioners():
    return (CopyActioner(), TextActioner(), DataRecordActioner(), TestActioner())
