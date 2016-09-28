"""
Endpoints for management of filesystems.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos.messages import Notification, NotificationThread
from arkos.system import filesystems

from kraken import auth
from kraken.records import push_record
from kraken.jobs import as_job, job_response

backend = Blueprint("filesystems", __name__)


class DisksAPI(MethodView):
    @auth.required()
    def get(self, id):
        disks = filesystems.get(id)
        if id and not disks:
            abort(404)
        if type(disks) == list:
            return jsonify(filesystems=[x.serialized for x in disks])
        else:
            return jsonify(filesystem=disks.serialized)

    @auth.required()
    def post(self):
        data = request.get_json()["filesystem"]
        id = as_job(self._post, data)
        return job_response(id, data={"filesystem": data})

    def _post(self, job, data):
        nthread = NotificationThread(id=job.id)
        disk = filesystems.VirtualDisk(id=data["id"], size=data["size"])
        disk.create(will_crypt=data["crypt"], nthread=nthread)
        if data["crypt"]:
            try:
                msg = "Encrypting virtual disk..."
                nthread.update(Notification("info", "Filesystems", msg))
                disk.encrypt(data["passwd"])
            except Exception as e:
                disk.remove()
                raise
            msg = "Virtual disk created successfully"
            nthread.complete(Notification("success", "Filesystems", msg))
        push_record("filesystem", disk.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["filesystem"]
        disk = filesystems.get(id)
        if not id or not disk:
            abort(404)
        try:
            if data["operation"] == "mount":
                op = "mounted"
                if disk.mountpoint:
                    abort(400)
                elif disk.crypt and not data.get("passwd"):
                    abort(403)
                elif data.get("mountpoint"):
                    disk.mountpoint = data["mountpoint"]
                disk.mount(data.get("passwd"))
            elif data["operation"] == "umount":
                op = "unmounted"
                disk.umount()
            elif data["operation"] == "enable":
                op = "enabled"
                disk.enable()
            elif data["operation"] == "disable":
                op = "disabled"
                disk.disable()
        except Exception as e:
            resp = jsonify(message="Operation failed: {0}".format(str(e)))
            resp.status_code = 422
            return resp
        return jsonify(filesystem=disk.serialized,
                       message="Disk {0} successfully".format(op))

    @auth.required()
    def delete(self, id):
        disk = filesystems.get(id)
        if not id or not disk:
            abort(404)
        disk.remove()
        return Response(status=204)


@backend.route('/api/points')
@auth.required()
def list_points():
    return jsonify(points=[x.serialized for x in filesystems.get_points()])

disks_view = DisksAPI.as_view('disks_api')
backend.add_url_rule('/api/system/filesystems', defaults={'id': None},
                     view_func=disks_view, methods=['GET', ])
backend.add_url_rule('/api/system/filesystems', view_func=disks_view,
                     methods=['POST', ])
backend.add_url_rule('/api/system/filesystems/<string:id>',
                     view_func=disks_view, methods=['GET', 'PUT', 'DELETE'])
