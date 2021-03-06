"""
Endpoints for management of arkOS updates.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Blueprint, jsonify, request
from flask.views import MethodView

from arkos import logger, storage, updates
from arkos.messages import NotificationThread

from kraken import auth
from kraken.records import remove_record
from kraken.jobs import as_job, job_response

backend = Blueprint("updates", __name__)


class UpdatesAPI(MethodView):
    @auth.required()
    def get(self, id):
        ups = []
        data = storage.updates.get("updates")
        if request.args.get("rescan", None) or not data:
            try:
                data = updates.check_updates()
            except:
                msg = ("Could not reach the update server. "
                       "Please check your Internet settings.")
                logger.error("Updates", msg)
        for x in data:
            if id == x["id"]:
                return jsonify(update={"id": x["id"], "name": x["name"],
                                       "date": x["date"], "info": x["info"]})
            ups.append({"id": x["id"], "name": x["name"], "date": x["date"],
                        "info": x["info"]})
        return jsonify(updates=ups)

    @auth.required()
    def post(self):
        id = as_job(self._post)
        return job_response(id)

    def _post(self, job):
        nthread = NotificationThread(id=job.id)
        installed = updates.install_updates(nthread)
        for x in installed:
            remove_record("update", x)
        updates.check_updates()


updates_view = UpdatesAPI.as_view('updates_api')
backend.add_url_rule('/api/updates', defaults={'id': None},
                     view_func=updates_view, methods=['GET', ])
backend.add_url_rule('/api/updates', view_func=updates_view,
                     methods=['POST', ])
backend.add_url_rule('/api/updates/<int:id>', view_func=updates_view,
                     methods=['GET', ])
