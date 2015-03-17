import base64
import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import backup
from kraken.messages import Message, push_record
from kraken.utilities import as_job, job_response

backend = Blueprint("backup", __name__)


class BackupsAPI(MethodView):
    def get(self, id, time):
        backups = backup.get()
        if id and time and backups:
            return jsonify(backup=[x for x in backups if x["id"] == id+"/"+time])
        elif id and backups:
            return jsonify(backups=[x for x in backups if x["pid"] == id])
        elif id or time:
            abort(404)
        return jsonify(backups=backups)
    
    def post(self, id, time):
        id = as_job(self._post, id)
        return job_response(id)
    
    def _post(self, id):
        message = Message()
        message.update("info", "Backing up %s..." % id)
        try:
            b = backup.create(id)
            message.complete("success", "%s backed up successfully" % id)
            push_record("backups", b)
        except Exception, e:
            message.complete("error", "%s could not be backed up: %s" % (id, str(e)))
    
    def put(self, id, time):
        data = json.loads(request.data).get("backup")
        data["id"] = id+"/"+time
        if id and time and data:
            id = as_job(self._put, data)
            return job_response(id, data={"backup": data})
        else:
            abort(404)
    
    def _put(self, data):
        message = Message()
        message.update("info", "Restoring %s..." % data["pid"])
        try:
            b = backup.restore(data)
            message.complete("success", "%s restored successfully" % b["pid"])
            push_record("backup", b)
        except Exception, e:
            message.complete("error", "%s could not be restored: %s" % (data["pid"], str(e)))
    
    def delete(self, id, time):
        backup.remove(id, time)
        return Response(status=204)


@backend.route('/backups/types')
def get_possible():
    return jsonify(types=backup.get_able())


backups_view = BackupsAPI.as_view('backups_api')
backend.add_url_rule('/backups', defaults={'id': None, 'time': None}, 
    view_func=backups_view, methods=['GET',])
backend.add_url_rule('/backups/<string:id>', defaults={'time': None},
    view_func=backups_view, methods=['GET', 'POST',])
backend.add_url_rule('/backups/<string:id>/<string:time>', view_func=backups_view, 
    methods=['GET', 'PUT', 'DELETE'])
