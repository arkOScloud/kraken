"""
Class to listen for notifications and broadcast to clients.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import datetime
import logging

from arkos.utilities import random_string
from kraken.redis_storage import storage


class APIHandler(logging.Handler):
    def emit(self, record):
        data = record.msg
        if type(data) in [str, bytes]:
            id = id or random_string(16)
            data = {"id": id, "message": record.msg, "message_id": id,
                    "title": None, "comp": "Unknown", "cls": "runtime",
                    "complete": True}
        logtime = datetime.datetime.fromtimestamp(record.created)
        logtime = logtime.isoformat()
        data.update({"cls": data["cls"], "level": record.levelname.lower(),
                     "time": logtime})
        pipe = storage.pipeline()
        storage.publish("notifications", data, pipe)
        storage.prepend("n:{0}".format(data["id"]), data, pipe)
        storage.expire("n:{0}".format(data["id"]), 604800, pipe)
        pipe.execute()
