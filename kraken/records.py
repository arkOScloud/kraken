"""
Functions to manage pushing and unloading remote records.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import json

from kraken.redis_storage import storage


def push_record(name, model):
    """
    Push an updated object record to the client.

    :param str name: Object type
    :param dict model: Serialized object
    """
    storage.publish("records:push", json.dumps({name: [model]}))


def remove_record(name, id):
    """
    Remove an object record from the client's store.

    :param str name: Object type
    :param str id: Object ID
    """
    storage.publish("records:purge", json.dumps({"model": name, "id": id}))
