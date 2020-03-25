from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
import logging

from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2.QtCore import QObject, Qt, Slot, Signal

from . import action_controllers
from . import controllers
from . import extend
from . import models
from . import tree_models
from . import types_controller

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class MainController(QObject):

    def __init__(self, window, default_uri=''):
        super().__init__(window)
        self._window = window
        self._default_uri = default_uri
        self._executor = ThreadPoolExecutor()
        self._tasks = []
        self._action_manager = extend.ActionManager()
        self._action_context = {
            action_controllers.CONTEXT_CLIPBOARD: QtGui.QGuiApplication.clipboard()
        }
        self._copier = None
        self._load_plugins()

        # Models
        self._create_models()

        # Views
        self._init_views(window)

        # Controllers
        self._create_controllers(window)

        self._init_shortcuts()
        self._task_done_signal.connect(self._task_done)
        self._status_bar.showMessage('Ready')

    def _load_plugins(self):
        logger.info("Starting loading plugins")
        self._action_manager.load_plugins()
        actioners = self._action_manager.get_actioners(name='copy-actioner')
        if actioners:
            # Somewhat arbitrarily just use the last one
            self._copier = partial(actioners[-1].do, 'copy', context=self._action_context)

        logger.info("Finished loading plugins")

    def _init_shortcuts(self):
        ctrl_c = QtGui.QKeySequence("Ctrl+C")

        QtWidgets.QShortcut(ctrl_c, self._window.splitter, self._copy)

    @Slot()
    def _copy(self):
        if not self._copier:
            return

        if self._window.entries_table.hasFocus():
            self._entries_table_controller.handle_copy(self._copier)
        elif self._window.entry_details.hasFocus():
            self._entry_details_controller.handle_copy(self._copier)

    def _create_models(self):
        self._db_model = models.DbModel()
        self._query_model = models.DataRecordQueryModel(self._db_model, self._execute, parent=self)
        self._entries_table = models.EntriesTable(self._query_model, parent=self)
        self._entry_details = tree_models.RecordTree(parent=self)

    def _init_views(self, window):
        window.entries_table.setSortingEnabled(True)
        window.entries_table.setModel(self._entries_table)
        window.entry_details.setModel(self._entry_details)

        self._init_display_as_class(window)
        window.refresh_button.clicked.connect(self._entries_table.refresh)

        # Keep out status bar
        self._status_bar = window.status_bar  # type: QtWidgets.QStatusBar

    def _init_display_as_class(self, window):
        window.display_as_class.stateChanged.connect(
            lambda state: self._entries_table.set_show_as_objects(state == Qt.Checked))
        self._entries_table.set_show_as_objects(window.display_as_class.checkState() == Qt.Checked)

    def _create_controllers(self, window):
        controllers.DatabaseController(self._db_model,
                                       window.uri_line,
                                       window.connect_button,
                                       default_uri=self._default_uri,
                                       executor=self._execute,
                                       parent=self)
        controllers.QueryController(self._query_model, window.query_line, parent=self)

        action_controller = action_controllers.ActionController(self._action_manager,
                                                                context=self._action_context,
                                                                executor=self._executor,
                                                                parent=self)

        # Entries table
        self._entries_table_controller = controllers.EntriesTableController(self._entries_table,
                                                                            window.entries_table,
                                                                            parent=self)
        self._entries_table_controller.context_menu_requested.connect(
            action_controller.trigger_context_menu)

        # Entry details
        self._entry_details_controller = controllers.EntryDetailsController(self._entries_table,
                                                                            window.entries_table,
                                                                            window.entry_details,
                                                                            self._entry_details,
                                                                            parent=self)
        self._entry_details_controller.context_menu_requested.connect(
            action_controller.trigger_context_menu)

        types_controller.TypeFilterController(self._query_model, window.type_filter, parent=self)

    def _execute(self, func, msg=None, blocking=False) -> Future:
        future = self._executor.submit(func)
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor if blocking else Qt.BusyCursor)
        self._tasks.append(future)
        future.add_done_callback(self._task_done_signal.emit)
        if msg is not None:
            self._status_bar.showMessage(msg)

        return future

    _task_done_signal = Signal(Future)

    @Slot(object)
    def _object_activated(self, obj):
        if self._app_common.type_viewers:
            self._execute(partial(self._app_common.call_viewers, obj),
                          msg="Calling viewer",
                          blocking=True)

    @Slot(Future)
    def _task_done(self, future):
        self._tasks.remove(future)
        QtWidgets.QApplication.restoreOverrideCursor()

        if not self._tasks:
            self._status_bar.clearMessage()

        try:
            new_msg = future.result()
            if new_msg is not None:
                self._status_bar.showMessage(new_msg, 1000)
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QErrorMessage(self._window).showMessage(str(exc))
