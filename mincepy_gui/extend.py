import logging
from typing import MutableSequence, Sequence

import stevedore

from . import plugins

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

ACTIONERS_NAMESPACE = 'mincepy_gui.actioners'


def get_actioners() -> Sequence:
    """Get all mincepy types and type helper instances registered as extensions"""
    mgr = stevedore.extension.ExtensionManager(
        namespace=ACTIONERS_NAMESPACE,
        invoke_on_load=False,
    )

    all_types = []

    def get_actioner(extension: stevedore.extension.Extension):
        try:
            all_types.extend(extension.plugin())
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to get actioner plugin from %s", extension.name)

    mgr.map(get_actioner)

    return all_types


class ActionerManager:
    """Group all actioners together and load plugins"""

    def __init__(self):
        self._actioners = []  # type: MutableSequence[plugins.Actioner]

    def load_plugins(self):
        self._actioners.extend(get_actioners())

    def register(self, actioner: plugins.Actioner):
        self._actioners.append(actioner)

    def probe(self, obj, context) -> Sequence:
        actions = []

        for actioner in self._actioners:
            possible_actions = actioner.probe(obj, context)
            if possible_actions:
                for action in possible_actions:
                    actions.append((action, actioner))

        return actions
