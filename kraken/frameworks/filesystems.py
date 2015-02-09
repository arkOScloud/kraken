import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos.system import filesystems
from kraken.messages import Message, push_record
from kraken.utilities import as_job, job_response

backend = Blueprint("filesystems", __name__)


class DisksAPI(MethodView):
    def get(self, id):
        disks, vdisks = filesystems.get_disk_partitions(), filesystems.get_virtual_disks()
        if id:
            for x in disks:
                if x.name == id:
                    return jsonify(disk_partition=x.as_dict())
            for x in vdisks:
                if x.name == id:
                    return jsonify(virtual_disk=x.as_dict())
            abort(404)
        if not disks+vdisks:
            abort(404)
        return jsonify(disk_partitions=[x.as_dict() for x in disks],
            virtual_disks=[x.as_dict() for x in vdisks])
    
    def post(self):
        data = json.loads(request.body)["virtual_disk"]
        id = as_job(_post, self, data)
        return job_response(id)
    
    def _post(self, data):
        message = Message()
        message.update("info", "Creating virtual disk...")
        disk = filesystems.VirtualDisk(name=data["name"], size=data["size"])
        try:
            disk.create()
        except Exception, e:
            message.complete("error", "Virtual disk could not be created: %s" % str(e))
            raise
        if data["encrypt"]:
            try:
                message.update("info", "Encrypting virtual disk...")
                disk.encrypt(data["passwd"])
            except Exception, e:
                disk.remove()
                message.complete("error", "Virtual disk could not be encrypted: %s" % str(e))
                raise
        push_record("virtual_disk", disk.as_dict())
    
    def put(self, id):
        data = json.loads(request.body)
        if data.get("virtual_disk"):
            stype = "virtual_disk"
            data = data.get("virtual_disk")
            disk = filesystems.get_virtual_disks(id)
        else:
            stype = "disk_partition"
            data = data.get("disk_partition")
            disk = filesystems.get_disk_partitions(id)
        if not id or not disk:
            abort(404)
        if data["operation"] == "mount":
            if disk.mountpoint:
                abort(400)
            elif disk.crypt and not data.get("passwd"):
                abort(403)
            elif data.get("mountpoint"):
                disk.mountpoint = data["mountpoint"]
            disk.mount(data.get("passwd"))
        elif data["operation"] == "umount":
            disk.umount()
        if stype == "virtual_disk":
            return jsonify(virtual_disk=disk.as_dict())
        else:
            return jsonify(disk_partition=disk.as_dict())
    
    def delete(self, id):
        disk = filesystems.get_virtual_disks(id)
        if not id or not disk:
            abort(404)
        disk.remove()
        return Response(status=204)


@backend.route('/points/')
def list_points():
    return jsonify(points=[x.as_dict() for x in filesystems.get_points()])

disks_view = DisksAPI.as_view('disks_api')
backend.add_url_rule('/system/disks/', defaults={'id': None}, 
    view_func=disks_view, methods=['GET',])
backend.add_url_rule('/system/disks/', view_func=disks_view, methods=['POST',])
backend.add_url_rule('/system/disks/<string:id>', view_func=disks_view, 
    methods=['GET', 'PUT', 'DELETE'])
