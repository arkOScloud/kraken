"""
Endpoints for management of system packages.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import pacman

from flask import Blueprint, jsonify, request, abort
from flask.views import MethodView

from arkos.messages import Notification, NotificationThread

from kraken import auth
from kraken.jobs import as_job, job_response
from kraken.records import push_record

backend = Blueprint("packages", __name__)


class PackagesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("refresh", False):
            pacman.refresh()
        if id:
            try:
                info = process_info(pacman.get_info(id))
                return jsonify(package=info)
            except:
                abort(404)
        else:
            return jsonify(packages=pacman.get_all())

    @auth.required()
    def post(self):
        install, remove = [], []
        data = request.get_json()["packages"]
        for x in data:
            if x["operation"] == "install":
                install.append(x["id"])
            elif x["operation"] == "remove":
                remove.append(x["id"])
        id = as_job(self._operation, install, remove)
        return job_response(id)

    def _operation(self, job, install, remove):
        if install:
            try:
                pacman.refresh()
                prereqs = pacman.needs_for(install)
                title = "Installing {0} package(s)".format(len(prereqs))
                msg = Notification("info", "Packages", ", ".join(prereqs))
                nthread = NotificationThread(
                    id=job.id, title=title, message=msg)
                pacman.install(install)
                for x in prereqs:
                    try:
                        info = process_info(pacman.get_info(x))
                        if "installed" not in info:
                            info["installed"] = True
                        push_record("package", info)
                    except:
                        pass
            except Exception as e:
                nthread.complete(Notification("error", "Packages", str(e)))
                return
        if remove:
            try:
                prereqs = pacman.depends_for(remove)
                title = "Removing {0} package(s)".format(len(prereqs))
                msg = Notification("info", "Packages", ", ".join(prereqs))
                nthread = NotificationThread(
                    id=job.id, title=title, message=msg)
                pacman.remove(remove)
                for x in prereqs:
                    try:
                        info = process_info(pacman.get_info(x))
                        if "installed" not in info:
                            info["installed"] = False
                        push_record("package", info)
                    except:
                        pass
            except Exception as e:
                nthread.complete(Notification("error", "Packages", str(e)))
                return
        msg = "Operations completed successfully"
        nthread.complete(Notification("success", "Packages", msg))


def process_info(info):
    data = {}
    for x in info:
        if x == "Name":
            data["id"] = info["Name"]
            continue
        data[x.lower().replace(" ", "_")] = info[x]
    if "upgradable" not in data:
        data["upgradable"] = False
    return data


packages_view = PackagesAPI.as_view('sites_api')
backend.add_url_rule('/api/system/packages', defaults={'id': None},
                     view_func=packages_view, methods=['GET', ])
backend.add_url_rule('/api/system/packages', view_func=packages_view,
                     methods=['POST', ])
backend.add_url_rule('/api/system/packages/<string:id>',
                     view_func=packages_view, methods=['GET', ])
