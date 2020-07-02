from concurrent import futures

from PySide2 import QtCore


class Executor(QtCore.QObject):
    """A simple executor that runs tasks on a thread pool and emits signals indicating start and
    completion of tasks"""

    # Task started: msg, num running, num blocking
    task_started = QtCore.Signal(str, int, int)
    # Task ended: the result, num running, num blocking
    task_ended = QtCore.Signal(futures.Future, int, int)

    def __init__(self, parent=QtCore.QModelIndex()):
        super(Executor, self).__init__(parent=parent)
        self._thread_pool = futures.ThreadPoolExecutor()
        self._num_blocking = 0
        self._num_running = 0
        self._tasks = {}

    @property
    def num_running(self):
        return self._num_running

    @property
    def num_blocking(self):
        return self._num_blocking

    def execute(self, func, msg=None, blocking=False) -> futures.Future:
        """Execute a task function optionally displaying a message.  Blocking tasks will result in
        a waiting cursor"""
        future = self._thread_pool.submit(func)
        # Keep track of whether the task is blocking or not
        self._tasks[future] = blocking
        self._num_running += 1
        if blocking:
            self._num_blocking += 1

        self.task_started.emit(msg, self.num_running, self.num_blocking)

        future.add_done_callback(self._task_done)
        return future

    def _task_done(self, future: futures.Future):
        assert self._num_running >= 1
        self._num_running -= 1
        if self._tasks.pop(future):
            assert self._num_blocking >= 1
            self._num_blocking -= 1

        self.task_ended.emit(future, self.num_running, self.num_blocking)
