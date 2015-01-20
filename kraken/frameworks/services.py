import json

from flask import Response, Blueprint, abort, jsonify
from flask.views import MethodView

from arkos.system import services

backend = Blueprint("services", __name__)


class ServicesAPI(MethodView):
    def get(self, id):
        svcs = services.get(id)
        if id and not svcs:
            abort(404)
        if type(svcs) == list:
            return jsonify(services=[x.as_dict() for x in svcs])
        else:
            return jsonify(service=svcs.as_dict())
    
    def post(self):
        data = json.loads(request.body)["service"]
        svc = services.Service(name=data["name"], cfg=data["cfg"])
        svc.add()
        return jsonify(service=svc)
    
    def put(self, id):
        data = json.loads(request.body)["service"]
        svc = services.get(id)
        if not id or not svc:
            abort(404)
        if data.get("operation"):
            if data["operation"] == "start":
                svc.start()
            elif data["operation"] == "stop":
                svc.stop()
            elif data["operation"] == "restart":
                svc.restart()
            elif data["operation"] == "real_restart":
                svc.real_restart()
            elif data["operation"] == "enable":
                svc.enable()
            elif data["operation"] == "disable":
                svc.disable()
        else:
            abort(400)
        return jsonify(service=svc)
    
    def delete(self, id):
        svc = services.get(id)
        if not id or not svc:
            abort(404)
        svc.remove()
        return Response(status=204)


services_view = ServicesAPI.as_view('services_api')
backend.add_url_rule('/system/services/', defaults={'id': None}, 
    view_func=services_view, methods=['GET',])
backend.add_url_rule('/system/services/', view_func=services_view, methods=['POST',])
backend.add_url_rule('/system/services/<string:id>', view_func=services_view, 
    methods=['GET', 'PUT', 'DELETE'])
