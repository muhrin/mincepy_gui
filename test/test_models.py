# pylint: disable=unused-import, redefined-outer-name

from mincepy import testing
from mincepy.testing import archive_uri, historian

from mincepy_gui import entry_details
import mincepy_gui


def test_record_tree(historian):
    car = testing.Car()
    car.save()
    record = historian.get_current_record(car)

    record_tree = entry_details.EntryDetails()
    record_tree.set_record(record, car)
    # Should have the car and the record
    data = []
    data.append(
        record_tree.data(record_tree.index(
            0, entry_details.EntryDetails.COLUMN_HEADERS.index('Value')),
                         role=mincepy_gui.DataRole))
    data.append(
        record_tree.data(record_tree.index(
            1, entry_details.EntryDetails.COLUMN_HEADERS.index('Value')),
                         role=mincepy_gui.DataRole))
    assert car in data
