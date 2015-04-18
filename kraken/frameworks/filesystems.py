import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos.system import filesystems
from kraken.messages import Message, push_record
from kraken.utilities import as_job, job_response

backend = Blueprint("filesystems", __name__)


class DisksAPI(MethodView):
    @auth.required()
    def get(self, id):
        disks = filesystems.get(id)
        if id and not disks:
            abort(404)
        if type(disks) == list:
            return jsonify(filesystems=[x.as_dict() for x in disks])
        else:
            return jsonify(filesystem=disks.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["filesystem"]
        id = as_job(self._post, data)
        return job_response(id, data={"filesystem": data})
    
    def _post(self, data):
        message = Message()
        message.update("info", "Creating virtual disk...")
        disk = filesystems.VirtualDisk(id=data["id"], size=data["size"])
        try:
            disk.create()
        except Exception, e:
            message.complete("error", "Virtual disk could not be created: %s" % str(e))
            raise
        if data["crypt"]:
            try:
                message.update("info", "Encrypting virtual disk...")
                disk.encrypt(data["passwd"])
            except Exception, e:
                disk.remove()
                message.complete("error", "Virtual disk could not be encrypted: %s" % str(e))
                raise
        message.complete("success", "Virtual disk created successfully")
        push_record("filesystem", disk.as_dict())
    
    @auth.required()
    def put(self, id):
        data = json.loads(request.data)["filesystem"]
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
        except Exception, e:
            resp = jsonify(message="Operation failed: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(filesystem=disk.as_dict(), message="Disk %s successfully"%op)
    
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
    return jsonify(points=[x.as_dict() for x in filesystems.get_points()])

disks_view = DisksAPI.as_view('disks_api')
backend.add_url_rule('/api/system/filesystems', defaults={'id': None}, 
    view_func=disks_view, methods=['GET',])
backend.add_url_rule('/api/system/filesystems', view_func=disks_view, methods=['POST',])
backend.add_url_rule('/api/system/filesystems/<string:id>', view_func=disks_view, 
    methods=['GET', 'PUT', 'DELETE'])
