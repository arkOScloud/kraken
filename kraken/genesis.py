"""
Functions for management of Genesis integration.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import os

from arkos import config
from flask import Blueprint, jsonify, send_from_directory

backend = Blueprint("genesis", __name__)


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
        resp = jsonify(
            errors={"msg": "Genesis does not appear to be installed."}
        )
        resp.status_code = 500
        return resp


def genesis_init(state):
    """Initialize the Genesis endpoints."""
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
                         methods=['GET', ])
    backend.add_url_rule('/<path:path>', view_func=genesis, methods=['GET', ])


def verify_genesis():
    if config.get("enviro", "run") == "vagrant":
        vpath = '/home/vagrant/genesis/dist'
    elif config.get("enviro", "run") == "dev":
        vpath = os.path.dirname(os.path.realpath(__file__))
        vpath = os.path.abspath(os.path.join(vpath, '../../genesis/dist'))
    else:
        vpath = '/var/lib/arkos/genesis'
    if not os.path.exists(vpath):
        return False
    return True


backend.record(genesis_init)
