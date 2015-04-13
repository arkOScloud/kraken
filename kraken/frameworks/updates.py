from flask import Response, Blueprint, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import storage, updates
from kraken.messages import Message, remove_record
from kraken.utilities import as_job, job_response

backend = Blueprint("updates", __name__)


class UpdatesAPI(MethodView):
    @auth.required()
    def get(self, id):
        ups = []
        data = storage.updates.get("updates")
        if request.args.get("rescan", None) or not data:
            data = updates.check_updates()
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
    
    def _post(self):
        installed = updates.install_updates(Message())
        for x in installed:
            remove_record("update", x)
        updates.check_updates()


updates_view = UpdatesAPI.as_view('updates_api')
backend.add_url_rule('/updates', defaults={'id': None}, 
    view_func=updates_view, methods=['GET',])
backend.add_url_rule('/updates', view_func=updates_view, methods=['POST',])
backend.add_url_rule('/updates/<int:id>', view_func=updates_view, methods=['GET',])
