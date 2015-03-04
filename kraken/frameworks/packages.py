import json
import pacman

from flask import Response, Blueprint, jsonify, request, abort
from flask.views import MethodView
from kraken.utilities import as_job, job_response
from kraken.messages import Message

backend = Blueprint("packages", __name__)


class PackagesAPI(MethodView):
    def get(self, id):
        if id:
            try:
                data = {}
                info = pacman.get_info(id)
                for x in info:
                    data[x.lower().replace(" ", "_")] = info[x]
                return jsonify(package=data)
            except:
                abort(404)
        else:
            return jsonify(packages=pacman.get_installed())
    
    def post(self):
        install, remove = [], []
        data = json.loads(request.data)["packages"]
        for x in data:
            if x["operation"] == "install":
                install.append(x["id"])
            elif x["operation"] == "remove":
                remove.append(x["id"])
        id = as_job(self._operation, install, remove)
        return job_response(id)
    
    def _operation(self, install, remove):
        message = Message()
        if install:
            try:
                pacman.refresh()
                prereqs = pacman.needs_for(install)
                message.update("info", "Installing %s package(s): %s" % (len(prereqs), ', '.join(prereqs)))
                pacman.install(install)
            except Exception, e:
                message.complete("error", str(e))
                return
        if remove:
            try:
                prereqs = pacman.depends_for(remove)
                message.update("info", "Removing %s package(s): %s" % (len(prereqs), ', '.join(prereqs)))
                pacman.remove(remove)
            except Exception, e:
                message.complete("error", str(e))
                return
        message.complete("success", "Operations completed successfully")


packages_view = PackagesAPI.as_view('sites_api')
backend.add_url_rule('/system/packages', defaults={'id': None}, 
    view_func=packages_view, methods=['GET',])
backend.add_url_rule('/system/packages', view_func=packages_view, methods=['POST',])
backend.add_url_rule('/system/packages/<string:id>', view_func=packages_view, 
    methods=['GET',])

@backend.route('/system/packages/available', defaults={'id': None}, methods=["GET",])
@backend.route('/system/packages/available/<string:id>', methods=["GET",])
def get_available(id):
    if id:
        try:
            data = {}
            info = pacman.get_info(id, False)
            for x in info:
                data[x.lower().replace(" ", "_")] = info[x]
            return jsonify(package=data)
        except:
            abort(404)
    else:
        return jsonify(packages=pacman.get_available())
