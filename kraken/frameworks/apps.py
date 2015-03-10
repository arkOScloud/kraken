import json
import os

from flask import Response, Blueprint, abort, jsonify, request, send_from_directory
from flask.views import MethodView

from arkos import applications
from kraken.messages import Message, push_record
from kraken.utilities import as_job, job_response

backend = Blueprint("apps", __name__)


class ApplicationsAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            applications.scan()
        apps = applications.get(id, type=request.args.get("type", None), 
            loadable=request.args.get("loadable", None),
            installed=request.args.get("installed", None))
        if id and not apps:
            abort(404)
        if type(apps) == list:
            return jsonify(apps=[x.as_dict() for x in apps])
        else:
            return jsonify(app=apps.as_dict())
    
    def put(self, id):
        operation = json.loads(request.data)["app"]["operation"]
        app = applications.get(id)
        if not app:
            abort(404)
        if operation == "install":
            id = as_job(self._install, app)
        elif operation == "uninstall":
            if not app.installed:
                resp = jsonify(message="Application isn't yet installed")
                resp.status_code = 422
                return resp
            id = as_job(self._uninstall, app)
        else:
            resp = jsonify(message="Unknown operation specified")
            resp.status_code = 422
            return resp
        data = app.as_dict()
        data["is_ready"] = False
        return job_response(id, {"app": data})
    
    def _install(self, app):
        message = Message()
        try:
            app.install(message=message)
            message.complete("success", "%s installed successfully" % app.name)
            push_record("app", app.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (app.name, str(e)))
            raise
    
    def _uninstall(self, app):
        message = Message()
        try:
            app.uninstall(message=message)
            message.complete("success", "%s uninstalled successfully" % app.name)
            push_record("app", app.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be uninstalled: %s" % (app.name, str(e)))
            raise


apps_view = ApplicationsAPI.as_view('apps_api')
backend.add_url_rule('/apps', defaults={'id': None}, 
    view_func=apps_view, methods=['GET',])
backend.add_url_rule('/apps/<string:id>', view_func=apps_view, 
    methods=['GET', 'PUT', 'DELETE'])

@backend.route('/apps/logo/<string:id>')
def get_app_logo(id):
    app = applications.get(id)
    if not app:
        abort(404)
    return send_from_directory(os.path.join('/var/lib/arkos/applications', id, 'assets'), "logo.png")

applications.get()
