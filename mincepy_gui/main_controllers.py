from concurrent import futures
from functools import partial
import logging

from PySide2 import QtGui, QtCore, QtWidgets
from PySide2.QtCore import Qt
import mincepy

from . import action_controllers
from . import db
from . import extend
from . import executors
from . import entry_details
from . import entry_table
from . import query
from . import types_controller

__all__ = ('MainController',)

logger = logging.getLogger(__name__)


class MainController(QtCore.QObject):

    def __init__(self, window, default_uri=''):
        super().__init__(window)
        self._window = window
        self._default_uri = default_uri

        # Set up the executor
        self._executor = executors.Executor(parent=self)
        self._executor.task_started.connect(self._task_started)
        self._executor.task_ended.connect(self._task_ended)

        self._action_manager = extend.ActionManager()
        self._action_context = {
            action_controllers.ActionContext.PARENT: self._window,
            action_controllers.ActionContext.CLIPBOARD: QtGui.QGuiApplication.clipboard()
        }
        self._copier = None
        self._load_plugins()

        # Keep reference to our status bar
        self._status_bar = window.status_bar  # type: QtWidgets.QStatusBar

        # Controllers
        self._create_controllers(window)

        self._init_shortcuts()
        window.refresh_button.clicked.connect(self._execute_current_query)
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

    def _create_controllers(self, window):
        # Database
        self._db_controller = self._create_database_controller(window)
        # Actions
        action_controller = self._create_actions_controller(self._db_controller,
                                                            self._action_context)
        # Results table
        self._results_table_controller = self._create_results_table(
            window, action_controller, self._db_controller.database_model)
        # Query
        self._query_controller = self._create_query_controller(window)
        # Type filter
        self._type_filter_controller = self._create_type_filter_controller(
            window, self._query_controller)
        # Entry details
        self._entry_details_controller = self._create_entry_details(
            window, action_controller, self._results_table_controller.entry_table)

    def _create_actions_controller(self, db_controller: db.DatabaseController, action_context):
        action_context[action_controllers.ActionContext.DATABASE] = db_controller
        return action_controllers.ActionController(self._action_manager,
                                                   context=self._action_context,
                                                   executor=self._executor.execute,
                                                   parent=self)

    def _create_database_controller(self, window):
        # Create model
        db_model = db.DatabaseModel()

        # Create controller
        db_controller = db.DatabaseController(db_model,
                                              window.uri_line,
                                              window.connect_button,
                                              default_uri=self._default_uri,
                                              executor=self._executor.execute,
                                              parent=self)

        # Connect everything
        db_controller.historian_created.connect(self._handle_historian_created)
        return db_controller

    def _create_results_table(self, window, action_controller, db_model: db.ConstDatabaseModel):
        # Create the model
        results_table_model = entry_table.EntryTableModel(parent=self)

        # Create the controller
        results_table_controller = entry_table.EntryTableController(results_table_model,
                                                                    window.entries_table,
                                                                    window.display_as_class,
                                                                    parent=self)

        # Connect everything up

        # When a query completes, update the results table
        self._query_completed.connect(results_table_controller.set_source)

        # Respond to context menu requests from the results table
        results_table_controller.context_menu_requested.connect(
            action_controller.trigger_context_menu)

        @QtCore.Slot(list)
        def handle_objects_deleted(obj_ids: list):
            to_check = set(obj_ids)
            results_table_controller.remove_matching_records(
                lambda record: record.obj_id in to_check)

        db_model.objects_deleted.connect(handle_objects_deleted)

        # Respond to requests to sort the results table
        window.entries_table.setSortingEnabled(True)
        results_table_model.sort_requested.connect(self._handle_query_sort_requested)

        return results_table_controller

    def _create_query_controller(self, window):
        # Create the model
        query_model = query.QueryModel(parent=self)

        # Create the controller
        query_controller = query.QueryController(query_model,
                                                 window.query_line,
                                                 window.obj_id_line,
                                                 parent=self)

        # Connect everything up
        query_model.query_changed.connect(lambda _new_query: self._execute_current_query())

        return query_controller

    def _create_type_filter_controller(self, window, query_controller):
        # Create the controller (using internal model from view)
        type_filter_controller = types_controller.TypeFilterController(
            window.type_filter, executor=self._executor.execute, parent=self)

        # Connect everything up
        type_filter_controller.type_restriction_changed.connect(
            query_controller.set_type_restriction)

        return type_filter_controller

    def _create_entry_details(self, window, action_controller,
                              results_table: entry_table.ConstEntryTable):
        # Create the model
        entry_details_model = entry_details.EntryDetails(parent=self)
        # Link model and view
        window.entry_details.setModel(entry_details_model)

        # Create the controller
        entry_details_controller = entry_details.EntryDetailsController(results_table,
                                                                        window.entries_table,
                                                                        window.entry_details,
                                                                        entry_details_model,
                                                                        parent=self)

        # Connect everything up
        entry_details_controller.context_menu_requested.connect(
            action_controller.trigger_context_menu)

        return entry_details_controller

    @QtCore.Slot(str, int, int)
    def _task_started(self, msg: str, _num_running: int, num_blocking: int):
        """Execute a task function optionally displaying a message.  Blocking tasks will result in
        a waiting cursor"""
        # Set the cursor
        cursor = Qt.WaitCursor if num_blocking > 0 else Qt.BusyCursor
        app = QtWidgets.QApplication
        current_override = app.overrideCursor()
        if current_override is None:
            app.setOverrideCursor(cursor)
        elif current_override != cursor:
            app.changeOverrideCursor(cursor)

        # Set the status message
        if msg is not None:
            self._status_bar.showMessage(msg)

    @QtCore.Slot(futures.Future)
    def _task_ended(self, future: futures.Future, num_running: int, num_blocking: int):
        cursor = Qt.WaitCursor if num_blocking > 0 else Qt.BusyCursor
        app = QtWidgets.QApplication
        current_override = app.overrideCursor()
        if num_running == 0:
            app.restoreOverrideCursor()
        elif current_override != cursor:
            app.setOverrideCursor(cursor)

        try:
            new_msg = future.result()
            if new_msg is not None:
                self._status_bar.showMessage(new_msg, 1000)
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QErrorMessage(self._window).showMessage(str(exc))

    # Signals
    _query_completed = QtCore.Signal(object, mincepy.Historian)

    @QtCore.Slot()
    def _copy(self):
        if not self._copier:
            return

        if self._window.entries_table.hasFocus():
            self._results_table_controller.handle_copy(self._copier)
        elif self._window.entry_details.hasFocus():
            self._entry_details_controller.handle_copy(self._copier)

    @QtCore.Slot()
    def _execute_current_query(self):
        historian = self._db_controller.database_model.historian
        if historian is None:
            return

        def execute_query():
            query_model = self._query_controller.query_model
            results = historian.find_records(**query_model.get_query())
            self._query_completed.emit(results, historian)

        self._executor.execute(execute_query, "Querying...", blocking=False)

    @QtCore.Slot(mincepy.Historian)
    def _handle_historian_created(self, historian: mincepy.Historian):
        mincepy.set_historian(historian)
        self._results_table_controller.reset()
        self._entry_details_controller.reset(historian)
        self._type_filter_controller.update(historian)
        self._execute_current_query()

    @QtCore.Slot(dict)
    def _handle_query_changed(self, _new_query: dict):
        self._execute_current_query()

    @QtCore.Slot(str, QtCore.Qt.SortOrder)
    def _handle_query_sort_requested(self, path, order):
        if order == QtCore.Qt.SortOrder.AscendingOrder:
            sort = {path: mincepy.ASCENDING}
        elif order == QtCore.Qt.SortOrder.DescendingOrder:
            sort = {path: mincepy.DESCENDING}
        else:
            return

        self._query_controller.set_sort(sort)
