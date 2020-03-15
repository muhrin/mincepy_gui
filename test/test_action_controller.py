from typing import Iterable

import mincepy_gui
import mincepy_gui.actioners


class TestActioner(mincepy_gui.Actioner):

    def __init__(self, actions_list: list):
        self._actions_list = actions_list
        self._trigger_count = {}

    def probe(self, obj, context) -> Iterable[str]:
        return self._actions_list

    def do(self, action, obj, context):
        self._trigger_count[action] = self._trigger_count.get(action, 0) + 1


if __name__ == "__main__":
    """A manual way to test.  Not ideal but better than nothing"""
    test_actioner = mincepy_gui.actioners.TestActioner
    test_actioner.enabled = True
    test_actioner.actions = ('test-action1', 'test-action2')
    mincepy_gui.start()
