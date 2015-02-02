import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications
from kraken.messages import Message, update_model
from kraken.utilities import as_job, job_response

backend = Blueprint("apps", __name__)


class ApplicationsAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            applications.scan()
        apps = applications.get(id)
        if id and not apps:
            abort(404)
        if type(apps) == list:
            return jsonify(apps=[x.as_dict() for x in apps])
        else:
            return jsonify(app=apps.as_dict())
    
    def post(self):
        data = json.loads(request.body)["available_app"]
        app = applications.get_available(data["id"])
        if not app:
            abort(404)
        id = as_job(_post, self, app)
        return job_response(id)
    
    def _post(self, app):
        message = Message()
        try:
            applications.install(app["id"], message=message)
            message.complete("success", "%s installed successfully" % app["name"])
            update_model("applications", applications.get())
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (app["name"], str(e)))
            raise
    
    def delete(self, id):
        app = applications.get(id)
        if not app:
            abort(404)
        id = as_job(_delete, self, app, success_code=204)
        return job_response(id)
    
    def _delete(self, app):
        message = Message()
        try:
            app.uninstall(message=message)
            message.complete("success", "%s uninstalled successfully" % app.name)
        except Exception, e:
            message.complete("error", "%s could not be uninstalled: %s" % (app.name, str(e)))
            raise


@backend.route('/apps/available/')
def list_available():
    if request.args.get("rescan", None):
        applications.scan_available()
    return jsonify(available_apps=[x.as_dict() for x in applications.get_available()])

@backend.route('/apps/updatable/')
def list_updatable():
    if request.args.get("rescan", None):
        applications.scan_updatable()
    return jsonify(updatable_apps=[x.as_dict() for x in applications.get_updatable()])


apps_view = ApplicationsAPI.as_view('apps_api')
backend.add_url_rule('/apps/', defaults={'id': None}, 
    view_func=apps_view, methods=['GET',])
backend.add_url_rule('/apps/', view_func=apps_view, methods=['POST',])
backend.add_url_rule('/apps/<string:id>', view_func=apps_view, 
    methods=['GET', 'DELETE'])

# TODO fix
applications.get()
#applications.get_available()
#applications.get_updatable()
