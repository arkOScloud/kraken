"""
Classes and functions to manage asynchronous status messages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import datetime
import logging

from flask import Blueprint, jsonify, abort, Response, request
from flask.views import MethodView

from kraken import auth
from kraken.redis_storage import storage

from arkos.messages import Notification, NotificationThread
from arkos.utilities import random_string

backend = Blueprint("messages", __name__)


class APIHandler(logging.Handler):
    def emit(self, record):
        data = record.msg
        if type(data) in [str, bytes]:
            data = {"id": id or random_string(16), "message": record.msg,
                    "thread_id": random_string(16), "title": None,
                    "comp": "Unknown", "cls": "runtime", "complete": True}
        logtime = datetime.datetime.fromtimestamp(record.created)
        logtime = logtime.isoformat()
        data.update({"cls": data["cls"], "level": record.levelname.lower(),
                     "time": logtime})
        pipe = storage.pipeline()
        tid = "n:thread:{0}".format(data["thread_id"])
        kid = "n:{0}".format(data["id"])
        storage.set(kid, data, pipe=pipe)
        storage.append(tid, data["id"], pipe)
        storage.expire(tid, 604800, pipe)
        storage.expire(kid, 604800, pipe)
        pipe.execute()


class NotificationsAPI(MethodView):
    @auth.required()
    def get(self, id):
        messages = []
        tid = request.args.get("thread", None)
        if id is not None:
            message = storage.get_all("n:{0}".format(id))
            if not message:
                abort(404)
            return jsonify(notification=message)
        elif tid:
            ids = storage.get_list("n:thread:{0}".format(tid))
            if not ids:
                abort(404)
        else:
            ids = storage.scan("n:*")
            ids = [x.split("arkos:n:")[1] for x in ids]
        messages = [storage.get_all("n:{0}".format(x)) for x in ids]
        return jsonify(messages=sorted(messages, key=lambda x: x["time"]))

    @auth.required()
    def post(self):
        msg = request.get_json()["notification"]
        if not msg.get("message") or not msg.get("level")\
                or not msg.get("comp"):
            abort(400)
        notif = Notification(
            msg["level"], msg["comp"], msg["message"],
            msg.get("cls"), msg.get("id"), msg.get("title"))
        msg["id"] = notif.id
        if msg.get("complete") is False or\
                (msg.get("complete") is True and msg.get("thread_id")):
            nthread = NotificationThread(id=msg.get("thread_id"))
            if msg["complete"] is True:
                nthread.complete(notif)
            else:
                nthread.update(notif)
            msg["thread_id"] = nthread.id
        else:
            notif.send()
        return jsonify(notification=msg), 201

    @auth.required()
    def delete(self, id):
        msg = storage.get_all("n:{0}".format(id))
        if not msg:
            abort(404)
        if msg["thread_id"]:
            msgs = storage.get_list("n:thread:{0}".format(msg["thread_id"]))
            storage.delete("n:thread:{0}".format(msg["thread_id"]))
            for x in msgs:
                storage.delete("n:{0}".format(x))
                remove_record("notification", x)
        else:
            storage.delete("n:{0}".format(id))
        return Response(status=204)


@backend.route('/api/genesis')
@auth.required()
def get_messages():
    """Endpoint to return updated records."""
    _pushes = storage.get_list("genesis:pushes")
    purges = storage.get_list("genesis:purges")
    storage.delete("genesis:pushes")
    storage.delete("genesis:purges")
    pushes = {}
    for x in _pushes:
        if not x["model"] in pushes:
            pushes[x["model"]] = []
        pushes[x["model"]].append(x["record"])
    return jsonify(pushes=pushes, purges=purges)


@backend.route('/api/jobs')
@auth.required()
def get_jobs():
    """Endpoint to return a list of all pending jobs."""
    jobs = []
    for x in storage.scan("job"):
        jobs.append("/api/jobs/{0}".format(x.split("arkos:job:")[1]))
    return jsonify(jobs=jobs)


@backend.route('/api/jobs/<string:id>')
@auth.required()
def get_job(id):
    """Endpoint to return information about a specific job."""
    data = {}
    job = storage.get("job:{0}".format(id))
    if not job:
        abort(404)
    if storage.exists("n:thread:{0}".format(id)):
        last_msg = storage.lindex("n:thread:{0}".format(id), -1)
        data = storage.get_all("n:{0}".format(last_msg))
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


notifs_view = NotificationsAPI.as_view('notifs_api')
backend.add_url_rule('/api/notifications', defaults={'id': None},
                     view_func=notifs_view, methods=['GET', ])
backend.add_url_rule('/api/notifications', view_func=notifs_view,
                     methods=['POST', ])
backend.add_url_rule('/api/notifications/<string:id>', view_func=notifs_view,
                     methods=['GET', 'DELETE'])
