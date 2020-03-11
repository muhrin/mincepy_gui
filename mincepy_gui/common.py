from concurrent.futures import Future

from PySide2.QtCore import Qt
from pytray.futures import capture_exceptions

__all__ = ('DataRole',)


def default_executor(func, msg=None, blocking=False):  # pylint: disable=unused-argument
    future = Future()
    with capture_exceptions(future):
        future.set_result(func())

    return future


# Role to get the actual data associated with an index
DataRole = Qt.UserRole  # pylint: disable=invalid-name
