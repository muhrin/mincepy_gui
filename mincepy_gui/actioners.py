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
            return ("Delete Record",)
        if isinstance(obj, Iterable) \
                and all(map(lambda val: isinstance(val, mincepy.DataRecord), obj)):
            return ("Delete Records",)

        return None

    def do(self, action, obj, context):
        pass


def get_actioners():
    return (TextActioner(), DataRecordActioner())
