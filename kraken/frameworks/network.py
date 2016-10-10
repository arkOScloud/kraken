"""
Endpoints for management of network settings.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import logger
from arkos.system import network

backend = Blueprint("networks", __name__)


class NetworksAPI(MethodView):
    @auth.required()
    def get(self, id):
        nets = network.get_connections(id)
        if id and not nets:
            abort(404)
        if isinstance(nets, networks.Connection):
            return jsonify(network=nets.serialized)
        else:
            return jsonify(networks=[x.serialized for x in nets])

    @auth.required()
    def post(self):
        data = request.get_json()["network"]
        net = network.Connection(id=data["id"], config=data["config"])
        net.add()
        return jsonify(network=net.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["network"]
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
                else:
                    abort(422)
            except Exception as e:
                logger.error("Network", str(e))
                return jsonify(errors={"msg": str(e)}), 500
        else:
            net.config = data["config"]
            net.update()
        return jsonify(network=net.serialized)

    @auth.required()
    def delete(self, id):
        net = network.get_connections(id)
        if not id or not net:
            abort(404)
        net.remove()
        return Response(status=204)


@backend.route('/api/system/netifaces', defaults={'id': None})
@backend.route('/api/system/netifaces/<string:id>')
@auth.required()
def get_netifaces(id):
    ifaces = network.get_interfaces(id)
    if id and not ifaces:
        abort(404)
    if isinstance(ifaces, network.Interface):
        return jsonify(netiface=ifaces.serialized)
    else:
        return jsonify(netifaces=[x.serialized for x in ifaces])


network_view = NetworksAPI.as_view('networks_api')
backend.add_url_rule('/api/system/networks', defaults={'id': None},
    view_func=network_view, methods=['GET',])
backend.add_url_rule('/api/system/networks', view_func=network_view, methods=['POST',])
backend.add_url_rule('/api/system/networks/<string:id>', view_func=network_view,
    methods=['GET', 'PUT', 'DELETE'])
