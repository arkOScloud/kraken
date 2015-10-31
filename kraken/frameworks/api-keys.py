import base64
import hashlib
import random

from flask import make_response, Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import secrets

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


def genAPIKey():
    return base64.b64encode(hashlib.sha256(str(random.getrandbits(256))).digest(),
        random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')


keys_view = APIKeysAPI.as_view('keys_api')
backend.add_url_rule('/api/api_keys', view_func=keys_view, methods=['GET', 'POST'])
backend.add_url_rule('/api/api_keys/<string:id>', view_func=keys_view,
    methods=['DELETE',])
