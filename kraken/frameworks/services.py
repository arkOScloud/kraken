import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos.system import services
from kraken.messages import Message

backend = Blueprint("services", __name__)


class ServicesAPI(MethodView):
    def get(self, id):
        svcs = services.get(id)
        if id and not svcs:
            abort(404)
        if type(svcs) == list:
            return jsonify(services=[x.as_dict() for x in svcs if not any(y in x.name for y in ["systemd", "dbus"])])
        else:
            return jsonify(service=svcs.as_dict())
    
    def post(self):
        data = json.loads(request.data)["service"]
        svc = services.Service(name=data["id"], cfg=data["cfg"])
        svc.add()
        return jsonify(service=svc.as_dict())
    
    def put(self, id):
        data = json.loads(request.data)["service"]
        svc = services.get(id)
        if id and not svc:
            abort(404)
        if not data.get("operation"):
            abort(400)
        try:
            if data["operation"] == "start":
                tag = "started"
                svc.start()
            elif data["operation"] == "stop":
                tag = "stopped"
                svc.stop()
            elif data["operation"] == "restart":
                tag = "restarted"
                svc.restart()
            elif data["operation"] == "real_restart":
                tag = "restarted"
                svc.restart(real=True)
            elif data["operation"] == "enable":
                tag = "enabled"
                svc.enable()
            elif data["operation"] == "disable":
                tag = "disabled"
                svc.disable()
        except services.ActionError, e:
            resp = jsonify(message="%s service could not be %s." % (data["id"], tag))
            resp.status_code = 422
            return resp
        return jsonify(service=svc.as_dict())
    
    def delete(self, id):
        svc = services.get(id)
        if id and not svc:
            abort(404)
        svc.remove()
        return Response(status=204)


services_view = ServicesAPI.as_view('services_api')
backend.add_url_rule('/system/services', defaults={'id': None}, 
    view_func=services_view, methods=['GET',])
backend.add_url_rule('/system/services', view_func=services_view, methods=['POST',])
backend.add_url_rule('/system/services/<string:id>', view_func=services_view, 
    methods=['GET', 'PUT', 'DELETE'])
