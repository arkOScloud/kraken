import json

from flask import Response, Blueprint, jsonify, request

from arkos.system import packages

backend = Blueprint("packages", __name__)


@backend.route('/system/packages/install', methods=["POST",])
def install(data):
    data = json.loads(request.body)["packages"]
    try:
        packages.install(data, query=True)
    except:
        abort(500)
    return Response(status=201)

@backend.route('/system/packages/remove', methods=["POST",])
def remove(data):
    data = json.loads(request.body)["packages"]
    try:
        packages.remove(data)
    except:
        abort(500)
    return Response(status=201)
