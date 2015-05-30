import base64
import hashlib
import json
import random

from flask import make_response, Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import config

backend = Blueprint("api_keys", __name__)


class APIKeysAPI(MethodView):
    @auth.required()
    def get(self):
        keys = []
        data = config.get_all("api-keys")
        for user in data:
            for key in data[user]:
                keys.append({"key": key, "user": user})
        return jsonify(api_keys=keys)

    @auth.required()
    def post(self):
        data = json.loads(request.data)["api_key"]
        key = genAPIKey()
        keys = config.get("api-keys", data["user"], [])
        keys.append(key)
        config.set("api-keys", data["user"], keys)
        config.save()
        return jsonify(api_key={"user": data["user"], "key": key})

    @auth.required()
    def delete(self, id):
        data = config.get_all("api-keys")
        for user in data:
            for key in data[user]:
                if key == id:
                    data[user].remove(key)
                    config.save()
        return Response(status=204)


def genAPIKey():
    return base64.b64encode(hashlib.sha256(str(random.getrandbits(256))).digest(),
        random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')


keys_view = APIKeysAPI.as_view('keys_api')
backend.add_url_rule('/api/api_keys', view_func=keys_view, methods=['GET', 'POST'])
backend.add_url_rule('/api/api_keys/<string:id>', view_func=keys_view,
    methods=['DELETE',])
