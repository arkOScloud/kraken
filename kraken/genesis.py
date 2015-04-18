import json
import os

from kraken import auth
from arkos import config, applications
from arkos.utilities import shell
from flask import Blueprint, jsonify, send_from_directory

backend = Blueprint("genesis", __name__)
DEBUG = False


def genesis(path):
    if path and not path.startswith(("assets", "public", "fonts", "img")):
        path = None
    if config.get("enviro", "run") == "vagrant":
        if os.path.exists('/home/vagrant/genesis/dist'):
            return send_from_directory('/home/vagrant/genesis/dist', path or 'index.html')
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        sdir = os.path.abspath(os.path.join(sdir, '../../genesis/dist'))
        return send_from_directory(sdir, path or 'index.html')
    elif os.path.exists('/var/lib/arkos/genesis/dist'):
        return send_from_directory('/var/lib/arkos/genesis/dist', path or 'index.html')
    else:
        resp = jsonify(message="Genesis does not appear to be installed.")
        resp.status_code = 500
        return resp

def genesis_init(state):
    path = ""
    if config.get("enviro", "run") == "vagrant":
        path = '/home/vagrant/genesis'
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.abspath(os.path.join(sdir, '../../genesis'))
    elif os.path.exists('/var/lib/arkos/genesis'):
        path = '/var/lib/arkos/genesis'
    if not os.path.exists(path):
        return
    backend.add_url_rule('/', defaults={'path': None}, view_func=genesis, 
        methods=['GET',])
    backend.add_url_rule('/<path:path>', view_func=genesis, methods=['GET',])
    genesis_build()

def genesis_build():
    if config.get("enviro", "run") == "vagrant":
        path = '/home/vagrant/genesis'
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.abspath(os.path.join(sdir, '../../genesis'))
    else:
        path = '/var/lib/arkos/genesis'
    if not os.path.exists(os.path.join(path, 'lib')):
        os.makedirs(os.path.join(path, 'lib'))
    for x in os.listdir(os.path.join(path, 'lib')):
        if os.path.islink(os.path.join(path, 'lib', x)):
            os.unlink(os.path.join(path, 'lib', x))
    libpaths = []
    apps = applications.get()
    for x in apps:
        genpath = "/var/lib/arkos/applications/%s/genesis" % x.id
        if os.path.exists(genpath):
            libpaths.append("lib/%s"%x.id)
            os.symlink(genpath, os.path.join(path, 'lib', x.id))
    if libpaths:
        with open(os.path.join(path, 'package.json'), 'r') as f:
            data = json.loads(f.read())
        data["ember-addon"] = {"paths": libpaths}
        with open(os.path.join(path, 'package.json'), 'w') as f:
            f.write(json.dumps(data, sort_keys=True, 
                indent=2, separators=(',', ': ')))
    mydir = os.getcwd()
    os.chdir(path)
    s = shell("ember build%s" % (" -prod" if DEBUG else ""))
    os.chdir(mydir)
    if s["code"] != 0:
        raise Exception("Genesis rebuild process failed")


backend.record(genesis_init)
