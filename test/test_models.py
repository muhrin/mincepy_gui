from mincepy.testing import *
from mincepy_gui import models, tree_models

import mincepy_gui


def test_record_tree(historian):
    car = Car()
    car.save()
    record = historian.get_current_record(car)

    record_tree = tree_models.RecordTree()
    record_tree.set_record(record, car)
    # Should have the car and the record
    data = []
    data.append(
        record_tree.data(record_tree.index(0, tree_models.RecordTree.COLUMN_HEADERS.index('Value')),
                         role=mincepy_gui.DataRole))
    data.append(
        record_tree.data(record_tree.index(1, tree_models.RecordTree.COLUMN_HEADERS.index('Value')),
                         role=mincepy_gui.DataRole))
    assert car in data
