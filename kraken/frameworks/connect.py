from flask import make_response, Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import config
#from arkos import connect
from arkos.utilities import api
from kraken import auth

backend = Blueprint("connect", __name__)


class ConnectAPI(MethodView):
    @auth.required()
    def get(self):
        data = {"key": config.get("connect", "key", None), "subscriptions": []}
        if data["key"]:
            cdata = api("https://connect.arkos.io/api/v1/subscriptions",
                headers={"X-API-Key": data["key"]}, crit=True)
            data["subscriptions"] = cdata["subscriptions"]
            for x in cdata["subscriptions"]:
                if x["service_name"] == "ConnectDNS":
                    connect.activate_dns()
                elif x["service_name"] == "Link":
                    connect.activate_link()
        return jsonify(connect=data)

    @auth.required()
    def post(self):
        data = request.get_json()["connect"]
        cdata = {"key": None, "subscriptions": []}
        try:
            cdata = api("https://connect.arkos.io/api/v1/subscriptions",
                headers={"X-API-Key": data["key"]}, crit=True)
            config.set("connect", "key", data["key"])
            config.save()
            cdata["subscriptions"] = data["subscriptions"]
            for x in cdata["subscriptions"]:
                if x["service_name"] == "ConnectDNS":
                    connect.activate_dns()
                elif x["service_name"] == "Link":
                    connect.activate_link()
        except:
            resp = jsonify(message="Could not register with Connect. Please check that the key is correct.")
            resp.status_code = 400
            return resp
        return jsonify(connect=cdata, message="Connect API Key registered successfully")


conn_view = ConnectAPI.as_view('conn_api')
backend.add_url_rule('/api/connect', defaults={'id': None},
    view_func=conn_view, methods=['GET',])
backend.add_url_rule('/api/connect', view_func=conn_view, methods=['POST',])
