"""
Classes and functions to manage asynchronous status messages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from kraken import auth
from flask import Blueprint, jsonify, abort
from arkos.utilities import random_string
from kraken.redis_storage import storage

backend = Blueprint("messages", __name__)


class Message:
    """An asynchronous status message made available via polling."""

    def __init__(self, cls="", msg="", head=None, job=None):
        """
        Initialize.

        :param str cls: Message class
        :param str msg: Message text
        :param str head: Message header text
        :param Job job: Job to update message through
        """
        self.id = random_string()[0:10]
        self.job = job
        if cls and msg:
            data = {"id": self.id, "class": cls, "message": msg,
                    "headline": head, "complete": True}
        else:
            data = {"id": self.id, "class": "info", "headline": None,
                    "message": "Please wait...", "complete": False}
        storage.append("genesis:messages", data)
        if self.job:
            self.job.update_message(cls, msg, head)

    def update(self, cls, msg, head=None):
        """
        Send a message update.

        :param str cls: Message class
        :param str msg: Message text
        :param str head: Message header text
        """
        data = {"id": self.id, "class": cls, "message": msg, "headline": head,
                "complete": False}
        storage.append("genesis:messages", data)
        if self.job:
            self.job.update_message(cls, msg, head)

    def complete(self, cls, msg, head=None):
        """
        Send a completed message at the end of the operation.

        :param str cls: Message class
        :param str msg: Message text
        :param str head: Message header text
        """
        data = {"id": self.id, "class": cls, "message": msg, "headline": head,
                "complete": True}
        storage.append("genesis:messages", data)
        if self.job:
            self.job.update_message(cls, msg, head)


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
    job = storage.get_all("job:{0}".format(id))
    if not job:
        abort(404)
    response = jsonify(**job)
    response.status_code = int(job["status"])
    return response


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
