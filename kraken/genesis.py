"""
Functions for management of Genesis integration.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import json
import os

from arkos import config, applications
from arkos.utilities import shell
from flask import Blueprint, jsonify, send_from_directory

backend = Blueprint("genesis", __name__)
DEBUG = False


def genesis(path):
    """Serve Genesis components via the API."""
    gpath = '/var/lib/arkos/genesis'
    if path and not path.startswith(("assets", "public", "fonts", "img")):
        path = None
    if config.get("enviro", "run") == "vagrant":
        vpath = '/home/vagrant/genesis/dist'
        if os.path.exists(vpath):
            return send_from_directory(vpath, path or 'index.html',
                                       cache_timeout=0)
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        sdir = os.path.abspath(os.path.join(sdir, '../../genesis/dist'))
        return send_from_directory(sdir, path or 'index.html', cache_timeout=0)
    elif os.path.exists(gpath):
        return send_from_directory(gpath, path or 'index.html',
                                   cache_timeout=0)
    else:
        resp = jsonify(message="Genesis does not appear to be installed.")
        resp.status_code = 500
        return resp


def genesis_init(state):
    """Initialize the Genesis endpoints."""
    path = ""
    if config.get("enviro", "run") == "vagrant":
        path = '/home/vagrant/genesis'
        genesis_build()
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.abspath(os.path.join(sdir, '../../genesis'))
        genesis_build()
    elif os.path.exists('/var/lib/arkos/genesis'):
        path = '/var/lib/arkos/genesis'
    if not os.path.exists(path):
        return
    backend.add_url_rule('/', defaults={'path': None}, view_func=genesis,
                         methods=['GET', ])
    backend.add_url_rule('/<path:path>', view_func=genesis, methods=['GET', ])


def genesis_build():
    """Build Genesis from source."""
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
        genpath = "/var/lib/arkos/applications/{0}/genesis".format(x.id)
        if os.path.exists(genpath):
            libpaths.append("lib/{0}".format(x.id))
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
    s = shell("ember build{0}".format(" -prod" if not DEBUG else ""))
    os.chdir(mydir)
    if s["code"] != 0:
        raise Exception("Genesis rebuild process failed")


backend.record(genesis_init)
