"""
Classes and functions to manage asynchronous status messages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import logging

from kraken import auth
from flask import Blueprint, jsonify, abort
from kraken.redis_storage import storage

from arkos.system import systemtime
from arkos.messages import MessageContext

backend = Blueprint("messages", __name__)


class JobMessageContext(MessageContext):
    """A context for asynchronous, updatable status messages for jobs."""

    def __init__(self, comp, title=None, job=None):
        """
        Create a new notification context.

        :param str comp: Section of application to state as origin
        :param str title: Message title text
        :param Job job: Job to update message through
        """
        super().__init__(comp, title)
        self.job = job

    def info(self, comp, msg, title=None, complete=False):
        """
        Update the notification with an INFO message.

        :param str msg: Message text
        :param str title: Message title text
        :param bool complete: Is this the last message to be pushed?
        """
        super().info(msg, title, complete)
        if self.job:
            self.job.update_message("info", msg, title)

    def success(self, comp, msg, title=None, complete=False):
        """
        Update the notification with a SUCCESS message.

        :param str msg: Message text
        :param str title: Message title text
        :param bool complete: Is this the last message to be pushed?
        """
        super().success(msg, title, complete)
        if self.job:
            self.job.update_message("success", msg, title)

    def warning(self, comp, msg, title=None, complete=False):
        """
        Update the notification with a WARN message.

        :param str msg: Message text
        :param str title: Message title text
        :param bool complete: Is this the last message to be pushed?
        """
        super().warning(msg, title, complete)
        if self.job:
            self.job.update_message("warn", msg, title)

    def error(self, comp, msg, title=None, complete=False):
        """
        Update the notification with an ERROR message.

        :param str msg: Message text
        :param str title: Message title text
        :param bool complete: Is this the last message to be pushed?
        """
        super().error(msg, title, complete)
        if self.job:
            self.job.update_message("error", msg, title)

    def debug(self, comp, msg, title=None, complete=False):
        """
        Update the notification with a DEBUG message.

        :param str msg: Message text
        :param str title: Message title text
        :param bool complete: Is this the last message to be pushed?
        """
        super().debug(msg, title, complete)
        if self.job:
            self.job.update_message("debug", msg, title)


class SerialFormatter(logging.Formatter):
    def format(self, record):
        data = record.msg
        data.update({
            "level": record.levelname,
            "time": systemtime.get_iso_time(record.created, "unix")
        })
        return data


class APIHandler(logging.Handler):
    def emit(record):
        storage.append("notifications", record)


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
