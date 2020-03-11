from PySide2.QtCore import QObject, QPoint, Slot
from PySide2 import QtWidgets

from . import common
from . import extend


class ActionController(QObject):

    def __init__(self,
                 action_manager: extend.ActionerManager,
                 context=None,
                 executor=common.default_executor,
                 parent=None):
        super().__init__(parent)
        self._action_manager = action_manager
        self._context = context or {}
        self._executor = executor

    @Slot(dict, QPoint)
    def trigger_context_menu(self, groups: dict, where: QPoint):
        menu = QtWidgets.QMenu()
        for group, value in groups.items():
            actions = self._action_manager.probe(value, self._context)
            for name, actioner in actions:
                menu.addAction(name, lambda: actioner.do(name, value, self._context))
        if menu.actions():
            menu.exec_(where)
