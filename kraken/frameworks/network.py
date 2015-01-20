import json

from flask import Response, Blueprint, abort, jsonify
from flask.views import MethodView

from arkos.system import network

backend = Blueprint("networks", __name__)


class NetworksAPI(MethodView):
    def get(self, id):
        nets = network.get_connections(id)
        if not nets:
            abort(404)
        if type(nets) == list:
            return jsonify(networks=[x.as_dict() for x in nets])
        else:
            return jsonify(network=nets.as_dict())
    
    def post(self):
        data = json.loads(request.body)["network"]
        net = network.Connection(name=data["name"], config=data["config"])
        net.add()
        return jsonify(network=net)
    
    def put(self, id):
        data = json.loads(request.body)["network"]
        net = network.get_connections(id)
        if not id or not net:
            abort(404)
        if data.get("operation"):
            try:
                if data["operation"] == "connect":
                    net.connect()
                elif data["operation"] == "disconnect":
                    net.disconnect()
                elif data["operation"] == "enable":
                    net.enable()
                elif data["operation"] == "disable":
                    net.disable()
            except:
                abort(500)
            abort(400)
        else:
            net.name = data["name"]
            net.config = data["config"]
            net.update()
        return jsonify(network=net)
    
    def delete(self, id):
        net = network.get_connections(id)
        if not id or not net:
            abort(404)
        net.remove()
        return Response(status=204)


network_view = NetworksAPI.as_view('networks_api')
backend.add_url_rule('/system/networks/', defaults={'id': None}, 
    view_func=network_view, methods=['GET',])
backend.add_url_rule('/system/networks/', view_func=network_view, methods=['POST',])
backend.add_url_rule('/system/networks/<string:id>', view_func=network_view, 
    methods=['GET', 'PUT', 'DELETE'])
