from concurrent.futures import Future

from PySide2.QtCore import Qt
from pytray.futures import capture_exceptions

import mincepy

__all__ = 'default_executor', 'default_create_historian'


def default_executor(func, msg=None, blocking=False):  # pylint: disable=unused-argument
    future = Future()
    with capture_exceptions(future):
        future.set_result(func())

    return future


def default_create_historian(uri) -> mincepy.Historian:
    historian = mincepy.historian(uri)
    mincepy.set_historian(historian)
    return historian


# Role to get the actual data associated with an index
DataRole = Qt.UserRole  # pylint: disable=invalid-name
