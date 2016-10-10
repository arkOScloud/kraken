"""
Classes and functions to manage asynchronous status messages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Blueprint, jsonify, abort, Response, request
from flask.views import MethodView

from kraken import auth
from kraken.redis_storage import storage

from arkos.messages import Notification, NotificationThread

backend = Blueprint("messages", __name__)


class NotificationsAPI(MethodView):
    @auth.required()
    def get(self, id):
        if id is not None:
            messages = storage.get_list("n:{0}".format(id))
            if not messages:
                abort(404)
            if len(messages) > 1:
                message = messages[0]
                message["history"] = messages[1:]
            else:
                message = messages[0]
                message["history"] = []
            return jsonify(notification=message)
        else:
            ids = (x.split("arkos:n:")[1] for x in storage.scan("n:*"))
        messages = (storage.lindex("n:{0}".format(x), 0) for x in ids)
        return jsonify(notifications=sorted(messages, key=lambda x: x["time"]))

    @auth.required()
    def post(self):
        msg = request.get_json()["notification"]
        if not msg.get("message") or not msg.get("level")\
                or not msg.get("comp"):
            abort(400)
        notif = Notification(
            msg["level"], msg["comp"], msg["message"],
            msg.get("cls"), msg.get("title"))

        # If ID is provided at POST, assume part of thread
        if msg.get("id"):
            nthread = NotificationThread(id=msg["id"])
            if msg.get("complete"):
                nthread.complete(notif)
            else:
                nthread.update(notif)
            msg["message_id"] = notif.message_id
        else:
            notif.send()
        return jsonify(notification=msg), 201

    @auth.required()
    def delete(self, id):
        if id:
            if not storage.exists("n:{0}".format(id)):
                abort(404)
            storage.delete("n:{0}".format(id))
        else:
            for x in storage.scan("n:*"):
                storage.delete("n:{0}".format(x.split("arkos:n:")[1]))
        return Response(status=204)


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
    if storage.exists("n:{0}".format(id)):
        data = storage.lindex("n:{0}".format(id), 0)
    return jsonify(**data), int(job)


notifs_view = NotificationsAPI.as_view('notifs_api')
backend.add_url_rule('/api/notifications', defaults={'id': None},
                     view_func=notifs_view, methods=['GET', 'DELETE'])
backend.add_url_rule('/api/notifications', view_func=notifs_view,
                     methods=['POST', ])
backend.add_url_rule('/api/notifications/<string:id>', view_func=notifs_view,
                     methods=['GET', 'DELETE'])
