"""
Endpoints for management of system services.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from kraken.application import app
from arkos.system import services

backend = Blueprint("services", __name__)


class ServicesAPI(MethodView):
    @auth.required()
    def get(self, id):
        try:
            svcs = services.get(id)
        except services.ActionError as e:
            if id:
                app.logger.error("{0} service status could not be obtained. Failed with error: {1}".format(id, e.emsg))
                resp = jsonify(message="{0} service status could not be obtained.".format(id))
            else:
                app.logger.error("Service status could not be obtained. Failed with error: {0}".format(e.emsg))
                resp = jsonify(message="Service status could not be obtained.")
            resp.status_code = 422
            return resp
        if id and not svcs:
            abort(404)
        if isinstance(svcs, services.Service):
            return jsonify(service=svcs.serialized)
        else:
            return jsonify(services=[x.serialized for x in svcs if not any(y in x.name for y in ["systemd", "dbus"])])

    @auth.required()
    def post(self):
        data = request.get_json()["service"]
        svc = services.Service(name=data["id"], cfg=data["cfg"])
        svc.add()
        return jsonify(service=svc.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["service"]
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
        except services.ActionError as e:
            app.logger.error("{0} service could not be {1}. Failed with error: {2}".format(id, tag, e.emsg))
            resp = jsonify(message="{0} service could not be {1}.".format(id, tag))
            resp.status_code = 422
            return resp
        return jsonify(service=svc.serialized)

    @auth.required()
    def delete(self, id):
        svc = services.get(id)
        if id and not svc:
            abort(404)
        svc.remove()
        return Response(status=204)


services_view = ServicesAPI.as_view('services_api')
backend.add_url_rule('/api/system/services', defaults={'id': None},
    view_func=services_view, methods=['GET',])
backend.add_url_rule('/api/system/services', view_func=services_view, methods=['POST',])
backend.add_url_rule('/api/system/services/<string:id>', view_func=services_view,
    methods=['GET', 'PUT', 'DELETE'])
