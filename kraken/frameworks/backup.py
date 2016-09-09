"""
Endpoints for management of arkOS backups.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import backup
from arkos.messages import NotificationThread

from kraken import auth
from kraken.messages import push_record
from kraken.jobs import as_job, job_response

backend = Blueprint("backup", __name__)


class BackupsAPI(MethodView):
    @auth.required()
    def get(self, id, time):
        backups = backup.get()
        if id and time and backups:
            return jsonify(
                backup=[x for x in backups if x["id"] == id + "/" + time])
        elif id and backups:
            return jsonify(backups=[x for x in backups if x["pid"] == id])
        elif id or time:
            abort(404)
        return jsonify(backups=backups)

    @auth.required()
    def post(self, id, time):
        data = request.get_json()["backup"]
        id = as_job(self._post, data)
        return job_response(id)

    def _post(self, job, id):
        nthread = NotificationThread(id=job.id)
        b = backup.create(id, nthread=nthread)
        push_record("backups", b)

    @auth.required()
    def put(self, id, time):
        data = request.get_json().get("backup")
        data["id"] = id + "/" + time
        if id and time and data:
            id = as_job(self._put, data)
            return job_response(id, data={"backup": data})
        else:
            abort(404)

    def _put(self, job, data):
        nthread = NotificationThread(id=job.id)
        b = backup.restore(data, nthread=nthread)
        push_record("backup", b)

    @auth.required()
    def delete(self, id, time):
        backup.remove(id, time)
        return Response(status=204)


@backend.route('/api/backups/types')
@auth.required()
def get_possible():
    return jsonify(types=backup.get_able())


backups_view = BackupsAPI.as_view('backups_api')
backend.add_url_rule('/api/backups', defaults={'id': None, 'time': None},
                     view_func=backups_view, methods=['GET', ])
backend.add_url_rule('/api/backups/<string:id>', defaults={'time': None},
                     view_func=backups_view, methods=['GET', 'POST', ])
backend.add_url_rule('/api/backups/<string:id>/<string:time>',
                     view_func=backups_view, methods=['GET', 'PUT', 'DELETE'])
