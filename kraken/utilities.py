import base64
import hashlib
import platform
import random
import traceback

from flask import current_app, Response, jsonify, request

from arkos import config, version
from arkos import storage as arkos_storage
from arkos.utilities import api, shell, random_string
from arkos.utilities.errors import RequestError
from werkzeug.exceptions import default_exceptions, HTTPException


def genAPIKey():
    return base64.b64encode(hashlib.sha256(str(random.getrandbits(256))).digest(),
        random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')

def make_json_error(err):
    if hasattr(err, "description"):
        message = err.description
    else:
        message = str(err)
    if (isinstance(err, HTTPException) and err.code == 500) \
    or not isinstance(err, HTTPException):
        apps = [x.id for x in arkos_storage.apps.get("applications") if x.installed]
        stacktrace = traceback.format_exc()
        report = "arkOS %s Crash Report\n" % version
        report += "--------------------\n\n"
        report += "Running in %s\n" % config.get("enviro", "run")
        report += "System: %s\n" % shell("uname -a")["stdout"]
        report += "Platform: %s %s\n" % (config.get("enviro", "arch"), config.get("enviro", "board"))
        report += "Python version %s\n" % '.'.join([str(x) for x in platform.python_version_tuple()])
        report += "Config path: %s\n\n" % config.filename
        report += "Loaded applicatons: \n%s\n\n" % "\n".join(apps)
        report += "Request: %s %s\n\n" % (request.method, request.path)
        report += stacktrace
        response = jsonify(message=message, stacktrace=stacktrace,
            report=report, version=version, arch=config.get("enviro", "arch"))
    else:
        response = jsonify(message=message)
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return add_cors_to_response(response)

def add_cors_to_response(resp):
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'PATCH, PUT, POST, OPTIONS, GET, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Origin, X-Requested-With, Accept, DNT, Cache-Control, Accept-Encoding, Content-Type'
    return resp
