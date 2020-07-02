"""Test the entry table model and controller"""

from PySide2 import QtCore

import mincepy
from mincepy_gui import columns
from mincepy_gui import common
from mincepy_gui import entry_table


def test_simple_entry_table():
    table = entry_table.EntryTableModel()
    table.batch_size = 10

    # Crate some records to populate the table with
    defaults = {'snapshot_hash': None, 'state_types': None}
    red_car = mincepy.DataRecord.new_builder(obj_id=1,
                                             type_id='car',
                                             state={
                                                 'colour': 'red'
                                             },
                                             **defaults).build()
    white_car = mincepy.DataRecord.new_builder(obj_id=2,
                                               type_id='car',
                                               state={
                                                   'colour': 'white'
                                               },
                                               **defaults).build()
    person = mincepy.DataRecord.new_builder(obj_id=2,
                                            type_id='person',
                                            state={
                                                'name': 'martin',
                                                'age': 35
                                            },
                                            **defaults).build()

    records = [red_car, white_car, person]
    table.set_source(iter(records), historian=None)
    table.fetchMore(QtCore.QModelIndex())
    assert table.rowCount() == len(records)

    cols = [
        columns.DataColumn('obj_id', formatter=str),
        columns.DataColumn('type_id', formatter=str),
    ]
    table.set_columns(cols)
    assert table.columnCount() == len(cols)

    for row, record in enumerate(records):
        assert record.obj_id == \
               table.data(table.createIndex(row, 0), role=common.DataRole)
        assert str(record.obj_id) == \
               table.data(table.createIndex(row, 0), role=QtCore.Qt.DisplayRole)

        assert record.type_id == \
               table.data(table.createIndex(row, 1), role=common.DataRole)
        assert str(record.type_id) == \
               table.data(table.createIndex(row, 1), role=QtCore.Qt.DisplayRole)

    # Now let's add some more columns
    table.append_columns(columns.data_column(('state', 'colour'), formatter=str),
                         columns.data_column(('state', 'name'), formatter=str),
                         columns.data_column(('state', 'age'), formatter=str))

    for row, record in enumerate(records):
        assert record.state.get('colour', None) == \
               table.data(table.createIndex(row, 2), role=common.DataRole)
        assert record.state.get('name', None) == \
               table.data(table.createIndex(row, 3), role=common.DataRole)
        assert record.state.get('age', None) == \
               table.data(table.createIndex(row, 4), role=common.DataRole)


def _create_records(num=10):
    defaults = {'snapshot_hash': None, 'state_types': None}

    records = []
    for row in range(num):
        record = mincepy.DataRecord.new_builder(obj_id=1,
                                                type_id='car',
                                                state={
                                                    'index': row
                                                },
                                                **defaults).build()
        records.append(record)
    return records


def test_fetching_more():
    empty_index = QtCore.QModelIndex()
    table = entry_table.EntryTableModel()
    table.batch_size = 2

    # Crate some records to populate the table with
    records = _create_records(11)
    table.set_source(iter(records), None)

    batch = 1  # The first batch is automatically loaded
    while table.canFetchMore(empty_index):
        assert table.rowCount() == table.batch_size * batch
        table.fetchMore(empty_index)
        batch += 1

    assert table.rowCount() == len(records)

    # Now, create new records and check it still works
    records = _create_records(9)
    table.set_source(iter(records), None)

    batch = 1  # The first batch is automatically loaded
    while table.canFetchMore(empty_index):
        assert table.rowCount() == table.batch_size * batch
        table.fetchMore(empty_index)
        batch += 1

    assert table.rowCount() == len(records)

    # Finally, create more than the current number of records and check it still works
    records = _create_records(21)
    table.set_source(iter(records), None)

    batch = 1  # The first batch is automatically loaded
    while table.canFetchMore(empty_index):
        assert table.rowCount() == table.batch_size * batch
        table.fetchMore(empty_index)
        batch += 1

    assert table.rowCount() == len(records)
