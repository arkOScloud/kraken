"""
Endpoints for management of arkOS Applications.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import os

from flask import Blueprint, abort, jsonify, request, send_from_directory
from flask.views import MethodView

from arkos import applications
from arkos.messages import NotificationThread

from kraken import auth
from kraken.records import push_record
from kraken.jobs import as_job, job_response

backend = Blueprint("apps", __name__)


class ApplicationsAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            applications.scan()
        installed = request.args.get("installed", None)
        if installed and installed.lower() == "true":
            installed = True
        elif installed and installed.lower() == "false":
            installed = False
        apps = applications.get(
            id, type=request.args.get("type", None),
            loadable=request.args.get("loadable", None),
            installed=installed,
            cry=False)
        if id and not apps:
            abort(404)
        if type(apps) == list:
            return jsonify(apps=[x.serialized for x in apps])
        else:
            return jsonify(app=apps.serialized)

    @auth.required()
    def put(self, id):
        operation = request.get_json()["app"]["operation"]
        app = applications.get(id)
        if not app:
            abort(404)
        if operation == "install":
            if app.installed and not getattr(app, "upgradable", None):
                return jsonify(app=app.serialized)
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
        data = app.serialized
        data["is_ready"] = False
        return job_response(id, {"app": data})

    def _install(self, job, app):
        nthread = NotificationThread(id=job.id)
        app.install(nthread=nthread, force=True, cry=False)
        push_record("app", app.serialized)

    def _uninstall(self, job, app):
        nthread = NotificationThread(id=job.id)
        app.uninstall(nthread=nthread)
        push_record("app", app.serialized)


@auth.required()
def dispatcher(id, path):
    a = applications.get(id)
    if not a or not hasattr(a, "_api"):
        abort(404)
    params = path.split("/")
    fn = getattr(a._api, params[0])
    return fn(*params[1:])


@backend.route('/api/apps/assets/<string:id>/<string:asset>')
def get_app_asset(id, asset):
    app = applications.get(id)
    if not app:
        abort(404)
    return send_from_directory(
        os.path.join('/var/lib/arkos/applications', id, 'assets'), asset)


apps_view = ApplicationsAPI.as_view('apps_api')
backend.add_url_rule('/api/apps', defaults={'id': None},
                     view_func=apps_view, methods=['GET', ])
backend.add_url_rule('/api/apps/<string:id>', view_func=apps_view,
                     methods=['GET', 'PUT'])
backend.add_url_rule('/api/apps/<string:id>/<path:path>', view_func=dispatcher,
                     methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
