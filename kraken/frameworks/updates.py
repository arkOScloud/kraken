from flask import Response, Blueprint, jsonify, request
from flask.views import MethodView

from arkos import storage, updates
from kraken.messages import Message

backend = Blueprint("updates", __name__)


class UpdatesAPI(MethodView):
    def get(self, id):
        ups = []
        data = storage.updates.get("updates")
        if request.args.get("rescan", None) or not data:
            data = updates.check_updates()
        for x in data:
            if id == data["id"]:
                return jsonify(update={"id": data["id"], "info": data["info"]})
            ups.append({"id": data["id"], "info": data["info"]})
        return jsonify(updates=ups)
    
    def post(self):
        updates.install_updates(Message())
        updates.check_updates()
        return Response(status=201)


updates_view = UpdatesAPI.as_view('updates_api')
backend.add_url_rule('/updates/', defaults={'id': None}, 
    view_func=updates_view, methods=['GET',])
backend.add_url_rule('/updates/', view_func=updates_view, methods=['POST',])
backend.add_url_rule('/updates/<int:id>', view_func=updates_view, methods=['GET',])
