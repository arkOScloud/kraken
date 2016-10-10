"""
Endpoints for management of Kraken API keys.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import secrets
from arkos.utilities import genAPIKey

backend = Blueprint("api_keys", __name__)


class APIKeysAPI(MethodView):
    @auth.required()
    def get(self):
        keys = secrets.get_all("api-keys")
        return jsonify(api_keys=keys)

    @auth.required()
    def post(self):
        data = request.get_json()["api_key"]
        key = genAPIKey()
        key = {"key": key, "user": data["user"], "comment": data["comment"]}
        secrets.append("api-keys", key)
        secrets.save()
        return jsonify(api_key=key)

    @auth.required()
    def delete(self, id):
        data = secrets.get_all("api-keys")
        for x in data:
            if x["key"] == id:
                data.remove(x)
                secrets.save()
                break
        return Response(status=204)


keys_view = APIKeysAPI.as_view('keys_api')
backend.add_url_rule('/api/api_keys', view_func=keys_view,
                     methods=['GET', 'POST'])
backend.add_url_rule('/api/api_keys/<string:id>', view_func=keys_view,
                     methods=['DELETE', ])
