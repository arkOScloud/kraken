"""
Classes and functions to manage asynchronous status messages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import datetime
import logging

from kraken import auth
from flask import Blueprint, jsonify, abort
from kraken.redis_storage import storage

from arkos.utilities import random_string

backend = Blueprint("messages", __name__)


class APIHandler(logging.Handler):
    def emit(self, record):
        data = record.msg
        if type(data) in [str, bytes]:
            data = {"id": id or random_string(16), "message": record.msg,
                    "thread_id": random_string(16), "title": None,
                    "comp": "Unknown", "cls": "runtime", "complete": True}
        levelname = "critical"
        logtime = datetime.datetime.fromtimestamp(record.created)
        logtime = logtime.strftime("%Y-%m-%d %H:%M:%S")
        logtime = "%s,%03d" % (logtime, record.msecs)
        data.update({"cls": data["cls"], "level": record.levelname.lower(),
                     "time": logtime})
        pipe = storage.pipeline()
        tid = "notifications:{0}".format(data["thread_id"])
        kid = "notifications:{0}:{1}".format(data["thread_id"], data["id"])
        storage.set(kid, data, pipe=pipe)
        storage.append(tid, data["id"], pipe)
        storage.expire(tid, 604800, pipe)
        storage.expire(kid, 604800, pipe)
        pipe.execute()


@backend.route('/api/genesis')
@auth.required()
def get_messages():
    """Endpoint to return updated status messages."""
    messages = storage.get_list("genesis:messages")
    _pushes = storage.get_list("genesis:pushes")
    purges = storage.get_list("genesis:purges")
    storage.delete("genesis:messages")
    storage.delete("genesis:pushes")
    storage.delete("genesis:purges")
    pushes = {}
    for x in _pushes:
        if not x["model"] in pushes:
            pushes[x["model"]] = []
        pushes[x["model"]].append(x["record"])
    return jsonify(messages=messages, pushes=pushes, purges=purges)


@backend.route('/api/jobs')
@auth.required()
def get_jobs():
    """Endpoint to return a list of all pending jobs."""
    jobs = []
    for x in storage.scan("job"):
        jobs.append("/api/jobs/{0}".format(x.split("arkos:job")[1]))
    return jsonify(jobs=jobs)


@backend.route('/api/jobs/<string:id>')
@auth.required()
def get_job(id):
    """Endpoint to return information about a specific job."""
    data = {}
    job = storage.get("job:{0}".format(id))
    if not job:
        abort(404)
    if storage.exists("notifications:{0}".format(id)):
        last_msg = storage.lindex("notifications:{0}".format(id), -1)
        fid = "notifications:{0}:{1}".format(id, last_msg)
        data = storage.get_all(fid)
    return jsonify(**data), int(job)


def push_record(name, model):
    """
    Push an updated object record to the client.

    :param str name: Object type
    :param dict model: Serialized object
    """
    storage.append("genesis:pushes", {"model": name, "record": model})


def remove_record(name, id):
    """
    Remove an object record from the client's store.

    :param str name: Object type
    :param str id: Object ID
    """
    storage.append("genesis:purges", {"model": name, "id": id})
