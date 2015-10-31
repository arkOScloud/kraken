import glob
import os

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos.system import users

backend = Blueprint("ssh", __name__)


class SSHKeysAPI(MethodView):
    @auth.required()
    def get(self, id):
        keys = []
        kfiles = glob.glob("/home/*/.ssh/authorized_keys")
        for x in kfiles:
            user = x.split("/")[2]
            with open(x, "r") as f:
                data = f.readlines()
            for y in data:
                y = y.rstrip("\n")
                if not y.split():
                    continue
                try:
                    key = {"id": user+"-"+y.split()[1][:10], "user": user, "key": y}
                except IndexError:
                    continue
                if id and key["id"] == id:
                    return jsonify(ssh_key=key)
                keys.append(key)
        if id:
            abort(404)
        return jsonify(ssh_keys=keys)

    @auth.required()
    def post(self):
        data = request.get_json()["ssh_key"]
        key = {"user": data["user"], "key": data["key"]}
        user = users.get(name=key["user"])
        if not os.path.exists("/home/%s/.ssh" % data["user"]):
            os.makedirs("/home/%s/.ssh" % data["user"])
            os.chown("/home/%s/.ssh" % data["user"], user.uid, 100)
            os.chmod("/home/%s/.ssh" % data["user"], 0700)
        if not os.path.exists("/home/%s/.ssh/authorized_keys" % data["user"]):
            with open("/home/%s/.ssh/authorized_keys" % data["user"], "w") as f:
                f.write(data["key"])
                if not data["key"].endswith("\n"):
                    f.write("\n")
            key["id"] = key["user"]+"-"+data["key"].split()[1][:10]
            os.chown("/home/%s/.ssh/authorized_keys" % key["user"], user.uid, 100)
            os.chmod("/home/%s/.ssh/authorized_keys" % key["user"], 0600)
        else:
            with open("/home/%s/.ssh/authorized_keys" % data["user"], "r+") as f:
                fc = f.read()
                if fc and not fc.endswith("\n"):
                    f.write("\n")
                f.write(data["key"])
                if not data["key"].endswith("\n"):
                    f.write("\n")
                f.seek(0)
                key["id"] = key["user"]+"-"+data["key"].split()[1][:10]
        return jsonify(ssh_key=key, message="SSH key for %s added successfully" % data["user"])

    @auth.required()
    def delete(self, id):
        user, ldat = id.rsplit("-", 1)
        if not glob.glob("/home/%s/.ssh/authorized_keys" % user):
            abort(404)
        with open("/home/%s/.ssh/authorized_keys" % user, "r") as f:
            data = []
            for x in f.readlines():
                if x.split() and ldat == x.split()[1][:10]:
                    continue
                data.append(x)
        with open("/home/%s/.ssh/authorized_keys" % user, "w") as f:
            f.writelines(data)
        return Response(status=204)


ssh_view = SSHKeysAPI.as_view('ssh_api')
backend.add_url_rule('/api/system/ssh_keys', defaults={'id': None},
    view_func=ssh_view, methods=['GET',])
backend.add_url_rule('/api/system/ssh_keys', view_func=ssh_view, methods=['POST',])
backend.add_url_rule('/api/system/ssh_keys/<string:id>', view_func=ssh_view,
    methods=['GET', 'DELETE'])
