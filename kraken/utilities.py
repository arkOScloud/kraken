"""
Utility functions.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import platform
import random
import traceback

from flask import jsonify, request

from arkos import config, logger, version
from arkos import storage as arkos_storage
from arkos.utilities import shell
from werkzeug.exceptions import HTTPException


def genAPIKey():
    """Generate an API key."""
    rep = random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD']).encode()
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(str(random.getrandbits(256)).encode())
    final = digest.finalize()
    return base64.b64encode(final, rep).decode('utf-8').rstrip('==')

def make_json_error(err):
    """Prepare a standardized error report."""
    if hasattr(err, "description"):
        message = err.description
    else:
        message = str(err)
    if (isinstance(err, HTTPException) and err.code == 500)\
            or not isinstance(err, HTTPException):
        pyver = [str(x) for x in platform.python_version_tuple()]
        apps = arkos_storage.apps.get("applications")
        apps = [x.id for x in apps if x.installed]
        stacktrace = traceback.format_exc()
        report = "arkOS {0} Crash Report\n".format(version)
        report += "--------------------\n\n"
        report += "Running in {0}\n".format(config.get("enviro", "run"))
        report += "System: {0}\n".format(shell("uname -a")["stdout"].decode())
        report += "Platform: {0} {1}\n".format(config.get("enviro", "arch"),
                                               config.get("enviro", "board"))
        report += "Python version {0}\n".format('.'.join(pyver))
        report += "Config path: {0}\n\n".format(config.filename)
        report += "Loaded applicatons: \n{0}\n\n".format("\n".join(apps))
        report += "Request: {0} {1}\n\n".format(request.method, request.path)
        report += stacktrace
        response = jsonify(errors={"msg": message, "stack": stacktrace,
                           "report": report, "version": version,
                           "arch": config.get("enviro", "arch")})
        logger.critical("Unknown", stacktrace)
    else:
        response = jsonify(errors={"msg": message})
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return add_cors_to_response(response)


def add_cors_to_response(resp):
    """Add all-origin CORS to the provided response."""
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'PATCH, PUT, POST, OPTIONS, GET, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Origin, X-Requested-With, Accept, DNT, Cache-Control, Accept-Encoding, Content-Type'
    return resp
