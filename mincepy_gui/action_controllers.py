import enum
from functools import partial
from typing import Mapping, Iterable

from PySide2.QtCore import QObject, QPoint, Slot
from PySide2 import QtWidgets

from . import common
from . import extend

__all__ = ('CONTEXT_CLIPBOARD', 'ActionContext')


class AutoNumber(enum.Enum):

    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class ActionContext(AutoNumber):
    PARENT = ()
    CLIPBOARD = ()
    DATABASE = ()


CONTEXT_CLIPBOARD = ActionContext.CLIPBOARD


class ActionController(QObject):
    """Controller that is responsible for actions"""

    def __init__(self,
                 action_manager: extend.ActionManager,
                 context=None,
                 executor=common.default_executor,
                 parent=None):
        super().__init__(parent)
        self._action_manager = action_manager
        self._context = context or {}
        self._executor = executor

    @Slot(dict, QPoint)
    def trigger_context_menu(self, groups: Mapping[str, Iterable], where: QPoint):
        """Request a context menu at the given qpoint that can respond to the objects given in the
        passed groups.  Groups should be a dictionary that maps a group name (str) to an iterable
        of objects to be acted on by actioners."""
        menu = QtWidgets.QMenu()
        for group, obj in groups.items():
            group_created = False
            actions = self._action_manager.probe(obj, self._context)
            for name, actioner in actions:
                if not group_created:
                    menu.addSection(group)
                    group_created = True

                menu.addAction(name, partial(actioner.do, name, obj, self._context))
        if menu.actions():
            menu.exec_(where)
