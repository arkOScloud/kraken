import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications
from kraken.messages import Message

backend = Blueprint("apps", __name__)


class ApplicationsAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            applications.scan()
        apps = applications.get(id)
        if id and not apps:
            abort(404)
        if type(apps) == list:
            return jsonify(applications=[x.as_dict() for x in apps])
        else:
            return jsonify(application=apps.as_dict())
    
    def post(self):
        data = json.loads(request.body)["available_app"]
        message = Message()
        try:
            applications.install(data["id"], message=message)
            message.complete("success", "%s installed successfully" % data["name"])
            return self.get(None)
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (data["name"], str(e)))
            abort(500)
    
    def delete(self, id):
        message = Message()
        app = applications.get(id)
        if not app:
            abort(404)
        try:
            app.uninstall(message=message)
            message.complete("success", "%s uninstalled successfully" % app.name)
            return self.get(None)
        except Exception, e:
            message.complete("error", "%s could not be uninstalled: %s" % (data["name"], str(e)))
            abort(500)


@backend.route('/apps/available/')
def list_available(data):
    if request.args.get("rescan", None):
        applications.scan_available()
    return jsonify(available_apps=[x.as_dict() for x in applications.get_available()])

@backend.route('/apps/updatable/')
def list_updatable(data):
    if request.args.get("rescan", None):
        applications.scan_updatable()
    return jsonify(updatable_apps=[x.as_dict() for x in applications.get_updatable()])


apps_view = ApplicationsAPI.as_view('apps_api')
backend.add_url_rule('/apps/', defaults={'id': None}, 
    view_func=apps_view, methods=['GET',])
backend.add_url_rule('/apps/', view_func=apps_view, methods=['POST',])
backend.add_url_rule('/apps/<int:id>', view_func=apps_view, 
    methods=['GET', 'DELETE'])
