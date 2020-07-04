import datetime
import inspect
import json
import os
import pprint
import sys
import subprocess
import typing
import uuid

import pytray.pretty
from pytray import tree
import bson


def obj_dict(obj):
    """Given an object return a dictionary that represents it"""
    repr_dict = {}
    for name in dir(obj):
        if not name.startswith('_'):
            try:
                value = getattr(obj, name)
                if not inspect.isroutine(value):
                    repr_dict[name] = value
            except Exception as exc:  # pylint: disable=broad-except
                repr_dict[name] = '{}: {}'.format(type(exc).__name__, exc)

    return repr_dict


class UUIDEncoder(json.JSONEncoder):

    def default(self, obj):  # pylint: disable=arguments-differ, method-hidden
        if isinstance(obj, uuid.UUID):
            # if the obj is uuid, we simply return the value of uuid
            return repr(obj)
        if isinstance(obj, bson.ObjectId):
            return repr(obj)
        return json.JSONEncoder.default(self, obj)


class UUIDDecoder(json.JSONDecoder):

    def decode(self, s):  # pylint: disable=arguments-differ
        decoded = super(UUIDDecoder, self).decode(s)

        def to_uuid(entry, path):  # pylint: disable=unused-argument
            obj_id = 'ObjectId'
            if isinstance(entry, str):
                if entry.startswith('UUID('):
                    try:
                        return uuid.UUID(entry[6:-2])
                    except ValueError:
                        pass
                elif entry.startswith(obj_id):
                    try:
                        # Object id format is ObjectId('...')
                        return bson.ObjectId(entry[len(obj_id) + 2:-2])
                    except ValueError:
                        pass

            return entry

        return tree.transform(to_uuid, decoded)


def pretty_type_string(obj_type: typing.Type) -> str:
    """Given an type will return a simple type string"""
    type_str = pytray.pretty.type_string(obj_type)
    parts = type_str.split('.')
    if len(parts) > 2:
        return "|".join([parts[0], parts[-1]])

    return type_str


def pretty_format(value, single_line=False, max_length=None) -> str:
    if isinstance(value, type):
        return pretty_type_string(value)
    if isinstance(value, datetime.datetime):
        if value.year == datetime.datetime.now().year:
            fmt = "%b %d %H:%M:%S"
        else:
            fmt = "%b %d %Y %H:%M:%S"

        return value.strftime(fmt)

    if isinstance(value, str):
        string = value
    else:
        string = pprint.pformat(value, depth=2, indent=0, compact=True)
    if single_line:
        string = string.replace('\n', '')
    if max_length and len(string) > max_length:
        string = string[:max_length - 3] + "..."

    return string


def open_file(filename):
    """Open a generic file on in a semi-portable way"""
    if sys.platform == "win32":
        os.startfile(filename)  # Not present on linux pylint: disable=no-member
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])
