"""
Endpoints for management of SSH keys.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

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
                if len(y.split()) == 3:
                    key = {
                        "id": user+"-"+y.split()[-1],
                        "user": user, "key": y
                    }
                else:
                    try:
                        key = {
                            "id": user+"-"+y.split()[1][:10],
                            "user": user, "key": y
                        }
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
        ssh_path = "/home/{0}/.ssh".format(data["user"])
        akeys_path = os.path.join(ssh_path, "authorized_keys")
        if not os.path.exists(ssh_path):
            os.makedirs(ssh_path)
            os.chown(ssh_path, user.uid, 100)
            os.chmod(ssh_path, 0o700)
        if not os.path.exists(akeys_path):
            with open(akeys_path, "w") as f:
                f.write(data["key"])
                if not data["key"].endswith("\n"):
                    f.write("\n")
            if len(data["key"].split()) == 3:
                key["id"] = key["user"]+"-"+data["key"].split()[-1]
            else:
                key["id"] = key["user"]+"-"+data["key"].split()[1][:10]
            os.chown(akeys_path, user.uid, 100)
            os.chmod(akeys_path, 0o600)
        else:
            with open(akeys_path, "r+") as f:
                fc = f.read()
                if fc and not fc.endswith("\n"):
                    f.write("\n")
                f.write(data["key"])
                if not data["key"].endswith("\n"):
                    f.write("\n")
                f.seek(0)
                if len(data["key"].split()) == 3:
                    key["id"] = key["user"]+"-"+data["key"].split()[-1]
                else:
                    key["id"] = key["user"]+"-"+data["key"].split()[1][:10]
        return jsonify(ssh_key=key)

    @auth.required()
    def delete(self, id):
        user, ldat = id.split("-", 1)
        akeys_path = "/home/{0}/.ssh/authorized_keys".format(user)
        if not glob.glob(akeys_path):
            abort(404)
        with open(akeys_path, "r") as f:
            data = []
            for x in f.readlines():
                if x.split() and (
                        ldat == x.split()[1][:10] or ldat == x.split()[-1]
                        ):
                    continue
                data.append(x)
        with open(akeys_path, "w") as f:
            f.writelines(data)
        return Response(status=204)


ssh_view = SSHKeysAPI.as_view('ssh_api')
backend.add_url_rule('/api/system/ssh_keys', defaults={'id': None},
    view_func=ssh_view, methods=['GET',])
backend.add_url_rule('/api/system/ssh_keys', view_func=ssh_view, methods=['POST',])
backend.add_url_rule('/api/system/ssh_keys/<string:id>', view_func=ssh_view,
    methods=['GET', 'DELETE'])
